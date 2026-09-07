"""Closed form for the constrained rest point, and its validation.

The funnel sweep (2026-08-28) measured that pinning the *price* row drags the
settled *deadline* off its efficient value, on a coordinate the contract does
not mention. That note recorded the displacement and said a closed form "would
be a genuine addition and is not attempted here". This is that closed form.

Derivation.  The d-component of the joint concession field is

    F_d = d/dd (P U_B) + d/dd (P U_S)
        = P dW/dd + W dP/dd .

With P = sigma(U_B/lam) sigma(U_S/lam) and sigma' = sigma(1-sigma),

    dP/dd = (P/lam) [ w_B dU_B/dd + w_S dU_S/dd ],   w_i := 1 - sigma(U_i/lam)

so, substituting dU_i/dd = -gamma_i (d - d_i) and P > 0, F_d vanishes exactly when

    gamma~_B (d - d_B) + gamma~_S (d - d_S) = 0,   gamma~_i := gamma_i (1 + W w_i / lam)

    =>   d(p) = (gamma~_B d_B + gamma~_S d_S) / (gamma~_B + gamma~_S).          (*)

(*) is the same weighted average as the efficient deadline of Proposition 1,
with each party's weight multiplied by its *acceptance slack* w_i.  When the
budget row binds against the seller, U_S falls, w_S rises, and the seller's
deadline preference gains weight: every unconstrained coordinate moves toward
the ideal point of whichever party the constraint hurts.  Where the constraint
does not bind, U_B = U_S forces w_B = w_S and (*) collapses to d_eff, so
Proposition 1 is the special case.

Run:  uv run python experiments/constrained_rest_point.py
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

# Reference calibration of docs/formulation.md 3.2. Not used for live work.
A, B_CURV, C_COST, E_CURV = 12.0, 0.04, 6.0, 0.02
GAMMA_B = GAMMA_S = 0.3
D_B, D_S = 40.0, 12.0
LAMBDA = 60.0
Q_PIN = 100.0

SWEEP = Path("results/summary/funnel_sweep.json")
OUT = Path("results/summary/constrained_rest_point.json")


def _sigma(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-z))


def u_buyer(p: float, d: float, q: float = Q_PIN) -> float:
    return A * q - (B_CURV / 2) * q * q - p * q - (GAMMA_B / 2) * (d - D_B) ** 2


def u_seller(p: float, d: float, q: float = Q_PIN) -> float:
    return p * q - C_COST * q - (E_CURV / 2) * q * q - (GAMMA_S / 2) * (d - D_S) ** 2


def field_d(p: float, d: float) -> float:
    """-F_d / P: vanishes exactly where the joint field's d-component does."""
    ub, us = u_buyer(p, d), u_seller(p, d)
    w = ub + us
    t_b = GAMMA_B * (1.0 + w * (1.0 - _sigma(ub / LAMBDA)) / LAMBDA)
    t_s = GAMMA_S * (1.0 + w * (1.0 - _sigma(us / LAMBDA)) / LAMBDA)
    return t_b * (d - D_B) + t_s * (d - D_S)


def rest_deadline(p: float, lo: float = -50.0, hi: float = 120.0, n: int = 20000) -> float:
    """The interior (attracting) root of (*). The two outer roots are repelling."""
    xs = np.linspace(lo, hi, n)
    vs = [field_d(p, x) for x in xs]
    roots = [
        brentq(lambda d: field_d(p, d), xs[i], xs[i + 1])
        for i in range(n - 1)
        if vs[i] * vs[i + 1] < 0
    ]
    if not roots:
        raise RuntimeError(f"no rest point bracketed for p={p}")
    return sorted(roots)[len(roots) // 2]


def effective_weights(p: float) -> dict[str, float]:
    d = rest_deadline(p)
    ub, us = u_buyer(p, d), u_seller(p, d)
    w = ub + us
    w_b, w_s = 1.0 - _sigma(ub / LAMBDA), 1.0 - _sigma(us / LAMBDA)
    t_b, t_s = GAMMA_B * (1 + w * w_b / LAMBDA), GAMMA_S * (1 + w * w_s / LAMBDA)
    return {
        "p": p, "d": d, "u_buyer": ub, "u_seller": us,
        "slack_buyer": w_b, "slack_seller": w_s,
        "weight_buyer": t_b, "weight_seller": t_s,
        "seller_share": t_s / (t_b + t_s),
    }


def main() -> None:
    rows = json.loads(SWEEP.read_text())["rows"]
    recs, errs = [], []
    for r in rows:
        pred = rest_deadline(r["filt_price_mean"])
        meas = r["filt_deadline_mean"]
        errs.append(abs(pred - meas))
        recs.append({
            "p_boundary": r["p_boundary"], "binds": not r["filter_helps"],
            "measured_deadline": meas, "predicted_deadline": pred,
            "error_days": pred - meas,
        })

    meas = np.array([r["measured_deadline"] for r in recs])
    pred = np.array([r["predicted_deadline"] for r in recs])
    r2 = 1 - ((pred - meas) ** 2).sum() / ((meas - meas.mean()) ** 2).sum()

    summary = {
        "calibration": {
            "a": A, "b": B_CURV, "c": C_COST, "e": E_CURV,
            "gamma_b": GAMMA_B, "gamma_s": GAMMA_S,
            "d_b": D_B, "d_s": D_S, "lambda": LAMBDA, "q_pin": Q_PIN,
        },
        "unconstrained_check": {"p_star": 8.5, "d_predicted": rest_deadline(8.5), "d_eff": 26.0},
        "fit": {"r2": r2, "max_abs_error_days": float(max(errs)),
                "mean_abs_error_days": float(np.mean(errs)), "n_points": len(recs)},
        "weights_at": [effective_weights(p) for p in (8.5, 6.12)],
        "rows": recs,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(summary, indent=2))

    print(f"{'B/qmin':>8} {'binds':>6} {'measured':>9} {'closed form':>12} {'err':>7}")
    for r in recs:
        print(f"{r['p_boundary']:>8.3f} {str(r['binds']):>6} {r['measured_deadline']:>9.3f} "
              f"{r['predicted_deadline']:>12.3f} {r['error_days']:>+7.3f}")
    print(f"\nR^2 = {r2:.5f}   max |err| = {max(errs):.3f} d   mean |err| = {np.mean(errs):.3f} d")
    print(f"unconstrained: d({8.5}) = {rest_deadline(8.5):.6f}  (d_eff = 26)")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
