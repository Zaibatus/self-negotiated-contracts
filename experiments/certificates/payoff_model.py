"""
Payoff-based formulation validation.

Replaces the prototype's arbitrary "targets" with genuine utilities, so that
the Nash equilibrium is derived from preferences rather than baked into a
concession heuristic.

Model
-----
Terms x = (p, q, d).  Quasi-linear quadratic utilities, price = pure transfer:
    U_B(x) = a q - (b/2) q^2 - p q - (gB/2)(d - dB0)^2
    U_S(x) =            p q - c q - (e/2) q^2 - (gS/2)(d - dS0)^2
Disagreement payoffs normalised to 0.

Joint surplus W = U_B + U_S is independent of p (transfer), so efficiency
fixes (q, d) and bargaining fixes p:
    q_eff = (a - c)/(b + e),  d_eff = (gB dB0 + gS dS0)/(gB + gS)
Nash bargaining solution (symmetric, quasi-linear): efficient (q,d) + equal
split of W  ->  closed form for p.

Acceptance-weighted objective (the concession trade-off):
    P(x) = sigma(U_B(x)/lam) * sigma(U_S(x)/lam)        (deal closes only if
                                                         both find it OK)
    Uhat_i(x) = P(x) * U_i(x)
Single-negotiating-text protocol: agents alternately propose modifications to
a shared draft x; each ascends its own Uhat_i, limited by a step budget rho
(in a unit-normalising metric M) and a switching cost kappa.

Frictional net-gain energy (payoff units):
    g_i(x) = [ rho * ||grad Uhat_i(x)||_M - kappa_k ]_+ ,   G = g_B + g_S
    NE_kappa = { x : G(x) = 0 }  (no agent's remaining incentive is worth the
                                   friction)
Deadline pressure = escalating friction kappa_k, which forces G -> 0 by T_max.
"""

import numpy as np
from scipy.optimize import minimize

# ----------------------------- parameters -----------------------------------

A, B_Q = 12.0, 0.04        # buyer value  V(q) = A q - B_Q/2 q^2
C0, E_Q = 6.0, 0.02        # seller cost  C(q) = C0 q + E_Q/2 q^2
GB, GS = 0.3, 0.3          # deadline curvature
DB0, DS0 = 40.0, 12.0      # ideal deadlines (buyer late, seller early)
LAM = 60.0                 # acceptance temperature (utility scale ~120)

# unit-normalising metric: typical scales for (p, q, d)
SCALE = np.array([1.0, 10.0, 5.0])
MINV = 1.0 / SCALE                      # ||v||_M = ||v / SCALE||


def U_B(x):
    p, q, d = x
    return A * q - 0.5 * B_Q * q ** 2 - p * q - 0.5 * GB * (d - DB0) ** 2


def U_S(x):
    p, q, d = x
    return p * q - C0 * q - 0.5 * E_Q * q ** 2 - 0.5 * GS * (d - DS0) ** 2


def W(x):
    return U_B(x) + U_S(x)


# --------------------------- Nash bargaining --------------------------------

def nbs_closed_form():
    q = (A - C0) / (B_Q + E_Q)
    d = (GB * DB0 + GS * DS0) / (GB + GS)
    w = (A - C0) * q - 0.5 * (B_Q + E_Q) * q ** 2 \
        - 0.5 * GB * (d - DB0) ** 2 - 0.5 * GS * (d - DS0) ** 2
    # U_S = T - C(q) - Phi_S = w/2  ->  T = w/2 + C(q) + Phi_S
    T = 0.5 * w + C0 * q + 0.5 * E_Q * q ** 2 + 0.5 * GS * (d - DS0) ** 2
    p = T / q
    return np.array([p, q, d]), w


def nbs_numeric(bounds, extra_cons=()):
    """Maximise the Nash product over a box (+ optional constraints)."""
    def neg(x):
        ub, us = U_B(x), U_S(x)
        if ub <= 0 or us <= 0:
            return 1e6 - ub - us
        return -(np.log(ub) + np.log(us))
    best, bx = np.inf, None
    for seed in range(6):
        x0 = np.array([np.random.default_rng(seed).uniform(lo, hi)
                       for lo, hi in bounds])
        r = minimize(neg, x0, bounds=bounds, constraints=extra_cons,
                     method="SLSQP", options={"maxiter": 500, "ftol": 1e-12})
        if r.fun < best:
            best, bx = r.fun, r.x
    return bx


# ----------------------- acceptance-weighted objective ----------------------

def sigma(u):
    return 1.0 / (1.0 + np.exp(-np.clip(u, -50, 50)))


def P_accept(x):
    return sigma(U_B(x) / LAM) * sigma(U_S(x) / LAM)


def Uhat(x, role):
    u = U_B(x) if role == "buyer" else U_S(x)
    return P_accept(x) * u


def grad_Uhat(x, role, h=1e-5):
    g = np.zeros(3)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h * SCALE[i]
        g[i] = (Uhat(x + e, role) - Uhat(x - e, role)) / (2 * e[i])
    return g


def norm_M(v):
    return float(np.linalg.norm(v * SCALE))      # dual norm in the metric


def G_energy(x, kappa, rho):
    tot = 0.0
    for role in ("buyer", "seller"):
        gain = rho * norm_M(grad_Uhat(x, role)) - kappa
        tot += max(gain, 0.0)
    return tot


if __name__ == "__main__":
    x_nbs, w = nbs_closed_form()
    print("Nash bargaining solution (closed form):")
    print(f"  p={x_nbs[0]:.3f}  q={x_nbs[1]:.2f}  d={x_nbs[2]:.2f}")
    print(f"  W={w:.2f}  U_B={U_B(x_nbs):.2f}  U_S={U_S(x_nbs):.2f}")
    bounds = [(6.0, 12.0), (20.0, 120.0), (7.0, 45.0)]
    x_num = nbs_numeric(bounds)
    print(f"  numeric check: p={x_num[0]:.3f} q={x_num[1]:.2f} d={x_num[2]:.2f}"
          f"  (max |diff| = {np.max(np.abs(x_num - x_nbs)):.2e})")
    print(f"  P_accept at NBS = {P_accept(x_nbs):.4f}")
    print(f"  G at NBS (kappa=0, rho=1): {G_energy(x_nbs, 0.0, 1.0):.3f}")
