"""Fit a contraction rate to the live negotiation trajectories.

`analyse_trajectories.py` answers whether distance to x*_NBS *decreases*. This
asks the quantitative follow-up the Lyapunov layer actually needs: does it
decrease **geometrically**, and at what rate?

The certificate claims V(x_{k+1}) <= (1 - alpha) V(x_k) for V = ||x - x*||^2.
On a geometric trajectory d_k = ||x_k - x*|| that is d_{k+1} = rho * d_k with
rho^2 = 1 - alpha. So fitting rho to observed distances gives the empirical
counterpart of the certificate's rate.

Two things make the fit non-trivial and both are handled explicitly:

  * **The trajectories do not converge to zero.** They flatten at a positive
    floor -- agreement lands near x*_NBS, not on it. Fitting log d against k
    without an offset therefore reads a *slowing* contraction that is really a
    floor. The model fitted here is d_k = f + (d_0 - f) rho^k, with f found by
    a grid search on the residual.
  * **rho is descriptive, not certified.** Live agents run no step-size
    schedule, so this is not a measurement of the theorem's alpha. It is the
    rate the observed dynamics happen to contract at, which is the honest
    quantity and the one a reader will ask for.

Only trajectories with >= 4 points can support a two-parameter fit, so the
count is reported rather than the sample being padded.

Reproduce:

    uv run python experiments/fit_contraction.py --arms c_bargain a_bargain
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import PayoffModel, dist_M  # noqa: E402

MIN_POINTS_FOR_FIT = 4


def fit_geometric(d: np.ndarray, grid: int = 80) -> tuple[float, float, float]:
    """Fit d_k = f + (d_0 - f) rho^k. Returns (rho, f, residual)."""
    best = (float("nan"), 0.0, float("inf"))
    k = np.arange(len(d))
    for f in np.linspace(0.0, float(d.min()) * 0.999, grid):
        y = np.log(np.maximum(d - f, 1e-9))
        slope, intercept = np.polyfit(k, y, 1)
        residual = float(np.sum((y - (slope * k + intercept)) ** 2))
        if residual < best[2]:
            best = (float(np.exp(slope)), float(f), residual)
    return best


def analyse(arm: str, registry: ContractRegistry, results: Path) -> dict[str, Any]:
    models: dict[str, PayoffModel] = {}
    star: dict[str, np.ndarray] = {}

    def model_for(pair_id: str) -> PayoffModel | None:
        if pair_id not in models:
            business_id, customer_id = pair_id.split("|", 1)
            business = registry.businesses.get(business_id)
            customer = registry.customers.get(customer_id)
            if business is None or customer is None:
                return None
            try:
                models[pair_id] = PayoffModel.from_scenario(business, customer)
            except ValueError:
                return None
            star[pair_id] = models[pair_id].nash_bargaining_solution()[0]
        return models.get(pair_id)

    fits: list[dict[str, Any]] = []
    ratios: list[float] = []

    for run in sorted(results.glob(f"arm_{arm}_*/certificates.jsonl")):
        by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for line in run.read_text(encoding="utf-8").splitlines():
            if line.strip():
                record = json.loads(line)
                by_pair[record["pair_id"]].append(record)
        for pair_id, records in by_pair.items():
            if model_for(pair_id) is None:
                continue
            records.sort(key=lambda r: r["round_index"])
            d = np.array(
                [
                    dist_M(np.array(r["x_applied"], dtype=float), star[pair_id])
                    for r in records
                ]
            )
            if len(d) >= 2:
                ratios.extend(list(d[1:] / np.maximum(d[:-1], 1e-12)))
            if len(d) < MIN_POINTS_FOR_FIT:
                continue
            rho, floor, _ = fit_geometric(d)
            fits.append(
                {
                    "run": run.parent.name,
                    "pair": pair_id,
                    "points": len(d),
                    "rho": rho,
                    "floor": floor,
                    "d_first": float(d[0]),
                    "d_last": float(d[-1]),
                }
            )
    return {"arm": arm, "fits": fits, "ratios": ratios}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", nargs="+", default=["c_bargain"])
    parser.add_argument("--data", default="data/bargain_3_9")
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="results/summary/contraction.json")
    args = parser.parse_args()

    registry = ContractRegistry.from_data_dir(Path(args.data))
    results = Path(args.results)
    report = {arm: analyse(arm, registry, results) for arm in args.arms}

    for arm, data in report.items():
        fits, ratios = data["fits"], np.array(data["ratios"])
        print(f"\n=== arm {arm} ===")
        if ratios.size:
            print(f"  per-step distance ratio: n={ratios.size}  "
                  f"median {np.median(ratios):.3f}  "
                  f"fraction < 1 {np.mean(ratios < 1):.3f}")
        if not fits:
            print(f"  no trajectory with >= {MIN_POINTS_FOR_FIT} points; "
                  "nothing to fit")
            continue
        print(f"\n  {'run':<18}{'pair':<30}{'n':>3}{'rho':>8}"
              f"{'floor':>8}{'d first':>9}{'d last':>8}")
        for f in fits:
            print(f"  {f['run']:<18}{f['pair']:<30}{f['points']:>3}"
                  f"{f['rho']:>8.3f}{f['floor']:>8.3f}"
                  f"{f['d_first']:>9.3f}{f['d_last']:>8.3f}")
        rho = np.array([f["rho"] for f in fits])
        print(f"\n  fitted on {len(fits)} trajectories: median rho "
              f"{np.median(rho):.3f}  range {rho.min():.3f}-{rho.max():.3f}")
        print(f"  => per-round contraction of V = d^2 is rho^2 = "
              f"{np.median(rho) ** 2:.3f}")
        print("  rho is DESCRIPTIVE: live agents run no step schedule, so this "
              "is not\n  the theorem's alpha.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
