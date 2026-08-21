"""Shared figure style for the thesis. The only sanctioned way to make a figure.

Conventions live in ``thesis_writing/FIGURES.md``; this module enforces them.
Nothing here should be overridden at a call site — if a figure needs something
this module cannot do, extend the module.

The two rules that motivate most of the code below:

1. Vector or it does not ship (§1). ``save`` writes PDF and refuses anything
   else, because a raster figure recompressed by a publisher is wrong forever.
2. Colour is semantic (§4). ``ACCENT`` means *unsafe / ungoverned / breach* and
   means nothing else; arms are otherwise separated by marker and dash so the
   figures survive greyscale.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

FIGURE_DIR = Path(__file__).resolve().parent

# --- Geometry (FIGURES.md §2) ------------------------------------------------
# a4paper with hmargin=2.8cm gives a 15.4 cm text block. Figures are authored at
# that width and included with [width=\textwidth], never scaled in LaTeX.
TEXT_WIDTH_IN = 6.06
FULL = TEXT_WIDTH_IN
HALF = TEXT_WIDTH_IN / 2

MIN_FONT_PT = 8.0

# --- Palette (FIGURES.md §4) -------------------------------------------------
INK = "#1a1a1a"
GREY_DARK = "#4d4d4d"
GREY = "#808080"
GREY_LIGHT = "#bfbfbf"
ACCENT = "#b2182b"  # unsafe / ungoverned / breach. Nothing else.

SEQ = LinearSegmentedColormap.from_list("thesis_seq", ["#ffffff", ACCENT])

# Arms are distinguished by marker and dash first, colour second, so that the
# greyscale test in FIGURES.md §7 passes. Arm A is red everywhere because arm A
# is the ungoverned arm; arm D is red-adjacent grey because A and D are
# behaviourally identical by construction (SCIENCE.md §5) and their difference
# is the noise floor.
ARM_STYLE = {
    "A": {"color": ACCENT, "marker": "o", "linestyle": "-", "hatch": ""},
    "B": {"color": INK, "marker": "s", "linestyle": "-", "hatch": ""},
    "C": {"color": GREY_DARK, "marker": "^", "linestyle": "--", "hatch": "//"},
    "C-meet": {"color": GREY, "marker": "D", "linestyle": "-.", "hatch": "\\\\"},
    "D": {"color": GREY_LIGHT, "marker": "v", "linestyle": ":", "hatch": ".."},
}

ARM_ORDER = ["A", "D", "B", "C", "C-meet"]


def use_thesis_style() -> None:
    """Apply the house rcParams. Call once at the top of every render script."""
    plt.style.use("default")
    plt.rcParams.update(
        {
            # Type: serif to match the 12pt report body; 9pt base against a 12pt
            # body, with nothing below the 8pt floor (FIGURES.md §2).
            "font.family": "serif",
            "font.size": 9,
            "axes.labelsize": 9,
            "axes.titlesize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "legend.fontsize": 8,
            "figure.titlesize": 9,
            # Embed fonts as TrueType rather than Type 3, so text stays
            # selectable and searchable in the final PDF.
            "pdf.fonttype": 42,
            "ps.fonttype": 42,
            # Declutter: no top/right spines, grid behind the data.
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.axisbelow": True,
            "axes.edgecolor": GREY_DARK,
            "axes.linewidth": 0.8,
            "grid.color": GREY_LIGHT,
            "grid.linewidth": 0.5,
            "grid.alpha": 0.4,
            "legend.frameon": False,
            "lines.linewidth": 1.4,
            "lines.markersize": 4,
            "figure.figsize": (FULL, 3.4),
            "figure.dpi": 150,
            "savefig.dpi": 400,
        }
    )


def _check_font_sizes(fig) -> list[str]:
    """Return descriptions of any text artist rendering below the 8pt floor."""
    offenders = []
    for text in fig.findobj(plt.Text):
        content = text.get_text().strip()
        if not content:
            continue
        size = text.get_fontsize()
        if size < MIN_FONT_PT:
            offenders.append(f"{size:.1f}pt: {content[:40]!r}")
    return offenders


def save(fig, name: str) -> Path:
    """Write ``fig`` to ``figures/<name>.pdf``. The only sanctioned save path.

    Refuses non-PDF output (FIGURES.md §1) and warns on sub-8pt text (§2).
    """
    stem = Path(name).stem
    suffix = Path(name).suffix.lower()
    if suffix and suffix != ".pdf":
        raise ValueError(
            f"FIGURES.md §1: every figure is a PDF; refusing to write {suffix!r}. "
            "A raster figure recompressed by a publisher cannot be fixed later."
        )

    offenders = _check_font_sizes(fig)
    if offenders:
        warnings.warn(
            f"{stem}: text below the {MIN_FONT_PT:.0f}pt floor (FIGURES.md §2): "
            + "; ".join(offenders),
            stacklevel=2,
        )

    fig.tight_layout()
    out = FIGURE_DIR / f"{stem}.pdf"
    fig.savefig(out, format="pdf", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return out


def background_series(ax, series, **kwargs) -> None:
    """Draw a cohort as a light grey background layer (FIGURES.md §3).

    The alternative to a spaghetti plot: the cohort goes back, and only the two
    or three series carrying the claim are drawn on top of it.
    """
    style = {"color": GREY_LIGHT, "linewidth": 0.7, "alpha": 0.55, "zorder": 1}
    style.update(kwargs)
    for item in series:
        if isinstance(item, tuple):
            ax.plot(item[0], item[1], **style)
        else:
            ax.plot(item, **style)


def panel(nrows=1, ncols=2, height=3.0, width=FULL, labels=True, **kwargs):
    """Multi-panel figure as a *single* PDF, with (a)/(b) labels drawn here.

    The template loads the deprecated ``subfigure`` package rather than
    ``subcaption``, and CLAUDE.md forbids adding packages — so panels are
    composed in matplotlib and included as one graphic (FIGURES.md §8).
    """
    fig, axes = plt.subplots(nrows, ncols, figsize=(width, height), **kwargs)
    flat = axes.ravel() if hasattr(axes, "ravel") else [axes]
    if labels and len(flat) > 1:
        for ax, letter in zip(flat, "abcdefgh"):
            ax.set_title(
                f"({letter})",
                loc="left",
                fontsize=9,
                color=INK,
                pad=6,
            )
    return fig, axes


def finish(ax, xlabel=None, ylabel=None, grid_axis="y") -> None:
    """Apply the shared axis furniture: labels, a light grid, no chartjunk."""
    if xlabel:
        ax.set_xlabel(xlabel)
    if ylabel:
        ax.set_ylabel(ylabel)
    if grid_axis:
        ax.grid(True, axis=grid_axis)
    ax.tick_params(length=3, color=GREY_DARK)
