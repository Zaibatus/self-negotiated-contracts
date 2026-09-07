"""Safety and convergence compose, and a contract's welfare cost is a priori.

Three results, all synthetic on the reference calibration, all free.

1. THE FILTER PRESERVES THE LYAPUNOV ASCENT. The sweep's update is
   u = eta * grad(Psi) * SCALE^2, i.e. preconditioned ascent on the potential.
   Passing it through the DCBF-QP -- a MINIMUM-INTERVENTION projection, not a
   projected-gradient step -- leaves Psi non-decreasing on every step at every
   budget, binding or not. With proposal noise, filtered and unfiltered degrade
   identically, so the filter contributes nothing to the non-monotonicity.
   Enforcement does not buy safety at the cost of convergence.

2. THE WELFARE GAP DECOMPOSES.
       Psi* - Psi_final  =  [Psi* - Psi_c*]  +  [Psi_c* - Psi_final]
                            price of the        failure of the
                            contract            dynamics
   where Psi_c* = max{ Psi(x) : x in C(theta) }. Measured, the second term is
   below 0.05 of 187.57 (< 0.03%) at every budget: the filtered dynamic reaches
   the best the contract allows. Essentially all realised welfare loss is
   attributable to where theta was written, none to the negotiation.

3. THE PRICE OF A CONTRACT HAS A CLOSED FORM, computable before any negotiation
   runs. With quantity pinned and the deadline row inactive,

       L(theta) = Psi* - Psi( p_bar, q_min, d_4(p_bar) ),  p_bar = min(B/q_min, p*)

   where d_4 is the displaced deadline of Proposition 4. Exact to 2e-12 against
   numerical maximisation over the whole sweep. L(theta) = 0 exactly when
   C(theta) contains the bargaining solution.

Run:  uv run python experiments/contract_welfare_cost.py
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import brentq, minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import DCBFFilter, project_into_safe_set  # noqa: E402
from src.contract import Contract  # noqa: E402
from src.payoffs import SCALE, PayoffModel, dist_M  # noqa: E402

OUT = Path("results/summary/contract_welfare_cost.json")
Q_PIN, ETA, GAMMA, T_MAX = 100.0, 1e-2, 0.4, 400
GB = GS = 0.3
D_B, D_S, LAM = 40.0, 12.0, 60.0
BUDGETS = [6.12, 6.59, 7.06, 7.52, 7.99, 8.46, 8.50, 8.93, 9.86, 10.80, 13.60]

MODEL = PayoffModel()
X_STAR, _ = MODEL.nash_bargaining_solution()
P_STAR = float(X_STAR[0])


def psi(x: np.ndarray) -> float:
    return float(MODEL.p_accept(x) * MODEL.surplus(x))


PSI_STAR = psi(X_STAR)


def contract_at(p_boundary: float) -> Contract:
    return Contract(budget=p_boundary * Q_PIN, cost_floor=6.0, q_min=Q_PIN,
                    q_max=Q_PIN, d_min=0.0, d_max=60.0, deadline_active=False)


def _sigma(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def deadline_prop4(p: float) -> float:
    """Proposition 4's displaced deadline rest point at pinned price p."""
    def f(d: float) -> float:
        x = np.array([p, Q_PIN, d])
        ub, us = MODEL.u_buyer(x), MODEL.u_seller(x)
        w = ub + us
        return (GB * (d - D_B) * (1 + w * (1 - _sigma(ub / LAM)) / LAM)
                + GS * (d - D_S) * (1 + w * (1 - _sigma(us / LAM)) / LAM))
    grid = np.linspace(-50, 120, 1200)
    vals = [f(z) for z in grid]
    roots = [brentq(f, grid[i], grid[i + 1]) for i in range(len(grid) - 1)
             if vals[i] * vals[i + 1] < 0]
    return sorted(roots)[len(roots) // 2]


def cost_closed_form(p_boundary: float) -> float:
    p_bar = min(p_boundary, P_STAR)
    return PSI_STAR - psi(np.array([p_bar, Q_PIN, deadline_prop4(p_bar)]))


def cost_numeric(p_boundary: float) -> float:
    best = None
    for p0 in np.linspace(4, 16, 9):
        r = minimize(lambda z: -psi(np.array([z[0], Q_PIN, z[1]])), [p0, 26.0],
                     bounds=[(6.0, p_boundary), (0.0, 60.0)], method="L-BFGS-B")
        if best is None or -r.fun > -best.fun:
            best = r
    return PSI_STAR - (-best.fun)


def run(contract: Contract | None, noise: float, seed: int = 0):
    rng = np.random.default_rng(seed)
    x = np.array([12.75, Q_PIN, 26.0])
    filt = DCBFFilter(gamma=GAMMA) if contract is not None else None
    if contract is not None and not contract.is_safe(x):
        x = project_into_safe_set(x, contract)
    series = [psi(x)]
    for _ in range(T_MAX):
        u = ETA * MODEL.concession_field(x) * SCALE**2
        if noise:
            u = u + rng.normal(0.0, noise, 3) * SCALE
        if filt is not None:
            u = filt.step([x], [u], [contract]).u[:3]
        nxt = x + u
        series.append(psi(nxt))
        if dist_M(nxt, x) < 1e-6:
            x = nxt
            break
        x = nxt
    return x, np.array(series)


def main() -> None:
    rows: list[dict[str, Any]] = []
    for pb in BUDGETS:
        c = contract_at(pb)
        _, clean = run(c, 0.0)
        _, free = run(None, 0.0)
        l_closed, l_numeric = cost_closed_form(pb), cost_numeric(pb)
        rows.append({
            "b_over_qmin": pb, "binds": pb < P_STAR,
            "psi_up_filtered": float((np.diff(clean) >= -1e-12).mean()),
            "psi_up_unfiltered": float((np.diff(free) >= -1e-12).mean()),
            "worst_filtered_drop": float(np.diff(clean).min()),
            "psi_final": float(clean[-1]),
            "cost_closed_form": l_closed, "cost_numeric": l_numeric,
            "closed_form_error": l_closed - l_numeric,
            "dynamics_gap": float((PSI_STAR - l_numeric) - clean[-1]),
        })

    noisy = []
    for pb in (6.12, 8.93, 13.60):
        c = contract_at(pb)
        uf = ff = tu = tf = 0
        for s in range(15):
            _, a = run(None, 0.02, s)
            _, b = run(c, 0.02, s)
            uf += int((np.diff(a) >= -1e-12).sum()); tu += len(a) - 1
            ff += int((np.diff(b) >= -1e-12).sum()); tf += len(b) - 1
        noisy.append({"b_over_qmin": pb, "unfiltered": uf / tu, "filtered": ff / tf})

    report = {"psi_star": PSI_STAR, "p_star": P_STAR, "rows": rows, "with_noise": noisy,
              "max_closed_form_error": max(abs(r["closed_form_error"]) for r in rows),
              "max_dynamics_gap": max(r["dynamics_gap"] for r in rows)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"{'B/qmin':>8}{'binds':>7}{'Psi up filt':>13}{'worst drop':>13}"
          f"{'L closed':>11}{'L numeric':>11}{'dyn gap':>10}")
    for r in rows:
        print(f"{r['b_over_qmin']:>8.2f}{str(r['binds']):>7}{r['psi_up_filtered']:>13.4f}"
              f"{r['worst_filtered_drop']:>13.2e}{r['cost_closed_form']:>11.4f}"
              f"{r['cost_numeric']:>11.4f}{r['dynamics_gap']:>10.4f}")
    print(f"\nmax closed-form error {report['max_closed_form_error']:.2e}"
          f"   max dynamics gap {report['max_dynamics_gap']:.4f} of Psi* = {PSI_STAR:.2f}"
          f"  ({100*report['max_dynamics_gap']/PSI_STAR:.3f}%)")
    print("\nwith proposal noise 0.02, Psi-up fraction:")
    for n in noisy:
        print(f"  B/qmin {n['b_over_qmin']:>6.2f}   unfiltered {n['unfiltered']:.4f}"
              f"   filtered {n['filtered']:.4f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
