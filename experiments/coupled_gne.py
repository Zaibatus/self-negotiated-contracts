"""Coupling, the generalised Nash equilibrium, and what gamma actually prices.

The economic half of the formalism has never left simulation (limitation C4).
This gives it a potential-theoretic account and tests the one economic claim
section 3.8 makes but never checks.

Setup: two buyers, one seller, shared capacity q1 + q2 <= Q. Per-pair contracts
are deliberately loose, so the ONLY coupling is the capacity row.

Because each pair's concession field is grad(Psi_j) (see potential_certificate.py)
and the pairs interact only through the constraint, the coupled system is a
potential game with a coupled constraint, of total potential

    Psi_total(x_1, x_2) = Psi_1(x_1) + Psi_2(x_2).

Four results.

1. THE COUPLED FILTERED DYNAMIC LANDS ON THE VARIATIONAL GNE, i.e. on
   argmax Psi_total subject to the capacity row -- to 1e-6 in the potential and
   three decimals in the allocation, at every Q tested.

2. THE ALLOCATION EQUALISES MARGINAL POTENTIAL. At an interior solution
   dPsi_1/dq_1 = dPsi_2/dq_2, the classical efficient-allocation condition, and
   the common value is the shadow price. Verified against dPsi*_total/dQ by the
   envelope theorem to ~1e-7.

3. THE FILTER'S OWN DUAL IS THAT SHADOW PRICE. At rest the multiplier on the
   capacity row is exactly 2 * eta * lambda_econ, to 4e-7 relative over a 16x
   range of step size. The controller's Lagrange multiplier and the economic
   shadow price of capacity are the same number up to the step scaling.

4. THE CONSERVATISM PREMIUM IS A TRANSIENT, AND SECTION 3.8 HAS IT BACKWARDS.
   That section says the multiplier "decomposes into a scarcity price and a
   conservatism premium that vanishes as gamma -> 1". Measured: at rest the
   multiplier equals the scarcity price for EVERY gamma, so the premium is zero
   everywhere at equilibrium; and during approach the premium is exactly
   proportional to gamma (peak / base = 70.085 * gamma, constant to three
   decimals), so it GROWS with gamma rather than vanishing.

   The resting allocation is exactly gamma-independent too. That generalises the
   live null of section 5.7: gamma's inertness is structural, not an artefact of
   short negotiations -- it survives 1350-round sustained ones.

Run:  uv run python experiments/coupled_gne.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import (  # noqa: E402
    SHARED_CAPACITY_LABEL, DCBFFilter, build_rows,
)
from src.contract import Contract  # noqa: E402
from src.payoffs import SCALE, PayoffModel  # noqa: E402

OUT = Path("results/summary/coupled_gne.json")
ETA, T_MAX = 2e-3, 4000
CAPACITIES = [180.0, 160.0, 150.0, 140.0, 130.0]
GAMMAS = [0.1, 0.2, 0.4, 0.7, 1.0]

M1 = PayoffModel()
M2 = PayoffModel(a=14.0, b=0.05, c=6.0, e=0.02, gamma_b=0.3, gamma_s=0.3,
                 d_b=40.0, d_s=12.0, lam=60.0)
MODELS = [M1, M2]
X1, _ = M1.nash_bargaining_solution()
X2, _ = M2.nash_bargaining_solution()


def psi(model: PayoffModel, x: np.ndarray) -> float:
    return float(model.p_accept(x) * model.surplus(x))


def psi_total(z: np.ndarray) -> float:
    return psi(M1, z[:3]) + psi(M2, z[3:])


def variational_gne(capacity: float) -> tuple[np.ndarray, float]:
    """argmax Psi_total subject to q1 + q2 <= Q."""
    best = None
    for seed in range(8):
        z0 = np.concatenate([X1, X2]) + np.random.default_rng(seed).normal(0, 0.5, 6)
        r = minimize(lambda z: -psi_total(z), z0, method="SLSQP",
                     constraints=[{"type": "ineq",
                                   "fun": lambda z: capacity - (z[1] + z[4])}],
                     bounds=[(1e-3, 50), (1e-3, 300), (0, 60)] * 2,
                     options={"maxiter": 900, "ftol": 1e-13})
        if r.success and (best is None or -r.fun > -best.fun):
            best = r
    return best.x, -best.fun


def marginal_potential(z: np.ndarray, which: int, h: float = 1e-5) -> float:
    model = MODELS[which]
    x = z[:3] if which == 0 else z[3:]
    step = np.array([0.0, h, 0.0])
    return (psi(model, x + step) - psi(model, x - step)) / (2 * h)


def _loose() -> Contract:
    return Contract(budget=1e6, cost_floor=0.0, q_min=1e-3, q_max=1e6,
                    d_min=0.0, d_max=60.0, deadline_active=False)


def trace(capacity: float, gamma: float, eta: float = ETA):
    """Run the coupled filtered dynamic; return the capacity duals and rest state."""
    xs = [X1.copy(), X2.copy()]
    filt = DCBFFilter(gamma=gamma)
    contracts = [_loose(), _loose()]
    duals = []
    for _ in range(T_MAX):
        props = [eta * MODELS[i].concession_field(xs[i]) * SCALE**2 for i in range(2)]
        res = filt.step(xs, props, contracts, shared_capacity=capacity)
        _, _, labels = build_rows(xs, contracts, capacity)
        idx = [i for i, l in enumerate(labels) if l == SHARED_CAPACITY_LABEL]
        duals.append(float(res.duals[idx[0]]) if idx else 0.0)
        step = np.asarray(res.u, dtype=float).reshape(2, 3)
        nxt = [xs[i] + step[i] for i in range(2)]
        if max(float(np.linalg.norm(nxt[i] - xs[i])) for i in range(2)) < 1e-9:
            xs = nxt
            break
        xs = nxt
    return np.array(duals), np.concatenate(xs)


def main() -> None:
    report: dict[str, Any] = {"eta": ETA, "capacities": [], "gamma_sweep": [],
                              "eta_sweep": []}

    for cap in CAPACITIES:
        z_var, v_var = variational_gne(cap)
        duals, z_dyn = trace(cap, 0.4)
        lam = marginal_potential(z_var, 0)
        dq = 0.05
        _, vp = variational_gne(cap + dq)
        _, vm = variational_gne(cap - dq)
        report["capacities"].append({
            "capacity": cap,
            "q_dynamic": [float(z_dyn[1]), float(z_dyn[4])],
            "q_variational": [float(z_var[1]), float(z_var[4])],
            "psi_dynamic": psi_total(z_dyn), "psi_variational": v_var,
            "potential_gap": v_var - psi_total(z_dyn),
            "marginal_pair1": lam, "marginal_pair2": marginal_potential(z_var, 1),
            "dpsi_dQ": (vp - vm) / (2 * dq),
            "dual_rest": float(duals[-1]),
            "dual_over_2eta_lambda": float(duals[-1] / (2 * ETA * lam)),
        })

    lam140 = marginal_potential(variational_gne(140.0)[0], 0)
    base = 2 * ETA * lam140
    z_var140, _ = variational_gne(140.0)
    for g in GAMMAS:
        duals, z = trace(140.0, g)
        report["gamma_sweep"].append({
            "gamma": g, "peak_dual": float(duals.max()), "rest_dual": float(duals[-1]),
            "peak_over_base": float(duals.max() / base),
            "rest_over_base": float(duals[-1] / base),
            "peak_over_base_gamma": float(duals.max() / (base * g)),
            "q_rest": [float(z[1]), float(z[4])],
            "q_variational": [float(z_var140[1]), float(z_var140[4])],
            "rounds": int(len(duals)),
        })
    for eta in (5e-4, 1e-3, 2e-3, 4e-3, 8e-3):
        d, _ = trace(140.0, 0.4, eta)
        report["eta_sweep"].append({"eta": eta, "dual_rest": float(d[-1]),
                                    "ratio": float(d[-1] / (2 * eta * lam140))})

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print(f"{'Q':>7}{'q1 dyn':>9}{'q1 GNE':>9}{'q2 dyn':>9}{'q2 GNE':>9}"
          f"{'Psi gap':>11}{'lambda':>10}{'dPsi*/dQ':>11}{'dual/2eta.lam':>15}")
    for r in report["capacities"]:
        print(f"{r['capacity']:>7.0f}{r['q_dynamic'][0]:>9.3f}{r['q_variational'][0]:>9.3f}"
              f"{r['q_dynamic'][1]:>9.3f}{r['q_variational'][1]:>9.3f}"
              f"{r['potential_gap']:>11.2e}{r['marginal_pair1']:>10.5f}"
              f"{r['dpsi_dQ']:>11.5f}{r['dual_over_2eta_lambda']:>15.7f}")
    print(f"\ngamma sweep at Q=140 (base = 2*eta*lambda_econ = {base:.6f}):")
    print(f"{'gamma':>7}{'peak/base':>12}{'peak/(base.g)':>15}{'rest/base':>12}"
          f"{'q1 rest':>10}{'q1 GNE':>10}{'rounds':>8}")
    for r in report["gamma_sweep"]:
        print(f"{r['gamma']:>7.2f}{r['peak_over_base']:>12.3f}"
              f"{r['peak_over_base_gamma']:>15.3f}{r['rest_over_base']:>12.6f}"
              f"{r['q_rest'][0]:>10.4f}{r['q_variational'][0]:>10.4f}{r['rounds']:>8}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
