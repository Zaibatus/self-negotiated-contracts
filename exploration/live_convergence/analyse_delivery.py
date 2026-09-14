"""Score the delivery-axis predictions. Reads disk, no API calls.

Analysis rules fixed in PREREGISTRATION-delivery.md before the runs: deadline
movement is |d_k - d_{k-1}| > 1e-9 on x_applied within a (run, pair), counted
over continuation rounds; deadline_observed is read from each RoundRecord's
extraction field.

The filter cannot move d -- rewrite_proposal carries estimated_delivery through
untouched -- so every movement counted here is the agent's own.

Reproduce:
    uv run python exploration/live_convergence/analyse_delivery.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from math import comb
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.marketplace_integration.theta import ContractRegistry  # noqa: E402

HERE = Path(__file__).resolve().parent
DATA = HERE / "data" / "delivery_off09_3_9"
RESULTS = HERE / "results"
TOL = 1e-9


def fisher(a: int, b: int, c: int, d: int) -> float:
    n, r1, c1 = a + b + c + d, a + b, a + c
    if min(n, r1, c1) < 0 or n == 0:
        return 1.0
    obs = comb(r1, a) * comb(n - r1, c1 - a)
    total = tail = 0
    for k in range(max(0, c1 - (n - r1)), min(r1, c1) + 1):
        w = comb(r1, k) * comb(n - r1, c1 - k)
        total += w
        if w <= obs * (1 + 1e-12):
            tail += w
    return tail / total


def rounds_for(prefix: str) -> list[dict]:
    out = []
    for run in sorted(RESULTS.glob(f"{prefix}_v*/certificates.jsonl")):
        for line in run.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                rec["_run"] = run.parent.name
                out.append(rec)
    return out


def moved_d(rows: list[dict]) -> tuple[int, int]:
    """(rounds where d changed from the previous round of that pair, continuations)."""
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        by_pair[(r["_run"], r["pair_id"])].append(r)
    moved = cont = 0
    for seq in by_pair.values():
        seq.sort(key=lambda r: r["round_index"])
        for prev, cur in zip(seq, seq[1:]):
            cont += 1
            if abs(cur["x_applied"][2] - prev["x_applied"][2]) > TOL:
                moved += 1
    return moved, cont


def main() -> None:
    reg = ContractRegistry.from_data_dir(DATA)
    qmin = {k: c.q_min for k, c in reg.contracts.items()}
    A = [r for r in rounds_for("dlv_a") if r["pair_id"] in qmin]
    B = [r for r in rounds_for("dlv_b") if r["pair_id"] in qmin]

    obsB = sum(1 for r in B if (r.get("extraction") or {}).get("deadline_observed"))
    obsA = sum(1 for r in A if (r.get("extraction") or {}).get("deadline_observed"))
    print("=== the delivery axis ===")
    print(f"  arm A  {len(A):4d} rounds   deadline observed {obsA:4d} "
          f"({100 * obsA / max(len(A), 1):5.1f}%)   d values "
          f"{dict(Counter(round(r['x_applied'][2], 1) for r in A).most_common(5))}")
    print(f"  arm B  {len(B):4d} rounds   deadline observed {obsB:4d} "
          f"({100 * obsB / max(len(B), 1):5.1f}%)   d values "
          f"{dict(Counter(round(r['x_applied'][2], 1) for r in B).most_common(5))}")

    print(f"\n=== P11: deadline observed on >= 50% of arm B proposals ===")
    pct = 100 * obsB / max(len(B), 1)
    print(f"  {pct:.1f}%  ->  {'HELD' if pct >= 50 else 'FALSIFIED'}")

    mB, cB = moved_d(B)
    mA, cA = moved_d(A)
    print(f"\n=== P12: d moves on >= 10% of arm B continuation rounds ===")
    r12 = 100 * mB / max(cB, 1)
    print(f"  {mB} of {cB} = {r12:.1f}%  ->  {'HELD' if r12 >= 10 else 'FALSIFIED'}")

    # P13 -- movement rate before vs after the filter first alters price in a pair
    alt: dict[tuple[str, str], list[int]] = defaultdict(list)
    for r in B:
        if abs(r["x_applied"][0] - r["x_proposed"][0]) > 1e-6:
            alt[(r["_run"], r["pair_id"])].append(r["round_index"])
    by_pair: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in B:
        by_pair[(r["_run"], r["pair_id"])].append(r)
    bef = [0, 0]
    aft = [0, 0]
    for key, seq in by_pair.items():
        seq.sort(key=lambda r: r["round_index"])
        for prev, cur in zip(seq, seq[1:]):
            after = any(i < cur["round_index"] for i in alt[key])
            bucket = aft if after else bef
            bucket[1] += 1
            if abs(cur["x_applied"][2] - prev["x_applied"][2]) > TOL:
                bucket[0] += 1
    p13 = fisher(aft[0], aft[1] - aft[0], bef[0], bef[1] - bef[0])
    print(f"\n=== P13: d moves MORE after the filter has altered price (redirect) ===")
    print(f"  before any price alteration  {bef[0]:3d}/{bef[1]:3d} = "
          f"{100 * bef[0] / max(bef[1], 1):5.1f}%")
    print(f"  after  a price alteration    {aft[0]:3d}/{aft[1]:3d} = "
          f"{100 * aft[0] / max(aft[1], 1):5.1f}%")
    up = (aft[0] / max(aft[1], 1)) > (bef[0] / max(bef[1], 1))
    print(f"  Fisher p = {p13:.3e}  ->  {'HELD' if (p13 < 0.05 and up) else 'FALSIFIED'}")

    p14 = fisher(mB, cB - mB, mA, cA - mA)
    print(f"\n=== P14: arm B d-movement rate > arm A, Fisher p < 0.05 ===")
    print(f"  A {mA}/{cA} = {100 * mA / max(cA, 1):.1f}%   "
          f"B {mB}/{cB} = {100 * mB / max(cB, 1):.1f}%   p = {p14:.3e}")
    upB = (mB / max(cB, 1)) > (mA / max(cA, 1))
    print(f"  ->  {'HELD' if (p14 < 0.05 and upB) else 'FALSIFIED'}")

    ups = sum(1 for r in B if r["x_proposed"][1] > qmin[r["pair_id"]] + TOL)
    r15 = 100 * ups / max(len(B), 1)
    print(f"\n=== P15 (control): arm B upsell rate < 15% with no volume clause ===")
    print(f"  {ups} of {len(B)} = {r15:.1f}%  (was 46.1% on quantity_off09)  ->  "
          f"{'HELD' if r15 < 15 else 'FALSIFIED'}")

    out = {
        "arm_a": {"rounds": len(A), "observed": obsA, "moved": mA, "continuations": cA},
        "arm_b": {"rounds": len(B), "observed": obsB, "moved": mB, "continuations": cB,
                  "upsell_rounds": ups},
        "p13": {"before": bef, "after": aft, "fisher_p": p13},
        "p14_fisher_p": p14,
    }
    (HERE / "delivery_axis.json").write_text(json.dumps(out, indent=2, default=float))
    print("\nwritten to delivery_axis.json")


if __name__ == "__main__":
    main()
