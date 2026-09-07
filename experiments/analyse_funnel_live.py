"""Score the live funnel experiment against its pre-registered predictions.

Predictions are in docs/notes/2026-09-07-PREREGISTRATION-funnel-live.md, written
before any run existed. This script only measures; it does not restate them.

The design question the scenario answers: SCIENCE.md 14 measures synthetically
that the filter helps when B/q_min > p* and harms below. hardundis_010_3_9 is
the first scenario in the project with a pair on the unfavourable side
(b0008|c0003, margin -0.011, predicted L(theta) 1.97%), and it withholds the
budget so the buyer does not police the boundary itself.

Run:  uv run python experiments/analyse_funnel_live.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import PayoffModel  # noqa: E402

DATA = "data/hardundis_010_3_9"
OUT = Path("results/summary/funnel_live.json")
ARMS = {"A": "hu010_a_v%d", "B": "hu010_b_v%d"}


def _rounds(path: Path) -> dict[str, list[dict[str, Any]]]:
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            by[r["pair_id"]].append(r)
    for v in by.values():
        v.sort(key=lambda r: r["round_index"])
    return by


def main() -> None:
    reg = ContractRegistry.from_data_dir(DATA)
    models: dict[str, PayoffModel] = {}
    star: dict[str, np.ndarray] = {}
    margin: dict[str, float] = {}

    for pid, theta in reg.contracts.items():
        b_id, c_id = pid.split("|", 1)
        b, c = reg.businesses.get(b_id), reg.customers.get(c_id)
        if b is None or c is None:
            continue
        try:
            m = PayoffModel.from_scenario(b, c)
        except ValueError:
            continue
        models[pid] = m
        star[pid] = m.nash_bargaining_solution()[0]
        margin[pid] = theta.budget / theta.q_min - float(star[pid][0])

    per_arm: dict[str, dict[str, list[float]]] = {}
    settled_price: dict[str, dict[str, list[float]]] = {}
    lengths: dict[str, list[int]] = defaultdict(list)
    for arm, pattern in ARMS.items():
        vals: dict[str, list[float]] = defaultdict(list)
        prices: dict[str, list[float]] = defaultdict(list)
        for i in range(1, 6):
            path = Path("results") / (pattern % i) / "certificates.jsonl"
            if not path.exists():
                continue
            for pid, recs in _rounds(path).items():
                if pid not in models:
                    continue
                lengths[arm].append(len(recs))
                m, xs = models[pid], star[pid]
                psi_star = m.p_accept(xs) * m.surplus(xs)
                if psi_star <= 1e-9:
                    continue
                x = np.array(recs[-1]["x_applied"], dtype=float)
                vals[pid].append(float(m.p_accept(x) * m.surplus(x) / psi_star))
                prices[pid].append(float(x[0]))
        per_arm[arm] = vals
        settled_price[arm] = prices

    rows = []
    for pid in sorted(models):
        a = np.array(per_arm["A"].get(pid, []))
        b = np.array(per_arm["B"].get(pid, []))
        if not len(a) or not len(b):
            continue
        rows.append({
            "pair": pid, "margin": margin[pid], "below_crossover": margin[pid] < 0,
            "A_mean": float(a.mean()), "B_mean": float(b.mean()),
            "gain": float(b.mean() - a.mean()),
            "A_n": int(len(a)), "B_n": int(len(b)),
            "B_price_mean": float(np.mean(settled_price["B"].get(pid, [np.nan]))),
            "funnel_point": float(reg.contracts[pid].budget / reg.contracts[pid].q_min),
        })

    below = [r for r in rows if r["below_crossover"]]
    above = [r for r in rows if not r["below_crossover"]]
    report = {
        "scenario": DATA, "rows": rows,
        "above_mean_gain": float(np.mean([r["gain"] for r in above])) if above else None,
        "below_mean_gain": float(np.mean([r["gain"] for r in below])) if below else None,
        "median_rounds": {k: float(np.median(v)) for k, v in lengths.items()},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"scenario {DATA}\n")
    print(f"{'pair':<30}{'margin':>8}{'arm A':>9}{'arm B':>9}{'gain':>9}"
          f"{'B price':>10}{'funnel':>9}")
    for r in rows:
        flag = "  <-- BELOW" if r["below_crossover"] else ""
        print(f"{r['pair'][:28]:<30}{r['margin']:>+8.3f}{r['A_mean']:>9.4f}"
              f"{r['B_mean']:>9.4f}{r['gain']:>+9.4f}{r['B_price_mean']:>10.3f}"
              f"{r['funnel_point']:>9.3f}{flag}")
    print(f"\nmean A->B gain, above crossover: {report['above_mean_gain']}")
    print(f"mean A->B gain, below crossover: {report['below_mean_gain']}")
    print(f"median rounds per pair: {report['median_rounds']}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
