# The rational-seller floor, and live agents below it

**Date:** 2026-09-06
**Data:** analytic, plus re-analysis of stored live runs. **No API calls, no cost.**
**Code:** `experiments/bargaining_family.py`. Numbers in
`results/summary/bargaining_family.json` (tracked).
**Depends on** `2026-09-06-potential-and-lyapunov.md` for Ψ = P·W.

## The question

§5.3 attributes the harm-averted result to **buyer passivity, not seller
aggression**. That is right about the mechanism and stops one step short of the
consequence. If the buyer is merely passive, how bad can the outcome be? A
seller maximising its own expected payoff has an incentive to moderate: pushing
the transfer further collapses its own probability of a deal. So passivity
alone should have a floor.

## The model

Weight the buyer's gradient by its engagement α:

    F_α = α ∇Û_B + ∇Û_S = ∇( P (α U_B + U_S) )

The potential structure survives, with Ψ_α := P(αU_B + U_S). α = 1 is the
formulation's joint field and rests at the symmetric bargaining solution
(Proposition 1). α = 0 is a buyer that exerts **no bargaining pressure at all**.

Rest points on the reference calibration:

| α | rest p | U_B | U_S | buyer's share | Ψ/Ψ\* |
|---|---|---|---|---|---|
| 1.00 | 8.500 | 120.60 | 120.60 | 0.500 | 1.0000 |
| 0.50 | 8.916 | 78.97 | 162.23 | 0.327 | 0.9504 |
| 0.15 | 9.193 | 51.26 | 189.94 | 0.213 | 0.8655 |
| **0.00** | 9.293 | 41.26 | 199.94 | 0.171 | **0.8258** |

Engagement maps monotonically onto the surplus split. Disengagement is
observationally a bargaining-power asymmetry.

## Result 1 — the floor is a constant of the framework

Price is a pure transfer, so with (q, d) efficient the problem is
one-dimensional in the transfer. Writing u := U_S/λ and k := W/λ,

    Ψ(u)/W = σ(k − u)·σ(u),      symmetric split at u = k/2,

and a passive buyer lets the seller maximise Ψ·U_S. The resulting ratio depends
**only on k**, not on the scenario:

| k = W/λ | 1 | 2 | 3 | **4** | 6 | 12 | 20 |
|---|---|---|---|---|---|---|---|
| floor Ψ/Ψ\* | 0.9434 | 0.8240 | 0.8001 | **0.8258** | 0.8522 | 0.9026 | 0.9420 |

The calibration used throughout sets λ = W_max/4, so k = 4 and the floor is
**0.825817**. Every live pair returns 0.8258 numerically, against p\* ranging
5.680 to 10.423 — the invariance is structural, not a coincidence.

> **A seller facing a buyer that pushes back not at all still delivers 83% of
> the joint optimum**, because pushing the transfer further collapses its own
> probability of a deal.

## Result 2 — the live outcomes are outside the family

| scenario | pair | observed Ψ/Ψ\* | family min | outside? |
|---|---|---|---|---|
| bargain | b0001\|c0001 | 0.6193 | 0.8258 | **yes** |
| bargain | b0002\|c0001 | 0.2804 | 0.8258 | **yes** |
| bargain | b0004\|c0002 | 0.5451 | 0.8258 | **yes** |
| bargain | b0005\|c0002 | 0.6916 | 0.8258 | **yes** |
| bargain | b0008\|c0003 | 0.3926 | 0.8258 | **yes** |
| undisclosed | all five | 0.0000–0.0001 | 0.8258 | **yes** |

**10 of 10 pair-scenarios fall below the floor.** No buyer engagement weight in
[0, 1] — from fully engaged to wholly passive — produces an outcome as bad as
the live agents reach.

## What this means

The live failure is **not weak bargaining**. It is not in the image of the
bargaining model at all. The seller's self-limitation is real, but it is
contingent on the buyer *refusing*: a counterparty that accepts anything removes
the seller's reason to moderate, and the floor that self-interest would
otherwise supply disappears.

So the sharpest statement of what enforcement buys is not "it saves £21.70". It
is:

> **Enforcement substitutes for refusal.** A rational seller moderates only
> because a rational buyer would walk away. Where the buyer will not, the
> contract is the only thing left that makes the seller's own interest
> protective.

That reframes §5.3 and §8.1 without changing a single measured number.

## Limitations

- **λ = W_max/4 is a modelling choice**, not measured. The floor is 0.80 to
  0.94 across k ∈ [1, 20], so the *existence* of a floor near 0.8–0.9 is robust
  while 0.826 is specific to that choice. The table above is the sensitivity.
- **Ψ is model-derived** (assumption C5), from the same per-pair calibration the
  drift analysis uses.
- **α ∈ [0, 1] is the interpretable range.** Extending α below zero — a buyer
  actively acting against its own interest — does eventually reach the observed
  values, but a negative bargaining weight is not a behaviour, and the
  unbounded-price limit makes the test vacuous.
- **Final governed state**, not the replayed settled deal.
