"""Render the results-chapter figures. Reads only SCIENCE.md-traced constants.

    python figures/render_results.py

Figure slots are specified in ``thesis_writing/chapters/05-results.md``. Slot 3
(per-pair closure across arms) is deliberately absent: a 9-pair x 5-arm count of
closures is tabular data and is kept as a ``table`` float, per FIGURES.md §3.
"""

from __future__ import annotations

import numpy as np

import science_data as S
from thesis_style import (
    ACCENT,
    ARM_STYLE,
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


def _arm_colors(arms):
    return [ARM_STYLE[a]["color"] for a in arms]


def _arm_hatches(arms):
    return [ARM_STYLE[a]["hatch"] for a in arms]


def _bars(ax, arms, values, ylabel, ylim=None, short=False):
    """A bar per arm, coloured by the semantic arm palette, hatched for print."""
    x = np.arange(len(arms))
    bars = ax.bar(
        x,
        values,
        width=0.62,
        color=_arm_colors(arms),
        edgecolor=INK,
        linewidth=0.6,
    )
    for bar, hatch in zip(bars, _arm_hatches(arms)):
        if hatch:
            bar.set_hatch(hatch)
    labels = S.ARM_SHORT if short else S.ARM_LABELS
    ax.set_xticks(x)
    ax.set_xticklabels([labels[a] for a in arms])
    if ylim:
        ax.set_ylim(*ylim)
    finish(ax, ylabel=ylabel)
    return bars


# --- R1 ----------------------------------------------------------------------
def fig_exposure_by_arm():
    """Offered / settled / per-round exposure across the five arms."""
    arms = S.HEADLINE["arms"]
    fig, axes = panel(1, 3, height=2.9, width=FULL, labels=False)

    # (a) offered breach, with seed SDs and the A-D noise floor shaded.
    ax = axes[0]
    _bars(ax, arms, S.HEADLINE["offered_breach"], "share of proposals", (0, 1.18), short=True)
    ax.errorbar(
        np.arange(len(arms)),
        S.HEADLINE["offered_breach"],
        yerr=S.HEADLINE["offered_breach_sd"],
        fmt="none",
        ecolor=INK,
        elinewidth=0.9,
        capsize=2.5,
    )
    lo, hi = sorted([S.HEADLINE["offered_breach"][0], S.HEADLINE["offered_breach"][1]])
    ax.axhspan(lo, hi, color=GREY_LIGHT, alpha=0.7, zorder=0)
    ax.annotate(
        "A–D noise floor",
        xy=(3.55, (lo + hi) / 2), xytext=(1.15, 1.10),
        fontsize=8, color=GREY_DARK, ha="left", va="top",
        arrowprops=dict(arrowstyle="->", color=GREY_DARK, lw=0.8),
    )
    ax.set_title("(a) offered", loc="left", fontsize=9, color=INK, pad=6)

    # (b) settled breach. Values are labelled alternately high/low so the two
    # identical A and D bars do not overprint each other.
    ax = axes[1]
    _bars(ax, arms, S.HEADLINE["settled_breach"], "share of deals", (0, 0.23), short=True)
    for i, v in enumerate(S.HEADLINE["settled_breach"]):
        offset = 0.020 if i % 2 else 0.008
        ax.text(i, v + offset, f"{v:.3f}", ha="center", fontsize=8, color=INK)
    ax.set_title("(b) settled", loc="left", fontsize=9, color=INK, pad=6)

    # (c) per-round exposure on governed rounds.
    ax = axes[2]
    rates = [b / n for b, n in S.HEADLINE["governed"]]
    _bars(ax, arms, rates, "share of governed rounds", (0, 1.18), short=True)
    for i, (b, n) in enumerate(S.HEADLINE["governed"]):
        ax.text(i, rates[i] + 0.03, f"{b}/{n}", ha="center", fontsize=8, color=INK)
    ax.set_title("(c) per governed round", loc="left", fontsize=9, color=INK, pad=6)

    return save(fig, "fig_exposure_by_arm")


# --- R2 ----------------------------------------------------------------------
def fig_flagged_vs_corrected():
    """What detection sees against what enforcement corrects."""
    arms = S.MONITORING["arms"]
    fig, axes = panel(1, 2, height=3.0, width=FULL)

    ax = axes[0]
    x = np.arange(len(arms))
    w = 0.36
    flagged = ax.bar(
        x - w / 2,
        S.MONITORING["flag_rate"],
        width=w,
        color=[ARM_STYLE[a]["color"] for a in arms],
        edgecolor=INK,
        linewidth=0.6,
        label="flagged",
    )
    # Arms must look identical across panels, so carry the hatch here too.
    for bar, hatch in zip(flagged, _arm_hatches(arms)):
        if hatch:
            bar.set_hatch(hatch)
    corrected = [c if c is not None else 0.0 for c in S.MONITORING["correction_rate"]]
    ax.bar(
        x + w / 2,
        corrected,
        width=w,
        color="none",
        edgecolor=INK,
        linewidth=0.9,
        hatch="///",
        label="corrected",
    )
    for i, c in enumerate(S.MONITORING["correction_rate"]):
        if c is None:
            ax.text(i + w / 2, 0.03, "n/a", ha="center", fontsize=8, color=GREY_DARK, rotation=90)
    ax.set_xticks(x)
    ax.set_xticklabels([S.ARM_LABELS[a] for a in arms])
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", fontsize=8)
    finish(ax, ylabel="share of governed rounds")
    ax.set_title("(a) flagged and corrected", loc="left", fontsize=9, color=INK, pad=6)

    ax = axes[1]
    vals = S.MONITORING["continuation_breach"]
    _bars(ax, arms, vals, "breach rate, continuations only", (0, 1.0))
    for i, (v, n) in enumerate(zip(vals, S.MONITORING["continuation_n"])):
        ax.text(i, v + 0.03, f"n={n}", ha="center", fontsize=8, color=INK)
    ax.set_title("(b) continuation rounds", loc="left", fontsize=9, color=INK, pad=6)

    return save(fig, "fig_flagged_vs_corrected")


# --- R4 ----------------------------------------------------------------------
def fig_scenario_inversion():
    """The scenario edit raised offered breach and lowered settled breach."""
    fig, axes = panel(1, 2, height=2.9, width=FULL, labels=False)
    labels = ["mexican_3_9\n(stock)", "bargain_3_9\n(budget binds)"]
    x = np.arange(2)
    # No red here. Neither scenario is the ungoverned arm, and FIGURES.md §4
    # reserves ACCENT for "unsafe" — using it to mark "the taller bar" would
    # make red mean two different things in one figure. Greys, split by hatch.
    colors = [GREY, GREY_DARK]
    hatches = ["..", "//"]

    def scenario_bars(ax, values, ylabel, ylim, yerr=None):
        bars = ax.bar(x, values, width=0.55, color=colors,
                      edgecolor=INK, linewidth=0.6)
        for bar, h in zip(bars, hatches):
            bar.set_hatch(h)
        if yerr is not None:
            ax.errorbar(x, values, yerr=yerr, fmt="none", ecolor=INK,
                        elinewidth=0.9, capsize=2.5)
        ax.set_xticks(x)
        ax.set_xticklabels(labels)
        ax.set_ylim(*ylim)
        finish(ax, ylabel=ylabel)
        return bars

    ax = axes[0]
    scenario_bars(ax, S.INVERSION["offered_breach"], "proposals breaching $\\theta$",
                  (0, 1.22), yerr=S.INVERSION["offered_breach_sd"])
    ax.annotate("", xy=(0.96, 0.98), xytext=(0.04, 0.70),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.text(0.5, 1.13, "as designed", ha="center", fontsize=8, color=INK)
    ax.set_title("(a) offered", loc="left", fontsize=9, color=INK, pad=6)

    ax = axes[1]
    scenario_bars(ax, S.INVERSION["settled_breach"], "deals breaching $\\theta$", (0, 0.61))
    for i, (b, n) in enumerate(S.INVERSION["settled_counts"]):
        ax.text(i, S.INVERSION["settled_breach"][i] + 0.018, f"{b}/{n}",
                ha="center", fontsize=8, color=INK)
    ax.annotate("", xy=(0.96, 0.13), xytext=(0.04, 0.47),
                arrowprops=dict(arrowstyle="->", color=INK, lw=1.0))
    ax.text(0.5, 0.56, "the opposite", ha="center", fontsize=8, color=INK)
    ax.set_title("(b) settled", loc="left", fontsize=9, color=INK, pad=6)

    return save(fig, "fig_scenario_inversion")


# --- R5, the centrepiece -----------------------------------------------------
def fig_harm_averted():
    """Value transacted above the ceiling, per seed, arm A against arm B."""
    seeds = S.UNDISCLOSED["seeds"]
    a = S.UNDISCLOSED["a_over_gbp"]
    b = S.UNDISCLOSED["b_over_gbp"]
    x = np.arange(len(seeds))
    w = 0.36

    fig, ax = plt.subplots(figsize=(FULL, 3.1))

    ax.bar(x - w / 2, a, width=w, color=ACCENT, edgecolor=INK, linewidth=0.6,
           label="arm A — ungoverned")
    ax.bar(x + w / 2, b, width=w, color=GREY_LIGHT, edgecolor=INK, linewidth=0.6,
           label="arm B — enforced")
    # A zero-height bar draws nothing, which reads as missing data rather than
    # as zero. Mark each arm B position with an explicit flat cap on the axis.
    ax.hlines(y=np.zeros(len(x)), xmin=x, xmax=x + w,
              color=INK, linewidth=1.8, zorder=4)

    for i, v in enumerate(a):
        ax.text(i - w / 2, v + 0.12, f"£{v:.2f}", ha="center", fontsize=8, color=INK)
        ax.text(i - w / 2, v / 2, f"{S.UNDISCLOSED['a_breaching'][i]}/{S.UNDISCLOSED['a_deals'][i]}",
                ha="center", va="center", fontsize=8, color="white")
    for i in range(len(seeds)):
        ax.text(i + w / 2, 0.12, "£0.00", ha="center", fontsize=8, color=INK)
        ax.text(i + w / 2, 0.46, f"0/{S.UNDISCLOSED['b_deals'][i]}",
                ha="center", fontsize=8, color=GREY_DARK)

    ax.set_xticks(x)
    ax.set_xticklabels(seeds)
    ax.set_ylim(0, 6.6)
    ax.legend(loc="upper right", fontsize=8, ncol=2)
    finish(ax, xlabel="seed", ylabel="transacted above the ceiling (£)")

    # Z-order (FIGURES.md §5): the total lands top-left, where the eye enters.
    ax.text(
        -0.42, 5.55,
        f"£{S.UNDISCLOSED['total_over']['A']:.2f} total, "
        f"{S.UNDISCLOSED['total_share']['A']:.2%} of value transacted"
        f"     $\\longrightarrow$     £{S.UNDISCLOSED['total_over']['B']:.2f}",
        fontsize=8.5, color=INK, va="center",
    )
    return save(fig, "fig_harm_averted")


# --- R6 ----------------------------------------------------------------------
def fig_refinement_lattice():
    """Schematic: the negotiated envelope does not refine the mandate.

    Illustrative geometry, not measured values. The shape encodes SCIENCE.md §9:
    the negotiated budget row is *looser* than the mandate on every pair, while
    its cost floor binds, so neither set contains the other and only the meet
    lies inside both.
    """
    q = np.linspace(6.0, 19.0, 400)

    mandate = dict(B=100.0, c=6.0, q_min=8.0, q_max=16.0)
    negotiated = dict(B=130.0, c=7.0, q_min=8.0, q_max=16.0)
    meet = dict(B=100.0, c=7.0, q_min=8.0, q_max=16.0)

    fig, ax = plt.subplots(figsize=(FULL * 0.66, 3.3))

    def draw(theta, color, hatch, label, lw=1.2, ls="-", zorder=3):
        inside = (q >= theta["q_min"]) & (q <= theta["q_max"])
        upper = np.where(inside, theta["B"] / np.maximum(q, 1e-9), np.nan)
        lower = np.where(inside, theta["c"], np.nan)
        ax.fill_between(q, lower, upper, where=inside & (upper > lower),
                        facecolor=color, alpha=0.15, edgecolor=color,
                        hatch=hatch, linewidth=0.0, zorder=1)
        ax.plot(q, upper, color=color, lw=lw, ls=ls, zorder=zorder, label=label)
        ax.plot(q, lower, color=color, lw=lw, ls=ls, zorder=zorder)

    # The meet shares its budget boundary with the mandate (a min) and its cost
    # floor with the negotiated contract (a max), so those lines coincide
    # exactly. Draw the parents thick underneath and the meet thin and dashed on
    # top, so a shared boundary reads as two contracts agreeing rather than as a
    # missing line.
    draw(negotiated, ACCENT, "\\\\", r"$C(\theta_{\mathrm{neg}})$", lw=2.2, zorder=2)
    draw(mandate, GREY_DARK, "", r"$C(\theta_{\mathrm{man}})$", lw=2.2, zorder=2)
    draw(meet, INK, "xx", r"$C(\theta_{\mathrm{man}} \wedge \theta_{\mathrm{neg}})$",
         lw=1.0, ls=(0, (3, 2)), zorder=5)

    ax.annotate(
        "negotiated budget is looser:\nthis strip lies outside the\nmandate, so the envelope\ndoes not refine it",
        xy=(11.8, 10.3), xytext=(11.7, 16.4),
        fontsize=8, color=ACCENT, ha="left", va="top",
        arrowprops=dict(arrowstyle="->", color=ACCENT, lw=0.9),
    )
    ax.annotate(
        "meet floor = negotiated floor",
        xy=(15.4, 7.0), xytext=(11.9, 4.8),
        fontsize=8, color=INK,
        arrowprops=dict(arrowstyle="->", color=INK, lw=0.8),
    )
    ax.set_xlim(7.4, 17.8)
    ax.set_ylim(4, 17)
    finish(ax, xlabel="quantity $q$", ylabel="unit price $p$", grid_axis="both")
    ax.legend(loc="upper left", fontsize=8, labelspacing=0.35)
    return save(fig, "fig_refinement_lattice")


# --- R7 ----------------------------------------------------------------------
def fig_five_arm_summary():
    """Settled breach and overspend across all five arms."""
    arms = S.HEADLINE["arms"]
    fig, axes = panel(1, 2, height=2.9, width=FULL, labels=False)

    ax = axes[0]
    counts = S.HEADLINE["meaningful_breaches"]
    _bars(ax, arms, counts, "meaningful settled breaches", (0, 1.7), short=True)
    for i, (c, n) in enumerate(zip(counts, S.HEADLINE["deals_settled"])):
        ax.text(i, c + 0.08, f"{c} of {n}", ha="center", fontsize=8, color=INK)
    ax.set_yticks([0, 1])
    ax.set_title("(a) settled breaches", loc="left", fontsize=9, color=INK, pad=6)

    ax = axes[1]
    _bars(ax, arms, S.HEADLINE["overspend_gbp"], "overspend (£)", (0, 0.65), short=True)
    for i, v in enumerate(S.HEADLINE["overspend_gbp"]):
        ax.text(i, v + 0.025, f"£{v:.2f}", ha="center", fontsize=8, color=INK)
    ax.set_title("(b) overspend", loc="left", fontsize=9, color=INK, pad=6)

    return save(fig, "fig_five_arm_summary")


def main():
    use_thesis_style()
    for fn in (
        fig_exposure_by_arm,
        fig_flagged_vs_corrected,
        fig_scenario_inversion,
        fig_harm_averted,
        fig_refinement_lattice,
        fig_five_arm_summary,
    ):
        out = fn()
        print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
