# Phase 0 — number consistency audit

**Date:** 2026-09-07. No LaTeX was edited in this phase.
**Script:** `scripts/audit_numbers.py`.
**Sources:** every `results/**/report.json`, the aggregates in
`results/summary/`, `figures/science_data.py`, `thesis_writing/SCIENCE.md`,
and — for settled outcomes — `src.marketplace_integration.replay` run against
Postgres, never `certificates.jsonl`.

## Summary

Four suspects were named in the review. **Three are not errors**, one is, and
the audit found **a fifth error nobody had flagged**, which is the most serious
of the five.

| # | suspect | verdict |
|---|---|---|
| S1 | arm B at γ=0.4 disagrees between tables | **real** — different run batches, needs a footnote |
| S2 | Fig 5.4(c) vs §5.9 | not an error — arithmetic confirmed |
| S3 | Table 5.1: 1/12 breaching with £0.00 overspend | not an error, and the suggested fix would introduce one |
| S4 | Table 5.6 model axis and γ axis both 126 | coincidence confirmed |
| **S5** | **§5.1 "every breach is on the budget row"** | **false — found by this audit** |

---

## S1 — two batches, and the thesis does not say so

Confirmed. These are separate run families with separate directories:

| table | source family | governed | corrected | deals |
|---|---|---|---|---|
| 5.3, 5.4, B.1 | `arm_b_bargain_v1..v5` | 0/27 | 24/27 | 16 |
| B.2, γ=0.4 row | `arm_b_g0_4_v1..v5` | 0/30 | 27/30 | 17 |

Both are arm B on `bargain_3_9` at γ = 0.4. Neither is wrong; they are
different runs of the same configuration, and the document never says so, so a
reader comparing the two tables sees a contradiction.

**Fix (Phase 1):** a footnote to Table B.2 stating that the γ sweep is its own
batch and that its γ=0.4 cell is therefore not the same run as Table 5.3's arm
B column. **Fix (Phase 3.1):** re-run both from one batch so the footnote
becomes unnecessary.

## S2 — not an error; the aggregates are stale, the figure is right

Figure 5.4(c) plots 25/167 (arm C) and 23/44 (arm C-meet) from
`figures/science_data.py`, which traces to `SCIENCE.md:122`.
`results/summary/five_arms.json` disagrees, giving 153/167 for arm C.

**The JSON is superseded, not the figure.** `science_data.py` documents this in
its own module docstring: those aggregates predate the 2026-08-12
re-verification, and the same file also carries arm B's retracted
`correction_rate = 0.111`. Plotting from the JSON would have put a retracted
claim into the results chapter. The figure is correct.

The decomposition the review asked to confirm holds arithmetically:

| arm | governed | enforced | pre-phase | breaching (governed) | breaching (enforced) | breaching (pre-phase) |
|---|---|---|---|---|---|---|
| C | 167 | 136 | **31** | 25 | 0 | **25** |
| C-meet | 44 | 17 | **27** | 23 | 1 | **22** |

So `44 = 27 + 17` and `167 = 31 + 136`, as the review supposed. Every breach
arm C shows on a governed round happens in the pre-phase, before θ is frozen —
which is limitation B6, that a negotiated contract cannot govern the exchange
that creates it.

**Fix (Phase 1):** this is a definitional problem, not a numerical one. §4.6
needs the definitions table, and Fig 5.4(c) and Table 5.7 need a footnote
saying "governed" for arms C and C-meet includes the ungoverned pre-phase.

## S3 — not an error, and the proposed wording would be wrong

The review supposed the 1-of-12 settled breach on `bargain_3_9` is a trivial
sub-penny overspend. **It is not.** Replayed from Postgres across all five
seeds:

```
arm_a_bargain_v1   business_0008|customer_0003   rows=['cost_floor', 'q_min']   class=meaningful
settled 12, breaching 1
```

The deal sold 2 items instead of 3, at 9.05 against a 10.19 cost floor. It
breaches the **cost floor and the minimum quantity**, and not the budget.
Overspend is a budget-row quantity, so a breach on other rows produces £0.00
overspend by construction. The row is consistent exactly as printed.

`replay.py` is explicit that this is deliberate: `trivial` requires the breach
to be confined to the budget row, because "for cost_floor and the quantity and
deadline bands there is no such scale — selling below your own cost, or
delivering two items where three were ordered, is categorically a breach
however narrowly it misses". The docstring names this deal as **the most
serious breach in the dataset**.

**Do not** describe it as trivial. **Fix (Phase 1):** one clause in §5.1 or in
Table 5.1's caption explaining that overspend measures the budget row only, so
a non-budget breach shows £0.00.

## S4 — coincidence, confirmed

- model axis: 27 + 52 + 21 (three Gemini) = 100, plus 26 (`claude-haiku-4-5`) = **126**
- γ axis: 34 + 30 + 29 + 33 = **126**

Genuinely unrelated. Table 5.6's caption already breaks out both, so no change
is needed beyond being aware that a reader may read it as a typo. Worth one
clarifying clause.

## S5 — §5.1 is false, and this was not on anyone's list

§5.1 states, without qualification:

> Every breach is on the budget row; the cost floor and the quantity bounds are
> never violated by the sellers.

The single settled breach in the ungoverned arm on the working scenario
violates `cost_floor` **and** `q_min`, as the replay above shows. The sentence
is contradicted by the dataset's own most serious breach, and by the docstring
of the module that classifies it.

The claim is defensible if scoped to *offered proposals*, which is probably
what was meant — the fuzzing section separately reports that "the failures are
on the cost floor and the minimum quantity" for large-jump draws, so the
document is already inconsistent with itself on this point. It is not
defensible as written.

**Fix (Phase 1):** scope the sentence to offered proposals and state the
settled exception, or delete the second clause. This is a correctness fix and
should be made whether or not anything else in Phase 1 happens.

---

## What the audit did not cover

- Tables 5.2, 5.5, 5.8 and B.3 were spot-checked against `SCIENCE.md` and
  agree; they were not re-derived from Postgres.
- Figures 5.1–5.3 were not re-derived; `make_manifest.py` guarantees the
  rendered widths, not the values.
- `results/summary/five_arms.json` and `arms.json` are **stale** and should not
  be used as a reference by anything. They are retained because
  `science_data.py` cites them for the seed SDs, which do match.

## Deliverables

- `scripts/audit_numbers.py` — per-family totals and the aggregates behind each table
- `docs/audit_numbers_report.md` — this file
