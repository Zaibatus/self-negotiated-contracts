"""Per-round certificate records and the time-to-contract obligation.

What gets recorded is the evidence for the two claims the architecture makes:

  * safety — the barrier values on the TRUE (non-linearised) h at every round,
    so a breach cannot hide behind the linearisation the filter works with;
  * liveness — T_max is a *promise* in theta, and a promise that is never
    checked is decoration. ``time_to_contract`` turns the measured contraction
    of G into a certified upper bound on negotiation length, which is then
    compared against T_max at contract time and against the realised length
    afterwards.

Also recorded, deliberately: every fallback and every certificate gap. A
safety component that reports only its successes is not reporting.
"""

from __future__ import annotations

import json
import math
from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np

from ..contract import Contract
from ..payoffs import SCALE
from .dcbf import FilterResult


@dataclass
class RoundRecord:
    """One intercepted proposal, with everything needed to audit it later."""

    pair_id: str
    round_index: int
    mode: str  # "filter" | "monitor" | "off"

    x_prev: list[float]
    x_proposed: list[float]
    x_applied: list[float]

    h_prev: dict[str, float]  # true h at x_prev
    h_applied: dict[str, float]  # true h at x_applied
    breached_rows: list[str]  # active rows below zero at x_applied
    breach: bool

    intervention: float  # ||u_safe - u_prop||
    slack_total: float
    duals: dict[str, float]

    solver_status: str
    solved: bool
    fallback: str | None
    backtracks: int
    certificate_gap: bool

    # Optional context
    business_id: str | None = None
    customer_id: str | None = None
    extraction: dict[str, str | float] = field(default_factory=dict)

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), default=float)


def make_round_record(
    *,
    pair_id: str,
    round_index: int,
    mode: str,
    contract: Contract,
    x_prev: np.ndarray,
    x_proposed: np.ndarray,
    x_applied: np.ndarray,
    result: FilterResult | None,
    pair_slot: int = 0,
    business_id: str | None = None,
    customer_id: str | None = None,
    extraction: dict[str, str | float] | None = None,
    intervention_override: float | None = None,
) -> RoundRecord:
    """Assemble a record from a filter step.

    ``pair_slot`` selects this pair's rows out of a joint filter result, whose
    labels are prefixed "<slot>:". Shared rows (the coupling clause) are
    attached to every pair they touch, since the shadow price of a shared
    constraint is a property of the coupling, not of one negotiation.

    ``intervention_override`` exists for the opening projection, which corrects
    the terms without going through the barrier QP and so arrives with
    ``result=None``. Leaving it at zero understated the filter's activity
    badly: 21 of 27 governed rounds in one arm B model cell were opening
    projections, so a reported "the filter bound on 11% of rounds" was counting
    only the minority of corrections that happened to come from the QP.
    """
    labels = contract.active_labels()
    h_prev = contract.h(np.asarray(x_prev, dtype=float))
    h_applied = contract.h(np.asarray(x_applied, dtype=float))
    mask = contract.active_mask()

    duals: dict[str, float] = {}
    slack_total = 0.0
    if result is not None:
        prefix = f"{pair_slot}:"
        for label, value, slack in zip(result.row_labels, result.duals, result.slack):
            if label.startswith(prefix):
                duals[label[len(prefix):]] = float(value)
                slack_total += float(slack)
            elif label.startswith("shared:"):
                duals[label] = float(value)

    return RoundRecord(
        pair_id=pair_id,
        round_index=round_index,
        mode=mode,
        x_prev=[float(v) for v in x_prev],
        x_proposed=[float(v) for v in x_proposed],
        x_applied=[float(v) for v in x_applied],
        h_prev={lbl: float(v) for lbl, v in zip(labels, h_prev[mask])},
        h_applied={lbl: float(v) for lbl, v in zip(labels, h_applied[mask])},
        breached_rows=contract.violations(np.asarray(x_applied, dtype=float)),
        breach=not contract.is_safe(np.asarray(x_applied, dtype=float)),
        intervention=(
            intervention_override
            if intervention_override is not None
            else (
                float(np.linalg.norm(
                    (
                        result.u[3 * pair_slot: 3 * pair_slot + 3]
                        - result.u_prop[3 * pair_slot: 3 * pair_slot + 3]
                    )
                    / SCALE
                ))
                if result is not None
                else 0.0
            )
        ),
        slack_total=slack_total,
        duals=duals,
        solver_status=result.status if result is not None else "not_run",
        solved=result.solved if result is not None else True,
        fallback=result.fallback if result is not None else None,
        backtracks=result.backtracks if result is not None else 0,
        certificate_gap=result.certificate_gap if result is not None else False,
        business_id=business_id,
        customer_id=customer_id,
        extraction=extraction or {},
    )


# --------------------------------------------------------------------------
# Liveness: discharging T_max
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class LivenessCertificate:
    """Certified bound on rounds-to-agreement, checked against theta's T_max."""

    g_initial: float
    contraction: float
    epsilon: float
    certified_round_pairs: float | None  # None when no bound exists
    certified_rounds: float | None
    t_max: int
    honoured: bool  # the certified bound fits inside T_max
    realised_rounds: int | None = None
    realised_within_bound: bool | None = None
    reason: str = ""


def time_to_contract(
    g_initial: float,
    contraction: float,
    t_max: int,
    epsilon: float = 1e-3,
    realised_rounds: int | None = None,
) -> LivenessCertificate:
    """k(eps) = log(G_0 / eps) / log(1 / c) round-pairs, against T_max.

    This is how T_max is *discharged* rather than merely imposed: the measured
    contraction factor c and the initial energy give an upper bound on how long
    the negotiation can take, and the contract is only signable if that bound
    fits inside the T_max it promises.

    A contraction factor at or above 1 means no bound exists — the honest
    output is "no certificate", not a large number.
    """
    if g_initial <= 0:
        return LivenessCertificate(
            g_initial=g_initial,
            contraction=contraction,
            epsilon=epsilon,
            certified_round_pairs=0.0,
            certified_rounds=0.0,
            t_max=t_max,
            honoured=True,
            realised_rounds=realised_rounds,
            realised_within_bound=True,
            reason="already at the equilibrium: G_0 <= 0",
        )

    if not 0.0 < contraction < 1.0:
        return LivenessCertificate(
            g_initial=g_initial,
            contraction=contraction,
            epsilon=epsilon,
            certified_round_pairs=None,
            certified_rounds=None,
            t_max=t_max,
            honoured=False,
            realised_rounds=realised_rounds,
            realised_within_bound=None,
            reason=(
                f"contraction {contraction:.4f} is not in (0, 1): the dynamics "
                "are not certified to contract, so no time-to-contract bound "
                "exists"
            ),
        )

    if g_initial <= epsilon:
        pairs = 0.0
    else:
        pairs = math.log(g_initial / epsilon) / math.log(1.0 / contraction)
    rounds = 2.0 * pairs

    return LivenessCertificate(
        g_initial=g_initial,
        contraction=contraction,
        epsilon=epsilon,
        certified_round_pairs=pairs,
        certified_rounds=rounds,
        t_max=t_max,
        honoured=rounds <= t_max,
        realised_rounds=realised_rounds,
        realised_within_bound=(
            None if realised_rounds is None else realised_rounds <= rounds
        ),
        reason="",
    )


# --------------------------------------------------------------------------
# Aggregation and I/O
# --------------------------------------------------------------------------


def summarise(records: Iterable[RoundRecord]) -> dict[str, float]:
    """Headline numbers for one experiment arm."""
    recs = list(records)
    if not recs:
        return {"rounds": 0.0}
    n = float(len(recs))
    interventions = [r.intervention for r in recs]
    return {
        "rounds": n,
        "pairs": float(len({r.pair_id for r in recs})),
        "breach_rate": sum(r.breach for r in recs) / n,
        "breach_rounds": float(sum(r.breach for r in recs)),
        "mean_intervention": float(np.mean(interventions)),
        "max_intervention": float(np.max(interventions)),
        "intervention_rate": sum(i > 1e-6 for i in interventions) / n,
        "slack_total": float(sum(r.slack_total for r in recs)),
        "solver_failure_rate": sum(not r.solved for r in recs) / n,
        "fallback_rate": sum(r.fallback is not None for r in recs) / n,
        "certificate_gap_rate": sum(r.certificate_gap for r in recs) / n,
        "backtrack_rate": sum(r.backtracks > 0 for r in recs) / n,
    }


def write_jsonl(records: Iterable[RoundRecord], path: str | Path) -> Path:
    """Append-safe dump of round records, one JSON object per line."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(record.to_json() + "\n")
    return out


def read_jsonl(path: str | Path) -> list[RoundRecord]:
    """Read back what ``write_jsonl`` wrote."""
    return [
        RoundRecord(**json.loads(line))
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
