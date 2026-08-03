"""Estimating the payoff model from a live negotiation, per formulation 11.

Section 11 asks for utilities estimated from transcripts. Taken literally that
means fitting (a, b, c, e, lambda) jointly, and section 11's own practical
warning says why that will not work: LLM negotiations run five to fifteen
rounds, which does not identify five parameters. What comes back would be
error bars wide enough to swallow the result.

So the split here is by what the data can actually support:

  * **Structure from the scenario, exactly.** The seller's marginal cost is
    ``min_price_factor * list_price`` and the buyer's reservation price is in
    ``menu_features``. Both are ground truth in the YAML, and together they pin
    a, e and c (``PayoffModel.from_scenario``). Nothing is estimated.

  * **Acceptance temperature from the transcript.** lambda is one parameter and
    the transcript contains accept/reject events, so it is identifiable. Fitted
    by maximum likelihood, with the profile likelihood reported so a flat one
    is visible rather than hidden behind a point estimate.

  * **Cost-benefit rationalizability tested, not assumed.** This is the whole
    bridge from gradient-ascent proxies to LLM agents: the claim is that an
    agent moves iff rho ||grad Uhat_i||_M > kappa. It is the single assumption
    carrying the transfer, and it is falsifiable from the data we already log.
    ``assess_rationalizability`` reports the interval of kappa consistent with the
    observed move/stall pattern, and how many rounds no kappa can explain.

The honest failure mode is an empty consistent interval — the agent moved when
its incentive was small and stalled when it was large. That is a *result*: it
says LLM negotiators are not cost-benefit rationalizable at the observed
scale, and the convergence guarantees do not transfer. Reporting it as a
number rather than swallowing it is the point of the whole module.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np

from ..payoffs import PayoffModel, norm_M

# --------------------------------------------------------------------------
# Observations
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Round:
    """One observed move in a negotiation.

    ``moved`` is whether the agent changed the terms at all. A round where an
    agent sent prose without touching the numbers is a stall in term space,
    which is exactly what the rationalizability test needs to see.
    """

    x_before: np.ndarray
    x_after: np.ndarray
    role: str  # "buyer" | "seller"

    @property
    def moved(self) -> bool:
        return not np.allclose(self.x_before, self.x_after, atol=1e-9)

    @property
    def displacement(self) -> float:
        """Step length in scaled units — the realised rho for this round."""
        from ..payoffs import dist_M

        return dist_M(self.x_after, self.x_before)


@dataclass(frozen=True)
class AcceptanceEvent:
    """A draft that was either accepted (paid for) or walked away from."""

    x: np.ndarray
    accepted: bool


# --------------------------------------------------------------------------
# lambda by maximum likelihood
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LambdaFit:
    """What the acceptance data supports, including when it supports little."""

    lam: float
    n_events: int
    n_accepted: int
    log_likelihood: float
    identified: bool
    profile: dict[float, float] = field(default_factory=dict)
    reason: str = ""


def fit_lambda(
    model: PayoffModel,
    events: list[AcceptanceEvent],
    grid: np.ndarray | None = None,
) -> LambdaFit:
    """Maximum-likelihood acceptance temperature on a grid.

    P(accept | x) = sigma(U_B/lambda) * sigma(U_S/lambda), so small lambda is a
    sharp threshold and large lambda is near-indifference. A grid search is
    used rather than a gradient method because the likelihood is one
    dimensional and cheap, and because the whole profile is worth reporting.

    ``identified`` is False when the data cannot distinguish values of lambda:
    with no rejections every lambda that makes acceptance likely fits equally
    well, and the returned point estimate would be an artefact of the grid.
    """
    if not events:
        return LambdaFit(
            lam=model.lam,
            n_events=0,
            n_accepted=0,
            log_likelihood=float("nan"),
            identified=False,
            reason="no acceptance events observed; keeping the prior lambda",
        )

    if grid is None:
        _, w_max = model.nash_bargaining_solution()
        base = max(abs(w_max), 1e-6)
        grid = base * np.geomspace(1e-3, 1e2, 120)

    n_accepted = sum(e.accepted for e in events)
    profile: dict[float, float] = {}
    best_lam, best_ll = float(grid[0]), -np.inf

    for lam in grid:
        candidate = replace(model, lam=float(lam))
        total = 0.0
        for event in events:
            p = float(np.clip(candidate.p_accept(event.x), 1e-12, 1 - 1e-12))
            total += np.log(p) if event.accepted else np.log1p(-p)
        profile[float(lam)] = total
        if total > best_ll:
            best_ll, best_lam = total, float(lam)

    # Identification: the likelihood must actually discriminate. A flat profile
    # (or one-sided data) means the point estimate carries no information.
    spread = best_ll - min(profile.values())
    one_sided = n_accepted in (0, len(events))
    identified = bool(spread > 1.0 and not one_sided)
    reason = ""
    if one_sided:
        reason = (
            f"all {len(events)} events have the same outcome "
            f"({'accepted' if n_accepted else 'rejected'}); lambda is not "
            "identified from one-sided data"
        )
    elif not identified:
        reason = (
            f"log-likelihood varies by only {spread:.2f} across the grid; "
            "lambda is effectively flat and the point estimate is an artefact"
        )

    return LambdaFit(
        lam=best_lam if identified else model.lam,
        n_events=len(events),
        n_accepted=int(n_accepted),
        log_likelihood=best_ll,
        identified=identified,
        profile=profile,
        reason=reason,
    )


def calibrate(
    model: PayoffModel, events: list[AcceptanceEvent]
) -> tuple[PayoffModel, LambdaFit]:
    """Scenario structure plus a transcript-fitted lambda.

    Returns the model unchanged when lambda is not identified, so a run with
    thin acceptance data degrades to the scenario prior instead of to a number
    the data did not support.
    """
    fit = fit_lambda(model, events)
    return (replace(model, lam=fit.lam) if fit.identified else model), fit


# --------------------------------------------------------------------------
# The bridge assumption, tested
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RationalizabilityReport:
    """Is the observed move/stall pattern explainable by any friction level?

    Under cost-benefit rationalizability an agent moves iff
    rho ||grad Uhat_i||_M > kappa. Every round the agent moved therefore puts a
    ceiling on kappa, and every round it stalled puts a floor under it. If the
    highest floor exceeds the lowest ceiling, no kappa explains the data.
    """

    n_rounds: int
    n_moved: int
    kappa_lower: float  # highest incentive at which the agent still stalled
    kappa_upper: float  # lowest incentive at which the agent moved
    consistent: bool
    n_inconsistent_rounds: int
    incentives_moved: list[float]
    incentives_stalled: list[float]

    @property
    def interval(self) -> tuple[float, float] | None:
        return (self.kappa_lower, self.kappa_upper) if self.consistent else None

    def describe(self) -> str:
        if self.n_rounds == 0:
            return "no rounds observed"
        if self.consistent:
            return (
                f"consistent with cost-benefit rationalizability for kappa in "
                f"[{self.kappa_lower:.3f}, {self.kappa_upper:.3f}] "
                f"({self.n_moved}/{self.n_rounds} rounds moved)"
            )
        return (
            f"NOT consistent: the agent stalled at incentive "
            f"{self.kappa_lower:.3f} and moved at {self.kappa_upper:.3f}, so no "
            f"single kappa explains it; {self.n_inconsistent_rounds} of "
            f"{self.n_rounds} rounds cannot be reconciled. The bridge from the "
            "gradient-ascent proxies to these agents does not hold at this scale"
        )


def assess_rationalizability(
    model: PayoffModel, rounds: list[Round], rho: float = 1.0
) -> RationalizabilityReport:
    """Bound kappa from the observed move/stall pattern.

    ``rho`` scales the incentive into the same units as kappa. Passing 1.0
    reports the raw gradient norms, which is usually what you want: the
    *ordering* of incentives between moved and stalled rounds is what carries
    the test, and it is invariant to rho.
    """
    moved_incentives: list[float] = []
    stalled_incentives: list[float] = []

    for observation in rounds:
        incentive = rho * norm_M(
            model.grad_u_hat(observation.x_before, observation.role)
        )
        (moved_incentives if observation.moved else stalled_incentives).append(
            incentive
        )

    # Moving requires incentive > kappa, so kappa < min(moved).
    # Stalling requires incentive <= kappa, so kappa >= max(stalled).
    upper = min(moved_incentives) if moved_incentives else float("inf")
    lower = max(stalled_incentives) if stalled_incentives else 0.0
    consistent = lower < upper

    inconsistent = 0
    if not consistent:
        inconsistent = sum(1 for v in moved_incentives if v <= lower) + sum(
            1 for v in stalled_incentives if v >= upper
        )

    return RationalizabilityReport(
        n_rounds=len(rounds),
        n_moved=len(moved_incentives),
        kappa_lower=lower,
        kappa_upper=upper,
        consistent=consistent,
        n_inconsistent_rounds=inconsistent,
        incentives_moved=moved_incentives,
        incentives_stalled=stalled_incentives,
    )


def rounds_from_trajectory(
    trajectory: list[np.ndarray], first_role: str = "seller"
) -> list[Round]:
    """Turn an observed term trajectory into alternating-role rounds.

    In Magentic the seller emits the structured proposals, so a pair's
    trajectory starts with a seller move and alternates as the buyer's
    counter-offers are extracted from prose.
    """
    other = "buyer" if first_role == "seller" else "seller"
    return [
        Round(
            x_before=np.asarray(trajectory[k], dtype=float),
            x_after=np.asarray(trajectory[k + 1], dtype=float),
            role=first_role if k % 2 == 0 else other,
        )
        for k in range(len(trajectory) - 1)
    ]
