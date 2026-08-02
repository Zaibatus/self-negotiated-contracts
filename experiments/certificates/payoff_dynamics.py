"""
Validation of the payoff-based formulation: dynamics, energy, equilibrium.

E1  Balance point of the alternating concession dynamics; relation to NBS.
E2  G with escalating friction (deadline pressure) -> terminates by T_max.
E3  kappa-sweep: where the frictional NE set sits as friction shrinks.
E4  Stability: is the induced concession game monotone (Rosen DSC / stable
    game / passive)?  Sampled eigenvalues of sym(Jacobian) of the joint
    concession field.
E5  Binding budget: constrained NBS vs where the filtered dynamics land, and
    G -> 0 anchor-free.
"""

import numpy as np
from scipy.optimize import minimize

from payoff_model import (U_B, U_S, W, P_accept, Uhat, grad_Uhat, norm_M,
                          G_energy, nbs_closed_form, nbs_numeric, SCALE)

rng = np.random.default_rng(3)
X_REF = nbs_closed_form()[0]        # module-level reference point

BOUNDS = [(6.0, 12.0), (20.0, 120.0), (7.0, 45.0)]
X0 = np.array([11.0, 40.0, 40.0])          # far start (feasible)


# ------------------------- concession dynamics ------------------------------

def concession_field(x):
    """Joint field over one round-pair: sum of both agents' ascent
    directions on their acceptance-weighted objectives."""
    return grad_Uhat(x, "buyer") + grad_Uhat(x, "seller")


def clip_to_box(x):
    return np.array([np.clip(x[i], *BOUNDS[i]) for i in range(3)])


def step_agent(x, role, rho, kappa, eta=None):
    """Friction-limited ascent step on Uhat_role. Returns (new_x, moved)."""
    g = grad_Uhat(x, role)
    gain = rho * norm_M(g) - kappa
    if gain <= 0:
        return x, False
    step = g * (SCALE ** 2)                    # metric-consistent ascent
    nrm = norm_M(g)
    step = step / nrm * rho if nrm > 0 else step
    return clip_to_box(x + step), True


def run_dynamics(kappa0=0.0, T_max=None, rho=0.5, T=200, x0=None,
                 escalate=False):
    """Alternating friction-limited concessions on a shared draft."""
    x = (X0 if x0 is None else x0).copy()
    traj, Gs, kappas = [x.copy()], [], []
    for k in range(T):
        if escalate and T_max:
            frac = min(k / T_max, 0.999)
            kappa = kappa0 / (1.0 - frac)      # deadline pressure
        else:
            kappa = kappa0
        kappas.append(kappa)
        if k % 2 == 0:
            Gs.append(G_energy(x, kappa, rho))
        role = "buyer" if k % 2 == 0 else "seller"
        x, _ = step_agent(x, role, rho, kappa)
        traj.append(x.copy())
    return np.array(traj), np.array(Gs), np.array(kappas)


# --------------------------------- E1 ---------------------------------------

def e1_balance_point():
    """Zero of the joint concession field = stationary point of Uhat_B+Uhat_S
    = P(x) * W(x). Compare with NBS."""
    def neg_PW(x):
        return -(P_accept(x) * W(x))
    best, bx = np.inf, None
    for s in range(8):
        x0 = np.array([np.random.default_rng(s).uniform(lo, hi)
                       for lo, hi in BOUNDS])
        r = minimize(neg_PW, x0, bounds=BOUNDS, method="SLSQP",
                     options={"maxiter": 600, "ftol": 1e-12})
        if r.fun < best:
            best, bx = r.fun, r.x
    x_nbs, _ = nbs_closed_form()
    print("E1  Balance point (argmax P*W, zero of joint concession field):")
    print(f"    p={bx[0]:.3f} q={bx[1]:.2f} d={bx[2]:.2f} | "
          f"U_B={U_B(bx):.2f} U_S={U_S(bx):.2f} W={W(bx):.2f} "
          f"P={P_accept(bx):.4f}")
    print(f"    NBS       p={x_nbs[0]:.3f} q={x_nbs[1]:.2f} d={x_nbs[2]:.2f} | "
          f"W={W(x_nbs):.2f}")
    print(f"    ||balance - NBS|| (scaled) = "
          f"{np.linalg.norm((bx - x_nbs) / SCALE):.4f}")
    print(f"    field norm at balance = {norm_M(concession_field(bx)):.3e}, "
          f"at NBS = {norm_M(concession_field(x_nbs)):.3e}")
    return bx


# --------------------------------- E2 ---------------------------------------

def e2_escalating_friction(T_max=40, kappa0=2.0, rho=0.5):
    traj, Gs, kappas = run_dynamics(kappa0=kappa0, T_max=T_max, rho=rho,
                                    T=2 * T_max, escalate=True)
    stop = next((i for i, g in enumerate(Gs) if g <= 1e-9), None)
    dec = np.mean(np.diff(Gs) <= 1e-9)
    print(f"\nE2  Escalating friction (kappa_0={kappa0}, T_max={T_max} "
          f"round-pairs):")
    print(f"    G: {Gs[0]:.2f} -> {Gs[-1]:.4f};  G=0 first reached at "
          f"round-pair {stop} (<= T_max: {stop is not None and stop <= T_max})")
    print(f"    G decreasing on {dec:.0%} of round-pairs")
    xf = traj[-1]
    print(f"    settled at p={xf[0]:.3f} q={xf[1]:.2f} d={xf[2]:.2f} | "
          f"U_B={U_B(xf):.1f} U_S={U_S(xf):.1f} W={W(xf):.1f}")
    return traj, Gs


# --------------------------------- E3 ---------------------------------------

def e3_kappa_sweep(rho=0.5, bal=None):
    x_nbs, _ = nbs_closed_form()
    bal = e1_balance_point() if bal is None else bal
    print("\nE3  Friction sweep (fixed kappa, 400 round-pairs):")
    print(f"    {'kappa':>7}{'||x-NBS||_s':>13}{'||x-balance||_s':>17}"
          f"{'G_final':>10}{'W':>9}")
    for kappa in [8.0, 4.0, 2.0, 1.0, 0.5, 0.25]:
        traj, Gs, _ = run_dynamics(kappa0=kappa, rho=rho, T=800)
        xf = traj[-200:].mean(axis=0)          # average over the limit cycle
        print(f"    {kappa:>7.2f}"
              f"{np.linalg.norm((xf - x_nbs) / SCALE):>13.3f}"
              f"{np.linalg.norm((xf - bal) / SCALE):>17.3f}"
              f"{Gs[-1]:>10.3f}{W(xf):>9.2f}")


# --------------------------------- E4 ---------------------------------------

def e4_monotonicity(n=400, h=1e-4, ref=None):
    """Stable game / Rosen DSC / passivity test: is the joint concession field
    V(x) = grad Uhat_B + grad Uhat_S monotone-decreasing, i.e. is
    sym(J_V) negative semidefinite on the operating region?"""
    worst, frac_ok = -np.inf, 0
    for _ in range(n):
        x = np.array([rng.uniform(lo, hi) for lo, hi in BOUNDS])
        J = np.zeros((3, 3))
        for i in range(3):
            e = np.zeros(3)
            e[i] = h * SCALE[i]
            J[:, i] = (concession_field(x + e) - concession_field(x - e)) \
                / (2 * e[i])
        S = 0.5 * (J + J.T)
        # express in the normalising metric so eigenvalues are comparable
        D = np.diag(SCALE)
        S = D @ S @ D
        lmax = np.max(np.linalg.eigvalsh(S))
        worst = max(worst, lmax)
        frac_ok += (lmax <= 1e-8)
    print(f"\nE4  Stability of the induced game (sampled over the box, "
          f"n={n}):")
    print(f"    sym(J) negative semidefinite at {frac_ok / n:.1%} of sampled "
          f"states; worst eigenvalue = {worst:+.4f}")
    # restricted region: near the balance point
    ok, worstr = 0, -np.inf
    for _ in range(n):
        x = (X_REF if ref is None else ref) + rng.normal(0, 1, 3) * SCALE * 0.5
        x = clip_to_box(x)
        J = np.zeros((3, 3))
        for i in range(3):
            e = np.zeros(3)
            e[i] = h * SCALE[i]
            J[:, i] = (concession_field(x + e) - concession_field(x - e)) \
                / (2 * e[i])
        S = 0.5 * (J + J.T)
        D = np.diag(SCALE)
        S = D @ S @ D
        lmax = np.max(np.linalg.eigvalsh(S))
        worstr = max(worstr, lmax)
        ok += (lmax <= 1e-8)
    print(f"    within 0.5 scaled units of the balance point: NSD at "
          f"{ok / n:.1%}; worst = {worstr:+.4f}")


# --------------------------------- E5 ---------------------------------------

def e5_binding_budget(Bmax=800.0, kappa0=2.0, T_max=40, rho=0.5):
    """Budget p*q <= Bmax binds at the NBS (p*q = 850). Constrained NBS vs
    where the dynamics land under the same constraint."""
    cons = ({"type": "ineq", "fun": lambda x: Bmax - x[0] * x[1]},)
    x_c = nbs_numeric(BOUNDS, extra_cons=cons)
    print(f"\nE5  Binding budget (B={Bmax}; unconstrained NBS spend = 850):")
    print(f"    constrained NBS: p={x_c[0]:.3f} q={x_c[1]:.2f} d={x_c[2]:.2f} "
          f"| spend={x_c[0] * x_c[1]:.1f} U_B={U_B(x_c):.1f} "
          f"U_S={U_S(x_c):.1f}")

    # dynamics with a projection onto the budget set (stand-in for the DCBF
    # filter, which enforces the same set)
    def project(x):
        x = clip_to_box(x)
        if x[0] * x[1] > Bmax:                 # scale price down to the bound
            x[0] = Bmax / x[1]
        return x

    x = X0.copy()
    Gs = []
    for k in range(2 * T_max):
        frac = min(k / T_max, 0.999)
        kappa = kappa0 / (1.0 - frac)
        if k % 2 == 0:
            Gs.append(G_energy(x, kappa, rho))
        role = "buyer" if k % 2 == 0 else "seller"
        xn, _ = step_agent(x, role, rho, kappa)
        x = project(xn)
    print(f"    dynamics settle: p={x[0]:.3f} q={x[1]:.2f} d={x[2]:.2f} "
          f"| spend={x[0] * x[1]:.1f}")
    print(f"    distance to constrained NBS (scaled) = "
          f"{np.linalg.norm((x - x_c) / SCALE):.3f}")
    print(f"    G: {Gs[0]:.2f} -> {Gs[-1]:.4f}  (anchor-free, no x* used)")


if __name__ == "__main__":
    X_REF = e1_balance_point()
    e2_escalating_friction()
    e3_kappa_sweep(bal=X_REF)
    e4_monotonicity(ref=X_REF)
    e5_binding_budget()
