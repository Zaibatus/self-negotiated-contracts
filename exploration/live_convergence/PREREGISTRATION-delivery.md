# PRE-REGISTRATION — does the redirection generalise off the quantity axis?

**Written 2026-09-14, BEFORE any run on `delivery_off09_3_9` exists.** Nothing
here may be edited after the first run.

## Why

The quantity experiment found that the filter redirects the seller onto a
second axis: upsell rate **14.6% before** the filter alters price in a pair,
**55.8% after** (Fisher p = 3.4 × 10⁻⁷). Two readings:

- **H_general** — blocked on one axis, an agent uses whatever other lever it has
  been offered. A property of enforcement.
- **H_quantity** — a quirk of quantity. The budget row `h₁ = B − pq` is bilinear
  in `(p, q)`, so quantity is entangled with the very row that binds, and the
  filter itself was cutting `q` on 15% of rounds.

Delivery separates them. It appears in **no active row**, so the mechanism has
nothing to do with the QP's geometry.

## The design, and why it is a cleaner isolation than quantity

`exploration/live_convergence/data/delivery_off09_3_9` — the off09 recipe plus
two delivery clauses, no volume clauses. **θ is byte-identical to
`disclosed_offset_low_3_9`** (verified), and `deadline_active` stays **False**.

That matters:

* `from_order_proposal` reads `deadline = parse_days(estimated_delivery)`
  unconditionally, so `d` is **recorded** whether or not it is constrained.
* `rewrite_proposal` rebuilds only `items` and `total_price` and carries
  `estimated_delivery` through untouched, so the filter **cannot** move `d`.

Any movement in `d` is therefore the agent's own. The quantity experiment could
not claim that — there the filter cut `q` itself.

## The risk

`estimated_delivery` is optional on Magentic's `OrderProposal` and has been
empty in **all 4,126 rounds ever recorded** in this project, so `d` has been
0.0 throughout the dissertation. If the seller ignores the instruction, there is
no second axis and nothing downstream can be measured. The message schema and
the agent classes are untouched; only scenario text changed.

## Registered predictions

**P11 — is the axis alive at all?** `deadline_observed` will be true on **≥ 50%**
of arm B proposals. Baseline: 0 of 3,865.
*Falsified if* < 50%. **This is the prediction most likely to fail** and it
gates everything below; if it fails, the finding is that the seller will not
populate an optional schema field on instruction, and the delivery axis is
closed for reasons upstream of the contract.

**P12 — does it move?** `d` will change between consecutive rounds of a pair on
**≥ 10%** of arm B continuation rounds. Baseline 0.0%.
*Falsified if* < 10%. Stated separately from P11 because a constant delivery
time quoted every round is an observed axis that is not a negotiated one — the
distinction the quantity run taught me to make.

**P13 — the load-bearing one, the redirect test.** Within arm B, the rate of
deadline movement will be **higher after** the filter has altered price in that
pair than before, Fisher exact **p < 0.05**. This is the direct analogue of
14.6% → 55.8%.
*Falsified if* p ≥ 0.05 or the direction reverses.

**P14 — the asymmetry replicates on a new axis.** Arm B's deadline-movement
rate will exceed arm A's, Fisher exact **p < 0.05**.
*Falsified if* p ≥ 0.05 or the direction reverses.

**P15 — the control, and a check on the quantity result.** With no volume
clause in this scenario, arm B's upsell rate (`q > q_min`) will fall **below
15%**, against 46.1% on `quantity_off09_3_9`.
*Falsified if* ≥ 15%. If this fails, the quantity result was not caused by the
volume clause and my reading of it was wrong.

## What I expect

P11 is the gate and I cannot call it. LLM agents routinely skip optional fields,
and 4,126 empty rounds is a strong prior — but none of those runs ever asked.

If P11 and P12 hold I expect P13 to hold, because the seller's position is the
same as in the quantity run: price blocked, one other lever offered, and a buyer
explicitly instructed to press for that lever when price stalls.

P15 is the one whose failure would most change the previous conclusion.

## Protocol

Arms A (`--live`, `mode=off`) and B (`mode=filter`, `theta_source=scenario`),
**5 seeds each**, γ = 0.4, T_max = 6, `gemini-2.5-flash` minimal reasoning.
Schemas `dlv_a_v1..v5`, `dlv_b_v1..v5`. Results to
`exploration/live_convergence/results/`. Estimated **~£1.50**, against the £5
ask-first threshold. Cumulative exploration spend would reach ~£3.

## Analysis, fixed in advance

Deadline movement is `|d_k − d_{k−1}| > 1e-9` on `x_applied` within a
(run, pair), counted over continuation rounds. `deadline_observed` is read from
the `extraction` field of each `RoundRecord`. Fisher exact, two-sided, pooling
seeds within arm, with the standing caveat that 5 seeds × 3 customers is 5 draws
of the same 3 situations.
