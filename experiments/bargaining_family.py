"""The rational-seller floor, and the live outcomes that fall below it.

Model the buyer's engagement as a weight alpha on its gradient:

    F_alpha = alpha * grad(Uhat_B) + grad(Uhat_S) = grad( P (alpha U_B + U_S) )

so the potential structure of potential_certificate.py survives, with
Psi_alpha := P (alpha U_B + U_S).  alpha = 1 is the formulation's joint field
and rests at the symmetric Nash bargaining solution (Proposition 1); alpha = 0
is a WHOLLY PASSIVE buyer that exerts no bargaining pressure at all.

Two results.

1. THE FLOOR IS A CONSTANT OF THE FRAMEWORK.  Price is a pure transfer, so with
   (q, d) efficient the problem is one-dimensional in the transfer.  Writing
   u := U_S / lambda and k := W / lambda,

       Psi(u) / W = sigma(k - u) sigma(u),        symmetric split at u = k/2,

   and a passive buyer lets the seller maximise Psi * U_S.  The resulting ratio
   Psi(passive) / Psi* depends ONLY on k, not on the scenario.  At the
   calibration used throughout (lambda = W_max/4, so k = 4) it is 0.825817,
   which is what every live pair returns numerically.

   A seller facing a buyer that pushes back not at all still delivers 83% of the
   joint optimum, because pushing the transfer further collapses its own
   probability of a deal.  Self-interest is protective -- but only because the
   buyer would refuse.

2. THE LIVE OUTCOMES ARE OUTSIDE THE FAMILY.  No engagement weight in [0, 1]
   produces outcomes as bad as the live agents reach: 0.28-0.69 disclosed,
   0.000 undisclosed, against a floor of 0.826.  The failure is not weak
   bargaining. An agent that accepts anything removes the counterparty's reason
   to moderate, and enforcement substitutes for the refusal.

Run:  uv run python experiments/bargaining_family.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from scipy.optimize import minimize, minimize_scalar

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import PayoffModel  # noqa: E402

OUT = Path("results/summary/bargaining_family.json")
ALPHAS = np.linspace(0.0, 1.0, 21)


def _sigma(z):
    return 1.0 / (1.0 + np.exp(-z))


def analytic_floor(k: float) -> float:
    """Psi(passive) / Psi* as a function of k = W / lambda. Scenario-independent."""
    p = lambda u: _sigma(k - u) * _sigma(u)
    r = minimize_scalar(lambda u: -(p(u) * u), bounds=(1e-9, k - 1e-9),
                        method="bounded", options={"xatol": 1e-12})
    return float(p(r.x) / p(k / 2))


def _setup(data: str):
    reg = ContractRegistry.from_data_dir("data/" + data)
    models: dict[str, PayoffModel | None] = {}
    star: dict[str, np.ndarray] = {}

    def model_for(pid: str):
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


def family_curve(model: PayoffModel, x_star: np.ndarray) -> np.ndarray:
    """Psi/Psi* at the rest point of F_alpha, for alpha in [0, 1]."""
    q = float(x_star[1])
    psi_star = model.p_accept(x_star) * model.surplus(x_star)
    out = []
    for a in ALPHAS:
        best = None
        for p0 in np.linspace(x_star[0] * 0.6, x_star[0] * 2.5, 14):
            def neg(z, a=a):
                x = np.array([z[0], q, z[1]])
                return -(model.p_accept(x) * (a * model.u_buyer(x) + model.u_seller(x)))
            r = minimize(neg, [p0, float(x_star[2])],
                         bounds=[(1e-3, x_star[0] * 3), (0.0, 60.0)], method="L-BFGS-B")
            if best is None or -r.fun > -best.fun:
                best = r
        x = np.array([best.x[0], q, best.x[1]])
        out.append(float(model.p_accept(x) * model.surplus(x) / psi_star))
    return np.array(out)


def main() -> None:
    report: dict[str, Any] = {
        "analytic_floor_by_k": {str(k): analytic_floor(float(k))
                                for k in (1, 2, 3, 4, 5, 6, 8, 12, 20)},
        "floor_at_calibration": analytic_floor(4.0),
        "scenarios": {},
    }
    for data, pattern in (("bargain_3_9", "arm_a_bargain_v%d"),
                          ("undisclosed_3_9", "arm_a_undis_v%d")):
        _, model_for, star = _setup(data)
        observed: dict[str, list[float]] = defaultdict(list)
        for i in range(1, 6):
            path = Path("results") / (pattern % i) / "certificates.jsonl"
            if not path.exists():
                continue
            for pid, recs in _rounds(path).items():
                m = model_for(pid)
                if m is None:
                    continue
                xs = star[pid]
                psi_star = m.p_accept(xs) * m.surplus(xs)
                if psi_star <= 1e-9:
                    continue
                x = np.array(recs[-1]["x_applied"], dtype=float)
                observed[pid].append(float(m.p_accept(x) * m.surplus(x) / psi_star))
        rows = []
        for pid, vals in sorted(observed.items()):
            m, xs = model_for(pid), star[pid]
            curve = family_curve(m, xs)
            obs = float(np.mean(vals))
            rows.append({"pair": pid, "observed": obs, "family_min": float(curve.min()),
                         "family_max": float(curve.max()),
                         "outside_family": bool(obs < curve.min() - 1e-6)})
        report["scenarios"][data] = rows

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    print("passive-buyer floor as a function of k = W/lambda (scenario-independent)")
    for k, v in report["analytic_floor_by_k"].items():
        mark = "   <- lambda = W_max/4, the calibration used" if k == "4" else ""
        print(f"   k={k:>3}   floor {v:.6f}{mark}")
    print()
    for data, rows in report["scenarios"].items():
        n = sum(r["outside_family"] for r in rows)
        print(f"{data}:")
        print(f"  {'pair':<30}{'observed':>10}{'family min':>12}{'outside?':>10}")
        for r in rows:
            print(f"  {r['pair'][:28]:<30}{r['observed']:>10.4f}{r['family_min']:>12.4f}"
                  f"{('YES' if r['outside_family'] else 'no'):>10}")
        print(f"  -> outside the alpha in [0,1] family: {n} of {len(rows)}\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
