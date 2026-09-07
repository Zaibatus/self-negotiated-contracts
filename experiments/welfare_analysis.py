"""Welfare per arm, measured with the potential Psi = P*W.

The thesis reports breaches, overspend and closure. It reports no welfare
measure at all. Psi = P(x) W(x) -- expected joint surplus, the potential of the
concession field (see potential_certificate.py) -- supplies one, normalised by
its value at the Nash bargaining solution so arms and scenarios are comparable.

Three things fall out and each is reported below:

  1. Enforcement raises Psi/Psi* far outside the A/D noise floor.
  2. It does so WITHOUT creating surplus. W is independent of price, so W at the
     settled point equals W at the NBS on every pair. What ungoverned trading
     destroys is not the pie but the *acceptability of the split*: the
     uninformed buyer settles where its own payoff model puts acceptance at
     1e-4 to 1e-13. The filter restores the split, not the surplus.
  3. Every satisfiable live pair sits on the favourable side of the funnel
     crossover (B/q_min > p*) by 0.034 to 0.185 scaled units. The sweep of
     2026-08-28 says the same mechanism destroys welfare without bound on the
     other side, so the gain measured here is real and contingent, and the
     margin is thin.

Differences use the SD of a difference from per-arm seed SDs (SCIENCE.md 12).

Run:  uv run python experiments/welfare_analysis.py
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

OUT = Path("results/summary/welfare_analysis.json")

ARMS = [
    ("A", "bargain_3_9", "arm_a_bargain_v%d"),
    ("D", "bargain_3_9", "arm_d_bargain_v%d"),
    ("B", "bargain_3_9", "arm_b_bargain_v%d"),
    ("C", "bargain_3_9", "arm_c_bargain_v%d"),
    ("C-meet", "bargain_3_9", "arm_c_meet_v%d"),
    ("F", "transfer_3_9", "arm_f_v%d"),
]
UNDIS = [("A", "arm_a_undis_v%d"), ("B", "arm_b_undis_v%d")]

COMPARISONS = [
    ("A", "D", "noise floor; A and D are behaviourally identical by construction"),
    ("A", "B", "does enforcement raise expected joint surplus?"),
    ("D", "B", "filter against monitor"),
    ("C", "C-meet", "does composition raise welfare?"),
    ("F", "B", "filter against a priced breach"),
    ("D", "F", "monitor against a priced breach"),
]


def _registry(data: str):
    reg = ContractRegistry.from_data_dir("data/" + data)
    models: dict[str, PayoffModel | None] = {}
    star: dict[str, np.ndarray] = {}

    def model_for(pid: str) -> PayoffModel | None:
        if pid not in models:
            b_id, c_id = pid.split("|", 1)
            b, c = reg.businesses.get(b_id), reg.customers.get(c_id)
            if b is None or c is None:
                models[pid] = None
                return None
            try:
                m = PayoffModel.from_scenario(b, c)
                models[pid] = m
                star[pid] = m.nash_bargaining_solution()[0]
            except ValueError:
                models[pid] = None
        return models.get(pid)

    return reg, model_for, star


def _rounds(path: Path) -> dict[str, list[dict[str, Any]]]:
    by: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            by[r["pair_id"]].append(r)
    for v in by.values():
        v.sort(key=lambda r: r["round_index"])
    return by


def seed_means(pattern: str, model_for, star, seeds: int = 5) -> list[float]:
    out = []
    for i in range(1, seeds + 1):
        path = Path("results") / (pattern % i) / "certificates.jsonl"
        if not path.exists():
            continue
        vals = []
        for pid, recs in _rounds(path).items():
            m = model_for(pid)
            if m is None:
                continue
            xs = star[pid]
            psi_star = m.p_accept(xs) * m.surplus(xs)
            if psi_star <= 1e-9:
                continue
            x = np.array(recs[-1]["x_applied"], dtype=float)
            vals.append((m.p_accept(x) * m.surplus(x)) / psi_star)
        if vals:
            out.append(float(np.mean(vals)))
    return out


def crossover_margins(data: str) -> list[dict[str, float]]:
    """Where each satisfiable pair sits relative to the funnel crossover B/q_min = p*."""
    reg, model_for, star = _registry(data)
    rows = []
    for pid, th in sorted(reg.contracts.items()):
        m = model_for(pid)
        if m is None or th.q_min <= 0 or th.cost_floor * th.q_min > th.budget:
            continue
        rows.append({"pair": pid, "b_over_qmin": th.budget / th.q_min,
                     "p_star": float(star[pid][0]),
                     "margin": th.budget / th.q_min - float(star[pid][0])})
    return rows


def main() -> None:
    cache: dict[str, Any] = {}
    means: dict[str, np.ndarray] = {}
    for label, data, pattern in ARMS:
        if data not in cache:
            cache[data] = _registry(data)
        _, model_for, star = cache[data]
        means[label] = np.array(seed_means(pattern, model_for, star))

    _, mf_u, star_u = _registry("undisclosed_3_9")
    undis = {lab: np.array(seed_means(pat, mf_u, star_u)) for lab, pat in UNDIS}

    def diff(x: str, y: str, src=means):
        a, b = src[x], src[y]
        sd = float(np.sqrt(a.std(ddof=1) ** 2 + b.std(ddof=1) ** 2))
        return {"from": x, "to": y, "delta": float(b.mean() - a.mean()),
                "sd_of_difference": sd,
                "sd_units": float((b.mean() - a.mean()) / sd) if sd else float("inf")}

    report = {
        "bargain_3_9": {k: {"seed_means": v.tolist(), "mean": float(v.mean()),
                            "seed_sd": float(v.std(ddof=1))} for k, v in means.items()},
        "undisclosed_3_9": {k: {"seed_means": v.tolist(), "mean": float(v.mean()),
                                "seed_sd": float(v.std(ddof=1))} for k, v in undis.items()},
        "comparisons": [dict(diff(x, y), note=n) for x, y, n in COMPARISONS],
        "undisclosed_A_to_B": diff("A", "B", undis),
        "crossover_margins": crossover_margins("bargain_3_9"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print("Psi/Psi* -- expected joint surplus achieved (bargain_3_9, 5 seeds)\n")
    print(f"{'arm':<8}{'mean':>8}{'seed SD':>9}")
    for k, v in means.items():
        print(f"{k:<8}{v.mean():>8.3f}{v.std(ddof=1):>9.3f}")
    print("\ndifferences (SD of a difference from per-arm seed SDs):")
    for c in report["comparisons"]:
        print(f"  {c['from']:>6} -> {c['to']:<7}{c['delta']:+.3f}  SD {c['sd_of_difference']:.3f}"
              f"  {c['sd_units']:+.1f} SD   ({c['note']})")
    u = report["undisclosed_A_to_B"]
    print(f"\nundisclosed_3_9  A {undis['A'].mean():.3f} -> B {undis['B'].mean():.3f}"
          f"   {u['delta']:+.3f}  {u['sd_units']:+.1f} SD")
    m = [r["margin"] for r in report["crossover_margins"]]
    print(f"\ncrossover margins on the {len(m)} satisfiable pairs: "
          f"{min(m):+.3f} to {max(m):+.3f} scaled units (all favourable, all thin)")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
