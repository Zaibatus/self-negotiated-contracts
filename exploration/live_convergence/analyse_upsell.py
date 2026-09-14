"""Score the upsell-asymmetry predictions. Reads disk, no API calls.

Analysis rules were fixed in PREREGISTRATION-upsell-asymmetry.md before the
runs: an upsell is `q > q_min + 1e-9` on `x_proposed` -- what the agent put on
the table -- never on `x_applied`, which is what the filter left behind.

Reproduce:
    uv run python exploration/live_convergence/analyse_upsell.py
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.marketplace_integration.theta import ContractRegistry  # noqa: E402

DATA = Path(__file__).resolve().parent / "data" / "quantity_off09_3_9"
RESULTS = Path(__file__).resolve().parent / "results"
TOL = 1e-9


def rounds_for(arm: str) -> list[dict]:
    out = []
    for run in sorted(RESULTS.glob(f"qty_{arm}_v*/certificates.jsonl")):
        for line in run.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                rec["_run"] = run.parent.name
                out.append(rec)
    return out


def fisher(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact on [[a,b],[c,d]], by exact enumeration."""
    from math import comb

    n = a + b + c + d
    r1, c1 = a + b, a + c
    obs = comb(r1, a) * comb(n - r1, c1 - a)
    total = tail = 0
    for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1):
        w = comb(r1, k) * comb(n - r1, c1 - k)
        total += w
        if w <= obs * (1 + 1e-12):
            tail += w
    return tail / total


def main() -> None:
    reg = ContractRegistry.from_data_dir(DATA)
    qmin = {k: c.q_min for k, c in reg.contracts.items()}

    stats = {}
    for arm in ("a", "b"):
        rows = rounds_for(arm)
        rows = [r for r in rows if r["pair_id"] in qmin]
        ups = [r for r in rows if r["x_proposed"][1] > qmin[r["pair_id"]] + TOL]
        per_pair = Counter(r["pair_id"] + "|" + r["_run"] for r in rows)
        stats[arm] = {
            "seeds": len({r["_run"] for r in rows}),
            "rounds": len(rows),
            "upsell_rounds": len(ups),
            "upsell_rate": len(ups) / len(rows) if rows else 0.0,
            "median_rounds_per_pair": statistics.median(per_pair.values()) if per_pair else 0,
            "rows": rows,
            "ups": ups,
        }

    A, B = stats["a"], stats["b"]
    print("=== upsell rate (q > q_min on x_proposed) ===")
    for arm, s in (("A (off)", A), ("B (filter)", B)):
        print(f"  {arm:12s} {s['upsell_rounds']:3d} of {s['rounds']:4d} rounds "
              f"= {100 * s['upsell_rate']:5.1f}%   ({s['seeds']} seeds)")

    print(f"\n=== P6: arm A shows >= 1 upsell round over 5 seeds ===")
    print(f"  observed {A['upsell_rounds']}  ->  "
          f"{'HELD' if A['upsell_rounds'] >= 1 else 'FALSIFIED'}")

    p = fisher(B["upsell_rounds"], B["rounds"] - B["upsell_rounds"],
               A["upsell_rounds"], A["rounds"] - A["upsell_rounds"])
    print(f"\n=== P7: arm B rate > arm A rate, Fisher exact p < 0.05 ===")
    print(f"  p = {p:.2e}   B>A: {B['upsell_rate'] > A['upsell_rate']}  ->  "
          f"{'HELD' if (p < 0.05 and B['upsell_rate'] > A['upsell_rate']) else 'FALSIFIED'}")

    # P8 -- was an upsell preceded, in the same pair AND run, by a round in
    # which the filter altered price?
    price_altered_before: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in B["rows"]:
        if abs(r["x_applied"][0] - r["x_proposed"][0]) > 1e-6:
            price_altered_before[(r["_run"], r["pair_id"])].append(r["round_index"])
    preceded = sum(
        1 for r in B["ups"]
        if any(i < r["round_index"]
               for i in price_altered_before[(r["_run"], r["pair_id"])])
    )
    n_up = len(B["ups"])
    frac = preceded / n_up if n_up else 0.0
    print(f"\n=== P8: >= 2/3 of arm B upsells preceded by a price alteration in that pair ===")
    print(f"  {preceded} of {n_up} = {frac:.3f}  ->  "
          f"{'HELD' if frac >= 2 / 3 else 'FALSIFIED'}")

    duals = Counter()
    for r in B["rows"]:
        for k, v in (r.get("duals") or {}).items():
            if abs(v) > 1e-6:
                duals[k] += 1
    qd = duals["q_min"] + duals["q_max"]
    print(f"\n=== P9: quantity duals active on < 5% of governed rounds ===")
    print(f"  all duals: {dict(duals)}")
    print(f"  quantity {qd}/{B['rounds']} = {100 * qd / max(B['rounds'], 1):.1f}%  ->  "
          f"{'HELD' if 100 * qd / max(B['rounds'], 1) < 5 else 'FALSIFIED'}")

    print(f"\n=== P10: median arm B rounds per pair < 6 ===")
    print(f"  median {B['median_rounds_per_pair']}  ->  "
          f"{'HELD' if B['median_rounds_per_pair'] < 6 else 'FALSIFIED'}")

    out = {k: {kk: vv for kk, vv in v.items() if kk not in ("rows", "ups")}
           for k, v in stats.items()}
    out["fisher_p"] = p
    out["p8_preceded"] = f"{preceded}/{n_up}"
    out["duals"] = dict(duals)
    path = Path(__file__).resolve().parent / "upsell_asymmetry.json"
    path.write_text(json.dumps(out, indent=2, default=float))
    print(f"\nwritten to {path.name}")


if __name__ == "__main__":
    main()
