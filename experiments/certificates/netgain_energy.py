"""
Net-gain energy validation (Zusai, arXiv:1805.04898 adapted to bilateral
negotiation).

Idea: cost-benefit rationalizable agents move IFF their net gain is positive,
so the move the dynamics still choose to make is the *revealed* remaining
gain. We define the energy as the squared deterministic displacement the
(filtered) concession dynamics would produce from the current state over one
buyer+seller round-pair, summed over pairs:

    G(x) = sum_pairs || x''_pair - x_pair ||^2

with x'' obtained by a two-round deterministic lookahead THROUGH the joint
DCBF filter (capacity included). Because the filter is inside the lookahead,
G = 0 exactly at the *constrained* equilibrium (the GNE) — no anchor needed.

Head-to-head on identical noisy trajectories (binding capacity Q=140):
  V_naive : ||x - x*_unconstrained||^2 summed   (known to FAIL)
  V_gne   : ||x - x*_GNE||^2 summed, GNE estimated empirically (cheating fix)
  G       : revealed net-gain energy, anchor-free (the candidate)
"""

import numpy as np

from dcbf_negotiation import Contract
from lyapunov_layer import (nash_point, V, proposal, joint_dcbf_filter,
                            contraction_rate)

rng = np.random.default_rng(11)

X1_0 = np.array([9.0, 65.0, 30.0])
X2_0 = np.array([8.5, 70.0, 25.0])


# --------------------- deterministic lookahead energy -----------------------

def roundpair_lookahead(xs, contracts, capacity, first_role="buyer"):
    """Apply one deterministic buyer round + seller round through the joint
    filter. Returns the new states."""
    xs = [x.copy() for x in xs]
    order = [first_role, "seller" if first_role == "buyer" else "buyer"]
    for role in order:
        ups = [proposal(x, role, noisy=False) for x in xs]
        us, _, _ = joint_dcbf_filter(xs, ups, contracts,
                                     shared_capacity=capacity)
        xs = [x + u for x, u in zip(xs, us)]
    return xs


def G_netgain(xs, contracts, capacity, first_role="buyer"):
    """Revealed net-gain energy: squared deterministic round-pair
    displacement, summed over pairs."""
    xs2 = roundpair_lookahead(xs, contracts, capacity, first_role)
    return float(sum(np.sum((b - a) ** 2) for a, b in zip(xs, xs2)))


# ----------------------------- GNE estimation -------------------------------

def estimate_gne(capacity, T=300):
    c1, c2 = Contract(), Contract()
    xs = [X1_0.copy(), X2_0.copy()]
    for k in range(T):
        role = "buyer" if k % 2 == 0 else "seller"
        ups = [proposal(x, role, noisy=False) for x in xs]
        us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2],
                                     shared_capacity=capacity)
        xs = [x + u for x, u in zip(xs, us)]
    return xs


# ------------------------------- experiment ---------------------------------

def run_tracking(capacity, episodes=20, T=40):
    """Noisy coupled trajectories; track V_naive, V_gne, G on the SAME data."""
    x_unc = nash_point()
    g1, g2 = estimate_gne(capacity) if capacity is not None else (x_unc, x_unc)
    stats = {name: {"rates": [], "dec": []} for name in
             ["V_naive", "V_gne", "G_netgain"]}
    for _ in range(episodes):
        c1, c2 = Contract(), Contract()
        xs = [X1_0.copy(), X2_0.copy()]
        series = {"V_naive": [], "V_gne": [], "G_netgain": []}
        for k in range(T):
            if k % 2 == 0:                     # round-pair boundary
                series["V_naive"].append(V(xs[0], x_unc) + V(xs[1], x_unc))
                series["V_gne"].append(V(xs[0], g1) + V(xs[1], g2))
                series["G_netgain"].append(
                    G_netgain(xs, [c1, c2], capacity, first_role="buyer"))
            role = "buyer" if k % 2 == 0 else "seller"
            ups = [proposal(x, role) for x in xs]        # noisy
            us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2],
                                         shared_capacity=capacity)
            xs = [x + u for x, u in zip(xs, us)]
        for name, vals in series.items():
            vals = np.array(vals)
            stats[name]["rates"].append(contraction_rate(vals))
            stats[name]["dec"].append(np.mean(np.diff(vals) <= 1e-9))
    return {name: {"contraction": float(np.mean(s["rates"])),
                   "frac_steps_decreasing": float(np.mean(s["dec"]))}
            for name, s in stats.items()}


def main():
    x_unc = nash_point()
    for label, cap in [("single-regime: slack capacity Q=170", 170.0),
                       ("BINDING capacity Q=140", 140.0)]:
        print(f"=== {label} ===")
        res = run_tracking(cap)
        print(f"{'energy':<14}{'contraction':>14}{'frac decreasing':>18}")
        print("-" * 46)
        for name in ["V_naive", "V_gne", "G_netgain"]:
            r = res[name]
            print(f"{name:<14}{r['contraction']:>14.4f}"
                  f"{r['frac_steps_decreasing']:>18.4f}")
        print()
    # sanity: noise-free G decay on the binding case
    c1, c2 = Contract(), Contract()
    xs = [X1_0.copy(), X2_0.copy()]
    Gs = []
    for k in range(60):
        if k % 2 == 0:
            Gs.append(G_netgain(xs, [c1, c2], 140.0))
        role = "buyer" if k % 2 == 0 else "seller"
        ups = [proposal(x, role, noisy=False) for x in xs]
        us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2], shared_capacity=140.0)
        xs = [x + u for x, u in zip(xs, us)]
    Gs = np.array(Gs)
    dec = np.mean(np.diff(Gs) <= 1e-9)
    print(f"[noise-free sanity, Q=140] G monotone-decreasing on "
          f"{dec:.0%} of steps; G_0={Gs[0]:.2f} -> G_end={Gs[-1]:.4f}")


if __name__ == "__main__":
    main()
