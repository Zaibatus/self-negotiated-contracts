"""Arm-against-arm comparison: what the guarantee buys, and what it costs.

The headline of a treatment arm is a difference, not a level, so this reads two
sets of finished schemas and puts them side by side.

The cost side is the part that must not be omitted. A safety filter that
rewrites proposals can prevent a deal from closing at all, and if it does, the
size of that effect is the price of the guarantee. But "did not close" has
three quite different causes and only one of them is a cost:

  (a) **structurally infeasible** — C(theta) is empty for that pair, so no
      terms could ever have complied. Not closing is the *correct* outcome and
      booking it as a filter-caused failure would be false;
  (b) **closed in neither arm** — the pair failed ungoverned too, so this is
      agent variance rather than anything the filter did;
  (c) **closed ungoverned, did not close filtered** — this alone is the price.

Reporting (a) and (b) inside the same number as (c) is the easy way to make a
safety layer look expensive; folding (c) away is the easy way to make it look
free. Both are available here separately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .replay import ReplayResult


@dataclass
class ArmSummary:
    """One arm, aggregated over its seeds."""

    name: str
    results: list[ReplayResult] = field(default_factory=list)

    @property
    def deals(self) -> list:
        return [d for r in self.results for d in r.deals]

    @property
    def closed_pairs(self) -> set[str]:
        """Pairs that settled at least once across the arm's seeds."""
        return {d.pair_id for d in self.deals}

    def closures_by_pair(self) -> dict[str, int]:
        """How many seeds each pair closed in — the unit of the cost comparison.

        Per-pair counts rather than a single closure rate, because with three
        customers a rate collapses distinct situations into one number and
        hides which pair moved.
        """
        counts: dict[str, int] = {}
        for deal in self.deals:
            counts[deal.pair_id] = counts.get(deal.pair_id, 0) + 1
        return counts

    def governed_split(self, infeasible_pairs: set[str]) -> dict[str, float]:
        """Per-round breaches, split by whether the pair was governed at all.

        This is the single most load-bearing number in the arm B note — 0 of 27
        breaching rounds on governed pairs. It has to be split, because pairs
        with an empty safe set are deliberately never filtered (projecting into
        an empty set is not a safety operation), so their proposals breach and
        cannot be made not to. An unsplit rate mixes a guarantee with a
        scenario property and reads as though the filter failed.

        These are **outcome** numbers: replay reads the database, so under a
        filtered arm it sees the terms that actually reached the counterparty.
        That is the right surface for a safety claim. What the filter *did* to
        get there is a different question and is not visible here — see
        ``filter_telemetry``.
        """
        governed = {"rounds": 0, "breaches": 0}
        infeasible = {"rounds": 0, "breaches": 0}

        for result in self.results:
            for record in result.records:
                bucket = (
                    infeasible if record.pair_id in infeasible_pairs else governed
                )
                bucket["rounds"] += 1
                bucket["breaches"] += int(record.breach)

        out = {
            "governed_rounds": float(governed["rounds"]),
            "governed_breaches": float(governed["breaches"]),
            "infeasible_rounds": float(infeasible["rounds"]),
            "infeasible_breaches": float(infeasible["breaches"]),
        }
        if governed["rounds"]:
            out["governed_breach_rate"] = governed["breaches"] / governed["rounds"]
        if infeasible["rounds"]:
            out["infeasible_breach_rate"] = (
                infeasible["breaches"] / infeasible["rounds"]
            )
        return out

    def headline(self) -> dict[str, float]:
        summaries = [r.summary() for r in self.results]
        offered = [s.get("breach_rate", 0.0) for s in summaries]
        deals = self.deals
        spend = sum(d.spend for d in deals)
        breached = [d for d in deals if d.breached]

        out = {
            "seeds": float(len(self.results)),
            "proposals": float(sum(s["proposals_seen"] for s in summaries)),
            "offered_breach_rate": float(np.mean(offered)) if offered else 0.0,
            "offered_breach_sd": (
                float(np.std(offered, ddof=1)) if len(offered) > 1 else 0.0
            ),
            "deals_settled": float(len(deals)),
            "deals_breached": float(len(breached)),
            "overspend_total": float(sum(d.overspend for d in deals)),
            "value_transacted": float(spend),
        }
        if deals:
            out["settled_breach_rate"] = len(breached) / len(deals)
            out["overspend_share"] = (
                sum(d.overspend for d in deals) / spend if spend > 0 else 0.0
            )
        for label in ("within", "infeasible", "trivial", "meaningful"):
            out[f"deals_{label}"] = float(
                sum(1 for d in deals if d.classification == label)
            )
        return out


@dataclass
class CostOfGuarantee:
    """The three-way split of pairs that did not close under the filter."""

    infeasible: list[str] = field(default_factory=list)
    closed_in_neither: list[str] = field(default_factory=list)
    lost_to_the_filter: list[str] = field(default_factory=list)
    seeds: int = 0
    baseline_closures: dict[str, int] = field(default_factory=dict)
    treated_closures: dict[str, int] = field(default_factory=dict)

    @property
    def price(self) -> int:
        """Pairs that closed ungoverned and stopped closing under the filter."""
        return len(self.lost_to_the_filter)

    def describe(self) -> str:
        if self.price == 0:
            return (
                f"no detectable feasibility cost at n={self.seeds} seeds. That "
                "is not the same as no cost: with this many seeds and three "
                "customers, only a large effect would have been visible"
            )
        return (
            f"{self.price} pair(s) closed ungoverned and did not close under "
            f"the filter: {', '.join(sorted(self.lost_to_the_filter))}. This is "
            "the price of the guarantee"
        )


def cost_of_guarantee(
    baseline: ArmSummary, treated: ArmSummary, infeasible_pairs: set[str]
) -> CostOfGuarantee:
    """Split non-closure into scenario, variance and filter causes."""
    base_counts = baseline.closures_by_pair()
    treat_counts = treated.closures_by_pair()
    all_pairs = set(base_counts) | set(treat_counts) | infeasible_pairs

    out = CostOfGuarantee(
        seeds=len(treated.results),
        baseline_closures=base_counts,
        treated_closures=treat_counts,
    )
    for pair in sorted(all_pairs):
        base, treat = base_counts.get(pair, 0), treat_counts.get(pair, 0)
        if pair in infeasible_pairs:
            out.infeasible.append(pair)
        elif base == 0 and treat == 0:
            out.closed_in_neither.append(pair)
        elif base > 0 and treat == 0:
            out.lost_to_the_filter.append(pair)
    return out


def filter_telemetry(
    experiments: list[str],
    infeasible_pairs: set[str],
    results_dir: str | Path = "results",
) -> dict[str, float]:
    """What the regulator DID, read from the live protocol's own records.

    Replay cannot answer this. It reconstructs rounds from the database, which
    under a filtered arm already holds the corrected terms — so intervention is
    always zero there and the filter appears never to have acted. The mechanism
    lives in results/<run>/certificates.jsonl, written by the protocol as it
    ran.

    Those files stay gitignored as raw per-round data, so the numbers are
    folded into results/summary/arms.json here. Otherwise every mechanism claim
    in docs/notes/ would be reproducible from nothing in the repository.

    One subtlety that changes how these read. The protocol computes the filter
    step in *every* mode and only applies it when mode == "filter", so the
    recorded intervention is the correction the filter *computed*: actually
    applied under arm B, purely counterfactual under arms A and D. That is why
    the key is ``correction_nonzero`` rather than ``corrected`` — calling it
    "corrected" on an unfiltered arm would claim an intervention that never
    happened.

    It is also what makes arm D worth running: on an ungoverned trajectory it
    measures exactly what enforcement would have had to do.

    Note ``flagged`` counts *rate* violations too, not only breaches. The DCBF
    condition h(x_{k+1}) >= (1-gamma) h(x_k) can be violated while the terms are
    still inside C(theta) — approaching the boundary too fast is a flag without
    being a breach — so flagged exceeds the breach count.

    Returns an empty dict when no certificate files are present, rather than
    zeros — absent evidence and measured zero are not the same reading.
    """
    root = Path(results_dir)
    rounds = flagged = correction_nonzero = 0
    interventions: list[float] = []
    out: dict[str, float] = {}

    found = False
    for experiment in experiments:
        path = root / experiment / "certificates.jsonl"
        if not path.exists():
            continue
        found = True
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            if record["pair_id"] in infeasible_pairs:
                continue
            rounds += 1
            has_correction = record["intervention"] > 1e-6
            # "Flagged" = the proposal was not admissible. Under monitor the
            # applied terms ARE the proposed terms, so breached_rows says it;
            # under filter breached_rows is evaluated after the correction and
            # is empty precisely when the filter worked, so a non-zero
            # intervention is the signal. The union covers both arms.
            flagged += int(bool(record["breached_rows"]) or has_correction)
            if has_correction:
                correction_nonzero += 1
                interventions.append(record["intervention"])
            out["solver_failures"] = out.get("solver_failures", 0.0) + float(
                not record["solved"]
            )
            out["certificate_gaps"] = out.get("certificate_gaps", 0.0) + float(
                record["certificate_gap"]
            )
            out["backtracks"] = out.get("backtracks", 0.0) + float(
                record["backtracks"] > 0
            )
            if record["fallback"]:
                key = f"fallback_{record['fallback']}"
                out[key] = out.get(key, 0.0) + 1.0

    if not found:
        return {}

    out.update(
        {
            "governed_rounds": float(rounds),
            "flagged": float(flagged),
            "correction_nonzero": float(correction_nonzero),
        }
    )
    if rounds:
        out["flag_rate"] = flagged / rounds
        out["correction_rate"] = correction_nonzero / rounds
    if interventions:
        out["intervention_mean"] = float(np.mean(interventions))
        out["intervention_max"] = float(np.max(interventions))
    return out


def write_summary(
    arms: dict[str, ArmSummary],
    infeasible_pairs: set[str],
    experiments: dict[str, list[str]] | None = None,
    path: str | Path = "results/summary/arms.json",
    results_dir: str | Path = "results",
) -> Path:
    """Emit every number the notes quote, to one tracked file.

    results/*/certificates.jsonl stays gitignored as raw data, so without this
    the per-round claims in docs/notes/ are reproducible from nothing in the
    repository.
    """
    payload = {
        "infeasible_pairs": sorted(infeasible_pairs),
        "arms": {
            name: {
                "headline": arm.headline(),
                "governed_split": arm.governed_split(infeasible_pairs),
                "filter_telemetry": filter_telemetry(
                    (experiments or {}).get(name, []), infeasible_pairs, results_dir
                ),
                "closures_by_pair": arm.closures_by_pair(),
            }
            for name, arm in arms.items()
        },
    }
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return out


def print_comparison(
    baseline: ArmSummary, treated: ArmSummary, cost: CostOfGuarantee
) -> None:
    """The arm-against-arm table."""
    a, b = baseline.headline(), treated.headline()

    print("\n" + "=" * 78)
    print(f"{treated.name.upper()} vs {baseline.name.upper()}")
    print("=" * 78)

    rows = [
        ("proposals offered", "proposals", "{:.0f}"),
        ("  breaching theta", "offered_breach_rate", "{:.3f}"),
        ("deals settled", "deals_settled", "{:.0f}"),
        ("  breaching theta", "settled_breach_rate", "{:.3f}"),
        ("  meaningful breaches", "deals_meaningful", "{:.0f}"),
        ("  trivial breaches", "deals_trivial", "{:.0f}"),
        ("overspend / value", "overspend_share", "{:.4f}"),
        ("value transacted", "value_transacted", "{:.2f}"),
    ]
    print(f"  {'':<24}{baseline.name:>14}{treated.name:>14}   {'change':>12}")
    print("  " + "-" * 68)
    for label, key, fmt in rows:
        left, right = a.get(key, 0.0), b.get(key, 0.0)
        delta = right - left
        print(
            f"  {label:<24}{fmt.format(left):>14}{fmt.format(right):>14}"
            f"   {fmt.format(delta):>12}"
        )

    print("\n  cost of the guarantee (closure, per pair across seeds)")
    print("  " + "-" * 68)
    print(f"  {'pair':<34}{baseline.name:>12}{treated.name:>12}   note")
    for pair in sorted(
        set(cost.baseline_closures) | set(cost.treated_closures) | set(cost.infeasible)
    ):
        base = cost.baseline_closures.get(pair, 0)
        treat = cost.treated_closures.get(pair, 0)
        if pair in cost.infeasible:
            note = "infeasible: no-close is correct"
        elif pair in cost.lost_to_the_filter:
            note = "<-- LOST TO THE FILTER"
        elif pair in cost.closed_in_neither:
            note = "closed in neither: variance"
        else:
            note = ""
        print(f"  {pair:<34}{base:>12}{treat:>12}   {note}")

    print(f"\n  {cost.describe()}")
