# Arm D — monitoring without enforcement: tendency or bound?

**Date:** 2026-08-05
**Data:** `arm_d_bargain_v1..v5`, `data/bargain_3_9`, gemini-2.5-flash, γ = 0.4, T_max = 6 — the same knobs as arm B, `mode="monitor"`. Five live runs.

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts

for i in 1 2 3 4 5; do
  uv run python experiments/arm_d_monitored.py --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_d_bargain_v$i" --override
done
```

Every number below is in `results/summary/arms.json`, which is tracked.

---

## The question this arm exists to answer

The arm A note concluded that the claim which survives is not *"the filter
prevents harm the buyer would otherwise have accepted"* but *"the filter
converts a tendency into a bound"*. Arm D is the evidence either way: identical
detection to arm B, no correction.

**Answer: overwhelmingly the bound.** The per-round guarantee is absolute and
the effect is enormous. The realised harm prevented is one deal in twelve, and
at n = 12 that is not distinguishable from noise.

## Three arms side by side

| | arm A (off) | arm D (monitor) | arm B (filter) |
|---|---|---|---|
| proposals offered | 95 | 80 | 51 |
| &nbsp;&nbsp;breaching θ | 0.858 | 0.822 | **0.472** |
| deals settled | 12 | 12 | 16 |
| &nbsp;&nbsp;breaching θ | 0.083 | 0.083 | **0.000** |
| &nbsp;&nbsp;meaningful breaches | 1 | 1 | **0** |
| overspend / value | 0.00% | 0.00% | 0.00% |
| value transacted | $143.75 | $156.27 | $259.45 |

Per-round, split by whether the pair was governed at all:

| | arm A | arm D | arm B |
|---|---|---|---|
| governed pairs (C(θ) non-empty) | 46/58 | 37/51 | **0/27** |
| infeasible pairs (never filtered) | 37/37 | 29/29 | 24/24 |

## Arm A vs arm D is the noise floor, and that is what makes the rest readable

Arms A and D are behaviourally identical by construction — both pass every
message through untouched, and the agents never see the flags. So **every A/D
difference is seed noise**, and its size is the yardstick against which any
A/B difference has to be read:

| | A vs D (noise) | A vs B (treatment) | ratio |
|---|---|---|---|
| offered breach rate | 0.036 | 0.386 | ~11× |
| governed per-round breach rate | 0.068 | 0.793 | ~12× |
| deals settled | 0 | +4 | — |
| settled breach rate | 0.000 | 0.083 | — |

The safety effect clears the noise floor by an order of magnitude. The
closure and settled-breach differences do not, and are discussed below.

Arms A and D also settled the same number of deals (12 each), had the same
number of meaningful breaches (1 each) and lost no pair relative to each other
— which is the sanity check that monitoring changes nothing, and it passes.

## Enforcement is prevention, not just correction

The most interesting number in this note is the gap between what the filter
*would* have had to do and what it *did*:

| | arm D (counterfactual) | arm B (applied) |
|---|---|---|
| governed rounds | 51 | 27 |
| flagged | 49 (**96%**) | 3 (**11%**) |
| non-zero correction | 25 | 3 |
| mean correction (scaled units) | 0.299 | 0.795 |

Arm D says: on an ungoverned trajectory, 96% of governed rounds propose terms
that violate θ or approach its boundary too fast. Arm B corrects 11%.

That is not the filter missing things. It is that **enforcement changes the
trajectory so that violations stop arising**. The opening proposal is projected
into C(θ), every subsequent round starts from a compliant state, and the
negotiation simply does not wander outside. The filter earns its keep mostly by
prevention; the corrections it visibly applies are the residue.

The corollary is that a monitor cannot be costed as "the filter minus the
rewriting". A monitor sits on a trajectory that a filter would never have
produced, so 49 flags and 3 corrections are not two measurements of the same
thing — they are measurements on different paths. Reporting them as a
before/after would imply a pairing that does not exist.

## Surplus

| | arm A | arm D | arm B |
|---|---|---|---|
| surplus loss vs Nash benchmark | 0.93% | 0.00% | 0.00% |
| distance of settled terms to x\*_NBS (scaled) | 0.221 | 0.124 | 0.085 |

Arm D lands between A and B on both. Since D is behaviourally identical to A,
that spread *is* the noise on these two statistics — which means arm B's
apparent advantage over arm A (0.221 → 0.085) is roughly the same size as the
A→D noise (0.221 → 0.124) and should not be claimed as a filter effect.

## What does not survive scrutiny

**Arm B settling 16 deals against 12 for both A and D.** A and D agreeing
exactly at 12 makes +4 look real, but two things argue against reading it that
way. Almost all of it is one pair (`business_0008|customer_0003`, 2 → 5), the
same customer that dominated closure variance in arm A. And arm B's runs
**predate the reconciliation fix** (`8696016`): they were produced under a
seller reasoning from prices it never offered, which is exactly the kind of
perturbation that could change whether a negotiation closes. Its outcome
numbers come from the database and stand; its *trajectories* are not what a
correctly-informed seller would have produced.

So: the per-round safety result (0/27) is robust — it is an outcome measured
at the database and the effect is 12× the noise floor. The closure and surplus
differences are not, and I am not claiming them.

**The settled-breach improvement is one deal.** 1/12 → 0/16. Arms A and D both
produced exactly one meaningful settled breach, so the noise on that statistic
is zero *in this sample* — but a single event out of twelve cannot support a
rate claim either way.

## The answer, stated plainly

Does the filter prevent harm the buyer would otherwise have accepted, or does
it mainly convert a tendency into a bound?

**Mainly a bound**, and the arm D numbers make the case precisely:

- the marketplace proposes inadmissible terms almost continuously — 96% of
  governed rounds flagged when nothing is enforced;
- the buyer declines nearly all of them unaided, so only 1 deal in 12 settles
  outside θ;
- the filter takes per-round exposure to **zero** and takes that one deal to
  zero as well, but the second of those is a single event.

The thesis claim that this supports is about *guarantees*, not about harm
averted on this scenario. A buyer that declines 96% of bad offers is not a
buyer that declines all of them, and it offers no bound. Arm D is what turns
that from an assertion into a measurement — and it also shows the honest limit:
on `bargain_3_9` the realised harm was small enough that no filter could have
prevented much of it.

## Limitations

- **n = 5 seeds × 3 customers**, twice over for the ungoverned condition (A and
  D). Fifteen draws of three situations, not 36 independent observations. Every
  difference here is seed variance under one fixed scenario.
- **Arm B's trajectories predate `8696016`** — see above. **[resolved
  2026-08-07]** The γ = 0.4 cell of the γ sweep is arm B re-run under post-fix
  code: 17 deals against 16, zero governed breaches in both. The
  reconciliation fix did not move the outcome measurements. See
  `2026-08-07-gamma-independence.md`.
- **Termination is measured, not enforced.** G_κ comes from a friction schedule
  the agents never experience (formulation §A.5 item 1). T_max = 6 barely binds
  at observed lengths of median 3, p90 5, so the liveness column carries almost
  no signal.
- **Φ / Φ_proj are not reported as convergence results** — §5's 96% is under a
  tuned diminishing step and live agents have none.
- **`bargain_3_9` gives the filter little to prevent**, by construction: the
  scenario tells the buyer its budget and the buyer then polices it. That is
  the finding of the arm A note and it bounds what any treatment arm can show
  here.
