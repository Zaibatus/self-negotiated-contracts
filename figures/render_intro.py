"""Chapter 1's figure: the enforcement point in the message path.

The one diagram the prose of Section 1.4 cannot carry quickly. Three blocks
left to right, numbered so the text can refer to the numbers, and the worked
exchange of Section 1.2 (£13.51 -> £11.57 against a £11.58 budget) carried
along the path so the figure states a measured example rather than a cartoon.

FIGURES.md: five blocks maximum, visible entry point, greyscale first, ACCENT
reserved for the breaching value and nothing else.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyBboxPatch  # noqa: E402

from thesis_style import ACCENT, FULL, GREY, GREY_DARK, INK, save, use_thesis_style  # noqa: E402


def box(ax, x, y, w, h, *, edge=INK, lw=1.1, fill="white"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012",
                                linewidth=lw, edgecolor=edge, facecolor=fill, zorder=3))


def arrow(ax, x0, x1, y, label, colour):
    ax.annotate("", xy=(x1, y), xytext=(x0, y), zorder=4,
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.3, shrinkA=0, shrinkB=0))
    ax.text((x0 + x1) / 2, y + 0.055, label, ha="center", va="bottom",
            fontsize=9, color=colour, zorder=5)


def main() -> None:
    use_thesis_style()
    fig, ax = plt.subplots(figsize=(FULL, 3.05))
    ax.set_xlim(0, 10); ax.set_ylim(0, 3.75); ax.axis("off")

    ybot, bh, bw = 1.95, 1.34, 2.5
    ytop = ybot + bh
    ymid = ybot + bh / 2

    def block(x, n, title, body, lw=1.1):
        box(ax, x, ybot, bw, bh, lw=lw)
        cx = x + bw / 2
        ax.text(cx, ytop - 0.14, f"{n}.  {title}", ha="center", va="top",
                fontsize=9.5, color=INK, weight="bold")
        ax.text(cx, ytop - 0.46, body, ha="center", va="top",
                fontsize=8.5, color=GREY_DARK, linespacing=1.4)

    block(0.10, 1, "seller agent", "stock agent,\nstock prompt")
    block(3.75, 2, "protocol filter",
          "inside $C(\\theta)$?  forward\notherwise rewrite\nto the nearest terms", lw=1.7)
    block(7.40, 3, "buyer agent", "never sees the\noriginal terms")

    arrow(ax, 2.64, 3.71, ymid, "£13.51", ACCENT)
    arrow(ax, 6.29, 7.36, ymid, "£11.57", INK)

    # the contract enters from below: it is configuration, not a message
    box(ax, 3.30, 0.30, 3.40, 0.78, edge=GREY, lw=1.0, fill="#f4f4f4")
    ax.text(5.00, 0.94, "$\\theta$  read from the scenario file", ha="center", va="top",
            fontsize=8.5, color=GREY_DARK)
    ax.text(5.00, 0.63, "budget $B$ = £11.58", ha="center", va="top",
            fontsize=8.5, color=INK)
    ax.annotate("", xy=(5.00, ybot - 0.03), xytext=(5.00, 1.13), zorder=2,
                arrowprops=dict(arrowstyle="-|>", color=GREY, lw=1.0,
                                linestyle="--", shrinkA=0, shrinkB=0))

    ax.text(0.10, 3.62, "no agent is modified, and no prompt is edited",
            ha="left", va="top", fontsize=8.5, color=GREY_DARK, style="italic")

    out = save(fig, "fig_enforcement_point")
    print(f"wrote {out.name}")


if __name__ == "__main__":
    main()
