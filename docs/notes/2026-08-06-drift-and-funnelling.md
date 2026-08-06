# Do offers drift toward the Nash solution, and does the contract funnel them?

**Date:** 2026-08-06
**Data:** `arm_{a,b,d}_bargain_v1..v5` — already on disk. **No API calls.**
**Answers supervision asks (1) and (2) of 2026-08-06.**

## Reproduce

```bash
uv run python experiments/analyse_trajectories.py --arms a b d
```

Output is written to `results/summary/trajectories.json`, which is tracked.

---

# Question 1 — do the offers drift toward the bargaining solution?

**Yes, clearly, on the measure that works — and the measure the formulation
would have you use does not work here.**

## What this can and cannot show

Descriptive only. Live agents have no step-size schedule, so a decrease
fraction is **not** a test of the convergence theorem (outline G4); that
theorem is about a specific dynamic these agents are not running. The question
is the weaker one: do observed negotiations move toward x\*_NBS at all?

## Distance to x\*_NBS falls, on almost every step

Binding trajectories — seller proposals only, exact terms:

| arm | trajectories | median length | ≥3 points | steps | steps down | fraction |
|---|---|---|---|---|---|---|
| A | 22 | 2 | 10 | 36 | 35 | **0.97** |
| D | 25 | 2 | 5 | 26 | 26 | **1.00** |
| B | 23 | 1 | **0** | 4 | 4 | 1.00 *(n = 4, says nothing)* |

Classified: arm A gives 9 monotone, 1 non-convergent, 12 too short; arm D gives
5 monotone, 20 too short. **Arm B has no trajectory with three points**, so the
question is not answerable there at all — see question 2, where that is the
finding rather than the obstacle.

Mean distance falls from **0.969 → 0.286** scaled units (arm A) and
**1.002 → 0.325** (arm D).

## The part that is not mechanical

A seller conceding downward from list price will approach *any* target below
it, so the *direction* proves little on its own. What is not mechanical is
where it stops: only **3 of 18** arm-A trajectories and **4 of 21** arm-D
trajectories overshoot past the NBS price. Roughly 82% approach it and halt
before crossing.

That is the honest content of "the pair moves toward the Nash equilibrium
during the discussion": they approach it and stop near it, rather than
conceding through it.

## Φ is unusable as a convergence diagnostic here, and here is why

Measured on the same binding trajectories, Φ *rises*:

| arm | steps | fraction decreasing | fraction ending lower |
|---|---|---|---|
| A | 36 | 0.36 | 0.06 |
| D | 26 | 0.19 | 0.00 |

Distance falls on 97% of steps while Φ falls on 36%. They disagree, and Φ is
the one at fault. **Φ has a second zero far from the deal.** Sweeping price for
`business_0001|customer_0001` (NBS at p = 5.68):

| price | P(accept) | Φ |
|---|---|---|
| 5.18 | 0.009 | 0.24 |
| 5.58 | 0.639 | 2.25 |
| **5.68** | 0.776 | **0.00** |
| 5.78 | 0.639 | 1.56 |
| 6.18 | 0.009 | 0.16 |

Far from agreement, acceptance is hopeless, so Û = P·U is flat and *both*
gradients vanish — the field is zero because nobody has any incentive, not
because everyone is satisfied. Φ therefore rises and then falls as a
negotiation comes in from a far start, and "Φ ended higher than it started" is
the expected geometry rather than evidence of non-convergence.

This sharpens formulation §5's "locally Φ ≈ L‖x − x\*‖" into something
concrete and operational: **Φ is a merit function only inside the certified
monotone radius (≈ 1 scaled unit), and these trajectories begin at 0.97–1.00 —
right at its edge.** Using Φ as a live convergence diagnostic without checking
that the state is inside that radius will produce exactly the wrong reading.

## A bug this analysis found

`phi_projected` selected constraint rows with `h_i ≤ tol`, which includes rows
the state has already **violated**. Projecting onto the tangent cone of a
constraint you are outside is meaningless, and the function returned a
confident number at breaching states — reading **0.00 at the opening of nearly
every ungoverned negotiation**, which looks like instant convergence and is an
artefact.

Fixed: active now means `|h_i| ≤ tol`, and Φ_proj returns **NaN** outside
C(θ), because a state in breach needs recovery rather than convergence and
NaN propagates loudly through any aggregate that forgets to exclude it. Two
existing tests failed on the fix — both had fixtures sitting outside their own
contract's deadline band and passing only because the old code never checked.

The corrected statistic is itself a clean expression of the safety result:

| arm | rounds with the state inside C(θ) |
|---|---|
| A | 12 / 58 (21%) |
| D | 14 / 51 (27%) |
| **B** | **27 / 27 (100%)** |

---

# Question 2 — does the contract funnel outcomes?

**Yes, decisively — and more strongly than "narrow". It collapses them to a
single point.**

Dispersion is computed **within pair across seeds**, never pooled across
customers: the three customers buy different baskets at different price levels,
so a pooled spread would mostly measure the scenario.

## Settled outcomes

| arm | pairs | SD price | SD quantity | SD overall | SD distance-to-NBS |
|---|---|---|---|---|---|
| A | 5 | 0.384 | 0.009 | 0.384 | 0.344 |
| D | 5 | 0.386 | 0.000 | 0.386 | 0.355 |
| **B** | 5 | **0.000** | **0.000** | **0.000** | **0.000** |

Arms A and D are behaviourally identical, so their difference — **0.002** — is
the noise floor. Arm B's reduction is **0.384**, about 190× that.

Per-round proposals show the same thing: SD 0.504 (A), 0.449 (D), **0.000** (B).

## Not "narrower" — identical, and to a point the contract chooses

Every settled price under arm B is exactly the same number across every seed:

| pair | settled price (all seeds) | B / q_min |
|---|---|---|
| `business_0001\|customer_0001` | 5.785 ×4 | 5.790 |
| `business_0002\|customer_0001` | 5.785 ×5 | 5.790 |
| `business_0004\|customer_0002` | 7.450 ×5 | 7.450 |
| `business_0005\|customer_0002` | 7.450 ×4 | 7.450 |
| `business_0008\|customer_0003` | 10.460 ×5 | 10.460 |

**The funnel point is θ's budget boundary**, to the cent. The mechanism is
plain: the budget is the binding row, the filter projects onto it, quantity is
pinned at the customer's basket, so p = B/q_min is a single number fixed by θ
before any agent says anything.

## The answer to Pietro's framing, stated carefully

*Does the interaction plus the contract push the players toward a specific
result?* **Yes — and the contract, not the interaction, picks which result.**

That is double-edged and both edges belong in the dissertation:

- **Powerful.** A contract designer can steer the outcome precisely by choosing
  θ. Not "influence" — determine, to the cent, across every seed.
- **Cautionary.** The filter is not a neutral referee. It funnels to the
  *constraint boundary*, which is where the buyer spends its entire budget —
  not to the bargaining solution. Arm B's settled terms look closer to x\*_NBS
  (0.085 against arm A's 0.221) only because on this calibration the boundary
  happens to sit ~0.11 scaled units from the NBS. **That is a coincidence of
  `bargain_3_9`, not a property of the mechanism**, and a scenario where the
  budget binds far from the efficient split would show the filter pushing the
  outcome away from the bargaining solution.

## The compression is the cleanest evidence

| arm | median length | mean | max |
|---|---|---|---|
| A | 2 | 2.64 | 7 |
| D | 2 | 2.04 | 3 |
| **B** | **1** | **1.17** | **2** |

Under enforcement the negotiation barely happens: the opening proposal is
projected onto the boundary and there is nothing left to haggle over. This
needs no dispersion estimate and no noise floor — it is a count.

It is also **why question 1 is unanswerable for arm B**, and the two facts are
the same fact. Enforcement funnels the outcome by removing the negotiation, so
there is no trajectory left to test for convergence.

## Limitations

- **n = 5 seeds × 3 customers.** Everything here is five draws of three
  situations. The funnel effect is ~190× the A/D noise floor and survives
  easily; the drift result rests on 36 and 26 steps respectively and is
  descriptive.
- **The zero dispersion is partly definitional.** With arm B's median
  trajectory length of 1, the "settled" point often *is* the projected opening
  offer, and projection onto a fixed boundary from any starting point lands on
  the same place. That does not make it less true — it explains the mechanism —
  but it means the result is about projection, not about negotiation dynamics.
- **The funnel point is scenario-specific.** `bargain_3_9` has the budget
  binding; a scenario where a different row binds would funnel elsewhere, and
  one where nothing binds would not funnel at all.
- Distances use `PayoffModel.from_scenario`, whose surplus on this scenario is
  £0.25–0.60 against the formulation's reference of £241. The calibration is
  self-consistent (P(x\*) = 0.776 against the reference's 0.778) but the
  bargaining zone really is only a pound or two wide.
