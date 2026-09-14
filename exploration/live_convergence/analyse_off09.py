"""Per-round convergence diagnostics for the off09 pair. Reads disk, no API calls.

`fit_contraction.py` fits rho to distance-to-x*_NBS and `analyse_trajectories.py`
reports the decrease fraction. Neither prints the per-round series side by side,
and the distinction matters here: on `arm_b_off09` the `cost_floor` row is active
on 72% of governed rounds, so the negotiation settles at a *constrained* rest
point. Distance to the unconstrained NBS therefore rises while the projected
force imbalance falls, and reading only the first would call that divergence.

What this adds, per round: Phi, Phi_projected, distance to x*_NBS, min h, and
whether the filter intervened -- for the binding trajectory of both arms.

Reproduce:
    uv run python exploration/live_convergence/analyse_off09.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.certificates.energy import phi, phi_projected  # noqa: E402
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import PayoffModel, dist_M  # noqa: E402

DATA = ROOT / "data" / "disclosed_offset_low_3_9"
RESULTS = ROOT / "results"
OUT = Path(__file__).resolve().parent


def series_for(arm: str, registry: ContractRegistry) -> dict[str, list[dict]]:
    """One record per round, keyed by 'run|pair'."""
    models: dict[str, PayoffModel] = {}
    out: dict[str, list[dict]] = defaultdict(list)

    for run in sorted(RESULTS.glob(f"arm_{arm}_*/certificates.jsonl")):
        for line in run.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            pair = rec["pair_id"]
            business_id, customer_id = pair.split("|")
            contract = registry.get(business_id, customer_id)
            if contract is None:
                continue
            if pair not in models:
                b = registry.businesses.get(business_id)
                c = registry.customers.get(customer_id)
                if b is None or c is None:
                    continue
                try:
                    models[pair] = PayoffModel.from_scenario(b, c)
                except ValueError:
                    continue
            model = models[pair]
            x_star, _ = model.nash_bargaining_solution()
            x = np.asarray(rec["x_applied"], dtype=float)

            out[f"{run.parent.name}|{pair}"].append(
                {
                    "round": rec["round_index"],
                    "x": x.tolist(),
                    "phi": float(phi(model, x)),
                    "phi_proj": float(phi_projected(model, x, contract)),
                    "dist_nbs": float(dist_M(x, x_star)),
                    "min_h": min(rec["h_applied"].values()),
                    "intervened": bool(rec.get("intervention", 0.0) > 1e-9),
                }
            )
    return out


def summarise(name: str, series: dict[str, list[dict]]) -> dict:
    """Down/flat/up per step, and net change per trajectory, each with its n.

    The stock `analyse_trajectories.py` prints one "frac dec" column computed as
    `diff <= 1e-9`, which counts an exactly-flat step as a decrease. That is not
    a quibble here: the filter pins terms on the cost-floor boundary and the
    seller re-proposes the same point, so a large share of governed steps are
    flat. They are separated out rather than folded into either side.
    """
    res: dict = {"trajectories": len(series)}
    defined = total = 0
    for rounds in series.values():
        for r in rounds:
            total += 1
            defined += not np.isnan(r["phi_proj"])
    res["rounds"] = total
    res["phi_proj_defined"] = f"{defined}/{total}"

    print(f"\n=== arm {name} ===")
    print(f"  {len(series)} trajectories, {total} rounds; "
          f"Phi_proj defined on {res['phi_proj_defined']} states")

    for key in ("phi", "phi_proj", "dist_nbs"):
        down = flat = up = 0
        net_down: list[bool] = []
        for rounds in series.values():
            vals = [r[key] for r in rounds]
            finite = [v for v in vals if not np.isnan(v)]
            if len(finite) >= 2:
                net_down.append(finite[-1] < finite[0])
            for a, b in zip(vals, vals[1:]):
                if np.isnan(a) or np.isnan(b):
                    continue
                d = b - a
                if abs(d) <= 1e-9:
                    flat += 1
                elif d < 0:
                    down += 1
                else:
                    up += 1
        n = down + flat + up
        res[key] = {
            "steps": n,
            "down": down, "flat": flat, "up": up,
            "frac_down": round(down / n, 3) if n else None,
            "frac_flat": round(flat / n, 3) if n else None,
            "net_down_trajectories": f"{sum(net_down)}/{len(net_down)}",
        }
        if n:
            print(f"  {key:10s} n={n:>4}  down {down / n:.3f}  flat {flat / n:.3f}  "
                  f"up {up / n:.3f}   net down on {sum(net_down)}/{len(net_down)} traj")
        else:
            print(f"  {key:10s} n=   0  (never defined on two consecutive rounds)")
    return res


def plot(report: dict) -> None:
    """Phi_projected and distance-to-NBS against round, governed vs ungoverned."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(2, 2, figsize=(11, 7), sharex="col")
    for col, arm in enumerate(("b_off09", "a_off09")):
        series = report["arms"][arm]["series"]
        for row, key, label in ((0, "phi_proj", r"$\Phi_{proj}$"),
                                (1, "dist_nbs", r"dist to $x^*_{NBS}$")):
            ax = axes[row][col]
            for rounds in series.values():
                ys = [r[key] for r in rounds]
                if sum(not np.isnan(y) for y in ys) < 2:
                    continue
                ax.plot(range(len(ys)), ys, alpha=0.55, lw=1.1)
            ax.set_ylabel(label)
            ax.grid(alpha=0.25)
            # An empty Phi_proj panel is a result, not a missing series: the
            # cone is undefined outside C(theta), and ungoverned states are
            # mostly outside it. Say so on the axes.
            if not ax.lines:
                defined = report["arms"][arm]["phi_proj_defined"]
                ax.text(0.5, 0.5,
                        f"undefined: only {defined} states lie in "
                        r"$C(\theta)$," "\nand none consecutively",
                        ha="center", va="center", fontsize=9,
                        transform=ax.transAxes, color="0.35")
            if row == 0:
                ax.set_title("arm B, governed" if arm == "b_off09"
                             else "arm A, ungoverned")
            if row == 1:
                ax.set_xlabel("round")
    fig.suptitle("disclosed_offset_low_3_9 (f=0.90): binding trajectories")
    fig.tight_layout()
    path = OUT / "off09_trajectories.png"
    fig.savefig(path, dpi=150)
    print(f"plot written to {path.relative_to(ROOT)}")


def main() -> None:
    registry = ContractRegistry.from_data_dir(DATA)
    report = {"scenario": str(DATA.relative_to(ROOT)), "arms": {}}

    for arm in ("b_off09", "a_off09"):
        series = series_for(arm, registry)
        report["arms"][arm] = summarise(arm, series)
        report["arms"][arm]["series"] = series

    plot(report)

    path = OUT / "per_round_off09.json"
    path.write_text(json.dumps(report, indent=2, default=float))
    print(f"\nwritten to {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
