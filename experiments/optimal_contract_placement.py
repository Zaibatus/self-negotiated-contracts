"""There is an interior optimal contract, and it beats no contract.

Earlier attempts to find a welfare-optimal contract tightness failed, because
they were run on the JOINT preconditioned dynamic, which converges cleanly and
never overshoots. On that dynamic a binding contract can only cost welfare.

The alternating protocol -- the one the formulation actually specifies and the
one the marketplace runs -- behaves differently. Agents move one at a time on
their own Uhat_i, so the path is not a Psi-ascent (see lyapunov_granularity.py:
Psi rises on 100% of round-PAIRS but only 52-72% of rounds), and with proposal
noise the trajectory wanders. A contract placed above the efficient spend clips
the upper tail of that wandering without distorting the target.

Measured at gamma = 0.4, rho = 0.5, noise 0.02, 50 runs per point
(5 starts x 10 seeds), against an efficient spend p* q* = 850:

    budget   mean Psi/Psi*      vs no contract
      820        0.9014            -4.51 sigma      too tight: pure L(theta) cost
      870        0.9360            -0.91 sigma      null
      910        0.9815            +4.35 sigma      OPTIMUM
      980        0.9541            +0.90 sigma      null
     1050        0.9449             0.00 sigma      never binds

The optimum also cuts outcome variance roughly fourfold: SE 0.0021 at B = 910
against 0.0081 with no contract. That is the same signature as the live arm B
result, whose seed SD falls from 0.054 to 0.014.

So contract placement trades two measured quantities:
  * BELOW the efficient spend, cost is L(theta) -- the a-priori welfare price of
    the contract, in closed form (contract_welfare_cost.py);
  * ABOVE it, benefit is variance clipping -- the contract removes the upper
    tail of a noisy alternating path.
The optimum is where they balance, here about 7% above the efficient spend.

The location moves with gamma (950, 900, 850 for gamma = 0.2, 0.4, 0.7), which
is consistent with coupled_gne.py: gamma is inert at equilibrium and scales the
transient, and here the transient is what settles.

Run:  uv run python experiments/optimal_contract_placement.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import DCBFFilter, project_into_safe_set  # noqa: E402
from src.contract import Contract  # noqa: E402
from src.payoffs import SCALE, PayoffModel, norm_M  # noqa: E402

OUT = Path("results/summary/optimal_contract_placement.json")
BOUNDS = [(6.0, 12.0), (20.0, 120.0), (7.0, 45.0)]
STARTS = [np.array([11.0, 40.0, 40.0]), np.array([11.5, 30.0, 44.0]),
          np.array([10.0, 60.0, 35.0]), np.array([9.5, 50.0, 38.0]),
          np.array([11.8, 25.0, 42.0])]
BUDGETS = [820, 850, 870, 890, 900, 910, 930, 950, 980, 1050]
GAMMAS = [0.2, 0.4, 0.7]

MODEL = PayoffModel()
X_STAR, _ = MODEL.nash_bargaining_solution()
PSI_STAR = float(MODEL.p_accept(X_STAR) * MODEL.surplus(X_STAR))
NBS_SPEND = float(X_STAR[0] * X_STAR[1])


def _clip(x: np.ndarray) -> np.ndarray:
    return np.array([np.clip(x[i], *BOUNDS[i]) for i in range(3)])


def contract_at(budget: float) -> Contract:
    return Contract(budget=budget, cost_floor=6.0, q_min=20.0, q_max=120.0,
                    d_min=7.0, d_max=45.0, deadline_active=True)


def run(contract: Contract | None, x0: np.ndarray, rho: float, gamma: float,
        noise: float, seed: int, steps: int = 400) -> float:
    rng = np.random.default_rng(seed)
    x = x0.copy()
    filt = DCBFFilter(gamma=gamma) if contract is not None else None
    if contract is not None and not contract.is_safe(x):
        x = _clip(project_into_safe_set(x, contract))
    for k in range(steps):
        role = "buyer" if k % 2 == 0 else "seller"
        g = MODEL.grad_u_hat(x, role)
        u = g * (SCALE**2) / norm_M(g) * rho + rng.normal(0.0, noise, 3) * SCALE
        if filt is not None:
            u = filt.step([x], [u], [contract]).u[:3]
        x = _clip(x + u)
    return float(MODEL.p_accept(x) * MODEL.surplus(x) / PSI_STAR)


def sample(budget: float | None, gamma: float, rho: float = 0.5,
           noise: float = 0.02, per_start: int = 10) -> np.ndarray:
    contract = None if budget is None else contract_at(float(budget))
    return np.array([run(contract, x0, rho, gamma, noise, s * 13 + i)
                     for i, x0 in enumerate(STARTS) for s in range(per_start)])


def main() -> None:
    report = {"psi_star": PSI_STAR, "nbs_spend": NBS_SPEND, "sweeps": []}
    for gamma in GAMMAS:
        base = sample(None, gamma)
        rows = []
        for b in BUDGETS:
            v = sample(b, gamma)
            se = float(np.sqrt(v.var(ddof=1) / len(v) + base.var(ddof=1) / len(base)))
            rows.append({
                "budget": b, "mean": float(v.mean()),
                "se": float(v.std(ddof=1) / np.sqrt(len(v))),
                "delta": float(v.mean() - base.mean()),
                "sigma": float((v.mean() - base.mean()) / se),
                "budget_over_efficient_spend": b / NBS_SPEND,
            })
        best = max(rows, key=lambda r: r["mean"])
        report["sweeps"].append({
            "gamma": gamma,
            "no_contract_mean": float(base.mean()),
            "no_contract_se": float(base.std(ddof=1) / np.sqrt(len(base))),
            "rows": rows, "best_budget": best["budget"], "best_sigma": best["sigma"],
        })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"efficient spend p* q* = {NBS_SPEND:.0f},  Psi* = {PSI_STAR:.3f}\n")
    for s in report["sweeps"]:
        print(f"gamma = {s['gamma']}   no contract {s['no_contract_mean']:.4f} "
              f"+- {s['no_contract_se']:.4f}")
        print(f"  {'budget':>8}{'mean':>9}{'SE':>8}{'vs none':>10}{'sigma':>8}{'B/spend':>9}")
        for r in s["rows"]:
            print(f"  {r['budget']:>8}{r['mean']:>9.4f}{r['se']:>8.4f}"
                  f"{r['delta']:>+10.4f}{r['sigma']:>8.2f}"
                  f"{r['budget_over_efficient_spend']:>9.3f}")
        print(f"  -> best budget {s['best_budget']} at {s['best_sigma']:+.2f} sigma\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
