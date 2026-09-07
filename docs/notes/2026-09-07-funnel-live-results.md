# The funnel crossover, tested live — results

**Date:** 2026-09-07
**Predictions:** `docs/notes/2026-09-07-PREREGISTRATION-funnel-live.md`,
written before any run existed and not edited since.
**Data:** live, `hardundis_010_3_9`, arms A and B, 5 seeds each, γ = 0.4,
T_max = 6, gemini-2.5-flash at minimal reasoning effort. Cost ~£1.15 including
the pilot.
**Code:** `experiments/analyse_funnel_live.py`; numbers in
`results/summary/funnel_live.json`. Runs `hu010_a_v1..v5`, `hu010_b_v1..v5`,
pilot `hb010_a_v1`.

## Result

| pair | margin | arm A | arm B | gain | B settled price | funnel point |
|---|---|---|---|---|---|---|
| b0001\|c0001 | +0.018 | 0.0000 | 0.9606 | +0.9606 | 5.420 | 5.420 |
| b0004\|c0002 | +0.022 | 0.0000 | 0.8861 | +0.8861 | 7.110 | 7.110 |
| b0005\|c0002 | +0.100 | 0.0000 | 0.7319 | +0.7319 | 7.110 | 7.110 |
| **b0008\|c0003** | **−0.011** | 0.0000 | **0.9803** | **+0.9803** | 10.270 | 10.270 |

Ψ/Ψ\* at the final governed state. Median rounds: **1** in both arms.

## Scoring the pre-registered predictions

**P1 — FALSIFIED.** P1 predicted the A→B gain would be *smaller* on the
below-crossover pair. It is **larger**: 0.9803 against an above-crossover mean
of 0.8595.

The reason is instructive and was not anticipated. Arm A collapses to **0.0000
on every pair** — with the budget withheld the buyer accepts terms whose
acceptance probability is effectively nil, exactly as §19 and §20 record. With
the baseline flat at zero the "gain" is just arm B's level, and arm B's level
tracks **|margin|**, not sign(margin). b0008|c0003 happens to have the
*smallest* |margin| of the four (0.011), so it lands nearest p\* and scores
highest. **P1 was the wrong discriminator**: it assumed the ungoverned baseline
would vary across pairs, and it does not.

**P2 — confirmed.** Arm B settles at the funnel point to the cent on all four
pairs: 5.420, 7.110, 7.110, 10.270 against B/q_min of 5.420, 7.110, 7.110,
10.270.

**P3 — confirmed.** The filter helps overwhelmingly on the below-crossover pair.
The predicted L(θ) of 1.97% is real — arm B settles at 10.270 against
p\* = 10.281 — but arm A settles at **10.96**, which is 0.679 above p\*,
**62× further away**. The funnel harm is theoretically real and practically
dominated by the agents' own failure.

**P4 — confirmed.** Median 1 round in both arms, against the pilot's median 2 on
the disclosed variant. `zone_position` is not the lever for negotiation length.

## The unregistered finding, and it is the strongest one

**Arm B's live welfare is exactly Ψ evaluated at the funnel point**, computable
from θ and the payoff model before any agent runs:

| pair | \|margin\| | Ψ(B/q_min)/Ψ\* predicted | measured | error |
|---|---|---|---|---|
| b0008\|c0003 | 0.011 | 0.9803 | 0.9803 | **0.0000** |
| b0001\|c0001 | 0.018 | 0.9606 | 0.9606 | **0.0000** |
| b0004\|c0002 | 0.022 | 0.8861 | 0.8861 | **0.0000** |
| b0005\|c0002 | 0.100 | 0.7319 | 0.7319 | **0.0000** |

Max error **0.0000** on four pairs, and the rank correlation of measured welfare
with |margin| is **−1.000**. Two results this project already had, composed:
the filter funnels every settled deal onto B/q_min (§7.1), and Ψ is the welfare
(§18). Together they determine arm B's welfare completely, with **no
contribution from the agents at all**.

## This corrects L(θ)

§21 defines L(θ) = Ψ\* − max{Ψ(x) : x ∈ C(θ)} and measures the dynamics term at
0.0000 — the *synthetic* dynamic reaches the constrained optimum. **Live agents
do not.** The filter funnels them to the boundary, not to the interior optimum,
so where the contract does not bind at p\* the realised loss is larger than
L(θ) says. For margins of +0.018 to +0.100, L(θ) = 0.0000 while the realised
loss is 0.039 to 0.268.

The corrected rule is simpler and now verified live to four decimals:

> **Realised welfare under enforcement is Ψ(B/q_min), so the welfare-optimal
> contract sets B/q_min = p\* exactly, and the loss is monotone in
> |B/q_min − p\*| — on either side.**

The sign asymmetry of §14 is a property of the *synthetic* comparison, where the
ungoverned baseline converges. Live, the ungoverned baseline is zero, so only
distance from the crossover matters.

## Limitations

- **Four pairs, one scenario, five seeds.** The 0.0000 agreement is not a
  statistical claim; it follows from arm B settling deterministically at the
  funnel point, which is itself the finding.
- **Arm A is degenerate here** (0.0000 everywhere), so this measures arm B's
  welfare well and the A→B contrast poorly. A disclosed scenario would vary arm
  A but then the buyer polices the boundary and arm B has nothing to add — the
  pilot showed exactly that. **No single scenario tests both**, which is a
  structural limit, not an oversight.
- **Authored scenario.** Tightening `zone_position` moved a fifth pair into the
  unsatisfiable class, so the harder bargain also destroyed a tradeable pair.
- Ψ is model-derived and inherits assumption C5 like every other payoff quantity.
