"""Open question G8, answered: the trades the platform permits destroy surplus.

Chapter 7 leaves G8 open -- whether a platform that detects a trade it knows
cannot comply should refuse it, or merely decline to filter and let it settle.
It frames refusal as "a platform refusing to let two willing parties transact,
on the basis of a constraint neither of them stated, which is a considerable
power to assert".

The pairs in question are exactly the pairs the payoff model refuses to build
for. `PayoffModel.from_scenario` raises when the buyer's reservation price r is
at or below the seller's marginal cost c, with the reason stated in its own
docstring: "any agreement destroys surplus". Unsatisfiability of theta
(c * q_min > B) and absence of a bargaining zone (r <= c) are the same
condition read two ways, because B is built from the same menu_features that
give r and c comes from the same min_price_factor that gives the cost floor.

So the objection does not apply as stated. The parties are not both better off:
the trade is negative-sum by construction, on the platform's own numbers -- the
very numbers it already trusts enough to build theta from and enforce.

This script computes r - c per pair and cross-references the actual settled
deals from the arm summaries.

Run:  uv run python experiments/no_bargaining_zone.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_integration.theta import ContractRegistry  # noqa: E402

OUT = Path("results/summary/no_bargaining_zone.json")
SOURCES = [("undisclosed_3_9", "undisclosed.json"), ("bargain_3_9", "five_arms.json")]


def zones(data: str) -> dict[str, dict[str, float]]:
    """r, c and the per-deal surplus for every definable pair."""
    reg = ContractRegistry.from_data_dir("data/" + data)
    out: dict[str, dict[str, float]] = {}
    for pid, theta in reg.contracts.items():
        b_id, c_id = pid.split("|", 1)
        business, customer = reg.businesses.get(b_id), reg.customers.get(c_id)
        if business is None or customer is None:
            continue
        reservation = cost = qty = 0.0
        for item, res in customer.menu_features.items():
            listed = business.menu_features.get(item)
            if listed is None:
                continue
            qty += 1.0
            reservation += float(res)
            cost += float(listed) * business.min_price_factor
        if qty <= 0:
            continue
        r, c = reservation / qty, cost / qty
        out[pid] = {
            "r": r, "c": c, "margin": r - c, "quantity": qty,
            "surplus_per_deal": (r - c) * qty,
            "theta_unsatisfiable": bool(theta.cost_floor * theta.q_min > theta.budget),
            "no_bargaining_zone": bool(r <= c),
        }
    return out


def main() -> None:
    report: dict[str, Any] = {}
    for data, summary_file in SOURCES:
        z = zones(data)
        path = Path("results/summary") / summary_file
        if not path.exists():
            continue
        arms = json.loads(path.read_text()).get("arms", {})
        per_arm = []
        for arm, rec in arms.items():
            closures = rec.get("closures_by_pair") if isinstance(rec, dict) else None
            if not closures:
                continue
            bad = [(p, n) for p, n in closures.items()
                   if p in z and z[p]["no_bargaining_zone"]]
            per_arm.append({
                "arm": arm,
                "settled_total": sum(closures.values()),
                "settled_no_zone": sum(n for _, n in bad),
                "surplus_destroyed": sum(n * z[p]["surplus_per_deal"] for p, n in bad),
                "detail": [{"pair": p, "deals": n, "margin": z[p]["margin"],
                            "quantity": z[p]["quantity"],
                            "surplus": n * z[p]["surplus_per_deal"]} for p, n in bad],
            })
        report[data] = {"pairs": z, "arms": per_arm,
                        "no_zone_pairs": sorted(p for p, v in z.items()
                                                if v["no_bargaining_zone"])}

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    for data, rec in report.items():
        print(f"=== {data} ===")
        print(f"  {'pair':<30}{'r':>8}{'c':>8}{'r-c':>9}{'qty':>5}{'surplus/deal':>14}")
        for pid in rec["no_zone_pairs"]:
            v = rec["pairs"][pid]
            print(f"  {pid[:28]:<30}{v['r']:>8.3f}{v['c']:>8.3f}{v['margin']:>9.3f}"
                  f"{v['quantity']:>5.0f}{v['surplus_per_deal']:>14.3f}")
        print(f"\n  {'arm':<14}{'settled':>9}{'no-zone':>9}{'surplus destroyed':>19}")
        for a in rec["arms"]:
            print(f"  {a['arm']:<14}{a['settled_total']:>9}{a['settled_no_zone']:>9}"
                  f"{a['surplus_destroyed']:>19.3f}")
            for d in a["detail"]:
                print(f"      -> {d['pair']} x{d['deals']}  "
                      f"r-c {d['margin']:+.3f}/unit, qty {d['quantity']:.0f}"
                      f"  = {d['surplus']:+.3f}")
        print()
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
