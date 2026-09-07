#!/usr/bin/env python3
"""Fisher exact tests for the categorical contrasts in Chapter 5.

The chapter's usual device is a standard deviation of a difference computed
from per-arm seed SDs. That is the right tool for a rate with spread, and the
wrong one for a contrast with none: 15 of 15 against 0 of 13 has no variance to
divide by. These are the contrasts where every seed points the same way, so an
exact test on the pooled counts says more than any multiple of a noise estimate.

    uv run python scripts/exact_tests.py
"""
from __future__ import annotations
from scipy.stats import fisher_exact

# (label, ungoverned successes/total, governed successes/total, where it is used)
CONTRASTS = [
    ("undisclosed_3_9, settled deals breaching",
     15, 15, 0, 13, "Section 5.3, Table 5.2"),
    ("bargain_3_9, governed rounds breaching",
     46, 58, 0, 27, "Section 5.4, Table 5.3"),
    ("transfer vs filter, settled deals breaching",
     4, 15, 0, 16, "Section 5.6, Table 5.5"),
    ("bargain_3_9, governed rounds breaching, monitor vs filter",
     37, 51, 0, 27, "Section 5.4, Table 5.3"),
]


def main() -> None:
    print(f"{'contrast':<52}{'a/n':>10}{'b/m':>10}{'odds':>10}{'p':>12}")
    for label, a, n, b, m in ((c[0], c[1], c[2], c[3], c[4]) for c in CONTRASTS):
        table = [[a, n - a], [b, m - b]]
        odds, p = fisher_exact(table, alternative="two-sided")
        odds_s = "inf" if odds == float("inf") else f"{odds:.1f}"
        print(f"{label:<52}{f'{a}/{n}':>10}{f'{b}/{m}':>10}{odds_s:>10}{p:>12.3g}")
    print("\n  two-sided Fisher exact on the pooled counts;")
    print("  every one of these contrasts is unanimous across all five seeds.")


if __name__ == "__main__":
    main()
