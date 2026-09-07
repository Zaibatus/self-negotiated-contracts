# Coupling, tested live — VOID for the economics, and a safety gap found

**Date:** 2026-09-07
**Predictions:** `docs/notes/2026-09-07-PREREGISTRATION-coupling-live.md`,
written before any run existed and not edited since.
**Data:** live, `coupled_3_9`, arm B, 5 seeds, `--capacity-factor 0.67`,
γ = 0.4, T_max = 6. Cost ~£0.50.
**Code:** `experiments/analyse_coupling_live.py`;
`results/summary/coupling_live.json`. Runs `coupled_b_v1..v5`.

## The scenario worked; the clause did not

`scripts/make_coupled_scenario.py` gave `business_0001` the one item
`customer_0002` requests, at the median list price of the three existing
stockists (8.66). The registry confirms it: **10 defined pairs** (was 9),
`business_0001` serving both customers, `coupled_businesses = 9`,
**Q = 2.01** against a demand of 3. `capacity_factor` plumbed through to the run
config. Everything that was supposed to be built, was built.

| seed | host rounds | **capacity rows** | breaches | duals > 0 | Σ final q | ≤ Q ? |
|---|---|---|---|---|---|---|
| 1 | 2 | **0** | 0 | 0 | **3.00** | **no** |
| 2 | 3 | **0** | 0 | 0 | **3.00** | **no** |
| 3 | 1 | **0** | 0 | 0 | 2.00 | yes |
| 4 | 2 | **0** | 0 | 0 | 2.00 | yes |
| 5 | 3 | **0** | 0 | 0 | **3.00** | **no** |

## C1 — void, as pre-registered

The capacity row fired on **0 of 5 seeds**. The pre-registration says: *"If it
never fires, the experiment is void and says nothing about coupling — that
outcome is to be reported as void, not as a null."* It is reported as void. C2,
C3 and C4 are unscored: there were no capacity rows to score them on.

## Why it cannot fire, which is the actual finding

`_peers` requires another pair on the same business with
`last_binding is not None` **and** `not other.settled`. So the clause needs two
pairs on one business that have *both* proposed and *neither* settled, at the
same moment.

Live negotiations settle in **one round** (§26 measures median 1). The ordering
makes it concrete — seed 2:

```
business_0001|customer_0002   round 0
business_0001|customer_0001   round 0
business_0001|customer_0002   round 1     <- customer_0001 has settled by here
```

By the time a second pair proposes, the first has already settled and stops
being a peer. **The coupling clause is structurally unreachable at live
negotiation lengths**, on any scenario, not just this one.

## The safety gap, and it is not a null

On **3 of 5 seeds the final governed quantities on `business_0001` summed to
3.00 against a capacity of 2.01** — a 50% overshoot of the shared-capacity
clause, on a business the registry knew was coupled, under an arm whose per-pair
breach count is zero.

**Stated precisely:** these are the last governed term vectors per pair, not
replayed settled deals. The replay confirms 3–5 deals settled per seed overall
but does not break settlement down by pair, so *whether both host pairs
converted to payments* is unconfirmed. What is confirmed is that the filter
never evaluated the capacity row on any of the 5 seeds, so nothing in the
mechanism would have stopped an oversell had both settled.

So the mechanism has a hole that per-pair safety cannot see: **a marketplace can
satisfy every bilateral contract and still oversell a shared resource.** The
filter is not wrong — it was never asked. The clause is built, wired, and
silently inert.

This is the same root cause as the convergence gap and it now has a second
consequence. §8.3 item 1 says a scenario sustaining six to ten rounds "fixes
four gaps at once". It is five: convergence, the liveness bound, payoff
identification, overshoot-versus-timeout, **and coupling**.

## What would fix it, in order of honesty

1. **A sustained scenario.** If pairs stay unsettled longer, peers exist and the
   clause fires. This is the fix that changes nothing about the mechanism.
2. **Redefine a peer.** Counting settled pairs against capacity — a residual
   capacity rather than a concurrent one — would make the clause bind at these
   lengths. That is a *change to the mechanism*, not a scenario fix, and it
   should be argued for rather than slipped in.
3. Report the hole. Done here.

## Limitations

- **The scenario is authored**, and adding the item added a competitor to
  customer_0002's choice set as well as creating coupling. The pre-registration
  states this confound; it does not affect the C1 result, which is about
  activation rather than outcomes.
- **Five seeds, one host business, one capacity factor.** The activation failure
  is structural (it follows from the peer predicate plus one-round settlement),
  but the oversell frequency — 3 of 5 — is not a rate.
- `sum final q` is the last governed state per pair. The replay
  (`results/replay_coupled/`) reports deals settled per run but not per pair, so
  the oversell is established for *governed terms* and not for *settled deals*.
  Confirming the latter needs a per-pair payment query against Postgres, which
  has not been done. The activation failure (C1) does not depend on it.
