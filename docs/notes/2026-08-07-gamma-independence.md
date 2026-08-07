# Is the model γ-independent or parametric, live?

**Date:** 2026-08-07
**Answers supervision ask (4) of 2026-08-06.**
**Data:** arm B on `bargain_3_9`, γ ∈ {0.2, 0.4, 0.7, 1.0}, 5 seeds each,
gemini-2.5-flash, T_max = 6. 20 new runs.

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts

for G in 0.2 0.4 0.7 1.0; do
  TAG=$(echo $G | tr '.' '_')
  for i in 1 2 3 4 5; do
    uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
        --gamma $G --t-max 6 --experiment "arm_b_g${TAG}_v$i" --override
  done
done
```

Numbers are in `results/summary/gamma_sweep.json` (tracked).

---

## Result

| γ | governed breaches | corrected | mean ‖u‖_M | deals | rounds/pair | surplus loss | margin inside C(θ) |
|---|---|---|---|---|---|---|---|
| 0.2 | **0/34** | 30/34 | 0.727 | 17 | 1.36 | 0.00% | −0.000 |
| 0.4 | **0/30** | 27/30 | 0.790 | 17 | 1.25 | 0.00% | −0.000 |
| 0.7 | **0/29** | 23/29 | 0.787 | 17 | 1.16 | 0.00% | 0.000 |
| 1.0 | **0/33** | 24/33 | 0.737 | 15 | 1.38 | 0.00% | 0.000 |

**Safety is γ-independent, as predicted.** Zero breaches at every γ, across 126
governed rounds. This is the expected result and it is worth being explicit
about why it is not trivial: γ controls how fast the draft may *approach* the
boundary, not whether the set is respected. A sweep that produced breaches at
high γ would have meant the barrier condition was being confused with the
constraint itself.

**Everything else is γ-independent too — and that is the finding, because the
formulation predicts otherwise.**

## The boundary-layer prediction fails on live agents. Marked corrected.

Addendum A.1 predicts a boundary layer: lower γ should park deals further
*inside* C(θ). In simulation the margin ran 3.19 → 0.34 as γ went 0.2 → 0.7,
a clean monotone effect that the note called "v1's conservatism premium
measured in term space".

Live, the margin is **0.000 at every γ**. There is no boundary layer at all.

The cause is structural, not noise:

| γ | share of governed rounds that are the *opening* |
|---|---|
| 0.2 | 74% |
| 0.4 | 80% |
| 0.7 | 86% |
| 1.0 | 73% |

Negotiations run 1.16–1.38 rounds per pair. Almost every deal is settled at the
**opening projection** — and `project_into_safe_set` uses `gamma=1.0`
internally, by construction, because it is a projection onto C(θ) rather than a
barrier step. So the step that decides the outcome never sees the arm's γ.

**γ governs the barrier; the barrier governs continuation rounds; live
negotiations barely have continuation rounds.** The boundary layer is a
cumulative effect of repeated barrier steps, and there is nothing here for it
to accumulate over.

This does not contradict the simulation — it bounds where the simulation's
result transfers. A.1's γ-sweep remains correct about the DCBF; it is simply
not reachable in a regime this short. The honest statement for the dissertation
is: **the conservatism premium is a property of sustained negotiation, and the
live testbed does not sustain one.**

## Is the design of `project_into_safe_set` right?

Arguably yes, and it is worth defending rather than treating as an accident.
The opening has no previous state, so there is no transition for a barrier
condition to govern; projecting onto C(θ) is the only well-defined thing to do,
and doing it at γ < 1 would mean deliberately leaving the first offer in breach
in order to recover from it gradually — knowingly forwarding a breaching offer,
which the protocol docstring already rejects.

But the consequence should be stated plainly: in a short-negotiation regime
**γ is very nearly inert**, and any claim that it is "an economic policy
parameter" (formulation §8, §9.4) is a claim about the simulation, not about
what has been observed live. Shadow prices — the other half of that claim —
remain unexercised on live agents (outline G2).

## What would make γ bite

Two routes, both currently blocked or unbuilt:

1. **Longer negotiations.** A scenario that sustains six to ten rounds would
   give the barrier something to act over. `bargain_3_9` produces the opposite,
   because the buyer knows its budget and settles immediately.
2. **Not projecting the opening.** Seeding x₀ at the proposal and letting the
   barrier recover geometrically would make γ govern from round one — at the
   cost of knowingly delivering a breaching first offer. That is a design
   change with a safety consequence, not a tuning knob, and would need
   supervision.

## Incidentally: this supersedes the pre-fix arm B runs

The γ = 0.4 cell here is arm B re-run under post-`8696016` code, so the arm B
and arm D notes' caveat — that arm B's trajectories were produced by a seller
reasoning from prices it never offered — no longer applies to a clean cell.
Comparing them: 17 deals here against 16 before, 0 governed breaches in both.
The reconciliation fix did not move the outcome measurements, which is
reassuring but was not guaranteed.

## Limitations

- **n = 5 seeds × 3 customers per γ.** Everything is five draws of three
  situations.
- **One model and one scenario.** γ-independence of safety is structural and
  would be surprising to see broken; γ-inertness of *outcomes* is specific to
  the short-negotiation regime this scenario produces.
- **Surplus loss reads 0.00% at every γ**, which is not evidence of anything:
  every deal settles on the budget boundary, and on this calibration the
  boundary sits close to the bargaining solution. See the funnelling note.
- **The margin statistic is min-h over active rows at the settled terms.** With
  every deal on the budget boundary it is measuring one row, so "no boundary
  layer" is specifically about the budget.
