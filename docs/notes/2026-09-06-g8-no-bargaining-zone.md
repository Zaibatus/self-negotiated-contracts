# G8 answered: the permitted trades are the ones with nothing to permit

**Date:** 2026-09-06
**Data:** analytic, cross-referenced against stored arm summaries.
**No API calls, no cost.**
**Code:** `experiments/no_bargaining_zone.py`. Numbers in
`results/summary/no_bargaining_zone.json` (tracked).

## The open question

Chapter 7 §7.4.2 leaves G8 open — whether a platform that detects a trade it
knows cannot comply should **refuse** it, or merely decline to filter and let
it settle. It frames refusal as costly:

> "It would also mean a platform refusing to let two willing parties transact,
> on the basis of a constraint neither of them stated, which is a considerable
> power to assert."

## The observation

The pairs in question are exactly the pairs `PayoffModel.from_scenario`
refuses to build for, and its own docstring gives the reason:

> "a buyer whose reservation price is at or below the seller's cost has nothing
> to negotiate about … **any agreement destroys surplus**"

Unsatisfiability of θ (c·q_min > B) and absence of a bargaining zone (r ≤ c)
are **the same condition read two ways**, because B is built from the same
`menu_features` that give r, and the cost floor from the same
`min_price_factor` that gives c.

| pair | r | c | r − c | qty | surplus per deal |
|---|---|---|---|---|---|
| b0003\|c0001 | 5.790 | 6.023 | −0.233 | 2 | **−0.466** |
| b0006\|c0002 | 7.450 | 9.266 | −1.816 | 1 | **−1.816** |
| b0007\|c0003 | 10.460 | 11.759 | −1.299 | 3 | **−3.898** |
| b0009\|c0003 | 10.460 | 14.005 | −3.545 | 3 | **−10.635** |

Every one is negative-sum. There are no gains from trade to forgo.

## What actually settled

Across **all six arms and both scenarios**, exactly one settled deal fell on
such a pair:

| scenario | arm | settled | of which no-zone | surplus destroyed |
|---|---|---|---|---|
| undisclosed | A | 15 | 0 | 0.000 |
| undisclosed | **B** | 14 | **1** | **−3.898** |
| bargain | A, B, C, C-meet, D | 12–16 | **0** | 0.000 |

The single deal is `business_0007|customer_0003` under arm B on
`undisclosed_3_9` — **precisely the deal Chapter 5 and §7.4.2 already identify
as the whole of arm B's residual £6.15**. Chapter 6 records it as limitation B4.

## The answer

Refusing costs nothing, because there is nothing to lose. The one trade the
current design permitted destroyed 3.90 units of model surplus and would have
destroyed none had it been refused.

The ethical objection does not apply as stated. **The parties are not both
better off.** The buyer's reservation is below the seller's cost, so the trade
is negative-sum by construction. A platform declining it is not overriding a
mutually beneficial exchange; it is preventing one party being made worse off
by its own agent's error.

The defence against "but those are only your model's numbers" is that they are
not the model's numbers. **r and c are the same two fields θ is built from.** A
platform that trusts `menu_features` and `min_price_factor` enough to enforce a
contract from them cannot consistently distrust them here. Either both readings
stand or neither does.

So G8 resolves in favour of refusal, and §8.3 item 4 — "Refusing would take
marketplace-wide overspend to zero and forbid nothing that should have been
allowed" — is now supported rather than asserted.

## Limitations

- **One settled deal.** The conclusion about the mechanism is structural (r ≤ c
  is checked in closed form on every pair); the *frequency* rests on a single
  observation, and 1 of 30 arm-scenario settlements is not a rate.
- **r and c are model-derived** from scenario configuration, and inherit
  assumption C5 like every other payoff quantity here. The argument above is
  that they inherit exactly as much trust as θ does, no more and no less.
- **Refusal was never run.** This says what refusing would have been worth on
  the stored runs. No arm implements it.
- Says nothing about a real marketplace, where a buyer's true reservation is
  not a configuration field.
