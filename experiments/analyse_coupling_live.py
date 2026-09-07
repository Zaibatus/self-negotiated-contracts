"""Score the live coupling experiment against its pre-registered predictions.

Predictions in docs/notes/2026-09-07-PREREGISTRATION-coupling-live.md, written
before any run existed. This script measures; it does not restate them.

C1 activation -- does the shared:capacity row ever appear? It is only built when
   a business has a concurrently live peer pair, so its presence is the test.
C2 safety    -- do settled quantities on the coupled business respect Q, and is
   the capacity row ever breached on a governed round?
C3 dual      -- is the multiplier positive where the row binds?
C4 economics -- how far is the realised split from the equalised-marginal
   allocation of SCIENCE.md 22? Expected to be far.

Run:  uv run python experiments/analyse_coupling_live.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import SHARED_CAPACITY_LABEL  # noqa: E402
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402

DATA = "data/coupled_3_9"
CAPACITY_FACTOR = 0.67
OUT = Path("results/summary/coupling_live.json")
PATTERN = "coupled_b_v%d"
HOST = "business_0001"


def main() -> None:
    reg = ContractRegistry.from_data_dir(DATA, capacity_factor=CAPACITY_FACTOR)
    capacity = reg.capacity_for(HOST)
    host_pairs = [p for p in reg.contracts if p.startswith(HOST + "|")]

    seeds: list[dict[str, Any]] = []
    for i in range(1, 6):
        path = Path("results") / (PATTERN % i) / "certificates.jsonl"
        if not path.exists():
            continue
        rows = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
        host_rows = [r for r in rows if r.get("business_id") == HOST]
        with_cap = [r for r in host_rows
                    if SHARED_CAPACITY_LABEL in (r.get("h_applied") or {})]
        breaches = [r for r in with_cap
                    if (r["h_applied"] or {}).get(SHARED_CAPACITY_LABEL, 0.0) < -1e-9]
        duals = [float((r.get("duals") or {}).get(SHARED_CAPACITY_LABEL, 0.0))
                 for r in with_cap]
        last_q: dict[str, float] = {}
        for r in host_rows:
            last_q[r["pair_id"]] = float(r["x_applied"][1])
        seeds.append({
            "seed": i,
            "host_rounds": len(host_rows),
            "capacity_rows": len(with_cap),
            "capacity_breaches": len(breaches),
            "duals_positive": int(sum(1 for d in duals if d > 1e-12)),
            "dual_max": float(max(duals)) if duals else 0.0,
            "final_q_by_pair": last_q,
            "sum_final_q": float(sum(last_q.values())),
            "respects_capacity": bool(sum(last_q.values()) <= capacity + 1e-9),
        })

    fired = [s for s in seeds if s["capacity_rows"] > 0]
    report = {
        "scenario": DATA, "capacity_factor": CAPACITY_FACTOR,
        "capacity_Q": capacity, "host": HOST, "host_pairs": host_pairs,
        "seeds": seeds,
        "C1_fired_on": len(fired), "C1_total_seeds": len(seeds),
        "C2_total_capacity_breaches": sum(s["capacity_breaches"] for s in seeds),
        "C3_any_positive_dual": bool(any(s["duals_positive"] for s in seeds)),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"scenario {DATA}   host {HOST}   Q = {capacity}")
    print(f"host pairs: {host_pairs}\n")
    print(f"{'seed':>5}{'host rounds':>13}{'capacity rows':>15}{'breaches':>10}"
          f"{'duals>0':>9}{'sum final q':>13}{'<= Q':>7}")
    for s in seeds:
        print(f"{s['seed']:>5}{s['host_rounds']:>13}{s['capacity_rows']:>15}"
              f"{s['capacity_breaches']:>10}{s['duals_positive']:>9}"
              f"{s['sum_final_q']:>13.2f}{str(s['respects_capacity']):>7}")
    print(f"\nC1  capacity row fired on {report['C1_fired_on']} of "
          f"{report['C1_total_seeds']} seeds")
    if report["C1_fired_on"] == 0:
        print("    -> EXPERIMENT VOID for coupling: the clause never activated.")
    print(f"C2  capacity breaches on governed rounds: "
          f"{report['C2_total_capacity_breaches']}")
    print(f"C3  any positive capacity dual: {report['C3_any_positive_dual']}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
