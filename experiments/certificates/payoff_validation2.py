"""
Round-2 validation: separating the two guarantees.

Insight from round 1: at the bargaining solution the two agents' individual
gradients are NONZERO and opposite (each still wants to push price its way),
while their SUM vanishes. So two distinct scalars are needed:

  Phi(x) = || grad Uhat_B(x) + grad Uhat_S(x) ||_M      "force imbalance"
      -> zero exactly at the balance point (= Nash bargaining solution, E1)
      -> anchor-free convergence certificate  (does it reach the deal?)

  G_kappa(x) = sum_i [ rho ||grad Uhat_i(x)||_M - kappa ]_+   "residual
      private incentive net of friction"
      -> zero on the frictional NE set
      -> termination certificate  (does it stop, and when?)

Experiments
  E6  Phi as Lyapunov function along the concession dynamics (decrease, ->0).
  E7  Termination threshold kappa* = rho * max_i ||grad Uhat_i(NBS)||_M, and
      the fixed-kappa phase transition (cycle vs stop).
  E8  T_max trade-off: guaranteed termination vs efficiency/fairness loss.
  E9  Stability radius: largest ball around NBS on which the game is monotone.
  E10 Binding budget: constrained NBS vs where the dynamics settle; Phi/G.
"""

import numpy as np
from scipy.optimize import minimize

from payoff_model import (U_B, U_S, W, P_accept, grad_Uhat, norm_M,
                          nbs_closed_form, nbs_numeric, SCALE)
from payoff_dynamics import (BOUNDS, X0, concession_field, clip_to_box,
                             step_agent)

rng = np.random.default_rng(5)
X_NBS, W_NBS = nbs_closed_form()


def Phi(x):
    return norm_M(concession_field(x))


def grad_norms(x):
    return (norm_M(grad_Uhat(x, "buyer")), norm_M(grad_Uhat(x, "seller")))


# --------------------------------- E6 ---------------------------------------
# NOTE: E6 and E7 are SUPERSEDED by payoff_validation3.py (E11, E12).
# E6 used a step decay that stopped before Phi converged; E7 evaluated the
# termination threshold only at the bargaining solution, so every sampled
# kappa exceeded the threshold at the far START and nothing moved.
# Do not quote E6/E7 output. Retained for provenance only.

def e6_phi_lyapunov(rho0=0.6, T=400, decay=0.995):
    """Diminishing step size (standard for gradient-type dynamics)."""
    x = X0.copy()
    Phis, dists = [Phi(x)], [np.linalg.norm((x - X_NBS) / SCALE)]
    for k in range(T):
        rho = rho0 * (decay ** k)
        role = "buyer" if k % 2 == 0 else "seller"
        x, _ = step_agent(x, role, rho, 0.0)
        if k % 2 == 1:
            Phis.append(Phi(x))
            dists.append(np.linalg.norm((x - X_NBS) / SCALE))
    Phis, dists = np.array(Phis), np.array(dists)
    print("E6  Phi as anchor-free convergence certificate "
          "(diminishing step, no friction):")
    print(f"    Phi: {Phis[0]:.3f} -> {Phis[-1]:.5f}; "
          f"decreasing on {np.mean(np.diff(Phis) <= 1e-9):.0%} of round-pairs")
    print(f"    ||x - NBS||_scaled: {dists[0]:.3f} -> {dists[-1]:.5f}")
    print(f"    settled p={x[0]:.3f} q={x[1]:.2f} d={x[2]:.2f} | "
          f"U_B={U_B(x):.2f} U_S={U_S(x):.2f} W={W(x):.2f} "
          f"(W_max={W_NBS:.2f})")
    # correlation: is Phi a valid surrogate for distance-to-equilibrium?
    print(f"    corr(Phi, ||x-NBS||) = {np.corrcoef(Phis, dists)[0, 1]:.4f}")
    return Phis, dists


# --------------------------------- E7 ---------------------------------------

def e7_threshold(rho=0.5):
    gb, gs = grad_norms(X_NBS)
    kstar = rho * max(gb, gs)
    print(f"\nE7  Termination threshold at the bargaining solution:")
    print(f"    ||grad Uhat_B||={gb:.2f}, ||grad Uhat_S||={gs:.2f}  ->  "
          f"kappa* = rho*max = {kstar:.2f}")
    print(f"    {'kappa':>8}{'stopped?':>10}{'stop k':>8}"
          f"{'||x-NBS||_s':>13}{'W':>9}")
    for kappa in [0.5 * kstar, 0.9 * kstar, 1.0 * kstar, 1.2 * kstar,
                  2.0 * kstar, 4.0 * kstar]:
        x = X0.copy()
        stop_k = None
        for k in range(600):
            role = "buyer" if k % 2 == 0 else "seller"
            xn, moved_i = step_agent(x, role, rho, kappa)
            other = "seller" if role == "buyer" else "buyer"
            _, moved_j = step_agent(x, other, rho, kappa)
            if not moved_i and not moved_j:
                stop_k = k
                break
            x = xn
        print(f"    {kappa:>8.2f}{str(stop_k is not None):>10}"
              f"{str(stop_k):>8}"
              f"{np.linalg.norm((x - X_NBS) / SCALE):>13.3f}{W(x):>9.2f}")


# --------------------------------- E8 ---------------------------------------

def e8_tmax_tradeoff(kappa0=2.0, rho=0.5):
    print(f"\nE8  T_max trade-off (escalating friction "
          f"kappa_k = kappa_0/(1-k/T_max)):")
    print(f"    {'T_max':>7}{'stop k':>8}{'||x-NBS||_s':>13}{'W':>9}"
          f"{'W loss %':>10}{'|U_B-U_S|':>11}")
    for T_max in [10, 20, 40, 80, 160, 320]:
        x = X0.copy()
        stop_k = None
        for k in range(2 * T_max):
            frac = min(k / T_max, 0.999)
            kappa = kappa0 / (1.0 - frac)
            role = "buyer" if k % 2 == 0 else "seller"
            xn, mi = step_agent(x, role, rho, kappa)
            other = "seller" if role == "buyer" else "buyer"
            _, mj = step_agent(x, other, rho, kappa)
            if not mi and not mj:
                stop_k = k
                break
            x = xn
        loss = 100 * (W_NBS - W(x)) / W_NBS
        print(f"    {T_max:>7}{str(stop_k):>8}"
              f"{np.linalg.norm((x - X_NBS) / SCALE):>13.3f}"
              f"{W(x):>9.2f}{loss:>10.2f}{abs(U_B(x) - U_S(x)):>11.2f}")


# --------------------------------- E9 ---------------------------------------

def e9_stability_radius(h=1e-4, n_per_r=150):
    print("\nE9  Stability (monotonicity) radius around the bargaining "
          "solution:")

    def lmax_at(x):
        J = np.zeros((3, 3))
        for i in range(3):
            e = np.zeros(3)
            e[i] = h * SCALE[i]
            J[:, i] = (concession_field(x + e) - concession_field(x - e)) \
                / (2 * e[i])
        D = np.diag(SCALE)
        S = 0.5 * (J + J.T)
        return float(np.max(np.linalg.eigvalsh(D @ S @ D)))

    print(f"    lambda_max(sym J) at NBS = {lmax_at(X_NBS):+.4f}")
    print(f"    {'radius r':>10}{'frac monotone':>15}{'worst lambda':>14}")
    for r in [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]:
        ok, worst = 0, -np.inf
        for _ in range(n_per_r):
            v = rng.normal(size=3)
            v = v / np.linalg.norm(v) * r * rng.uniform(0, 1) ** (1 / 3)
            x = clip_to_box(X_NBS + v * SCALE)
            lm = lmax_at(x)
            worst = max(worst, lm)
            ok += (lm <= 1e-8)
        print(f"    {r:>10.2f}{ok / n_per_r:>15.1%}{worst:>+14.4f}")


# -------------------------------- E10 ---------------------------------------

def e10_binding_budget(Bmax=800.0, rho0=0.6, T=400, decay=0.995):
    cons = ({"type": "ineq", "fun": lambda x: Bmax - x[0] * x[1]},)
    x_c = nbs_numeric(BOUNDS, extra_cons=cons)
    print(f"\nE10 Binding budget B={Bmax} (unconstrained NBS spend = "
          f"{X_NBS[0] * X_NBS[1]:.0f}):")
    print(f"    constrained NBS: p={x_c[0]:.3f} q={x_c[1]:.2f} "
          f"d={x_c[2]:.2f} spend={x_c[0] * x_c[1]:.1f}")

    def project(x):
        x = clip_to_box(x)
        if x[0] * x[1] > Bmax:
            x[0] = Bmax / x[1]
        return x

    x = X0.copy()
    Phis = [Phi(x)]
    for k in range(T):
        rho = rho0 * (decay ** k)
        role = "buyer" if k % 2 == 0 else "seller"
        xn, _ = step_agent(x, role, rho, 0.0)
        x = project(xn)
        if k % 2 == 1:
            Phis.append(Phi(x))
    print(f"    dynamics settle: p={x[0]:.3f} q={x[1]:.2f} d={x[2]:.2f} "
          f"spend={x[0] * x[1]:.1f}")
    print(f"    ||x - constrained NBS||_scaled = "
          f"{np.linalg.norm((x - x_c) / SCALE):.4f}   "
          f"(vs to unconstrained NBS: "
          f"{np.linalg.norm((x - X_NBS) / SCALE):.4f})")
    print(f"    Phi: {Phis[0]:.3f} -> {Phis[-1]:.4f}  "
          f"[unconstrained Phi is NOT the right certificate when a "
          f"constraint binds - see note]")


if __name__ == "__main__":
    e6_phi_lyapunov()
    e7_threshold()
    e8_tmax_tradeoff()
    e9_stability_radius()
    e10_binding_budget()
