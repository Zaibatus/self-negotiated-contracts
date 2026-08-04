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

from dataclasses import dataclass, field

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
