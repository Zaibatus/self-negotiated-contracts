"""The deadline enforced, and the opening at gamma: what actually changed.

Two treatments against the same control, arm B on disclosed_offset_low_3_9
at gamma = 0.4 (`arm_b_off09_1..5`):

  * ``arm_b_off09_tmax_v1..5`` ran with --enforce-tmax --t-max 6: the first
    runs in this project where an agent experienced the deadline rather than
    overrunning a bound only the report checks. Questions: does the round
    count actually stop at 6; do deals still close; and does cutting the
    gamma-decay short leave the buyer paying a visible conservatism premium
    (the gamma-liveness note predicts h_0 * (1-gamma)^(T_max-1) instead of
    the cents a 10-15 round negotiation decays to).

  * ``arm_b_off09_open04_v1..5`` ran with --open-with-gamma: route 2 of the
    gamma-independence note. The opening is corrected by one barrier step at
    gamma = 0.4 instead of the gamma = 1 projection, so the forwarded opener
    still breaches -- knowingly -- and the DCBF predicts the violation decays
    at ratio 1 - gamma per round. This is the controlled experiment on the
    module docstring's third asymmetry, and its safety cost (breach-rounds
    that the default design never emits) is reported, not hidden.

Certificates are read from results/; deals are replayed from Postgres, so
run with the marketplace .env sourced. No LLM calls.

Reproduce:
    uv run python exploration/live_convergence/analyse_enforced_deadline.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.marketplace_integration.replay import (  # noqa: E402
    _dsn_from_env,
    replay_schema,
)
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402

DATA = ROOT / "data" / "disclosed_offset_low_3_9"
RESULTS = ROOT / "results"

FAMILIES: dict[str, str] = {
    "baseline": "arm_b_off09_[1-5]",
    "tmax6": "arm_b_off09_tmax_v[1-5]",
    "open04": "arm_b_off09_open04_v[1-5]",
}
ECON_ROWS = ("budget", "cost_floor")
TOL = 1e-9


def econ_margin(rec: dict) -> float:
    h = rec["h_applied"]
    return min(h[k] for k in ECON_ROWS if k in h)


def load_family(pattern: str, registry: ContractRegistry):
    records: list[dict] = []
    reports: list[dict] = []
    schemas: list[str] = []
    for run in sorted(RESULTS.glob(pattern)):
        path = run / "certificates.jsonl"
        if not path.exists():
            continue
        schemas.append(run.name)
        reports.append(json.loads((run / "report.json").read_text()))
        for line in path.read_text().splitlines():
            if line.strip():
                rec = json.loads(line)
                rec["_run"] = run.name
                records.append(rec)

    def satisfiable(pair: str) -> bool:
        b_id, c_id = pair.split("|")
        c = registry.get(b_id, c_id)
        return bool(c is not None and c.without_deadline().is_satisfiable())

    records = [r for r in records if satisfiable(r["pair_id"])]
    return schemas, records, reports


def certificates_view(name: str, records: list[dict], registry: ContractRegistry):
    trajectories: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        trajectories[f"{r['_run']}|{r['pair_id']}"].append(r)

    lengths = sorted(len(t) for t in trajectories.values())
    breach_rounds = sum(bool(r.get("breach")) for r in records)

    premiums = []
    for key, rounds in trajectories.items():
        pair = key.split("|", 1)[1]
        b_id, c_id = pair.split("|")
        contract = registry.get(b_id, c_id)
        if contract is not None:
            premiums.append(
                float(rounds[-1]["x_applied"][0]) - contract.cost_floor
            )

    # Opening-violation decay: for trajectories that open in breach, the
    # per-step ratio |h_{k+1}| / |h_k| while h < 0. DCBF prediction: <= 1 - gamma.
    decay_ratios: list[float] = []
    recovery_rounds: list[int] = []
    for rounds in trajectories.values():
        hs = [econ_margin(r) for r in rounds]
        if hs[0] >= -TOL:
            continue
        recovered = next((k for k, h in enumerate(hs) if h >= -1e-6), None)
        if recovered is not None:
            recovery_rounds.append(recovered)
        for a, b in zip(hs, hs[1:]):
            if a < -1e-6:
                decay_ratios.append(max(b, 0.0) / a if b < 0 else 0.0)
    decay_ratios = [abs(r) for r in decay_ratios]

    return {
        "trajectories": len(trajectories),
        "rounds": len(records),
        "breach_rounds": int(breach_rounds),
        "length_median": float(np.median(lengths)) if lengths else None,
        "length_max": max(lengths) if lengths else None,
        "premium_median": float(np.median(premiums)) if premiums else None,
        "premium_mean": float(np.mean(premiums)) if premiums else None,
        "openings_in_breach": len(recovery_rounds),
        "recovery_rounds_median": (
            float(np.median(recovery_rounds)) if recovery_rounds else None
        ),
        "violation_decay_ratio_median": (
            float(np.median(decay_ratios)) if decay_ratios else None
        ),
        "violation_decay_steps": len(decay_ratios),
    }


async def deals_view(schemas: list[str], registry: ContractRegistry) -> dict:
    dsn = _dsn_from_env()
    deals = []
    for schema in schemas:
        result = await replay_schema(schema, registry, dsn)
        deals.extend(result.deals)
    sat = [d for d in deals if d.satisfiable]
    return {
        "deals": len(deals),
        "deals_satisfiable_pairs": len(sat),
        "deals_breached": int(sum(d.breached for d in sat)),
        "deals_meaningful": int(
            sum(d.classification == "meaningful" for d in deals)
        ),
        "total_overspend": float(sum(d.overspend for d in deals)),
        "mean_spend": float(np.mean([d.spend for d in sat])) if sat else None,
    }


def main() -> None:
    registry = ContractRegistry.from_data_dir(DATA)
    out: dict[str, dict] = {}
    for name, pattern in FAMILIES.items():
        schemas, records, reports = load_family(pattern, registry)
        if len(schemas) != 5:
            print(f"WARNING: {name} matched {len(schemas)} runs, expected 5")
        view = certificates_view(name, records, registry)
        view["refused_deadline"] = int(
            sum(r["report"].get("proposals_refused_deadline", 0) for r in reports)
        )
        view["pairs_deadline_hit"] = int(
            sum(r["report"].get("pairs_deadline_hit", 0) for r in reports)
        )
        view["deals"] = asyncio.run(deals_view(schemas, registry))
        out[name] = view

    cols = list(FAMILIES)
    rows = [
        ("trajectories (satisfiable pairs)", "trajectories", "{}"),
        ("governed rounds", "rounds", "{}"),
        ("breach rounds", "breach_rounds", "{}"),
        ("median rounds/pair", "length_median", "{:.1f}"),
        ("max rounds/pair", "length_max", "{}"),
        ("proposals refused (deadline)", "refused_deadline", "{}"),
        ("pairs that hit the deadline", "pairs_deadline_hit", "{}"),
        ("median premium over cost floor", "premium_median", "{:.4f}"),
        ("openings forwarded in breach", "openings_in_breach", "{}"),
        ("median rounds to recover", "recovery_rounds_median", "{}"),
        ("violation decay ratio (vs 0.6)", "violation_decay_ratio_median", "{}"),
    ]
    width = max(len(r[0]) for r in rows) + 2
    print(f"{'':{width}}" + "".join(f"{c:>12}" for c in cols))
    for label, key, fmt in rows:
        cells = []
        for c in cols:
            v = out[c].get(key)
            cells.append("-" if v is None else fmt.format(v))
        print(f"{label:{width}}" + "".join(f"{c:>12}" for c in cells))
    print()
    for label, key, fmt in [
        ("deals settled", "deals", "{}"),
        ("deals on satisfiable pairs", "deals_satisfiable_pairs", "{}"),
        ("  of which breached", "deals_breached", "{}"),
        ("meaningful-breach deals", "deals_meaningful", "{}"),
        ("total overspend", "total_overspend", "{:.2f}"),
    ]:
        cells = []
        for c in cols:
            v = out[c]["deals"].get(key)
            cells.append("-" if v is None else fmt.format(v))
        print(f"{label:{width}}" + "".join(f"{c:>12}" for c in cells))

    path = ROOT / "results" / "summary" / "enforced_deadline_off09.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"\nwritten to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
