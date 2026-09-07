# Fuzzing the enforcement path: what 60,000 sampled contracts find

**Date:** 2026-08-28
**Data:** synthetic. **No API calls, no marketplace, no cost.**
**Code:** `experiments/fuzz_safety.py`. Numbers in
`results/summary/fuzz_safety.json` (tracked).

## Reproduce

```bash
uv run python experiments/fuzz_safety.py --draws 60000 --seed 20260828
```

---

## Why

Every safety number in the thesis has the form *0 breaches of N governed
rounds*: 0/27, 0/126, 0/100. Those are observations of the situations three
customers and five seeds happened to produce. They are not evidence about the
**mechanism**, because the agents never proposed a large single-round jump,
never drove a safe set down to a sliver, and never moved quantity.

This samples the shipped code directly — `DCBFFilter`, `project_into_safe_set`
and `rewrite_proposal`, imported rather than reimplemented — over randomly
drawn contracts, states and proposed moves, in four regimes: `wide` (roomy
budgets), `tight` (the satisfiability boundary crowded), `degenerate` (safe set
a single point, which is what θ_negotiated ∧ θ_mandate produces on 16 of 17
`bargain_3_9` meets) and `jump` (single-round moves of order the state itself).

Two thresholds, because conflating them would make the whole exercise cry wolf:
**failed** is any violation past `is_safe`'s 1e-6, and **material** is past
1e-3, an order of magnitude inside the smallest breach that can exist on a wire
that quantises to the cent.

## Result

| property | tested | failed | material | worst h |
|---|---|---|---|---|
| P1 projection lands in C(θ) | 60000 | **0** | **0** | −1.0e−07 |
| P2 step from inside C stays in C | 60000 | 33287 | **3257** | **−0.575** |
| P3 true h honours the DCBF inequality | 60000 | **0** | **0** | −9.4e−08 |
| P5 something in FilterResult flags the exit | 60000 | 33220 | 3241 | −0.575 |

**P1 and P3 are clean and that is a real result.** `project_into_safe_set`
never returned a point outside C(θ) in 60,000 draws including degenerate sets —
the routine bug 7 broke is now sound. And the barrier inequality itself,
verified against the exact bilinear h rather than the linearisation, held to
1e−7 every time. The backtracking machinery does what it says.

**P2 is the finding, and P3 is why it is subtle.** The two disagree by
construction. P3 asks whether the step honoured
h(x⁺) ≥ (1−γ)h(x) − *slack*; P2 asks whether the state is still in the safe
set. A filter degrading gracefully onto slack passes the first and fails the
second. That is what graceful degradation *means*, and the headline "zero
breaches" does not distinguish them.

## Where the material breaches actually come from

| regime | material / 15000 | rate |
|---|---|---|
| wide | 66 | 0.44% |
| tight | 411 | 2.74% |
| degenerate | 563 | 3.75% |
| **jump** | **2217** | **14.78%** |

**Large single-round jumps dominate, and that inverts the obvious reading.**
Ranked by *raw* failures the order is degenerate (14884) > tight (11766) >
jump (4213): degeneracy produces the most exits. Ranked by *material* failures
the order reverses — degeneracy produces many exits of order 1e−5, and jumps
produce fewer exits of order 1e−1.

This is the attack surface `Contract.grad_h` names in its own docstring:

> d(B − p·q)/d(p, q) = (−q, −p): valid for the small per-round adjustments
> typical of negotiation. Large single-round jumps are a stated attack surface
> (formulation.md section 7.4); **the filter backtracks on the true h to close
> it.**

The backtrack does not close it. It closes the *inequality* (P3: 0/60000) and
not *set membership* (P2: 14.8% materially, in this regime). The claim in
`formulation.md` §7.4 should be narrowed to what is true.

## Which row breaks

Among material P2 failures: `cost_floor` 2023, `q_min` 1230, `q_max` 11.

**The budget row never breaks.** Not once. That matters more than the rest of
this note, because the budget row is the entire empirical centrepiece — the
£21.70 → £0.00 result and every overspend number are budget-row facts. What
leaks is the *lower* bounds: price below the seller's cost floor, quantity
below the customer's minimum.

That asymmetry is structural rather than lucky. The budget row `B − p·q` is the
one the QP linearises, so it is the one the backtrack was written to verify;
the lower bounds are exactly linear, get no special attention, and are where
the slack goes.

## Slack is not the discriminator

The first hypothesis was that slack use explains the exits. It does not:
slack was active on **100%** of steps that left C and on **90.1%** of steps that
stayed, at comparable magnitude (9.1e−04 against 1.6e−03). Slack is how the QP
routinely operates. What decides the outcome is whether the margin available —
h at the current state — is larger than the slack the QP takes.

## The wire

`rewrite_proposal` was fuzzed as the composition that actually reaches the
counterparty. Two regimes, and only one of them is real:

- **quantity unrounded (98 draws): 46 material breaches.** Rare in this fuzzer
  because a random u almost always moves quantity off an integer.
- **quantity rounded (59902 draws): 22225 material breaches**, worst −26.0.
  `_repair_quantisation` nudges *price* by cents and explicitly gives up on
  quantity and deadline rows, so a rounded quantity carries its budget breach
  through untouched.

**Live this never fires**, and the reason is worth stating rather than
assuming: quantity is the customer's basket, the filter never moves it, and
every arm B settled quantity has SD 0.000. The hole is real and currently
unreachable. It becomes reachable the moment a scenario lets quantity be
negotiated, which is exactly what a "generalise beyond one basket" reviewer
would ask for.

## What this changes in the write-up

1. **The safety claim needs one qualifying clause.** Not "zero breaches" but
   *zero breaches of the budget row, under the per-round moves live agents
   make*. Both qualifiers are supported by everything already in `SCIENCE.md`;
   neither is currently stated.
2. **`formulation.md` §7.4 overstates the backtrack.** It closes the barrier
   inequality, not set membership under large jumps. Mark corrected.
3. **There is no observability of an exit from C.** `certificate_gap` is set
   only when the *solver* fails (`dcbf.py:400`), so a step that solved cleanly
   and left the safe set is silent. This is the same shape as the five
   integration bugs — a plausible surface nobody asserted on — and the cheap
   fix is a post-hoc `is_safe` check on the applied state, recorded per round.
   P5 is not a broken promise; it is the absence of a signal the safety claim
   needs.

## Limitations

- **A property test, not a proof.** It reports "no counterexample in N draws"
  and nothing stronger. P1 and P3 passing 60,000 draws is evidence, not a
  theorem.
- **The sampler is mine, not the marketplace's.** The contract distribution is
  chosen to be adversarial and does not claim to be the distribution real
  scenarios induce. The `wide` regime is the closest to live, and it is also
  the mildest: 0.44%.
- **Deadline rows are active in 70% of draws.** `ContractSpec.deadline_active`
  defaults to False, so the live scenarios likely do not exercise them at all,
  and the deadline breaches in the wire table are correspondingly less
  relevant than they look.
- The `jump` regime proposes moves of order the state itself. Real sellers do
  not do this. An adversary would, and the exploitation experiment sketched
  against Fabraix is exactly that threat model.
