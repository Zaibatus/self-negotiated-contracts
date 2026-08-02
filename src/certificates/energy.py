"""Anchor-free net-gain energy — the convergence layer.

Zusai (arXiv:1805.04898): cost-benefit rationalizable agents revise only when
the best available payoff improvement, net of friction, is positive. So the
move an agent still chooses to make *is* a measurement of its remaining net
gain, and the aggregate net gain

    G(x) = sum_i g_i(x),     NE = { x : G(x) = 0 }

is an energy whose zero set is the (frictional) Nash set — with no anchor.
That matters because under coupling the agreement point moves to the
generalised Nash equilibrium, which has no closed form: a certificate
V(x) = ||x - x*||^2 anchored at a guessed x* plateaus at exactly its own
squared anchor error (measured: 510.3 against 509.9 predicted), while G goes
to zero at the equilibrium wherever it turns out to be.

Two operational definitions are implemented, per formulation.md section 5.2:

  1. ``g_realised`` — realised round-pair displacement ||x_{k+2} - x_k||^2.
     Assumption-free and model-free, so it is the one that survives contact
     with LLM agents whose decision rules we cannot open. Noisy.
  2. ``g_lookahead`` — squared displacement of a deterministic two-round
     rollout of a fitted concession model *through the safety filter*. Putting
     the filter inside the lookahead is what makes G's zero set the
     *constrained* equilibrium automatically.

The payoff-based third definition (full Zusai, in utility units) remains the
calibration target and is deliberately not faked here: converting term-unit
energies to payoff units is an open task, not an oversight.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..contract import Contract
from .dcbf import DCBFFilter

# --------------------------------------------------------------------------
# 1. Realised displacement — assumption-free
# --------------------------------------------------------------------------


def g_realised(trajectory: list[np.ndarray], k: int) -> float:
    """Revealed remaining net gain at round k: ||x_{k+2} - x_k||^2.

    A round-*pair*, because one round is a single agent's move and the energy
    is over the joint revision. Requires both sides' moves to be observable;
    in Magentic that is what buyer-side term extraction buys us.

    Raises IndexError if the pair is not complete, rather than silently
    substituting a shorter window and reporting a smaller energy.
    """
    if k < 0 or k + 2 >= len(trajectory):
        raise IndexError(
            f"round-pair at k={k} needs trajectory length >= {k + 3}, "
            f"got {len(trajectory)}"
        )
    a = np.asarray(trajectory[k], dtype=float)
    b = np.asarray(trajectory[k + 2], dtype=float)
    return float(np.sum((b - a) ** 2))


def g_realised_series(trajectories: dict[str, list[np.ndarray]]) -> list[float]:
    """Market energy per round-pair: sum over pairs of the realised displacement.

    Additivity is Zusai section 5.3 — the aggregate is the sum of the
    per-negotiation gains, with coupling entering through the shared rows of
    the joint filter rather than through the energy.

    Trajectories of different lengths are summed over the rounds they have;
    the series ends when the longest trajectory runs out of complete pairs.
    """
    if not trajectories:
        return []
    longest = max(len(t) for t in trajectories.values())
    series: list[float] = []
    for k in range(longest - 2):
        total = 0.0
        for traj in trajectories.values():
            if k + 2 < len(traj):
                total += g_realised(traj, k)
        series.append(total)
    return series


# --------------------------------------------------------------------------
# 2. Model-based lookahead — needs a concession model, gives a clean zero set
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ConcessionModel:
    """x_{k+1} = x_k + rate * (target - x_k), one per role.

    The scripted prototype hard-codes rate and target. On live agents both are
    fitted from the observed trajectory — see ``fit``.
    """

    rate: np.ndarray  # (3,) per-dimension concession rate in (0, 1]
    target: np.ndarray  # (3,) the role's aspiration point

    def propose(self, x: np.ndarray) -> np.ndarray:
        """The adjustment this role would propose from x, noise-free."""
        return self.rate * (self.target - np.asarray(x, dtype=float))

    @classmethod
    def fit(cls, states: list[np.ndarray], eps: float = 1e-9) -> ConcessionModel:
        """Fit rate and target per dimension from that role's own moves.

        Per dimension, the model says dx = -rate * x + rate * target, which is
        linear in x, so an ordinary least-squares fit of dx on x recovers
        rate = -slope and target = intercept / rate.

        Degenerate dimensions (no variation in x, or a non-contracting fit)
        fall back to rate 0 and target = the last observed value: the honest
        reading of "this dimension is not moving" is a zero concession rate,
        not an extrapolated one.
        """
        arr = np.asarray(states, dtype=float)
        if arr.ndim != 2 or arr.shape[0] < 3:
            raise ValueError(
                f"need at least 3 states of the same role to fit, got {arr.shape}"
            )
        deltas = np.diff(arr, axis=0)
        base = arr[:-1]

        rate = np.zeros(3)
        target = arr[-1].copy()
        for dim in range(3):
            xs, ys = base[:, dim], deltas[:, dim]
            if np.ptp(xs) < eps:
                continue
            slope, intercept = np.polyfit(xs, ys, 1)
            r = -float(slope)
            if not (eps < r <= 1.0):
                continue
            rate[dim] = r
            target[dim] = float(intercept) / r
        return cls(rate=rate, target=target)


def roundpair_lookahead(
    xs: list[np.ndarray],
    contracts: list[Contract],
    models: tuple[ConcessionModel, ConcessionModel],
    dcbf: DCBFFilter,
    shared_capacity: float | None = None,
) -> list[np.ndarray]:
    """One deterministic buyer round then seller round, through the filter."""
    current = [np.asarray(x, dtype=float).copy() for x in xs]
    for model in models:
        props = [model.propose(x) for x in current]
        result = dcbf.step(current, props, contracts, shared_capacity)
        current = [
            x + result.u[3 * i : 3 * i + 3] for i, x in enumerate(current)
        ]
    return current


def g_lookahead(
    xs: list[np.ndarray],
    contracts: list[Contract],
    models: tuple[ConcessionModel, ConcessionModel],
    dcbf: DCBFFilter,
    shared_capacity: float | None = None,
) -> float:
    """G(x) = ||f^2(x) - x||^2, the filter inside the rollout.

    Zero exactly at the constrained equilibrium — the GNE under coupling —
    without anyone having had to locate it.
    """
    after = roundpair_lookahead(xs, contracts, models, dcbf, shared_capacity)
    return float(sum(np.sum((b - a) ** 2) for a, b in zip(xs, after)))


# --------------------------------------------------------------------------
# Decay estimators
# --------------------------------------------------------------------------


def contraction_transient(values: list[float] | np.ndarray,
                          floor_frac: float = 0.05) -> float:
    """Per-round-pair contraction factor, fitted on the transient only.

    Fits log G against k from k = 0 until G first drops below floor_frac * G_0,
    or stops improving for three consecutive round-pairs. The noise-ball
    plateau and rising excursions are excluded deliberately: a fit that
    includes them measures the noise floor, not the contraction, and reporting
    it as evidence of convergence is the error the audit caught
    (formulation.md section 7.6).

    This is the canonical estimator. The naive whole-series fit is kept in the
    verbatim prototype only, for reproducing the v1 tables.
    """
    vals = np.maximum(np.asarray(values, dtype=float), 1e-12)
    if vals.size < 3:
        raise ValueError(f"need at least 3 round-pairs to fit, got {vals.size}")
    floor = max(vals[0] * floor_frac, 1e-9)
    end, worse, best = 1, 0, vals[0]
    for i in range(1, vals.size):
        if vals[i] < floor:
            end = i + 1
            break
        if vals[i] < best:
            best, worse = vals[i], 0
        else:
            worse += 1
            if worse >= 3:
                break
        end = i + 1
    end = max(end, 3)
    slope = np.polyfit(np.arange(end), np.log(vals[:end]), 1)[0]
    return float(np.exp(slope))


def drift_outside_ball(
    values: list[float] | np.ndarray,
) -> dict[str, float]:
    """Fit E[G_{k+1} | G_k] <= (1 - alpha) G_k + beta by least squares.

    The audit killed the global decrease-in-expectation claim: measured
    E[dV] = -56 far from equilibrium but +6.4 at mid-range, because rare
    heavy-tailed overshoots dominate the local mean. The surviving claim is a
    drift condition outside a ball, which converges in expectation to
    { G <= beta / alpha } — and that ball radius is itself a reportable
    measure of how erratic the agents are.
    """
    vals = np.asarray(values, dtype=float)
    if vals.size < 4:
        raise ValueError(f"need at least 4 round-pairs to fit drift, got {vals.size}")
    g_k, g_next = vals[:-1], vals[1:]
    slope, intercept = np.polyfit(g_k, g_next, 1)
    alpha = float(1.0 - slope)
    beta = float(max(intercept, 0.0))
    radius = beta / alpha if alpha > 1e-12 else float("inf")
    return {"alpha": alpha, "beta": beta, "ball_radius": radius}
