# Convergence, measured live at last — on arm C

**Date:** 2026-09-01
**Data:** `arm_c_bargain_v1..v5`, already on disk. **No API calls, no cost.**
**Code:** `experiments/analyse_trajectories.py` (bug fixed, see below) and
`experiments/fit_contraction.py` (new). Numbers in
`results/summary/contraction.json` (tracked).

## Reproduce

```bash
uv run python experiments/analyse_trajectories.py \
    --arms a_bargain b_bargain c_bargain
uv run python experiments/fit_contraction.py --arms c_bargain a_bargain
```

---

## Why this was never measured

The thesis says safety is demonstrated live and convergence is not. The reason
given is correct but incomplete: under enforcement the median negotiation is
**one round**, so arm B has no trajectory with three points and the question is
unanswerable there.

What nobody checked is whether some *other* arm has trajectories. Arm C does,
and the analysis never reached it because of a bug.

`analyse_trajectories.py` crashed on any arm containing a breaching state.
Φ_proj is deliberately NaN outside C(θ), that NaN serialises to `null` in
`section_11.json`, and `summarise` ran `np.diff` straight over the nulls —
`TypeError: unsupported operand type(s) for -: 'NoneType' and 'NoneType'`.
Arm B is the only arm whose states are always inside C(θ), which is why the
tool had only ever been run on A, B and D. Fixed by splitting each series at
its gaps and treating each defined run as its own sub-trajectory, so no step is
fabricated across an undefined round.

## Arm C has the trajectories, and they converge

Binding trajectories — seller proposals, exact structured terms:

| arm | traj | median length | ≥3 points | steps | down | fraction |
|---|---|---|---|---|---|---|
| A | 22 | 2 | 10 | 36 | 35 | 0.97 |
| B | 23 | **1** | **0** | 4 | 4 | — *(n = 4, says nothing)* |
| **C** | 23 | **9** | **16** | **144** | **143** | **0.99** |

Classified: arm C gives **15 monotone, 1 noisy-decreasing, 0 non-convergent,
7 too-short**. Arm A gives 9 monotone, 1 non-convergent, 12 too-short. Arm B
gives 23 too-short and nothing else.

Negotiation length is the cleanest statement of it — a count, needing no
dispersion estimate and no noise floor:

| arm | median | mean | max |
|---|---|---|---|
| A | 2 | 2.64 | 7 |
| B | 1 | 1.17 | 2 |
| **C** | **9** | **7.26** | **13** |

## The contraction rate, and the result that matters

Fitting d_k = f + (d₀ − f)ρ^k on every trajectory with ≥ 4 points:

| arm | trajectories fitted | median ρ | range | ρ² (contraction of V) |
|---|---|---|---|---|
| C | 16 | **0.624** | 0.576–0.787 | 0.390 |
| A | 3 | **0.621** | 0.475–0.771 | 0.386 |

**The rate is the same governed and ungoverned.** That is the finding. ρ is
stable across pairs, across seeds, and — to three significant figures — across
whether a contract is being enforced at all. Enforcement does not change how
fast a negotiation closes the gap to x\*_NBS. It changes **how many rounds
there are to watch**.

Stated for supervision: the observed dynamics contract at ρ ≈ 0.62 per round in
distance, ρ² ≈ 0.39 per round in V, and the contract is not what sets that rate.

The arm A figure rests on **3 trajectories** and is weak on its own. It is
reported because its agreement with arm C's 16 is the point; it would be worth
nothing as a standalone claim.

## They converge to a floor, not to the solution

Fitted floors are positive and pair-specific — 0.029 to 0.183 scaled units.
A representative trajectory:

```
1.075 → 0.690 → 0.455 → 0.315 → 0.235 → 0.185 → 0.155 → 0.135 → 0.125 → 0.115 → 0.110
```

So this is convergence **to a neighbourhood**, not asymptotic convergence to
x\*_NBS. The right formal object is a practical-stability / noise-ball
statement, which is also what the v1 prototype's F3 concluded when noise made
V decrease only in expectation. Anything stronger would be overclaiming.

## The catch, which belongs in the same breath as the result

**Arm C enforces the negotiated θ, and the negotiated θ is loose.** Its budget
row is 1.05–1.52× looser than the mandate on every pair. Measured against the
*mandate*, arm C's states are outside C(θ) almost throughout: of its 219
recorded rounds, **205 breach the mandate's budget row** and 15 the cost floor.
Φ_proj is correspondingly defined on only 14 of 167 rounds, against arm B's
27 of 27.

So this is **convergence under weak governance**. It is not a demonstration
that enforced negotiations converge, and it must not be written up as one.

That is not a footnote — it is the structure of the whole result:

> **A contract tight enough to make safety demonstrable is tight enough to
> destroy the trajectory convergence would be measured on. Arm B has perfect
> safety and no trajectory; arm C has a 13-round trajectory and breaches the
> mandate on 94% of rounds.**

The asymmetry the thesis leads with is therefore not a shortfall in the
experiment. It is a property of the regime, and it now has both halves
measured rather than one half asserted.

## What this changes in the write-up

1. **Chapter 1's asymmetry survives, but gains a positive half.** Convergence
   is no longer *only* proved on gradient-ascent proxies — there is live
   descriptive evidence, from 144 steps, with a fitted rate.
2. **The claim to make is bounded**: *offers contract geometrically toward the
   bargaining solution at ρ ≈ 0.62 per round, to a positive floor, on the arm
   whose contract does not pin the opening.* Not "enforced negotiations
   converge".
3. **The tension above is new material** and is the honest reason the two
   certificates cannot both be demonstrated on one arm.

## Limitations

- **Descriptive, not a test of the theorem.** Live agents run no step-size
  schedule, so ρ is the rate the observed dynamics happen to contract at, not
  the certificate's α. Outline G4 remains open.
- **n = 5 seeds × 3 customers**, as everywhere. 16 fitted trajectories come
  from 5 distinct pairs.
- **A two-parameter fit on 4–13 points.** The floor is found by grid search on
  the residual; no confidence interval is claimed for either parameter.
- **Arm A's ρ rests on 3 trajectories.** Suggestive, not established.
- The distance metric is `dist_M` against `PayoffModel.from_scenario`, whose
  bargaining zone on this scenario is only a pound or two wide — the same
  calibration caveat as the 2026-08-06 note.
