"""Render the theory-chapter figures.

    python figures/render_theory.py

Slots are specified in ``thesis_writing/chapters/03-theory.md:101-111``.

Two departures from those specs, both deliberate:

* **Slot 1 (Phi and G on one trajectory) is not rendered.** See the module note
  in ``main`` — the two available tunings do not produce the trajectory the spec
  describes, and inventing one that does is the failure mode of SCIENCE.md §11
  bug 6.
* **Slot 4 draws the corrected finding, not the specified one.** The spec asks
  for "the conservatism premium in term space"; that prediction is marked
  corrected in ``docs/notes/2026-08-07-gamma-independence.md:46-53``.

These figures are proved or simulated on gradient-ascent proxies, never
demonstrated live. Their captions must carry that tag (FIGURES.md §6).
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

import science_data as S
from thesis_style import (
    ACCENT,
    FULL,
    GREY,
    GREY_DARK,
    GREY_LIGHT,
    INK,
    finish,
    panel,
    save,
    use_thesis_style,
)
import matplotlib.pyplot as plt

CERT_DIR = Path(__file__).resolve().parent.parent / "experiments" / "certificates"
sys.path.insert(0, str(CERT_DIR))


# --- T2 ----------------------------------------------------------------------
def fig_friction_window():
    """Proposition 2: no constant friction both starts and stops the process."""
    import payoff_validation3 as V3
    from payoff_dynamics import X0

    rho = 0.5
    x0 = np.asarray(X0, dtype=float)
    nbs = np.asarray(V3.X_NBS, dtype=float)

    # kappa* evaluated along the straight path from the opening to the deal
    # point. A parameterised path rather than a tuned trajectory, so the curve
    # shows the state dependence itself and not an artefact of a step schedule.
    t = np.linspace(0.0, 1.0, 240)
    kstar = np.array([V3.kappa_star(x0 + s * (nbs - x0), rho)[0] for s in t])

    k_start, k_deal = kstar[0], kstar[-1]

    fig, ax = plt.subplots(figsize=(FULL * 0.68, 3.2))

    ax.axhspan(0, k_start, color=ACCENT, alpha=0.13, zorder=0)
    ax.axhspan(k_deal, k_deal * 1.35, color=ACCENT, alpha=0.13, zorder=0)
    ax.axhspan(k_start, k_deal, color=GREY_LIGHT, alpha=0.55, zorder=0)

    ax.plot(t, kstar, color=INK, lw=1.6, zorder=3, label=r"$\kappa^\star(x)$")
    ax.plot([0, 1], [k_start, k_deal], "o", color=INK, ms=5, zorder=4)

    ax.axhline(k_start, color=GREY_DARK, lw=0.8, ls="--", zorder=2)
    ax.axhline(k_deal, color=GREY_DARK, lw=0.8, ls="--", zorder=2)

    # The band labels carry the two threshold values, so no separate callout
    # annotations are needed (FIGURES.md §3 — can it be removed?).
    ax.text(0.5, k_start / 2,
            f"constant $\\kappa$ below $\\kappa^\\star(x_0) = {k_start:.2f}$\nnever stops",
            fontsize=8, color=ACCENT, va="center", ha="center")
    ax.text(0.5, (k_deal + k_deal * 1.35) / 2,
            f"constant $\\kappa$ above "
            f"$\\kappa^\\star(x^\\star_{{\\mathrm{{NBS}}}}) = {k_deal:.2f}$ never starts",
            fontsize=8, color=ACCENT, va="center", ha="center")
    ax.text(0.14, (k_start + k_deal) / 2 + 4, "the window",
            fontsize=8, color=GREY_DARK, va="center", ha="center")

    ax.set_xlim(0, 1)
    ax.set_ylim(0, k_deal * 1.35)
    ax.set_xticks([0, 0.5, 1.0])
    ax.set_xticklabels(["$x_0$\n(opening)", "", "$x^\\star_{\\mathrm{NBS}}$\n(deal)"])
    finish(ax, xlabel="position along the improving path",
           ylabel="required friction $\\kappa^\\star$")
    return save(fig, "fig_friction_window")


# --- T3 ----------------------------------------------------------------------
def fig_anchorfree_certificate():
    """The anchored certificate plateaus; the anchor-free one goes to zero.

    Ports the chart already produced by ``experiments/certificates/
    farstart_experiment.py:98-119`` onto the house style. The original wrote a
    PNG and used a bright three-hue palette; both are corrected here.
    """
    from farstart_experiment import estimate_gne_far, run_series

    g1, g2 = estimate_gne_far()
    s = run_series(noisy=False, g1=g1, g2=g2)
    k = np.arange(len(s["V_naive"])) * 2

    fig, ax = plt.subplots(figsize=(FULL * 0.72, 3.2))

    floor = 1e-6
    # Labels are kept short so the legend fits the empty band without covering
    # the curves; what each anchor means belongs in the caption (FIGURES.md §3).
    ax.semilogy(k, np.maximum(s["V_naive"], floor), "-o", color=ACCENT,
                ms=3, lw=1.3, markevery=3,
                label=r"$V$, anchored at unconstrained $x^\star$")
    ax.semilogy(k, np.maximum(s["V_gne"], floor), "--s", color=GREY_DARK,
                ms=3, lw=1.3, markevery=3,
                label=r"$V$, anchored at estimated GNE")
    ax.semilogy(k, np.maximum(s["G_netgain"], floor), "-^", color=INK,
                ms=3, lw=1.5, markevery=3,
                label=r"$G$, anchor-free")

    plateau = float(s["V_naive"][-1])
    ax.annotate("plateaus at its own\nsquared anchor error",
                xy=(k[-1] * 0.82, plateau), xytext=(k[-1] * 0.30, plateau * 26),
                fontsize=8, color=ACCENT,
                arrowprops=dict(arrowstyle="->", color=ACCENT, lw=0.8))

    ax.grid(True, which="both", alpha=0.3)
    finish(ax, xlabel="round-pair $k$", ylabel="certificate value", grid_axis=None)
    # The band under the plateau and right of the decay is empty; short labels
    # keep the legend inside it. Opaque ground as insurance if the decay shifts.
    ax.legend(loc="center right", fontsize=8, frameon=True, framealpha=0.92,
              facecolor="white", edgecolor="none", borderpad=0.4)
    return save(fig, "fig_anchorfree_certificate")


# --- T4 ----------------------------------------------------------------------
def fig_gamma_independence():
    """The boundary layer predicted in simulation does not appear live."""
    g = S.GAMMA["gamma"]
    x = np.arange(len(g))
    fig, axes = panel(1, 2, height=2.9, width=FULL, labels=False)

    # (a) margin inside C(theta): predicted to fall with gamma, measured flat.
    ax = axes[0]
    pred = S.GAMMA["predicted_margin_endpoints"]
    ax.plot([0, 2], [pred[0.2], pred[0.7]], ls="--", color=GREY,
            marker="o", ms=4, lw=1.2, label="predicted in simulation")
    ax.plot(x, S.GAMMA["margin"], ls="-", color=INK, marker="s", ms=4.5, lw=1.6,
            label="measured live")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v}" for v in g])
    ax.set_ylim(-0.45, 3.7)
    ax.axhline(0, color=GREY_DARK, lw=0.7, zorder=1)
    ax.annotate("0.000 at every $\\gamma$:\nno boundary layer",
                xy=(1.5, 0.0), xytext=(0.75, 1.5), fontsize=8, color=INK,
                arrowprops=dict(arrowstyle="->", color=INK, lw=0.8))
    ax.legend(loc="upper right", fontsize=8)
    finish(ax, xlabel="$\\gamma$", ylabel="margin inside $C(\\theta)$")
    ax.set_title("(a) the conservatism premium", loc="left", fontsize=9,
                 color=INK, pad=6)

    # (b) safety holds regardless. Every breach count is zero, so a zero-height
    # red bar would draw nothing while its legend entry implied otherwise. The
    # bars are the governed rounds; the zero is stated instead of drawn.
    ax = axes[1]
    ax.bar(x, S.GAMMA["governed"], width=0.6, color=GREY_LIGHT,
           edgecolor=INK, linewidth=0.6)
    for i, n in enumerate(S.GAMMA["governed"]):
        ax.text(i, n + 1.2, f"0/{n}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(x)
    ax.set_xticklabels([f"{v}" for v in g])
    ax.set_ylim(0, 50)
    total = sum(S.GAMMA["governed"])
    ax.text(-0.45, 46.5,
            f"0 breaching rounds at every $\\gamma$   (0/{total} in total)",
            fontsize=8, color=INK, va="center")
    finish(ax, xlabel="$\\gamma$", ylabel="governed rounds")
    ax.set_title("(b) safety", loc="left", fontsize=9, color=INK, pad=6)

    return save(fig, "fig_gamma_independence")


def main():
    use_thesis_style()
    for fn in (fig_friction_window, fig_anchorfree_certificate, fig_gamma_independence):
        out = fn()
        print(f"wrote {out.name}")

    print(
        "\nNOT RENDERED — 03-theory.md slot 1 (Phi falling to zero while G_kappa\n"
        "stays positive until friction bites). The frictionless diminishing-step\n"
        "run drives Phi down but computes no G; the escalating-friction run\n"
        "computes G but stalls it to zero at round-pair 19 with Phi still at\n"
        "~30.85, which is the opposite of the specified shape. Producing the\n"
        "specified figure needs a tuning that reaches the deal with friction\n"
        "active; picking one to make the curve look right is SCIENCE.md §11\n"
        "bug 6. Raise with the supervisor before drawing it."
    )


if __name__ == "__main__":
    main()
