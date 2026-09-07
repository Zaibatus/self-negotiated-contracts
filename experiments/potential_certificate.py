"""The concession field is integrable, and the right certificate is its potential.

The formulation defines the joint concession field as F = grad Uhat_B + grad Uhat_S
with Uhat_i = P * U_i. A sum of gradients is a gradient, so

    F = grad(P U_B) + grad(P U_S) = grad( P (U_B + U_S) ) = grad Psi,
    Psi := P * W,     the EXPECTED JOINT SURPLUS.

Proposition 1's proof already works with d(PW)/dp and d(PW)/dq: Psi was in the
formulation from the start, unnamed. Naming it has four consequences, each
checked here:

  1. grad F is symmetric everywhere (it is the Hessian of Psi), so the "sym" in
     the formulation's lambda_max(sym grad F) is a no-op.
  2. "F monotone" = "F passive" = "stable game" = "Psi concave". One condition,
     not three, and the 3.6.1 radius table is a concavity table.
  3. Psi is maximised at the Nash bargaining solution, so V := Psi* - Psi is a
     Lyapunov function for the concession dynamic, and Psi ALONE is an
     anchor-free monotonicity certificate: checking Psi_{k+1} >= Psi_k needs no
     x*, which is what the anchored certificates of 3.8 could not offer.
  4. Phi = ||F|| = ||grad Psi|| is a GRADIENT-NORM merit function. It is near
     zero at every stationary point AND on the plateau where acceptance
     collapses and Psi flattens. That is the second zero of 3.5.1, and it is a
     property of the choice of certificate, not of the negotiation.

Run:  uv run python experiments/potential_certificate.py
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.energy import field_jacobian, phi  # noqa: E402
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import PayoffModel, dist_M  # noqa: E402

SCALE_D = np.array([1.0, 10.0, 5.0])
OUT = Path("results/summary/potential_certificate.json")


def psi(model: PayoffModel, x: np.ndarray) -> float:
    """The potential: expected joint surplus P(x) W(x)."""
    return float(model.p_accept(x) * model.surplus(x))


def _grad(f, x, h: float = 1e-6) -> np.ndarray:
    g = np.zeros(3)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[i] = (f(x + e) - f(x - e)) / (2 * h)
    return g


def check_integrability(model: PayoffModel, x_star: np.ndarray, n: int = 400) -> dict[str, Any]:
    rng = np.random.default_rng(0)
    worst_grad = worst_asym = 0.0
    for _ in range(n):
        x = x_star + rng.normal(0, 1.0, 3) * SCALE_D
        f = model.concession_field(x)
        worst_grad = max(
            worst_grad,
            float(np.linalg.norm(f - _grad(lambda y: psi(model, y), x))
                  / max(np.linalg.norm(f), 1e-12)),
        )
        j = field_jacobian(model, x)
        worst_asym = max(worst_asym, float(np.abs(j - j.T).max() / max(np.abs(j).max(), 1e-12)))
    h = 1e-4
    hess = np.zeros((3, 3))
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        hess[:, i] = (_grad(lambda y: psi(model, y), x_star + e)
                      - _grad(lambda y: psi(model, y), x_star - e)) / (2 * h)
    hess = 0.5 * (hess + hess.T)
    return {
        "worst_rel_grad_mismatch": worst_grad,
        "worst_rel_jacobian_asymmetry": worst_asym,
        "hessian_eigenvalues_at_nbs": np.linalg.eigvalsh(hess).tolist(),
        "negative_definite_at_nbs": bool(np.all(np.linalg.eigvalsh(hess) < 0)),
    }


def check_spurious_zeros(model: PayoffModel, x_star: np.ndarray,
                         n: int = 200_000, far: float = 3.0,
                         small: float = 1.0) -> dict[str, Any]:
    """How often does each certificate read 'converged' far from the solution?"""
    rng = np.random.default_rng(1)
    star_psi = psi(model, x_star)
    far_phi = far_v = total = 0
    for _ in range(n):
        x = x_star + rng.normal(0, 4.0, 3) * SCALE_D
        if np.linalg.norm((x - x_star) / SCALE_D) <= far:
            continue
        total += 1
        far_phi += int(phi(model, x) < small)
        far_v += int(star_psi - psi(model, x) < small)
    return {
        "states_beyond_radius": total, "radius": far, "threshold": small,
        "phi_false_converged": far_phi, "phi_false_rate": far_phi / max(total, 1),
        "V_false_converged": far_v, "V_false_rate": far_v / max(total, 1),
    }


def _load_rounds(path: Path) -> dict[str, list[dict[str, Any]]]:
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rec = json.loads(line)
            by_pair[rec["pair_id"]].append(rec)
    for recs in by_pair.values():
        recs.sort(key=lambda r: r["round_index"])
    return by_pair


def check_live(arms: tuple[str, ...], data: str, results: Path) -> dict[str, Any]:
    reg = ContractRegistry.from_data_dir(data)
    models: dict[str, PayoffModel] = {}
    star: dict[str, np.ndarray] = {}

    def model_for(pid: str) -> PayoffModel | None:
        if pid not in models:
            b_id, c_id = pid.split("|", 1)
            b, c = reg.businesses.get(b_id), reg.customers.get(c_id)
            if b is None or c is None:
                return None
            try:
                models[pid] = PayoffModel.from_scenario(b, c)
            except ValueError:
                return None
            star[pid] = models[pid].nash_bargaining_solution()[0]
        return models.get(pid)

    out: dict[str, Any] = {}
    for arm in arms:
        n = d_s = d_ok = p_s = p_ok = f_s = f_ok = 0
        for run in sorted(results.glob(f"arm_{arm}_*/certificates.jsonl")):
            for pid, recs in _load_rounds(run).items():
                model = model_for(pid)
                if model is None or len(recs) < 3:
                    continue
                n += 1
                xs = [np.array(r["x_applied"], dtype=float) for r in recs]
                dist = np.array([dist_M(x, star[pid]) for x in xs])
                pot = np.array([psi(model, x) for x in xs])
                ph = np.array([phi(model, x) for x in xs])
                d_s += len(dist) - 1; d_ok += int((np.diff(dist) <= 1e-9).sum())
                p_s += len(pot) - 1;  p_ok += int((np.diff(pot) >= -1e-9).sum())
                f_s += len(ph) - 1;   f_ok += int((np.diff(ph) <= 1e-9).sum())
        out[arm] = {
            "trajectories": n,
            "distance_down": [d_ok, d_s], "distance_frac": d_ok / max(d_s, 1),
            "psi_up": [p_ok, p_s], "psi_frac": p_ok / max(p_s, 1),
            "phi_down": [f_ok, f_s], "phi_frac": f_ok / max(f_s, 1),
        }
    return out


def main() -> None:
    model = PayoffModel()
    x_star, _ = model.nash_bargaining_solution()

    report = {
        "integrability": check_integrability(model, x_star),
        "spurious_zeros": check_spurious_zeros(model, x_star),
        "live": check_live(("c", "a"), "data/bargain_3_9", Path("results")),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=2))

    i = report["integrability"]
    print("F = grad Psi ?      worst relative mismatch:", f"{i['worst_rel_grad_mismatch']:.2e}")
    print("grad F symmetric ?  worst relative asymmetry:", f"{i['worst_rel_jacobian_asymmetry']:.2e}")
    print("Hessian(Psi) at NBS:", np.round(i["hessian_eigenvalues_at_nbs"], 4),
          "-> negative definite:", i["negative_definite_at_nbs"])
    s = report["spurious_zeros"]
    print(f"\nbeyond {s['radius']} scaled units ({s['states_beyond_radius']} states):")
    print(f"  Phi < {s['threshold']} (false 'converged'): {s['phi_false_converged']} ({s['phi_false_rate']:.1%})")
    print(f"  V   < {s['threshold']} (false 'converged'): {s['V_false_converged']} ({s['V_false_rate']:.1%})")
    print("\nlive trajectories:")
    for arm, r in report["live"].items():
        print(f"  arm {arm.upper()} ({r['trajectories']} traj): "
              f"distance down {r['distance_frac']:.3f} | "
              f"Psi up {r['psi_frac']:.3f} | Phi down {r['phi_frac']:.3f}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
