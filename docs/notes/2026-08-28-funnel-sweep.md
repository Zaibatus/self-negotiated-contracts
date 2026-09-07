# Where the filter funnels to, as θ's boundary moves

**Date:** 2026-08-28
**Data:** synthetic. **No API calls, no marketplace, no cost.**
**Code:** `experiments/funnel_sweep.py`. Numbers in
`results/summary/funnel_sweep.json` (tracked).
**Closes** the untested conjecture in `docs/notes/2026-08-06-drift-and-funnelling.md`.

## Reproduce

```bash
uv run python experiments/funnel_sweep.py --seeds 200 --points 17
```

---

## The claim being tested

The funnelling note establishes that arm B collapses every settled price onto
θ's budget boundary, and then asserts something it never tested:

> Arm B's settled terms look closer to x\*_NBS (0.085 against arm A's 0.221)
> only because on this calibration the boundary happens to sit ~0.11 scaled
> units from the NBS. **That is a coincidence of `bargain_3_9`, not a property
> of the mechanism**, and a scenario where the budget binds far from the
> efficient split would show the filter pushing the outcome away from the
> bargaining solution.

That aside is load-bearing. It is the only thing standing between "the filter
improves outcomes" and "the filter improved outcomes here, by luck". Live it
cannot be tested — it needs `menu_features` rewritten and the marketplace
re-run, and the experimental programme is closed. In simulation it is one
sweep.

The dynamic is the concession field the formulation assumes,
x_{k+1} = x_k + η F(x_k) + noise, whose rest point is x\*_NBS by Proposition 1.
So a negative result cannot be blamed on the agents: these agents are running
exactly the dynamic the theory is about. Quantity is pinned (q_min = q_max)
because that is what the live scenarios do — every arm B settled quantity has
SD 0.000.

## Result — the conjecture holds, and the effect is large

x\*_NBS = (8.5, 100, 26), p\* = 8.500, 200 seeds per budget.

| B/q_min | vs p\* | unfiltered d | filtered d | verdict | filtered price SD |
|---|---|---|---|---|---|
| 6.12 | −2.38 | 0.058 | **2.899** | **50× worse** | 0.0000 |
| 7.06 | −1.44 | 0.058 | 1.940 | 33× worse | 0.0000 |
| 7.99 | −0.51 | 0.058 | 0.727 | 13× worse | 0.0000 |
| 8.46 | −0.04 | 0.058 | 0.066 | slightly worse | 0.0022 |
| 8.93 | +0.43 | 0.058 | 0.039 | better | 0.0222 |
| 10.80 | +2.30 | 0.058 | 0.039 | better | 0.0217 |
| 13.60 | +5.10 | 0.058 | 0.040 | better | 0.0236 |

**Of 17 budgets, the filter helps on 11 and hurts on 6, and the harm is
unbounded while the help is not.** Where it helps, it recovers 0.058 → 0.039 —
a third. Where it hurts, it costs up to 50×, and the cost grows linearly with
how far below p\* the boundary sits. There is no budget at which the filter
helps by more than a rounding error, because the unfiltered dynamic already
converges: free distance is 0.058 at every budget, since ungoverned agents
never see θ.

**The crossover is at the boundary, not near it.** The filter stops hurting
exactly where B/q_min passes p\*. `bargain_3_9`'s boundary sits ~0.11 scaled
units from the NBS — inside the narrow band around the crossover. The 2026-08-06
note's instinct was right and can now be stated as a measurement rather than a
suspicion.

## Two mechanism confirmations

**Zero dispersion is caused by binding, not by enforcement.** Filtered price SD
is exactly **0.0000** at every budget where the boundary binds below p\*, and
≈ 0.022 — indistinguishable from the unfiltered 0.0208 — at every budget where
it does not. This is the sharper form of the 2026-08-10 qualification: *which*
point outcomes collapse to is the result; *that* they collapse is not, and here
they do not collapse at all when the filter has nothing to bind on.

**The funnel point is θ's boundary to the cent.** Mean settled price tracks
B/q_min to within 0.001 at every binding budget, reproducing the live table
(5.785 against B/q_min = 5.790, and so on) in a setting where the boundary is
swept rather than fixed.

## The unexpected part: the filter displaces terms it does not constrain

The contract used here has `deadline_active=False`. It says nothing whatsoever
about delivery. The deadline is nevertheless dragged away from its efficient
value, monotonically, by how hard the *price* row binds:

| B/q_min | settled deadline | d\* |
|---|---|---|
| 6.12 | **17.74** | 26 |
| 7.06 | 19.53 | 26 |
| 7.99 | 23.41 | 26 |
| 8.93 | 26.01 | 26 |
| unfiltered, any budget | 26.00 | 26 |

At the tightest budget the deadline lands **8.3 days early on a term the
contract never mentions**. The decomposition is exact: total displacement 2.899
= √(2.38² price + 1.652² deadline), so **roughly a third of the squared
displacement is on the unconstrained coordinate**.

The mechanism is that pinning price off its efficient value moves the rest
point of the *remaining* coordinates — the constrained equilibrium is not the
unconstrained one restricted to the boundary. This is the same phenomenon as
the v1 prototype's F5 finding, where coupling moved the agreement point to the
generalised Nash equilibrium and a certificate anchored at the old point read
false instability. It is also the cleanest available argument for why the
thesis's central tool has to be equilibrium-independent: the equilibrium the
system actually reaches depends on the contract, and has no closed form.

## What this changes in the write-up

1. **The 2026-08-06 conjecture becomes a result.** Cite this note, not the
   aside. The cautionary half of the funnelling finding is now measured:
   50× at the extreme, with the crossover at B/q_min = p\*.
2. **State the limitation as a property of the mechanism, not of the
   scenario.** "The filter funnels to the constraint boundary, which coincides
   with the bargaining solution only by construction of this scenario" is now
   supported end to end.
3. **New: enforcement is not confined to the rows it constrains.** A contract
   that binds price relocates the deadline. Nothing in the current write-up
   anticipates this, and it is a real cost of enforcement that the safety
   numbers cannot show.

## Limitations

- **Scripted agents.** This says nothing about whether LLMs converge — that
  question is untouched and remains open. What it tests is a property of the
  *mechanism*, given that outcomes collapse onto the boundary.
- **One calibration.** The reference payoff model, one opening position
  (p\* × 1.5), one noise level, quantity pinned. The *shape* of the result —
  linear harm below the boundary, inert above — follows from projection and
  should be robust; the 50× is specific to how far the sweep runs.
- **η = 1e−2 with the SCALE² preconditioner** was chosen because it converges
  to x\* exactly (d = 0.0000 noise-free). At η = 2e−4 the free dynamic had not
  converged within T_max and every budget read as "the filter helps", which was
  an artefact of comparing against a runaway. Worth recording: the first
  version of this sweep produced a clean, interpretable and entirely wrong
  answer, for the same reason as integration bug 6.
- The deadline displacement is measured at settlement, not proved. A closed
  form for the constrained rest point would be a genuine addition and is not
  attempted here.
