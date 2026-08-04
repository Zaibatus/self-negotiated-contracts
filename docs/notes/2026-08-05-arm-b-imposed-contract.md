# Arm B — imposed contract under the DCBF filter, on `bargain_3_9`

**Date:** 2026-08-05
**Data:** `arm_b_bargain_v1..v5` against `arm_a_bargain_v1..v5`, `data/bargain_3_9`, gemini-2.5-flash, γ = 0.4, T_max = 6.

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts

for i in 1 2 3 4 5; do
  uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_b_bargain_v$i" --override
done
```

The comparison table is `results/arm_b_bargain/comparison.json`, produced by
`src/marketplace_integration/compare_arms.py`.

---

## Two bugs found by running this, both of which invalidated earlier results

Read this section first. The headline below is from the **third** set of arm B
runs; the first two measured something other than what they claimed.

### 1. The filter never reached the wire

`GovernedMarketplaceProtocol.execute_action` rewrote the proposal on a
`model_copy` of the request. But the server route builds its database row from
the request object *it* was handed
(`platform/server/routes/actions.py`: `ActionRowData(request=request, ...)`),
and the recipient fetches messages back out of that database. So every
correction was computed, written to `certificates.jsonl`, and discarded.

The evidence was unambiguous once looked at. For
`business_0002|customer_0001` in v4, the certificate log recorded the filter
pulling three proposals to 11.58, 11.58 and 11.40 — while the database, the
customer's payment and the seller's own confirmation text all showed 13.76,
12.29 and **11.12**, the unfiltered values.

**Arm B, as first run, enforced nothing.** The fix is to mutate
`action.parameters` in place; the copy is the bug, not the shortcut.

Worse than the bug is why it survived: the integration tests asserted on
`result.content`, which *does* carry the rewrite, rather than on the request
object the caller is left holding. A regulator that filtered nothing passed a
32-test suite. `TestTheRewriteReachesTheWire` now asserts on the persisted
surface, and fails against the old implementation.

### 2. Currency quantisation pushed the result out of the safe set

With the wire fixed, governed pairs still breached on 10 of 41 rounds — every
one by **exactly −0.01** on the budget row, all on the same pair, several with
zero filter intervention.

Prices round to the cent; the safe set does not. The QP's exact solution does
not land on a cent boundary, and rounding to nearest put the realised total a
penny outside C(θ) systematically. `rewrite_proposal` now takes the contract
and nudges cents until the true h is satisfied — quantising *into* the safe
set rather than to the nearest point. Rows that price cannot fix (quantity,
deadline) are left visibly breached rather than papered over.

**A "zero breaches" claim that ignores currency rounding is false as stated.**
This is the kind of thing that only shows up against a real marketplace.

---

## Headline

| | arm A (ungoverned) | arm B (filtered) | change |
|---|---|---|---|
| proposals offered | 95 | 51 | −44 |
| &nbsp;&nbsp;breaching θ | 0.858 | 0.472 | −0.385 |
| deals settled | 12 | 16 | +4 |
| &nbsp;&nbsp;breaching θ | 0.083 | **0.000** | −0.083 |
| &nbsp;&nbsp;meaningful breaches | 1 | **0** | −1 |
| overspend / value | 0.00% | 0.00% | — |
| value transacted | $143.75 | $259.45 | +$115.70 |

**On governed pairs the per-round breach rate is 0 of 27.** That is the live-LLM
replication of F1 (9.9% → 0% in simulation).

The residual 0.472 offered-breach rate is entirely the **structurally
infeasible** pairs — four of nine definable pairs on this scenario have an
empty safe set, and the regulator deliberately leaves them in monitor mode
because projecting into an empty set is not a safety operation. Their
proposals breach and cannot be made not to. Splitting the rate by whether the
pair was governed at all is the only honest way to report it:

| | breaching rounds |
|---|---|
| governed pairs (C(θ) non-empty) | **0 / 27** |
| infeasible pairs (left in monitor) | 26 / 26 |

## The cost of the guarantee

Zero, at this sample size, and the sample size is the caveat.

| pair | arm A closures | arm B closures | |
|---|---|---|---|
| `business_0001\|customer_0001` | 3 | 3 | |
| `business_0002\|customer_0001` | 2 | 2 | |
| `business_0004\|customer_0002` | 3 | 4 | |
| `business_0005\|customer_0002` | 2 | 2 | |
| `business_0008\|customer_0003` | 2 | 5 | |
| four infeasible pairs | 0 | 0 | no-close is correct |

**No pair closed ungoverned and stopped closing under the filter.** Reported as
*no detectable feasibility cost at n = 5*, not as *no cost*: with five seeds
and three customers only a large effect would have been visible.

Arm B settled **more** deals (16 vs 12) and transacted more value. I do not
claim the filter caused that. Almost all of the difference is one pair
(`business_0008|customer_0003`, 2 → 5), the same customer whose closure rate
was the dominant source of variance in arm A. This is well within what five
seeds of LLM stochasticity produce, and it should not be read as the safety
layer improving throughput.

## Filter behaviour

| | |
|---|---|
| rounds where the filter bound at all | 11.1% |
| intervention when it bound (scaled units) | mean 0.795, max 1.092 |
| OSQP solver failures | 0 |
| fallback tiers fired | **none** — no `retry_stiff_rho`, `hold`, `conservative_recovery` or `hold_outside_unverified` |
| certificate gaps | 0 |
| true-h backtracks | 0 |

Every filtered step was a solved QP with a verified guarantee. The tiered
fallback machinery did not fire once, which is the outcome it was designed for
but is worth stating as a measurement rather than an assumption.

## Surplus and convergence

| | arm A | arm B |
|---|---|---|
| surplus loss vs Nash benchmark | 0.93% | **0.00%** |
| distance of settled terms to x\*_NBS | 0.221 | **0.085** scaled units |

Settled deals under the filter are *closer* to the bargaining solution, not
further. That is a pleasant result and I would not lean on it: on this
scenario the budget binds at the same place the buyer targets anyway, so the
filter and the bargaining solution point the same way. It would not survive a
scenario where the contract and the efficient split disagree.

**Φ and Φ_proj are not reported as a convergence result.** Formulation §5's
"decreases on 96% of round-pairs" is measured under a tuned diminishing step;
live agents have no step schedule, so a decrease fraction here would test
something the formulation never claimed. The trajectories are in
`results/arm_b_bargain_v*/section_11.json` for inspection.

**Rounds to settle against T_max.** Observed trajectory lengths across both
arms: median 3, p90 5, max 13. T_max = 6 was calibrated from arm A's lengths
so the liveness column would carry signal rather than pass vacuously — the
`ControllerSpec` default of 12 would never have bound.

## Limitations

- **Termination is measured, not enforced.** G_κ is computed from a friction
  schedule the agents never experience. Formulation §A.5 item 1.
- **The seller's own books desync under filtering.** `BusinessAgent` calls
  `add_proposal()` before `send_message()`, so its local storage keeps the
  pre-filter proposal. Welfare analytics reads DB payments and is unaffected,
  but the seller's confirmation text quotes the unfiltered price — in
  deployment that means invoicing the wrong amount. The enforcement point
  rewrites the message without telling the sender.
- **λ is unidentified** at this transcript length; the payoff model falls back
  to the scenario prior throughout.
- **n = 5 seeds × 3 customers.** Five draws of the same three situations. Every
  ± here is seed variance under a fixed scenario, not sampling error over
  pairs.
- **`bargain_3_9` gives the filter little to prevent** — arm A had exactly one
  meaningful settled breach in twelve deals, for the reasons in the
  [arm A note](2026-08-05-arm-a-bargain-scenario.md). This arm is therefore
  closer to a cost measurement than a benefit measurement, and the honest
  headline is the per-round governed breach rate (0/27) rather than the
  deal-level difference.
