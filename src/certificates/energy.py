"""The convergence layer: two certificates, both anchor-free.

Formulation.md v2 section 5. The single scalar of v1 could not do both jobs,
and the reason is visible in the model: at the equilibrium the two agents'
individual gradients are large and opposite — each still wants to pull price
its way — and only their *sum* vanishes. So

    Phi(x)   = ||F(x)||_M,           F = grad Uhat_B + grad Uhat_S
    G_kappa(x) = sum_i [rho ||grad Uhat_i(x)||_M - kappa]_+

measure different things. Phi is the force imbalance on the draft and answers
*does it reach the deal?*; its zero set is the Nash bargaining solution
(Proposition 1). G_kappa is the residual private incentive net of friction and
answers *does it stop, and when?*; its zero set is the frictional equilibrium
set NE_kappa, which is a ball, not a point.

Both are built from current gradients only. Neither needs to know where the
agreement will land — which matters because under a binding constraint it
lands somewhere with no closed form, and a certificate anchored at a guessed
point stalls at exactly its own anchoring error (measured in v1: 510.3 against
509.9 predicted).

Under coupling, Phi itself is not enough: at a constrained equilibrium the
field is nonzero because it points into the constraint. The certificate must
be projected onto the tangent cone of the active constraints, giving Phi_proj,
which does vanish there.

Also here: the assumption-free realised-displacement energy of v1. It is
strictly weaker — it measures movement rather than incentive, and cannot tell
a negotiation that stopped because it agreed from one that stopped because it
gave up — but it needs no utility estimates at all, so it is the fallback when
the payoff model cannot be identified from a transcript.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..contract import Contract
from ..payoffs import SCALE, PayoffModel, norm_M

# --------------------------------------------------------------------------
# Phi — the convergence certificate
# --------------------------------------------------------------------------


def phi(model: PayoffModel, x: np.ndarray) -> float:
    """Force imbalance on the draft. Zero exactly at the bargaining solution.

    Not a distance: Phi is steep (locally Phi ~ L ||x - x*|| with L about 80
    for the reference calibration) and carries payoff-gradient units. It is a
    merit function, and comparing its magnitude across differently calibrated
    negotiations is meaningless.
    """
    return norm_M(model.concession_field(x))


def phi_projected(
    model: PayoffModel,
    x: np.ndarray,
    contract: Contract | None = None,
    tol: float = 1e-6,
) -> float:
    """Phi with the field projected onto the tangent cone of active constraints.

    At a constrained equilibrium the agents still want to move, but only in
    directions the contract forbids. Unprojected Phi reads that as
    non-convergence; the projection removes exactly the component the
    constraint absorbs, and what remains is the incentive that could still be
    acted on.

    A constraint that is active but whose gradient the field points *away*
    from is not binding on this motion, so it is left in place — projecting it
    out would discard a real component of the field.

    The projection is taken in scaled coordinates, so it is consistent with the
    metric every other norm here uses.
    """
    field = model.concession_field(x)
    if contract is None:
        return norm_M(field)

    rows = _active_rows(contract, x, tol)
    if not rows.size:
        return norm_M(field)

    field_s = field * SCALE
    for grad in rows:
        grad_s = grad * SCALE
        denom = float(grad_s @ grad_s)
        if denom <= tol:
            continue
        overlap = float(grad_s @ field_s)
        # h_i >= 0 is the safe side, so grad h_i . F >= 0 means the field
        # points back into the set: not binding on this motion.
        if overlap >= 0:
            continue
        field_s = field_s - (overlap / denom) * grad_s
    return float(np.linalg.norm(field_s))


def _active_rows(contract: Contract, x: np.ndarray, tol: float) -> np.ndarray:
    """Gradients of the constraints that are active (h_i ~ 0) at x."""
    values = contract.h(x)
    jac = contract.grad_h(x)
    mask = contract.active_mask()
    rows = [
        jac[i]
        for i in range(len(values))
        if mask[i] and values[i] <= tol
    ]
    return np.array(rows) if rows else np.empty((0, 3))


# --------------------------------------------------------------------------
# G_kappa — the termination certificate
# --------------------------------------------------------------------------


def g_kappa(model: PayoffModel, x: np.ndarray, kappa: float, rho: float) -> float:
    """Residual private incentive net of friction, summed over the two sides.

    Zero when neither agent's best available improvement is worth the
    switching cost. With kappa > 0 the zero set is a ball, not a point, which
    matches the economics: negotiations end when further haggling stops being
    worth it, not when it becomes impossible.
    """
    total = 0.0
    for role in ("buyer", "seller"):
        total += max(rho * norm_M(model.grad_u_hat(x, role)) - kappa, 0.0)
    return total


def kappa_star(model: PayoffModel, x: np.ndarray, rho: float) -> float:
    """Friction at which *both* sides stop moving at x.

    The termination threshold is state-dependent, and that is the whole
    content of Proposition 2: kappa* grows along an improving path, because
    the gradients grow as the draft gets better. So there is no constant
    friction that both permits progress at the start and halts motion at the
    deal.
    """
    return rho * max(
        norm_M(model.grad_u_hat(x, "buyer")),
        norm_M(model.grad_u_hat(x, "seller")),
    )


@dataclass(frozen=True)
class FrictionWindow:
    """The interval Prop. 2 says no constant friction can straddle."""

    kappa_at_start: float
    kappa_at_deal: float

    @property
    def constant_friction_possible(self) -> bool:
        """True only if some constant kappa both moves and stops.

        Requires kappa_at_start >= kappa_at_deal, i.e. the incentive to move
        *shrinks* along the path. It does not, for any calibration where the
        draft improves — which is why the deadline must be modelled as
        escalating friction.
        """
        return self.kappa_at_start >= self.kappa_at_deal

    def describe(self) -> str:
        if self.constant_friction_possible:
            return (
                f"a constant kappa in [{self.kappa_at_deal:.2f}, "
                f"{self.kappa_at_start:.2f}] both permits motion and terminates"
            )
        return (
            f"no constant kappa works: permitting motion at the start needs "
            f"kappa < {self.kappa_at_start:.2f}, halting at the deal needs "
            f"kappa >= {self.kappa_at_deal:.2f}. Termination requires "
            "escalating friction."
        )


def friction_window(
    model: PayoffModel, x_start: np.ndarray, rho: float
) -> FrictionWindow:
    """Measure the Prop. 2 window for one negotiation."""
    x_deal, _ = model.nash_bargaining_solution()
    return FrictionWindow(
        kappa_at_start=kappa_star(model, x_start, rho),
        kappa_at_deal=kappa_star(model, x_deal, rho),
    )


# --------------------------------------------------------------------------
# Stability: the hypothesis the convergence guarantee rests on
# --------------------------------------------------------------------------


def field_jacobian(model: PayoffModel, x: np.ndarray, h: float = 1e-4) -> np.ndarray:
    """Jacobian of F, by central differences in scaled coordinates."""
    x = np.asarray(x, dtype=float)
    jac = np.zeros((3, 3))
    for i in range(3):
        step = np.zeros(3)
        step[i] = h * SCALE[i]
        jac[:, i] = (
            model.concession_field(x + step) - model.concession_field(x - step)
        ) / (2 * step[i])
    return jac


def is_monotone(
    model: PayoffModel, x: np.ndarray, tol: float = 1e-8
) -> tuple[bool, float]:
    """Is the induced game statically stable at x?

    Convergence of *any* cost-benefit rationalizable dynamic needs the game to
    be monotone (Rosen's diagonally-strict concavity; equivalently passive;
    equivalently a stable game). With payoffs in hand this is checkable rather
    than assumed, which is the main practical gain of the payoff-based
    formulation.

    The symmetric part is expressed in the unit metric before its eigenvalues
    are taken — the congruence D sym(J) D with D = diag(sigma). Without that,
    the eigenvalues mix pounds, units and days and are not comparable across
    the three terms (it also changes the number: -0.07 unscaled against -6.86
    in the metric, for the reference calibration).

    Returns (monotone, lambda_max). Non-positive is stable.
    """
    jac = field_jacobian(model, x)
    sym = 0.5 * (jac + jac.T)
    metric = np.diag(SCALE)
    lam_max = float(np.max(np.linalg.eigvalsh(metric @ sym @ metric)))
    return lam_max <= tol, lam_max


def stability_radius(
    model: PayoffModel,
    radii: tuple[float, ...] = (0.5, 1.0, 1.5, 2.0, 3.0),
    samples: int = 150,
    seed: int = 0,
    threshold: float = 1.0,
) -> dict[str, float]:
    """Fraction of sampled states that are monotone, by distance from the deal.

    The certified radius is the largest tested radius at which every sample is
    monotone. This is a design instruction rather than a caveat: the contract
    should confine the negotiation to the region where the induced game is
    stable, and restricting C(theta) is how it discharges its convergence-side
    obligation.
    """
    rng = np.random.default_rng(seed)
    x_star, _ = model.nash_bargaining_solution()

    fractions: dict[str, float] = {}
    certified = 0.0
    for radius in radii:
        monotone = 0
        for _ in range(samples):
            direction = rng.normal(size=3)
            direction /= np.linalg.norm(direction) or 1.0
            offset = direction * radius * rng.uniform(0.0, 1.0) ** (1 / 3)
            ok, _ = is_monotone(model, x_star + offset * SCALE)
            monotone += int(ok)
        fraction = monotone / samples
        fractions[f"monotone_within_{radius}"] = fraction
        if fraction >= threshold:
            certified = radius
    fractions["certified_radius"] = certified
    _, lam_max = is_monotone(model, x_star)
    fractions["lambda_max_at_nbs"] = lam_max
    return fractions


def contract_is_inside_monotone_region(
    model: PayoffModel, contract: Contract, radius: float
) -> tuple[bool, float]:
    """Does C(theta) fit inside the certified stability ball?

    Design implication 2 of formulation.md section 9. Checked by the worst-case
    corner of the box that bounds the safe set, so a True here is conservative:
    the true safe set is a subset of that box because of the bilinear budget
    row.

    A contract that leaves the deadline unconstrained while the payoff model
    still prices it cannot be certified at all: C(theta) is unbounded in that
    dimension, so no ball contains it. Returning a finite distance there would
    quietly certify a contract that does not confine the negotiation.

    Returns (fits, worst-case distance in scaled units).
    """
    x_star, _ = model.nash_bargaining_solution()
    p_lo = contract.cost_floor
    p_hi = contract.budget / max(contract.q_min, 1e-9)
    q_lo, q_hi = contract.q_min, contract.q_max
    if contract.deadline_active:
        d_lo, d_hi = contract.d_min, contract.d_max
    elif model.deadline_active:
        return False, float("inf")
    else:
        # Neither the contract nor the payoffs depend on d: it is not a
        # dimension of this game, so it cannot take the state anywhere.
        d_lo = d_hi = float(x_star[2])

    worst = 0.0
    for p in (p_lo, p_hi):
        for q in (q_lo, q_hi):
            for d in (d_lo, d_hi):
                worst = max(
                    worst,
                    float(np.linalg.norm((np.array([p, q, d]) - x_star) / SCALE)),
                )
    return worst <= radius, worst


# --------------------------------------------------------------------------
# Assumption-free fallback: realised displacement (v1)
# --------------------------------------------------------------------------


def g_realised(trajectory: list[np.ndarray], k: int) -> float:
    """Squared round-pair displacement, in scaled units.

    Needs no utilities, so it survives a transcript the payoff model cannot be
    fitted to. It is strictly weaker than G_kappa: movement is evidence of
    remaining gain only under cost-benefit rationalizability, and a stalled
    negotiation and a settled one look identical.
    """
    if k < 0 or k + 2 >= len(trajectory):
        raise IndexError(
            f"round-pair at k={k} needs trajectory length >= {k + 3}, "
            f"got {len(trajectory)}"
        )
    a = np.asarray(trajectory[k], dtype=float)
    b = np.asarray(trajectory[k + 2], dtype=float)
    return float(np.sum(((b - a) / SCALE) ** 2))


def g_realised_series(trajectories: dict[str, list[np.ndarray]]) -> list[float]:
    """Market energy per round-pair: the sum over pairs.

    Additivity is Zusai section 5.3 — the aggregate is the sum of the
    per-negotiation gains, with coupling entering through the shared rows of
    the joint filter rather than through the energy.
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
# Decay estimators
# --------------------------------------------------------------------------


def contraction_transient(
    values: list[float] | np.ndarray, floor_frac: float = 0.05
) -> float:
    """Per-round-pair contraction factor, fitted on the transient only.

    Fits log of the series against k from k = 0 until it first drops below
    floor_frac of its initial value, or stops improving for three consecutive
    round-pairs. The noise-ball plateau and rising excursions are excluded
    deliberately: a fit that includes them measures the noise floor, not the
    contraction, and reporting it as evidence of convergence is the error the
    audit caught.
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


def drift_outside_ball(values: list[float] | np.ndarray) -> dict[str, float]:
    """Fit E[Phi_{k+1} | Phi_k] <= (1 - alpha) Phi_k + beta by least squares.

    The audit killed the global decrease-in-expectation claim: measured
    E[dV] = -56 far from equilibrium but +6.4 at mid-range, because rare
    heavy-tailed overshoots dominate the local mean. The surviving claim is a
    drift condition outside a ball, which converges in expectation to
    {Phi <= beta / alpha} — and that radius is itself a reportable measure of
    how erratic the agents are.
    """
    vals = np.asarray(values, dtype=float)
    if vals.size < 4:
        raise ValueError(f"need at least 4 round-pairs to fit drift, got {vals.size}")
    slope, intercept = np.polyfit(vals[:-1], vals[1:], 1)
    alpha = float(1.0 - slope)
    beta = float(max(intercept, 0.0))
    radius = beta / alpha if alpha > 1e-12 else float("inf")
    return {"alpha": alpha, "beta": beta, "ball_radius": radius}
