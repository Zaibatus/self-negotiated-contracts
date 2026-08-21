"""Authoritative figure data, transcribed from SCIENCE.md and the dated notes.

CLAUDE.md rule 1: *never invent a number; every figure traces to SCIENCE.md or a
dated note.* This module is that trace. Each table below carries the file and
line range it was copied from, so any value in any figure can be audited back to
a verified source in one step.

**Why this is not read from results/summary/*.json.** Those aggregates predate
the 2026-08-12 re-verification and disagree with SCIENCE.md in two places that
matter:

* ``five_arms.json`` gives arm C ``governed_breaches = 153/167``; SCIENCE.md:109
  gives **25/167**.
* ``five_arms.json`` gives arm B ``correction_rate = 0.111``. That is the
  *retracted* "the filter binds on 11.1% of rounds, a light touch" claim
  (SCIENCE.md:172). The verified value is **24/27 = 0.89**.

Plotting from the JSON would have put a retracted claim into the results chapter,
which CLAUDE.md rule 2 forbids. ``gamma_sweep.json`` *is* consistent with
SCIENCE.md §8 and is read directly by the theory figures.
"""

from __future__ import annotations

# --- SCIENCE.md §6: headline table, `bargain_3_9`, 5 seeds (SCIENCE.md:98-109) -
# Seed SDs for the offered-breach row come from results/summary/five_arms.json,
# whose `offered_breach_sd` values match SCIENCE.md §6 and §12 exactly.
HEADLINE = {
    "arms": ["A", "D", "B", "C", "C-meet"],
    "proposals": [95, 80, 51, 219, 67],
    "offered_breach": [0.858, 0.822, 0.472, 0.922, 0.664],
    "offered_breach_sd": [0.050, 0.039, 0.073, 0.042, 0.057],
    "deals_settled": [12, 12, 16, 14, 15],
    "settled_breach": [0.083, 0.083, 0.000, 0.143, 0.000],
    "meaningful_breaches": [1, 1, 0, 1, 0],
    "overspend_gbp": [0.00, 0.00, 0.00, 0.48, 0.00],
    "value_gbp": [143.75, 156.27, 259.45, 220.69, 251.60],
    # (breaching, governed) — SCIENCE.md:109
    "governed": [(46, 58), (37, 51), (0, 27), (25, 167), (23, 44)],
}

# --- Monitoring vs enforcement (2026-08-05-arm-d-monitoring-vs-enforcement.md) -
# Table at :92-96, recomputed after the intervention-logging bug (SCIENCE.md §11
# bug 4). The superseded table at :79 of that note is RETRACTED — do not use it.
MONITORING = {
    "arms": ["A", "D", "B"],
    "governed_rounds": [58, 51, 27],
    "openings": [22, 25, 23],
    "continuations": [36, 26, 4],
    "flag_rate": [0.79, 0.73, 0.89],
    "correction_rate": [None, None, 0.89],
    # Continuation-only breach rate, note :101-103. Arm B's denominator is 4.
    "continuation_breach": [26 / 36, 14 / 26, 3 / 4],
    "continuation_n": [36, 26, 4],
}

# --- Scenario inversion (2026-08-05-arm-a-bargain-scenario.md:32-39) ----------
# The designed effect landed on the offer side and reversed on the deal side.
INVERSION = {
    "scenarios": ["mexican_3_9", "bargain_3_9"],
    "offered_breach": [0.593, 0.858],
    "offered_breach_sd": [0.029, 0.050],
    "settled_breach": [0.400, 0.083],
    "settled_counts": [(6, 15), (1, 12)],
    "overspend_share": [0.0052, 0.0000],
    "meaningful": [2, 1],
    "trivial": [4, 0],
    "deals_closed": [(15, 15), (12, 15)],
}

# --- The harm-averted centrepiece (2026-08-10-undisclosed-budget.md) ----------
# Per-seed table at :87-93; governable-pair totals at :73-78. SCIENCE.md §7.
UNDISCLOSED = {
    "seeds": ["v1", "v2", "v3", "v4", "v5"],
    "a_over_gbp": [4.29, 4.29, 4.29, 4.29, 4.54],
    "b_over_gbp": [0.00, 0.00, 0.00, 0.00, 0.00],
    "a_deals": [3, 3, 3, 3, 3],
    "a_breaching": [3, 3, 3, 3, 3],
    "b_deals": [1, 3, 3, 3, 3],
    "b_breaching": [0, 0, 0, 0, 0],
    # Governable pairs only — the ones with a non-empty safe set.
    "total_over": {"A": 21.70, "B": 0.00},
    "total_share": {"A": 0.0793, "B": 0.0000},
    "value": {"A": 273.75, "B": 213.17},
    "deals": {"A": 15, "B": 13},
    # Marketplace-wide, including the 4 unsatisfiable pairs which run unfiltered
    # by design. SCIENCE.md:125-128 — the residual is one deal on an empty safe
    # set. This must never be presented as the headline.
    "marketplace_wide": {"A": 21.70, "B": 6.15},
}

# --- Proposition 2, the friction window (SCIENCE.md:51, :58-61) ---------------
# Proved on gradient-ascent proxies, NOT demonstrated live.
FRICTION = {
    "kappa_x0": 15.95,
    "kappa_nbs": 39.78,
    "grad_norm_at_nbs": 79.56,
    "nbs": (8.500, 100.00, 26.00),
}

# --- Safety replication, four axes (SCIENCE.md:135-142) ----------------------
REPLICATION = {
    "axis": [
        "model\n(3 Gemini models)",
        "enforcement rate\n(4 values of $\\gamma$)",
        "scenario\n(bargain, undisclosed)",
        "provenance\n(imposed, negotiated, composed)",
    ],
    "breaching": [0, 0, 0, 0],
    "governed": [100, 126, 49, 179],
}

ARM_LABELS = {
    "A": "A\nungoverned",
    "D": "D\nmonitor",
    "B": "B\nimposed",
    "C": "C\nnegotiated",
    "C-meet": "C-meet\ncomposed",
}

# Five two-line labels do not fit a third-width panel without colliding, which
# FIGURES.md §2 forbids. Tight panels use these and name the arms in the caption.
ARM_SHORT = {"A": "A", "D": "D", "B": "B", "C": "C", "C-meet": "C$\\wedge$M"}


def arm_index(name: str) -> int:
    return HEADLINE["arms"].index(name)
