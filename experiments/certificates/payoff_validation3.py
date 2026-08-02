"""
Round-3 validation: closing the three open points from round 2.

E11 Phi -> 0 with a properly tuned diminishing step (round 2 decayed too
    fast to finish).
E12 The FRICTION WINDOW. The termination threshold is state-dependent,
    kappa*(x) = rho * max_i ||grad Uhat_i(x)||_M. At a far start it is small,
    at the deal point it is large. Constant friction below kappa*(x_0) never
    stops; above kappa*(NBS) never starts. Only friction inside the window --
    or escalating friction -- both starts and stops.
E13 PROJECTED certificate under a binding constraint: the unconstrained field
    does not vanish at the constrained optimum; the field projected onto the
    tangent cone of the active constraints does. This is the merit function
    analogue of the KKT/GNE condition, and the anchor-free certificate that
    survives coupling.
"""

import numpy as np

from payoff_model import (U_B, U_S, W, grad_Uhat, norm_M, nbs_closed_form,
                          nbs_numeric, SCALE)
from payoff_dynamics import BOUNDS, X0, concession_field, clip_to_box, step_agent

rng = np.random.default_rng(13)
X_NBS, W_NBS = nbs_closed_form()
BMAX = 800.0


def Phi(x):
    return norm_M(concession_field(x))


def kappa_star(x, rho):
    gb = norm_M(grad_Uhat(x, "buyer"))
    gs = norm_M(grad_Uhat(x, "seller"))
    return rho * max(gb, gs), rho * min(gb, gs)


# --------------------------------- E11 --------------------------------------

def e11_phi_to_zero(rho0=0.8, T=3000, decay=0.9993):
    x = X0.copy()
    rec = []
    for k in range(T):
        rho = rho0 * (decay ** k)
        role = "buyer" if k % 2 == 0 else "seller"
        x, _ = step_agent(x, role, rho, 0.0)
        if k % 2 == 1:
            rec.append((Phi(x), np.linalg.norm((x - X_NBS) / SCALE)))
    P_, D_ = np.array(rec).T
    print("E11 Phi -> 0 (tuned diminishing step, no friction):")
    print(f"    Phi: {P_[0]:.3f} -> {P_[-1]:.4f}   "
          f"decreasing on {np.mean(np.diff(P_) <= 1e-9):.0%} of round-pairs")
    print(f"    ||x-NBS||_scaled: {D_[0]:.3f} -> {D_[-1]:.5f}")
    print(f"    settled p={x[0]:.4f} q={x[1]:.3f} d={x[2]:.3f} | "
          f"U_B={U_B(x):.2f} U_S={U_S(x):.2f} W={W(x):.3f} "
          f"(W_max={W_NBS:.3f}, gap {100*(W_NBS-W(x))/W_NBS:.3f}%)")
    print(f"    corr(Phi, dist) = {np.corrcoef(P_, D_)[0, 1]:.4f}; "
          f"ratio Phi/dist at end = {P_[-1]/max(D_[-1],1e-9):.1f} "
          f"(local slope of the merit function)")


# --------------------------------- E12 --------------------------------------

def e12_friction_window(rho=0.5):
    k_start, _ = kappa_star(X0, rho)
    k_deal, _ = kappa_star(X_NBS, rho)
    print(f"\nE12 Friction window (rho={rho}):")
    print(f"    kappa*(x_0)  = {k_start:.2f}   (below this, motion never "
          f"stalls at the start)")
    print(f"    kappa*(NBS)  = {k_deal:.2f}   (above this, no motion even at "
          f"the deal point)")
    print(f"    window = [{k_start:.2f}, {k_deal:.2f}]")
    print(f"    {'kappa':>8}{'moved?':>8}{'stop k':>8}{'||x-NBS||_s':>13}"
          f"{'W':>9}{'W loss %':>10}")
    for kappa in [0.5 * k_start, 0.9 * k_start, 1.5 * k_start, 0.5 * k_deal,
                  0.9 * k_deal, 1.1 * k_deal]:
        x = X0.copy()
        stop_k, moved_any = None, False
        for k in range(2000):
            role = "buyer" if k % 2 == 0 else "seller"
            xn, mi = step_agent(x, role, rho, kappa)
            other = "seller" if role == "buyer" else "buyer"
            _, mj = step_agent(x, other, rho, kappa)
            moved_any = moved_any or mi or mj
            if not mi and not mj:
                stop_k = k
                break
            x = xn
        loss = 100 * (W_NBS - W(x)) / W_NBS
        print(f"    {kappa:>8.2f}{str(moved_any):>8}{str(stop_k):>8}"
              f"{np.linalg.norm((x - X_NBS) / SCALE):>13.3f}{W(x):>9.2f}"
              f"{loss:>10.2f}")


# --------------------------------- E13 --------------------------------------

def budget_active(x, tol=1e-6):
    return x[0] * x[1] >= BMAX - tol


def grad_budget(x):
    # g(x) = BMAX - p q  ->  grad = (-q, -p, 0)
    return np.array([-x[1], -x[0], 0.0])


def Phi_projected(x):
    """Norm of the joint field projected onto the tangent cone of the active
    constraint set (metric-consistent projection)."""
    F = concession_field(x)
    if not budget_active(x):
        return norm_M(F)
    a = grad_budget(x)
    # work in scaled coordinates: v_s = v * SCALE (dual), a_s = a * SCALE
    F_s, a_s = F * SCALE, a * SCALE
    if a_s @ F_s >= 0:                       # field points into the set
        return float(np.linalg.norm(F_s))
    F_proj = F_s - (a_s @ F_s) / (a_s @ a_s) * a_s
    return float(np.linalg.norm(F_proj))


def project_budget(x):
    x = clip_to_box(x)
    if x[0] * x[1] > BMAX:
        x[0] = BMAX / x[1]
    return x


def e13_projected_certificate(rho0=0.8, T=3000, decay=0.9993):
    cons = ({"type": "ineq", "fun": lambda z: BMAX - z[0] * z[1]},)
    x_c = nbs_numeric(BOUNDS, extra_cons=cons)
    print(f"\nE13 Binding budget B={BMAX} "
          f"(unconstrained NBS spend={X_NBS[0]*X_NBS[1]:.0f}):")
    print(f"    constrained NBS: p={x_c[0]:.4f} q={x_c[1]:.3f} "
          f"d={x_c[2]:.3f} | U_B={U_B(x_c):.2f} U_S={U_S(x_c):.2f} "
          f"spend={x_c[0]*x_c[1]:.1f}")
    print(f"    at constrained NBS:  Phi = {Phi(x_c):8.3f}   "
          f"Phi_projected = {Phi_projected(x_c):.4f}")
    print(f"    at UNconstrained NBS: Phi = {Phi(X_NBS):8.3f}   "
          f"(feasible? {X_NBS[0]*X_NBS[1] <= BMAX})")

    x = X0.copy()
    rec = []
    for k in range(T):
        rho = rho0 * (decay ** k)
        role = "buyer" if k % 2 == 0 else "seller"
        xn, _ = step_agent(x, role, rho, 0.0)
        x = project_budget(xn)
        if k % 2 == 1:
            rec.append((Phi(x), Phi_projected(x),
                        np.linalg.norm((x - x_c) / SCALE)))
    P_, PP_, D_ = np.array(rec).T
    print(f"    along the constrained dynamics:")
    print(f"      Phi (unprojected): {P_[0]:.2f} -> {P_[-1]:.3f}  "
          f"decreasing {np.mean(np.diff(P_) <= 1e-9):.0%}")
    print(f"      Phi_projected    : {PP_[0]:.2f} -> {PP_[-1]:.4f}  "
          f"decreasing {np.mean(np.diff(PP_) <= 1e-9):.0%}")
    print(f"      ||x - constrained NBS||_scaled: {D_[0]:.3f} -> {D_[-1]:.5f}")
    print(f"      settled p={x[0]:.4f} q={x[1]:.3f} d={x[2]:.3f} "
          f"spend={x[0]*x[1]:.2f}")
    print(f"      corr(Phi_proj, dist) = {np.corrcoef(PP_, D_)[0,1]:.4f}  |  "
          f"corr(Phi, dist) = {np.corrcoef(P_, D_)[0,1]:.4f}")


if __name__ == "__main__":
    e11_phi_to_zero()
    e12_friction_window()
    e13_projected_certificate()
