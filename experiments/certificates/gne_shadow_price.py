"""
Binding-capacity composition experiment + shadow-price readout.
(Recreated after container reset — identical to the original.)

(1) GNE re-anchor: with shared capacity Q=140 < q1*+q2* = 162.9 the coupling
    constraint is BINDING at equilibrium. The agreement point shifts to the
    generalised Nash equilibrium (GNE), estimated from a long noise-free run.
(2) Shadow price: KKT multiplier of the shared-capacity DCBF constraint,
    extracted per round via NNLS on the KKT stationarity condition.
"""

import numpy as np
from scipy.optimize import nnls

from dcbf_negotiation import Contract
from lyapunov_layer import (nash_point, V, proposal, joint_dcbf_filter,
                            contraction_rate, TARGETS, R)

rng = np.random.default_rng(7)

GAMMA, RHO = 0.4, 1e4
X1_0 = np.array([9.0, 65.0, 30.0])
X2_0 = np.array([8.5, 70.0, 25.0])


def joint_filter_with_duals(xs, u_props, contracts, shared_capacity,
                            gamma=GAMMA, rho=RHO):
    n = len(xs)
    rows = []
    for i, (x, c) in enumerate(zip(xs, contracts)):
        h0, J = c.h(x), c.grad_h(x)
        for j in range(len(h0)):
            g = np.zeros(3 * n)
            g[3 * i:3 * i + 3] = J[j]
            rows.append((g, h0[j]))
    if shared_capacity is not None:
        g = np.zeros(3 * n)
        for i in range(n):
            g[3 * i + 1] = -1.0
        rows.append((g, shared_capacity - sum(x[1] for x in xs)))
    shared_idx = len(rows) - 1
    m = len(rows)
    u_prop_flat = np.concatenate(u_props)

    from scipy.optimize import minimize

    def obj(z):
        u, d = z[:3 * n], z[3 * n:]
        return np.sum((u - u_prop_flat) ** 2) + rho * np.sum(d ** 2)

    def obj_grad(z):
        return np.concatenate([2 * (z[:3 * n] - u_prop_flat),
                               2 * rho * z[3 * n:]])

    cons = []
    for idx, (g, h0) in enumerate(rows):
        cons.append({"type": "ineq",
                     "fun": (lambda z, g=g, h0=h0, idx=idx:
                             g @ z[:3 * n] + gamma * h0 + z[3 * n + idx])})
        cons.append({"type": "ineq",
                     "fun": (lambda z, idx=idx: z[3 * n + idx])})
    z0 = np.concatenate([u_prop_flat, np.zeros(m)])
    res = minimize(obj, z0, jac=obj_grad, constraints=cons, method="SLSQP",
                   options={"maxiter": 300, "ftol": 1e-10})
    z = res.x
    u = z[:3 * n]
    u_safes = [u[3 * i:3 * i + 3] for i in range(n)]

    grad_f = obj_grad(z)
    A_cols, col_is_shared = [], []
    for idx, (g, h0) in enumerate(rows):
        resid = g @ u + gamma * h0 + z[3 * n + idx]
        if abs(resid) < 1e-4:
            a = np.zeros(3 * n + m)
            a[:3 * n] = g
            a[3 * n + idx] = 1.0
            A_cols.append(a)
            col_is_shared.append(idx == shared_idx)
        if abs(z[3 * n + idx]) < 1e-8:
            a = np.zeros(3 * n + m)
            a[3 * n + idx] = 1.0
            A_cols.append(a)
            col_is_shared.append(False)
    lam_shared = 0.0
    if A_cols:
        A = np.stack(A_cols, axis=1)
        lam, _ = nnls(A, grad_f)
        for lval, is_sh in zip(lam, col_is_shared):
            if is_sh:
                lam_shared = float(lval)
    return u_safes, lam_shared


def estimate_gne(capacity, T=300):
    c1, c2 = Contract(), Contract()
    x1, x2 = X1_0.copy(), X2_0.copy()
    for k in range(T):
        role = "buyer" if k % 2 == 0 else "seller"
        ups = [proposal(x1, role, noisy=False), proposal(x2, role, noisy=False)]
        (u1, u2), _ = joint_filter_with_duals([x1, x2], ups, [c1, c2],
                                              capacity)
        x1, x2 = x1 + u1, x2 + u2
    return x1.copy(), x2.copy()


def run_coupled(capacity, anchor1, anchor2, episodes=20, T=40):
    rates, dec_fracs, lam_tail = [], [], []
    for _ in range(episodes):
        c1, c2 = Contract(), Contract()
        x1, x2 = X1_0.copy(), X2_0.copy()
        Vs = [V(x1, anchor1) + V(x2, anchor2)]
        lams = []
        for k in range(T):
            role = "buyer" if k % 2 == 0 else "seller"
            ups = [proposal(x1, role), proposal(x2, role)]
            (u1, u2), lam = joint_filter_with_duals([x1, x2], ups, [c1, c2],
                                                    capacity)
            x1, x2 = x1 + u1, x2 + u2
            lams.append(lam)
            if k % 2 == 1:
                Vs.append(V(x1, anchor1) + V(x2, anchor2))
        Vs = np.array(Vs)
        rates.append(contraction_rate(Vs))
        dec_fracs.append(np.mean(np.diff(Vs) <= 1e-9))
        lam_tail.append(np.mean(lams[-10:]))
    return {"V_sum_contraction": float(np.mean(rates)),
            "frac_steps_Vsum_decreasing": float(np.mean(dec_fracs)),
            "shadow_price_tail_mean": float(np.mean(lam_tail)),
            "shadow_price_tail_std": float(np.std(lam_tail))}


def main():
    x_unc = nash_point()
    print(f"Unconstrained Nash point x* = {np.round(x_unc, 2)}  "
          f"(q1*+q2* = {2 * x_unc[1]:.1f})\n")
    for Q in [170.0, 140.0]:
        binding = 2 * x_unc[1] > Q
        g1, g2 = estimate_gne(Q)
        qsum = g1[1] + g2[1]
        print(f"=== Q = {Q}  ({'BINDING' if binding else 'slack'}) ===")
        print(f"empirical GNE: pair1 {np.round(g1, 2)}, "
              f"pair2 {np.round(g2, 2)}  (q1+q2 = {qsum:.1f})")
        naive = run_coupled(Q, x_unc, x_unc)
        gne = run_coupled(Q, g1, g2)
        print(f"{'metric':<34}{'V @ unconstr. x*':>18}{'V @ GNE':>12}")
        print("-" * 64)
        for key in ["V_sum_contraction", "frac_steps_Vsum_decreasing",
                    "shadow_price_tail_mean"]:
            print(f"{key:<34}{naive[key]:>18.4f}{gne[key]:>12.4f}")
        print()


if __name__ == "__main__":
    main()
