"""
Far-start binding-capacity experiment — repairs the F5/G comparison.

Audit finding: the original binding-case starts sat ~4 q-units from the GNE,
leaving no transient to fit; contraction estimates were noise-ball artefacts.
Fix: start FAR from the constrained equilibrium (but feasible, so no recovery
transient pollutes the data), giving a long measurable transient.

Setup: Q=140 (binding: unconstrained q1*+q2* = 162.9, GNE q-sum ~131).
Far feasible start: q-sum 95, prices/deadlines also far from equilibrium.

Outputs:
  (1) noisy head-to-head with TRANSIENT-ONLY fits: V_naive / V_gne / G
  (2) noise-free three-curve figure (log scale): the dissertation figure —
      naive anchor plateaus at a positive offset (measuring the wrong point),
      GNE anchor decays to zero (but needed x* estimated), G decays to zero
      with no anchor at all.
"""

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from dcbf_negotiation import Contract
from lyapunov_layer import nash_point, V, proposal, joint_dcbf_filter
from netgain_energy import G_netgain
from audit import contraction_transient

rng = np.random.default_rng(23)

Q = 140.0
XF1 = np.array([11.0, 45.0, 40.0])     # far feasible start, pair 1
XF2 = np.array([10.5, 50.0, 38.0])     # far feasible start, pair 2 (sum q=95)


def estimate_gne_far(T=300):
    c1, c2 = Contract(), Contract()
    xs = [XF1.copy(), XF2.copy()]
    for k in range(T):
        role = "buyer" if k % 2 == 0 else "seller"
        ups = [proposal(x, role, noisy=False) for x in xs]
        us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2], shared_capacity=Q)
        xs = [x + u for x, u in zip(xs, us)]
    return xs


def run_series(noisy, g1, g2, T=60):
    x_unc = nash_point()
    c1, c2 = Contract(), Contract()
    xs = [XF1.copy(), XF2.copy()]
    series = {"V_naive": [], "V_gne": [], "G_netgain": []}
    for k in range(T):
        if k % 2 == 0:
            series["V_naive"].append(V(xs[0], x_unc) + V(xs[1], x_unc))
            series["V_gne"].append(V(xs[0], g1) + V(xs[1], g2))
            series["G_netgain"].append(
                G_netgain(xs, [c1, c2], Q, first_role="buyer"))
        role = "buyer" if k % 2 == 0 else "seller"
        ups = [proposal(x, role, noisy=noisy) for x in xs]
        us, _, _ = joint_dcbf_filter(xs, ups, [c1, c2], shared_capacity=Q)
        xs = [x + u for x, u in zip(xs, us)]
    return {k: np.array(v) for k, v in series.items()}


def main():
    g1, g2 = estimate_gne_far()
    x_unc = nash_point()
    print(f"GNE (far start): q1+q2 = {g1[1] + g2[1]:.1f} "
          f"(unconstrained {2 * x_unc[1]:.1f}); "
          f"offset ||GNE - x*_unc|| per pair: "
          f"{np.linalg.norm(g1 - x_unc):.2f}, {np.linalg.norm(g2 - x_unc):.2f}\n")

    # (1) noisy head-to-head, transient-only fits
    stats = {n: {"c": [], "d": []} for n in ["V_naive", "V_gne", "G_netgain"]}
    for _ in range(15):
        s = run_series(noisy=True, g1=g1, g2=g2)
        for n, vals in s.items():
            stats[n]["c"].append(contraction_transient(vals))
            stats[n]["d"].append(np.mean(np.diff(vals) <= 1e-9))
    print("Noisy far-start head-to-head (15 episodes, transient-only fit):")
    print(f"{'energy':<12}{'contraction':>13}{'frac decreasing':>17}")
    print("-" * 42)
    for n in stats:
        print(f"{n:<12}{np.mean(stats[n]['c']):>13.4f}"
              f"{np.mean(stats[n]['d']):>17.4f}")

    # (2) noise-free figure
    s = run_series(noisy=False, g1=g1, g2=g2)
    print("\nNoise-free endpoints: "
          f"V_naive {s['V_naive'][0]:.1f} -> {s['V_naive'][-1]:.2f} | "
          f"V_gne {s['V_gne'][0]:.1f} -> {s['V_gne'][-1]:.4f} | "
          f"G {s['G_netgain'][0]:.1f} -> {s['G_netgain'][-1]:.4f}")
    dec = {n: np.mean(np.diff(v) <= 1e-9) for n, v in s.items()}
    print("Noise-free monotone-decrease fractions: "
          + ", ".join(f"{n}={d:.0%}" for n, d in dec.items()))

    fig, ax = plt.subplots(figsize=(7, 4.4))
    k = np.arange(len(s["V_naive"]))
    ax.semilogy(k, np.maximum(s["V_naive"], 1e-6), "o-",
                label=r"$V$ anchored at unconstrained $x^*$ (wrong point)",
                color="#c0392b")
    ax.semilogy(k, np.maximum(s["V_gne"], 1e-6), "s-",
                label=r"$V$ anchored at estimated GNE (needs $x^*$)",
                color="#e67e22")
    ax.semilogy(k, np.maximum(s["G_netgain"], 1e-6), "^-",
                label=r"$G$: net-gain energy (anchor-free)",
                color="#1a7a4a")
    ax.set_xlabel("negotiation round-pair $k$")
    ax.set_ylabel("energy (log scale)")
    ax.set_title("Binding shared capacity ($Q=140$): only the anchor-free "
                 "net-gain energy\ncertifies convergence without knowing "
                 "the equilibrium")
    ax.legend(fontsize=8.5, loc="center right")
    ax.grid(alpha=0.3, which="both")
    fig.tight_layout()
    fig.savefig("../figures/figure_anchorfree_energy.png",
                dpi=200)
    print("\nFigure saved: figure_anchorfree_energy.png")


if __name__ == "__main__":
    main()
