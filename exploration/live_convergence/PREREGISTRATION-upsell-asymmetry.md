# PRE-REGISTRATION — is the upsell asymmetry real?

**Written 2026-09-14, BEFORE seeds v2–v5 exist.** v1 of each arm is the pilot
already reported in `NOTES.md` (commit `1f760ee`), run under identical config,
so it is pooled rather than re-run. Nothing here may be edited after the first
new run.

## Why

The pilot showed **arm A: 0 of 16 rounds with `q > q_min`; arm B: 7 of 40**, on
identical θ, identical scenario text, and identical prompts. Only the filter
differs. That asymmetry should not exist unless one of two things is true:

- **H_noise** — one seed is one seed, and the difference is run-to-run variance.
- **H_redirect** — the filter *causes* it. In arm B the filter holds price at
  the cost floor, so the seller cannot concede further on price and reaches for
  the other lever the scenario told it about: volume. In arm A price is always
  available, so the seller never needs the second axis.

H_redirect is the interesting one. It would mean a contract does not only
constrain a negotiation, it **redirects it onto a different axis** — which is a
claim about mechanism, not about safety, and nothing in the dissertation
measures it.

## Protocol

Arms A (`--live`, `mode=off`) and B (`mode=filter`, `theta_source=scenario`),
**seeds v2–v5 added to the existing v1**, giving 5 per arm. γ = 0.4,
T_max = 6, `gemini-2.5-flash` minimal reasoning, scenario
`exploration/live_convergence/data/quantity_off09_3_9`. Results to
`exploration/live_convergence/results/`. Schemas `qty_a_v2..v5`, `qty_b_v2..v5`.
Estimated **~£1.20** for the eight new runs, against the £5 ask-first threshold.

## Registered predictions

**P6 — does arm A ever upsell?** Pooled over 5 seeds, arm A will show **at
least one** round with `q > q_min`.
*Falsified if* arm A shows **zero** upsell rounds across all 5 seeds. That
outcome would favour H_redirect strongly, because it would make the asymmetry
structural rather than a rate difference.

**P7 — does the asymmetry survive?** Arm B's upsell rate will exceed arm A's,
Fisher exact **p < 0.05** on the 2×2 of (rounds with `q > q_min`) × arm.
*Falsified if* p ≥ 0.05.

**P8 — the mechanism test, and the one I most want to be right.** Within arm B,
upsell rounds will be **preceded in the same pair by at least one round in
which the filter altered price**, on **≥ 2/3** of upsell rounds. This is what
H_redirect predicts and H_noise does not.
*Falsified if* the fraction is < 2/3. I am registering the weaker 2/3 rather
than a majority because with ~35 expected upsell rounds the estimate is coarse.

**P9 — the budget row keeps doing the work.** `q_min`/`q_max` duals will be
active on **< 5%** of governed rounds, as in the pilot's 0 of 40, while the
`budget` dual stays the row that cuts quantity.
*Falsified if* quantity duals exceed 5%.

**P10 — the shortening replicates.** Median arm B rounds per pair will be
**< 6**, against off09's 10.5 on identical θ. The pilot gave 2.5.
*Falsified if* median ≥ 6.

## What I expect

P6 is the one I genuinely cannot call. If arm A upsells at any appreciable rate
the pilot asymmetry was noise and P7 will fail with it. My prior is that arm A
will show a small non-zero rate — sellers occasionally upsell unprompted — and
that P7 still holds because arm B's rate is several times higher.

P8 is the prediction that carries the interpretation. If P6 and P7 hold but P8
fails, the asymmetry is real and my explanation for it is wrong, which is the
outcome most worth knowing.

## Analysis, fixed in advance

Upsell rate is counted over **governed/recorded rounds** in
`certificates.jsonl`, `q > q_min + 1e-9` on `x_proposed` (what the agent put on
the table), never on `x_applied` (what the filter left). Fisher exact,
two-sided, pooling seeds within arm — with the caveat, as everywhere in this
project, that 5 seeds × 3 customers is 5 draws of the same 3 situations and the
p-value describes seed variance under a fixed scenario, not sampling error over
baskets.
