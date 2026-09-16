"""Does gamma do anything once the negotiation is long enough to see it?

The gamma-independence note (2026-08-07) measured gamma in {0.2, 0.4, 0.7,
1.0} on bargain_3_9 and found it inert: negotiations ran 1.2-1.4 rounds,
73-86% of governed rounds were the opening projection (which hardcodes
gamma = 1), and the margin was 0.000 at every gamma. Its "what would make
gamma bite" section named the missing regime: a scenario that sustains six
to ten rounds. disclosed_offset_low_3_9 (f = 0.90) is that scenario --
median 6 rounds under arm B, filter binding on 79% of rounds.

This reads the gamma sweep re-run there. Per cell:

  * the boundary layer: min true h over active rows at the applied state,
    on continuation rounds only (the opening projection ignores gamma by
    design, so folding it in would dilute the treatment with a constant);
  * the DCBF's own prediction to check it against: at the binding row,
    h_{k+1} >= (1 - gamma) h_k, so a cautious gamma approaches the boundary
    geometrically slower and should rest at a wider margin;
  * the conservatism premium: mean cost_floor dual, which section 6 says a
    small gamma inflates;
  * negotiation length and the contraction rate rho (same floor-offset fit
    as fit_contraction.py), because "gamma changes the trajectory" and
    "gamma changes where it ends" are different claims.

Reads disk only, no API calls.

Reproduce:
    uv run python exploration/live_convergence/analyse_gamma_off09.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from experiments.fit_contraction import (  # noqa: E402
    MIN_POINTS_FOR_FIT,
    fit_geometric,
)
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import PayoffModel, dist_M  # noqa: E402

DATA = ROOT / "data" / "disclosed_offset_low_3_9"
RESULTS = ROOT / "results"
OUT = Path(__file__).resolve().parent

# Explicit globs, cell by cell. A prefix glob like arm_b_off09_* would fold
# every later off09 family (g02, g07, g10, tmax, open04) into the 0.4 cell.
CELLS: dict[float, str] = {
    0.2: "arm_b_off09_g02_v[1-5]",
    0.4: "arm_b_off09_[1-5]",
    0.7: "arm_b_off09_g07_v[1-5]",
    1.0: "arm_b_off09_g10_v[1-5]",
}
TOL = 1e-9


def load_cell(pattern: str) -> tuple[list[dict], dict[str, list[np.ndarray]]]:
    """All round records, and the binding trajectory per run|pair."""
    records: list[dict] = []
    trajectories: dict[str, list[np.ndarray]] = defaultdict(list)
    runs = sorted(RESULTS.glob(pattern))
    for run in runs:
        path = run / "certificates.jsonl"
        if not path.exists():
            continue
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            rec["_run"] = run.name
            records.append(rec)
            trajectories[f"{run.name}|{rec['pair_id']}"].append(
                np.asarray(rec["x_applied"], dtype=float)
            )
    if len(runs) != 5:
        print(f"  WARNING: {pattern} matched {len(runs)} runs, expected 5")
    return records, trajectories


def cell_summary(
    gamma: float,
    records: list[dict],
    trajectories: dict[str, list[np.ndarray]],
    registry: ContractRegistry,
) -> dict:
    # A pair with an empty safe set is forwarded untouched by design (G8) and
    # every one of its rounds is recorded as a breach. That is the infeasible
    # category, not a filter failure, so it is split out before any statistic
    # that speaks about governance.
    def satisfiable(pair: str) -> bool:
        b_id, c_id = pair.split("|")
        contract = registry.get(b_id, c_id)
        return bool(
            contract is not None and contract.without_deadline().is_satisfiable()
        )

    unsat_pairs = {r["pair_id"] for r in records if not satisfiable(r["pair_id"])}
    breach_unsat = sum(
        bool(r.get("breach")) for r in records if r["pair_id"] in unsat_pairs
    )
    breach_governed = sum(
        bool(r.get("breach")) for r in records if r["pair_id"] not in unsat_pairs
    )
    records = [r for r in records if r["pair_id"] not in unsat_pairs]
    trajectories = {
        k: t for k, t in trajectories.items()
        if k.split("|", 1)[1] not in unsat_pairs
    }

    lengths = sorted(len(t) for t in trajectories.values())
    cont = [r for r in records if r["round_index"] >= 1]
    openings = [r for r in records if r["round_index"] == 0]

    # Margin over the economic rows only. The q_min box row is structurally
    # zero on this scenario (the basket sets q = q_min exactly, and the box
    # rows have never bound in any run in the project), so a min over all
    # rows reads 0.000 everywhere and hides the actual boundary layer.
    def margin(rec: dict) -> float:
        h = rec["h_applied"]
        return min(h[k] for k in ("budget", "cost_floor") if k in h)

    margins = [margin(r) for r in cont]
    intervened = [r for r in cont if r.get("intervention", 0.0) > TOL]
    margins_intervened = [margin(r) for r in intervened]

    # The DCBF signature is a decay profile, not a rest margin: from an
    # opening projected into C, h at the binding row may shrink by at most a
    # factor (1 - gamma) per round, so cautious cells should show a slower
    # geometric approach to the boundary. Mean min-h by round index.
    by_round: dict[int, list[float]] = defaultdict(list)
    for r in records:
        by_round[r["round_index"]].append(margin(r))
    h_profile = [
        {"round": k, "mean_min_h": float(np.mean(v)), "n": len(v)}
        for k, v in sorted(by_round.items())
    ]

    cf_duals = [
        float(r["duals"]["cost_floor"])
        for r in cont
        if "cost_floor" in r.get("duals", {})
    ]

    # Where the negotiation ends: price premium of the last on-table terms
    # over the pair's cost floor. If a cautious filter parks the state short
    # of the boundary, the buyer pays the conservatism premium in the price.
    premiums = []
    for key, traj in trajectories.items():
        pair = key.split("|", 1)[1]
        b_id, c_id = pair.split("|")
        contract = registry.get(b_id, c_id)
        if contract is not None and traj:
            premiums.append(float(traj[-1][0]) - contract.cost_floor)

    # Contraction. Distance to the unconstrained NBS rises here by
    # construction (the rest point is constrained), so rho is fitted twice:
    # against x*_NBS for continuity with fit_contraction.py, and against the
    # trajectory's own final point, which is the convergence the deal shows.
    rhos_nbs: list[float] = []
    rhos_rest: list[float] = []
    models: dict[str, PayoffModel] = {}
    for key, traj in trajectories.items():
        pair = key.split("|", 1)[1]
        if pair not in models:
            b_id, c_id = pair.split("|")
            b = registry.businesses.get(b_id)
            c = registry.customers.get(c_id)
            if b is None or c is None:
                continue
            try:
                models[pair] = PayoffModel.from_scenario(b, c)
            except ValueError:
                continue
        x_star, _ = models[pair].nash_bargaining_solution()
        if len(traj) >= MIN_POINTS_FOR_FIT:
            d = np.array([dist_M(x, x_star) for x in traj])
            if float(d.min()) > 0.0:
                rho, _, _ = fit_geometric(d)
                if np.isfinite(rho):
                    rhos_nbs.append(rho)
        # Per-step contraction toward the trajectory's own rest point. A
        # two-parameter fit needs the distance to stay positive, and most
        # trajectories sit exactly on their final point for many trailing
        # rounds, so per-trajectory fits would keep almost nothing. The
        # per-step ratio d_{k+1}/d_k over steps with d_k > 0 uses every
        # approach step instead; under the DCBF the binding row admits
        # h_{k+1} >= (1 - gamma) h_k, so the prediction is ratio ~ 1 - gamma.
        rest = traj[-1]
        d = [dist_M(x, rest) for x in traj]
        for a, b in zip(d, d[1:]):
            if a > 1e-6:
                rhos_rest.append(float(b / a))
    rhos = rhos_nbs

    return {
        "pairs_unsatisfiable": len(unsat_pairs),
        "breach_rounds_unsatisfiable_pairs": int(breach_unsat),
        "breach_rounds_governed_pairs": int(breach_governed),
        "h_profile": h_profile,
        "settled_premium_over_cost_floor": {
            "mean": float(np.mean(premiums)) if premiums else None,
            "median": float(np.median(premiums)) if premiums else None,
            "n": len(premiums),
        },
        "contraction_to_rest_point": {
            "steps": len(rhos_rest),
            "rho_median": float(np.median(rhos_rest)) if rhos_rest else None,
            "rho_iqr": (
                [
                    float(np.percentile(rhos_rest, 25)),
                    float(np.percentile(rhos_rest, 75)),
                ]
                if rhos_rest
                else None
            ),
            "prediction_one_minus_gamma": 1.0 - gamma,
        },
        "gamma": gamma,
        "runs": len({r["_run"] for r in records}),
        "trajectories": len(trajectories),
        "rounds_governed": len(records),
        "length": {
            "median": float(np.median(lengths)) if lengths else None,
            "max": max(lengths) if lengths else None,
            "frac_ge4": (
                float(np.mean([n >= 4 for n in lengths])) if lengths else None
            ),
        },
        "openings_outside_C": int(
            sum(r.get("intervention", 0.0) > TOL for r in openings)
        ),
        "continuation": {
            "rounds": len(cont),
            "intervention_rate": (
                float(np.mean([r.get("intervention", 0.0) > TOL for r in cont]))
                if cont
                else None
            ),
            "mean_intervention": (
                float(np.mean([r.get("intervention", 0.0) for r in cont]))
                if cont
                else None
            ),
            "margin_mean": float(np.mean(margins)) if margins else None,
            "margin_median": float(np.median(margins)) if margins else None,
            "margin_mean_intervened": (
                float(np.mean(margins_intervened)) if margins_intervened else None
            ),
            "cost_floor_dual_mean": (
                float(np.mean(cf_duals)) if cf_duals else None
            ),
            "cost_floor_dual_active_frac": (
                float(np.mean([d > TOL for d in cf_duals])) if cf_duals else None
            ),
        },
        "contraction": {
            "fits": len(rhos),
            "rho_median": float(np.median(rhos)) if rhos else None,
            "rho_iqr": (
                [float(np.percentile(rhos, 25)), float(np.percentile(rhos, 75))]
                if rhos
                else None
            ),
        },
    }


def main() -> None:
    registry = ContractRegistry.from_data_dir(DATA)
    cells = []
    for gamma, pattern in sorted(CELLS.items()):
        records, trajectories = load_cell(pattern)
        cells.append(cell_summary(gamma, records, trajectories, registry))

    header = (
        f"{'gamma':>5} {'traj':>5} {'rounds':>7} {'breach':>6} {'med len':>7} "
        f"{'interv%':>8} {'margin':>8} {'premium':>8} {'cf dual':>8} "
        f"{'rho_nbs':>8} {'rho_rest':>8}"
    )
    print(header)
    print("-" * len(header))
    for c in cells:
        k = c["continuation"]
        print(
            f"{c['gamma']:>5.1f} {c['trajectories']:>5} {c['rounds_governed']:>7} "
            f"{c['breach_rounds_governed_pairs']:>6} {c['length']['median']:>7.1f} "
            f"{100 * k['intervention_rate']:>7.1f}% "
            f"{k['margin_median']:>8.4f} "
            f"{c['settled_premium_over_cost_floor']['median']:>8.4f} "
            f"{k['cost_floor_dual_mean']:>8.4f} "
            f"{(c['contraction']['rho_median'] if c['contraction']['rho_median'] is not None else float('nan')):>8.3f} "
            f"{(c['contraction_to_rest_point']['rho_median'] if c['contraction_to_rest_point']['rho_median'] is not None else float('nan')):>8.3f}"
        )
        profile = "  h by round: " + " ".join(
            f"{p['round']}:{p['mean_min_h']:.3f}(n{p['n']})"
            for p in c["h_profile"][:8]
        )
        print(profile)

    out = {
        "scenario": str(DATA.relative_to(ROOT)),
        "design": "arm B (imposed theta, filter), 5 seeds per gamma",
        "cells": cells,
    }
    path = ROOT / "results" / "summary" / "gamma_liveness_off09.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\nwritten to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
