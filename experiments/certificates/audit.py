"""Audit script: reliability probes on top of the reproduced experiments."""

import numpy as np
from scipy.optimize import minimize

from dcbf_negotiation import Contract
from lyapunov_layer import (nash_point, V, proposal, joint_dcbf_filter, R)
from gne_shadow_price import joint_filter_with_duals, estimate_gne, X1_0, X2_0
from netgain_energy import G_netgain

rng = np.random.default_rng(99)


# ---------- (A) robust transient-only contraction estimator -----------------

def contraction_transient(Vs, floor_frac=0.05):
    """Fit log V vs k ONLY on the initial monotone-ish transient: from k=0
    until V first drops below floor_frac * V_0 (or stops improving for 3
    consecutive round-pairs). Avoids the noise-ball plateau AND rising
    excursions that polluted the original fit."""
    Vs = np.maximum(np.asarray(Vs, float), 1e-12)
    floor = max(Vs[0] * floor_frac, 1e-9)
    end, worse = 1, 0
    best = Vs[0]
    for i in range(1, len(Vs)):
        if Vs[i] < floor:
            end = i + 1
            break
        if Vs[i] < best:
            best, worse = Vs[i], 0
        else:
            worse += 1
            if worse >= 3:
                break
        end = i + 1
    end = max(end, 3)
    k = np.arange(end)
    coef = np.polyfit(k, np.log(Vs[:end]), 1)[0]
    return float(np.exp(coef))


def rerun_binding_with_robust_fit(episodes=12, T=40, Q=140.0):
    x_unc = nash_point()
    g1, g2 = estimate_gne(Q, T=200)
    out = {n: [] for n in ["V_naive", "V_gne", "G_netgain"]}
    dec = {n: [] for n in out}
    for _ in range(episodes):
        c1, c2 = Contract(), Contract()
        xs = [X1_0.copy(), X2_0.copy()]
        series = {n: [] for n in out}
        for k in range(T):
            if k % 2 == 0:
                series["V_naive"].append(V(xs[0], x_unc) + V(xs[1], x_unc))
                series["V_gne"].append(V(xs[0], g1) + V(xs[1], g2))
                series["G_netgain"].append(
                    G_netgain(xs, [c1, c2], Q, first_role="buyer"))
            role = "buyer" if k % 2 == 0 else "seller"
            ups = [proposal(x, role) for x in xs]
            us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2], shared_capacity=Q)
            xs = [x + u for x, u in zip(xs, us)]
        for n, vals in series.items():
            out[n].append(contraction_transient(vals))
            dec[n].append(np.mean(np.diff(vals) <= 1e-9))
    print("(A) Binding Q=140, TRANSIENT-ONLY contraction fit "
          f"({episodes} fresh episodes):")
    for n in out:
        print(f"    {n:<12} contraction={np.mean(out[n]):.4f}   "
              f"frac_decreasing={np.mean(dec[n]):.4f}")
    print()


# ---------- (B) SLSQP reliability probe -------------------------------------

def slsqp_probe(n_states=60):
    """Sample states along a noisy coupled trajectory; re-solve the joint QP
    at each and record scipy convergence status + worst constraint residual
    of the returned solution (linearised DCBF rows)."""
    c1, c2 = Contract(), Contract()
    xs = [X1_0.copy(), X2_0.copy()]
    fails, worst_resid = 0, 0.0
    n_checked = 0
    for k in range(n_states):
        role = "buyer" if k % 2 == 0 else "seller"
        ups = [proposal(x, role) for x in xs]
        # replicate the QP to inspect res.success and residuals
        n = 2
        rows = []
        for i, (x, c) in enumerate(zip(xs, [c1, c2])):
            h0, J = c.h(x), c.grad_h(x)
            for j in range(len(h0)):
                g = np.zeros(3 * n)
                g[3 * i:3 * i + 3] = J[j]
                rows.append((g, h0[j]))
        g = np.zeros(3 * n)
        g[1] = g[4] = -1.0
        rows.append((g, 140.0 - (xs[0][1] + xs[1][1])))
        m = len(rows)
        up = np.concatenate(ups)
        gamma, rho = 0.4, 1e4

        def obj(z):
            return np.sum((z[:3 * n] - up) ** 2) + rho * np.sum(z[3 * n:] ** 2)

        def gr(z):
            return np.concatenate([2 * (z[:3 * n] - up), 2 * rho * z[3 * n:]])

        cons = []
        for idx, (gv, h0) in enumerate(rows):
            cons.append({"type": "ineq",
                         "fun": (lambda z, gv=gv, h0=h0, idx=idx:
                                 gv @ z[:3 * n] + gamma * h0 + z[3 * n + idx])})
            cons.append({"type": "ineq",
                         "fun": (lambda z, idx=idx: z[3 * n + idx])})
        z0 = np.concatenate([up, np.zeros(m)])
        res = minimize(obj, z0, jac=gr, constraints=cons, method="SLSQP",
                       options={"maxiter": 300, "ftol": 1e-10})
        n_checked += 1
        if not res.success:
            fails += 1
        resid = min(gv @ res.x[:3 * n] + gamma * h0 + res.x[3 * n + i]
                    for i, (gv, h0) in enumerate(rows))
        worst_resid = min(worst_resid, resid)
        # advance the true trajectory with the standard filter
        us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2], shared_capacity=140.0)
        xs = [x + u for x, u in zip(xs, us)]
    print(f"(B) SLSQP probe over {n_checked} QPs on a live trajectory: "
          f"failures={fails}, worst linearised-constraint residual="
          f"{worst_resid:.2e}")
    print()


# ---------- (C) decrease-in-expectation check -------------------------------

def expectation_check(n_mc=300):
    """At fixed early/mid states of the single-pair filtered dynamics, Monte
    Carlo the ONE-round-pair change in V. Claim under test: E[dV] < 0 away
    from the noise ball (even though pointwise dV>0 happens ~31% of steps)."""
    x_star = nash_point()
    c = Contract()
    for label, x0 in [("early (far from x*)", np.array([9.0, 90.0, 30.0])),
                      ("mid (halfway)", 0.5 * (np.array([9.0, 90.0, 30.0])
                                               + x_star))]:
        dVs = []
        for _ in range(n_mc):
            x = x0.copy()
            for k in range(2):
                role = "buyer" if k % 2 == 0 else "seller"
                (u,), _, _ = joint_dcbf_filter([x], [proposal(x, role)], [c])
                x = x + u
            dVs.append(V(x, x_star) - V(x0, x_star))
        dVs = np.array(dVs)
        print(f"(C) E[dV] at {label}: {dVs.mean():+.3f} "
              f"(std err {dVs.std() / np.sqrt(n_mc):.3f}; "
              f"pointwise dV>0 on {np.mean(dVs > 0):.0%} of draws)")
    print()


# ---------- (D) F6 reduced reproduction -------------------------------------

def f6_reduced():
    x_unc = nash_point()
    for Q in [170.0, 140.0]:
        c1, c2 = Contract(), Contract()
        x1, x2 = X1_0.copy(), X2_0.copy()
        lams = []
        for k in range(150):
            role = "buyer" if k % 2 == 0 else "seller"
            ups = [proposal(x1, role, noisy=False),
                   proposal(x2, role, noisy=False)]
            (u1, u2), lam = joint_filter_with_duals(
                [x1, x2], ups, [c1, c2], Q)
            x1, x2 = x1 + u1, x2 + u2
            lams.append(lam)
        print(f"(D) Q={Q}: noise-free GNE q1+q2={x1[1] + x2[1]:.1f} "
              f"(unconstrained {2 * x_unc[1]:.1f}); shadow-price tail "
              f"lambda={np.mean(lams[-20:]):.3f}")
    print()


if __name__ == "__main__":
    f6_reduced()
    rerun_binding_with_robust_fit()
    slsqp_probe()
    expectation_check()
