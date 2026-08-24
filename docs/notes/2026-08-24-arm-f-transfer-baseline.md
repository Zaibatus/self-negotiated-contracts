# Arm F — the contract as a reward transfer (Christoffersen et al. baseline)

**Date:** 2026-08-24
**Status: IMPLEMENTED, NOT RUN.** No live experiment has been executed and no
money has been spent. Everything below the "Registered predictions" heading is a
prediction, not a measurement, and must not be cited as a result.
**Closes** the open supervision question in `chapters/02-related-work.md`
("implement-vs-compare for the Christoffersen baseline") on the *implement*
side, and item 6 of the remaining-work list in chapter 8.
**Reference:** Christoffersen, Haupt & Hadfield-Menell, "Get It in Writing:
Formal Contracts Mitigate Social Dilemmas in Multi-Agent RL", AAMAS 2023
(arXiv:2208.10469v3). Code MIT-licensed at
`github.com/Algorithmic-Alignment-Lab/contracts`, built on RLlib.

## Reproduce

```bash
# scenario generation is YAML only — offline, free
uv run python scripts/make_transfer_scenario.py \
    --source data/bargain_3_9 --dest data/transfer_3_9

uv run pytest tests/test_transfers.py -q      # 22 tests, offline

# the live arm — NOT YET RUN, costs money, needs approval first
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts
for i in 1 2 3 4 5; do
  uv run python experiments/arm_f_transfer.py --data data/transfer_3_9 \
      --t-max 6 --experiment "arm_f_v$i" --override
done
```

## Why implement it at all

Chapter 2 differentiates the two mechanisms in one line — *reward transfers make
the good outcome an equilibrium; this work bounds every intermediate step* — and
until now that was a conceptual claim about a paper rather than a measurement.
It is also the comparator an AAMAS reviewer will name first, since Christoffersen
et al. is an AAMAS paper and its code is public.

## What was ported, and what could not be

Their Definition 2.2: a contract is a function `(S x A) u {acc} -> R^N` whose
range is zero-sum. Reward becomes `R'((s,theta),a) = R(s,a) + theta(s,a)`.
Theorem 3.1: with a sufficiently rich contract space, all subgame-perfect
equilibria of the augmented game are jointly optimal.

**Note the notation collision.** Their `theta` is a transfer function; ours is
the constraint vector `(B, c, q_min, q_max, d_min, d_max)`. `transfers.py` uses
`theta` for ours only and names theirs `transfer`/`schedule` throughout.

Ported faithfully: zero-sum (pinned by a property test over a grid),
state-dependent on the proposed terms, bounded by an optional `cap` playing the
role of their `R_max/(1-gamma)` richness bound, pre-specified and binding.

**Not ported, because the substrate will not carry it:**

1. **The learning loop.** Their agents are RL policies that maximise expected
   discounted reward; Theorem 3.1 is a statement about what such agents converge
   to. An LLM here has no reward channel and no training loop. There is nothing
   for a transfer to act on except the agent's reading of its own instructions.
2. **Unanimous acceptance as a game stage.** Their augmented game has a proposer
   stage, an `acc` action, and rejection returning the null contract. Here the
   schedule is disclosed and acceptance is *assumed*.

**Both omissions favour the baseline, deliberately.** It is handed the agreement
its mechanism would otherwise have had to earn, and an unbounded transfer is
richer than its own theorem requires. If it still bounds nothing, that is not an
artefact of a weak port.

## The one channel a transfer has

With no reward signal, the schedule reaches the agents the only way anything
reaches an LLM: as text in context, via scenario YAML — the same mechanism
`make_bargain_scenario.py` uses for the budget. The marketplace, agent classes
and prompt templates stay stock.

This costs the baseline the property the filter has. Enforcement at the protocol
never touches an agent; a transfer must be *told* to one. Chapter 2 already
measures what instruction delivers on this testbed: 86% of proposals still
breach.

## Verified before use

Same standard the undisclosed scenario got. `transfer_3_9` is generated from
`bargain_3_9` with the clause appended to every business description and every
customer request, and nothing else touched:

| check | result |
|---|---|
| theta identical on all 9 pairs | **yes** |
| unsatisfiable set identical (4 of 9) | **yes** |
| `menu_features` untouched | **yes** |
| clause reaches the buyer | yes |
| clause reaches the seller | yes |
| budget named in the clause == B in theta | yes |

Pinned in `tests/test_transfers.py::TestTheScenarioPreservesTheta` rather than
checked once by hand. If a future edit to the generator starts moving
`menu_features`, arm F silently stops being a mechanism comparison and becomes a
scenario comparison.

Arm F runs the regulator in **`monitor`** mode. That is not a shortcut: a
transfer prices a breach rather than intercepting one, so it must not touch the
message path. Arms D and F therefore share a code path and differ only in the
scenario, which makes the clause the only thing any difference can be
attributed to.

## The baseline cannot be instantiated on `undisclosed_3_9` at all

**This is a result, and it costs nothing to establish.**

`undisclosed_3_9` is defined by withholding the budget from the buyer, and it is
the only scenario where enforcement averts measurable harm (£21.70 -> £0.00 on
governable pairs). A transfer schedule must state its own trigger: *"if the
total exceeds $X, the seller pays the buyer the excess."* Writing that clause
tells the buyer X. The moment the baseline is instantiated the scenario collapses
into the disclosed one, and the comparison measures the disclosure rather than
the mechanism.

This is arm C's structural failure arrived at from the other direction. A
self-negotiated contract cannot be formed when the buyer states no position
(0 of 105 buyer messages name a price); a transferred contract cannot be stated
when the constraint is the thing being withheld. **Both alternatives to
protocol-level enforcement require the constraint to be common knowledge — which
is exactly the case where enforcement is least needed.**

That generalisation is the most quotable thing in this note and it follows from
what the scenarios are, not from any run.

## Registered predictions — before any run exists

Reproduced from `experiments/arm_f_transfer.py`'s docstring so they cannot be
retrofitted.

1. **Offered breach stays in arm A/D territory** (0.82–0.86), not arm B's 0.472.
   A transfer changes the payoff of a breach; nothing in the message path
   changes.
2. **Settled breaches stay above zero.** Load-bearing: arm B settles 0.000, and
   the thesis claim is that a per-round bound is what buys that.
3. **Residual overspend stays above zero** even though the buyer is made whole
   in currency. A transfer redistributes; it does not prevent. **If overspend
   reaches zero here, the thesis's central contrast is weaker than claimed and
   chapter 5 must say so.**
4. **Some effect on settled terms is plausible anyway**, because an informed
   buyer told the seller must repay any excess has one more reason to hold out.
   If arm F beats arm D on settled breaches, that is the baseline working
   through the only channel it has — instruction — and should be reported as
   such, not as enforcement.

Prediction 4 is the honest version of "does the baseline do anything at all",
and *yes, a little* would not threaten the thesis.

## Cost, and what is still needed

5 seeds on `transfer_3_9` is the same shape as any other arm: ~5 runs, on the
order of £0.50 at the ~£0.10/run implied by the arm C-meet study (11 runs,
~£1.10). **Under the ~£5 threshold, but it has not been approved and has not
been run.**

Outstanding before this becomes a result:

- [ ] Approve and run the 5 seeds.
- [ ] Add arm F to the chapter 5 five-arm table, and to `SCIENCE.md` §5–6.
- [ ] Rewrite chapter 2's *"Whether to implement it or compare conceptually
      remains an open question"* and chapter 8's remaining-work item 6, both of
      which currently say the comparison is conceptual.
- [ ] Decide whether a rate above 1.0 is worth a second cell. At rate 1.0 a
      breach is exactly break-even for the seller, which is the weakest schedule
      that removes the gain; a punitive rate tests whether the baseline works at
      all when it is made harsher, and is the obvious reviewer question.
