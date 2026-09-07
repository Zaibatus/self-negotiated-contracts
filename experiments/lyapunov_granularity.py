"""Psi is a Lyapunov function for the round-PAIR, not for the round.

Section 3.4 defines the joint concession field as "the net force the two agents
exert on the draft over a round-pair". Its potential Psi = P*W therefore
ascends on round-pairs. It does NOT ascend on single rounds, and the gap is
large: each agent ascends its own Uhat_i, and a unilateral move that helps one
side can cost the other more than it gains.

Measured on the formulation's own alternating friction dynamic
(experiments/certificates/payoff_dynamics.py::step_agent):

  * per round      Psi increases on 52-72% of steps, worst single drop -6.97
  * per round-pair Psi increases on 100%, worst change strictly positive

This settles the granularity at which any live convergence diagnostic must be
read, and it is the granularity the live measurement already uses: the binding
trajectory holds seller proposals only, so consecutive points span a complete
round-pair. Live, Psi rises on 144 of 145 such steps (0.993) -- consistent with
the 1.000 here, and not comparable to the per-round figure.

It also bounds the claim of contract_welfare_cost.py, which showed the DCBF
filter preserving ascent. That result is for the JOINT preconditioned step. The
alternating protocol breaks monotonicity on its own, before any filter is
applied, so "the filter preserves ascent" must be read at round-pair
granularity too.

Run:  uv run python experiments/lyapunov_granularity.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "certificates"))
sys.path.insert(0, str(HERE.parent))

from payoff_dynamics import X0, step_agent  # noqa: E402
from payoff_model import P_accept, W, nbs_closed_form  # noqa: E402

OUT = Path("results/summary/lyapunov_granularity.json")
SETTINGS = [(0.0, 0.5), (2.0, 0.5), (0.0, 0.2), (2.0, 0.2), (0.0, 0.05), (2.0, 0.05)]


def psi(x: np.ndarray) -> float:
    return float(P_accept(x) * W(x))


def run(kappa: float, rho: float, steps: int = 400) -> np.ndarray:
    x = X0.copy()
    trace = [psi(x)]
    for k in range(steps):
        role = "buyer" if k % 2 == 0 else "seller"
        x, _ = step_agent(x, role, rho, kappa)
        trace.append(psi(x))
    return np.array(trace)


def main() -> None:
    x_star, _ = nbs_closed_form()
    psi_star = psi(x_star)
    rows = []
    for kappa, rho in SETTINGS:
        trace = run(kappa, rho)
        per_round = np.diff(trace)
        per_pair = np.diff(trace[::2])
        rows.append({
            "kappa": kappa, "rho": rho,
            "round_up_fraction": float((per_round >= -1e-12).mean()),
            "round_worst_change": float(per_round.min()),
            "pair_up_fraction": float((per_pair >= -1e-12).mean()),
            "pair_worst_change": float(per_pair.min()),
            "final_psi_ratio": float(trace[-1] / psi_star),
        })

    report = {"psi_star": psi_star, "x_star": x_star.tolist(), "rows": rows,
              "live_reference": {"arm_c_pair_granularity": [144, 145],
                                 "note": "binding trajectory is seller-to-seller, "
                                         "so consecutive points span a round-pair"}}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"Psi* = {psi_star:.4f}\n")
    print(f"{'kappa':>7}{'rho':>6}{'per-round up':>14}{'worst round':>13}"
          f"{'per-PAIR up':>13}{'worst pair':>12}{'final Psi/Psi*':>16}")
    for r in rows:
        print(f"{r['kappa']:>7.1f}{r['rho']:>6.2f}{r['round_up_fraction']:>14.4f}"
              f"{r['round_worst_change']:>13.3e}{r['pair_up_fraction']:>13.4f}"
              f"{r['pair_worst_change']:>12.3e}{r['final_psi_ratio']:>16.4f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
