# Two analyses that cost nothing: one confirms a finding, one kills a test

**Date:** 2026-09-08. No runs, no API calls, £0.00.

## 1. Enforcement preserves the market — mechanism confirmed, not inferred

`2026-09-08-adversarial-seller.md` reported that under an adversarial seller,
closure collapsed ungoverned and held under enforcement, and flagged the
mechanism as **inferred from closure counts rather than measured**. It is now
measured, from the message log in Postgres.

**Payments per seed, three customers each:**

| | seed 1 | 2 | 3 | 4 | 5 | total |
|---|---|---|---|---|---|---|
| arm A, ungoverned | **0** | 3 | 2 | 1 | **0** | **6 / 15** |
| arm B, governed | 3 | 3 | 3 | 3 | 3 | **15 / 15** |

Fisher exact, 6/15 against 15/15: **p = 0.0007**. **Two of five ungoverned
seeds close nothing at all.** Every governed seed closes every pair.

The message mix shows why. Ungoverned seed 1 emitted **225 text messages and
141 order proposals and settled nothing**; the governed run of the same seed
emitted 58 text, 7 proposals and 3 payments. The ungoverned negotiation churns:
the seller re-proposes above budget, the buyer refuses, and neither moves.

The buyers say so in as many words:

> "The total price of $37.53 is still above my budget of $31.38. I must have a
> total at or under $31.38."

> "I'm sorry, but the price of $8.31 is still above my budget of $7.45. I
> cannot accept this price."

So the mechanism is exactly what was guessed and is now evidenced: an
adversarial seller deadlocks the market, and the filter breaks the deadlock by
correcting the opening to something the buyer can accept. **The claim can be
stated without the hedge.**

## 2. Is the concession rate deadline-sensitive? The test is confounded

§5.11 says a constant ρ is a fixed proportional concession, unlike the
time-dependent Boulware and Conceder tactics, and that "whether these agents are
genuinely deadline-insensitive is not settled by T_max = 6 and is left open."
An attempt to settle it failed, twice, and both failures are worth recording.

**First attempt, wrong target.** Measuring the per-step contraction ratio
against each trajectory's own *endpoint* gave early 0.623, late 0.426,
p = 1.3 × 10⁻⁸ — apparently strong acceleration near the deadline, i.e.
Boulware-like. It is an artefact: distance to the endpoint is zero *at* the
endpoint by construction, so late steps must look fast. The thesis fits against
x\*_NBS, not the endpoint.

**Second attempt, right target, still confounded.** Against x\*_NBS the sign
reverses: early **0.694**, late **0.867**, p = 1.5 × 10⁻¹⁶. Deceleration, not
acceleration. But the thesis already fits `d_k = f + (d0 − f)ρ^k` with a
**positive floor** of 0.029 to 0.183, and such a model decelerates by
construction — as d → f the step ratio → 1. Simulating it:

| fitted floor | predicted early | predicted late |
|---|---|---|
| 0.00 | 0.624 | 0.624 |
| 0.10 | 0.715 | 0.911 |
| 0.18 | 0.764 | 0.947 |

The measured 0.694 / 0.867 sits inside that band. **The deceleration is what
the already-fitted model predicts, so this test cannot separate deadline
behaviour from floor approach.**

**Conclusion: §5.11's wording is correct and should not be changed.** What can
be added is why the question is hard. Deciding it needs trajectories at
*different* T_max, so that deadline proximity varies independently of distance
to the floor. Every run in this project uses T_max = 6, so the data cannot
answer it at any sample size.

Two wrong answers were nearly reported here. Both looked clean, both had a
small p-value, and both were artefacts of the comparison rather than facts about
the agents. That is the same failure mode as the seven integration defects in
Chapter 4, arriving through analysis rather than through code.
