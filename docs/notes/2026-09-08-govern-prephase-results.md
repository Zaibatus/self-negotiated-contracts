# Governing the pre-phase, measured

**2026-09-08.** 20 live runs, ~£2. Scores
`docs/notes/2026-09-08-PREREGISTRATION-govern-prephase.md`, written before the
option had been run once and not edited since. Outcomes recomputed by
`src.marketplace_integration.replay` against the Postgres database.

γ = 0.4, T_max = 6, five runs each on `bargain_3_9`, `offset_102_3_9`,
`offset_105_3_9`, `disclosed_offset_3_9`. Experiments `arm_gp_<f>_v<n>`.

## Result

| f | settled | breaching deals | overspend | fallback rounds | corrections |
|---|---|---|---|---|---|
| 1.00 | 15 | **0** | **£0.00** | 0 | 32 |
| 1.02 | 15 | **0** | **£0.00** | 1 | 28 |
| 1.05 | 15 | **0** | **£0.00** | 3 | 27 |
| 1.10 | 16 | **0** | **£0.00** | 0 | 22 |

Against the same arm with the pre-phase left ungoverned (15/2/£0.47,
15/2/£0.30, 15/8/£8.20, 15/7/£7.02):

**The residual is gone at every offset.** Not reduced — removed. Closure is
unchanged at f ≤ 1.05 and one deal higher at f = 1.10.

## Scoring

**P1 — HOLDS, exactly.** £0.00 marketplace-wide overspend and 0 breaching
settled deals at all four offsets. This is the load-bearing one, and it
confirms the attribution in the guarded-meet note: the residual there really
was the pre-phase and nothing else.

**P2 — HOLDS.** Closure is 15, 15, 15, 16 against arm B's 15 on `bargain_3_9`
(single-batch re-run; 16 in the batch Table 5.8 tabulates) and 17 at f = 1.1.
Every value is within one deal of arm B at the same offset, which is inside the
run-to-run variation these configurations show. Governing the pre-phase costs
no trade.

**P3 — HOLDS, and strongly.** Fallback rounds fall from 0, 21, 10, 13 to
**0, 1, 3, 0**. Correcting the opening tightens the inferred envelope, so the
meet is almost never empty and the guard almost never has to fire. The
mechanism is exactly the one predicted: the envelope is inferred from a seller
ask that has already been pulled inside the mandate, so `meet B = min(mandate
B, corrected ask × q)` no longer sits above `meet c × q_min`.

The guard is not thereby redundant — it fired on 4 rounds across the 20 runs,
and on those rounds it is what kept the mandate in force — but governing the
pre-phase removes most of the need for it.

**P4 — HOLDS.** No settled deal breaches on any pair. Stronger than predicted.

## Where the remaining breaching rounds are

23, 15, 20 and 22 rounds still breach. **Every one of them is on a pair whose
mandate is itself unsatisfiable** — 0 elsewhere, at every offset. That is
limitation B4(a), where the cost floor times the minimum quantity exceeds the
budget and nothing could ever comply. The design detects those and declines to
filter, which is the case §7.4.2 argues about and `--refuse-unsatisfiable`
addresses separately. None of them settles, which is why overspend is £0.00.

So with the pre-phase governed, the arm's breaches partition cleanly: zero on
anything the platform could have governed, and all of them on pairs it has
already decided not to.

## What this costs, and what it does not settle

**It weakens B6's reach, not B6 itself.** A *negotiated* contract still cannot
govern the exchange that creates it — that remains true and unrepaired. What
the measurement shows is that the exchange need not be ungoverned, because the
platform's own mandate exists from the first message. B6 should be read as a
statement about the negotiated contract, not as a licence to forward the
opening.

**It is a stricter regime than arm C-meet, and that is a choice.** During the
pre-phase the parties are held to the mandate rather than to anything they
agreed, so the freedom the composed arm exists to protect starts one round
later than it did. On these scenarios that costs nothing measurable in closure.
On a scenario where the parties would have agreed something the mandate forbids
and then converged back inside it, it would.

**No seed control exists.** `v1`–`v5` are five independent runs at an identical
configuration; what separates them is language-model sampling nondeterminism.
Nothing here is a seed comparison.

## Reproduce

```
set -a; . ../multi-agent-marketplace/.env; set +a
for e in 100:bargain_3_9 102:offset_102_3_9 105:offset_105_3_9 110:disclosed_offset_3_9; do
  for n in 1 2 3 4 5; do
    uv run python experiments/arm_c_meet_guarded.py --govern-prephase \
      --data "data/${e##*:}" --experiment "arm_gp_${e%%:*}_v${n}"
  done
done
```
