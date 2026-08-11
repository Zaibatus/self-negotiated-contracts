# Arm C — the self-negotiated contract

**Date:** 2026-08-10
**Closes outline G7** (arm C half; arm E remains deferred).
**Data:** `arm_c_bargain_v1..v5` on `data/bargain_3_9`, γ = 0.4, T_max = 6,
5 seeds. 5 new runs, ~$0.5. Compared against the stored arms A, B and D.

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts
for i in 1 2 3 4 5; do
  uv run python experiments/arm_c_negotiated.py --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_c_bargain_v$i" --override
done
```

The pre-phase counts against T_max by default; `--no-prephase-counts-against-tmax`
measures the enforced window alone. On this data the choice changes nothing —
see "The T_max question" below.

---

## What arm C is

The central treatment of the original design, and the one the repository is
named after: θ is **agreed between the agents** and only then enforced against
them. Arms B and D impose θ from the scenario data; neither agent agreed to it
or is told it exists.

θ is **inferred**, not exchanged. Adding a "propose terms of engagement"
message would fork the agent classes and kill the agent-agnostic claim the
other arms rest on, so instead the two positions the agents already state are
read as the envelope they have jointly committed to:

    h1 = B - p*q >= 0   with  B = p_s * q   ->  p <= p_s   the seller's own ask
    h2 = p - c   >= 0   with  c = p_b       ->  p >= p_b   the buyer's own offer

Each is a self-binding commitment in the only direction it can be: a seller
that opened at `p_s` cannot coherently demand more later, a buyer that offered
`p_b` cannot coherently offer less. The envelope is **frozen** the moment both
sides have spoken — a contract that tracked the latest offers would be
renegotiated every round and would constrain nothing, since each concession
would drag the boundary along behind it.

Quantity and deadline bands carry over from the scenario unchanged. They are
the *subject* of the negotiation rather than positions taken in it, and a band
inferred from one observation would have width zero. That is the one place arm
C is not purely self-negotiated, and it is a limitation below.

## The pre-phase resolves, and quickly

| | |
|---|---|
| pairs where θ was agreed | **29/40 (0.72)** |
| pre-phase length | mean **1.07** rounds, max 2 |
| pairs that never agreed | 11 — the buyer stated no price of its own |

Those 11 ran ungoverned for the whole negotiation, which is the honest outcome:
with only one side's position there is no envelope, and inventing the other
half would be imposing a contract while calling it negotiated. The rate is
reported rather than tuned away.

## The guarantee transfers intact

| arm C rounds | breaching the θ **it agreed** |
|---|---|
| before θ was agreed (pre-phase) | 25 / 31 |
| **under the agreed θ** | **0 / 136** |

**Zero breaches of the negotiated contract across 136 enforced rounds.**

**[qualified 2026-08-11: this is a weaker test than arm B's 0/27, and the two
should not be read as comparable.** The envelope is looser than the mandate on
every pair, so 136 rounds against an easier target is less evidence per round,
not more. What the number establishes is that the filter is indifferent to the
contract's provenance; it does *not* establish that a negotiated contract is as
protective.]**

It is worth stating why even that is not trivial: the
filter never inspects where θ came from. It reads the terms, solves the QP and
rewrites. Arms B and C share every line of that path and differ only in which
Contract object is handed to it, so a non-zero result here would have been an
enforcement bug rather than a finding about negotiated contracts.

All 25 breaches sit in the pre-phase, which is unavoidable rather than a
failure: before both sides have spoken there is no contract to enforce. It does
mean a self-negotiated contract **cannot** protect the opening exchange, and
that is a structural difference from an imposed one, not a tuning issue.

## The result that matters: the agreed contract does not refine the mandate

| | arm A | arm D | arm B | **arm C** |
|---|---|---|---|---|
| proposals offered | 95 | 80 | 51 | **219** |
| breaching the **scenario** θ | 0.858 | 0.822 | 0.472 | **0.922** |
| deals settled | 12 | 12 | 16 | 14 |
| settled breaching the scenario θ | 0.083 | 0.083 | **0.000** | **0.143** |
| overspend total | £0.00 | £0.00 | £0.00 | **£0.48** |
| governed rounds breaching | 46/58 | 37/51 | 0/27 | 25/167 |

**Arm C is the only arm on `bargain_3_9` that overspends**, it settles a higher
fraction of breaching deals than doing nothing at all (0.143 against arm A's
0.083), and its offered-breach rate against the mandate is the highest of the
four.

**[qualified 2026-08-11.]** The settled-breach comparison is **2/14 against
1/12 — one extra deal** — and £0.48 is that same deal or two. Both sit inside
the A/D noise floor this project insists on elsewhere, so the *rate* is not
claimable at n = 5 × 3. What carries the finding is the refinement fact below,
which is categorical and needs no interval: a contract that permits more cannot
forbid more. The direction is established; the magnitude is not.

The mechanism is not subtle, and §9's refinement relation is exactly the right
tool for naming it:

**[corrected 2026-08-11: the arithmetic below originally pooled 29 envelopes as
if independent. They are 9 distinct pairs observed across 1–5 seeds each, and
within a pair the ratio is *identical* in every seed — the seller's opening ask
and the buyer's stated budget are both deterministic given the scenario. The
effective n is 9, not 29. The corrected statement is categorical and therefore
stronger than the pooled mean it replaces.]**

| | per pair (n = 9) |
|---|---|
| inferred B / imposed B | **1.05–1.52×**, one value per pair, SD 0.000 across seeds |
| pairs where the ratio exceeds 1 | **9 / 9** |
| envelopes that **refine** the imposed θ | **0 / 9 pairs** (0 / 29 envelopes) |

Pooling gives 1.214× and the mean of the nine per-pair values is 1.234×, so the
pooled figure was not misleading in magnitude — but the *claim* it supported
should be the categorical one: **every pair's negotiated budget exceeds the
mandate's, in every seed.** That is a structural fact about where a seller's
opening ask sits, not an estimate with a spread.

The seller's opening ask sits above the customer's reservation price, so an
envelope whose ceiling is that ask is *looser* than a mandate whose ceiling is
the reservation. The negotiated contract sits **above** the imposed one in the
refinement order, in every single case, and enforcing something looser than the
mandate does not deliver the mandate.

So the honest statement of what arm C shows:

> A self-negotiated contract is enforced exactly as reliably as an imposed one
> — 0/136 — and enforcing it is **not** a substitute for governance, because
> what the parties agree between themselves need not satisfy what the platform
> requires of them.

That is a genuine contribution rather than a null result, and it points at the
composition the thesis should actually propose: enforce **θ_negotiated ∧
θ_mandate**, the meet of the two in the refinement lattice. That is also what a
real marketplace does — parties may agree their own terms, but only inside the
platform's rules. The machinery for it already exists (`Contract.refines`, and
the meet is componentwise), it is one arm's worth of work, and it is *not* run
here because it is a fourth treatment rather than a fix to this one.

## Arm C does not compress the negotiation, and that is the cost

The funnelling note's cleanest result was that enforcement removes the
negotiation: arm B's median binding trajectory is 1 round against 2 ungoverned.
Arm C does the opposite.

| | arm A | arm D | arm B | **arm C** |
|---|---|---|---|---|
| proposals | 95 | 80 | 51 | **219** |
| governed rounds | 58 | 51 | 27 | **167** |
| frozen pairs exceeding T_max = 6 | — | — | — | **14/29 (0.48)** |

The envelope permits the whole zone between the two opening positions, so the
haggling actually happens inside it — where arm B's projected opening landed on
the buyer's budget immediately and there was nothing left to argue about.
**Nearly half of arm C's agreed contracts run past the liveness bound**, which
is the sharpest liveness signal anywhere in this project: T_max has barely bound
in any other arm (limitation C8), and here it binds on 48% of pairs.

**[qualified 2026-08-11.]** This is less a discovery about liveness than a
consequence of a looser contract permitting more movement, measured against a
T_max that was calibrated on arm B and D lengths. The honest reading is that
T_max binds where there is a negotiation left to bound — which is arm C — not
that arm C is badly behaved.

Read together with the safety column, that is the trade the arm exposes:
a negotiated contract preserves the negotiation and pays for it in termination.

## The funnel, and a coincidence worth flagging

| arm | mean per-pair settled-price SD |
|---|---|
| A | 0.183 |
| **B** | **0.000** |
| C | 0.090 |

Arm C sits between the two — but the interesting part is *where* it lands, not
how tightly:

| pair | arm C settled prices | imposed B/q_min |
|---|---|---|
| `business_0001\|customer_0001` | 5.79 ×4 | 5.790 |
| `business_0005\|customer_0002` | 7.45, 6.99, 7.46, 7.45 | 7.450 |
| `business_0008\|customer_0003` | 10.617, 10.46 ×3 | 10.460 |

**Arm C funnels to the same point arm B does**, which at first reading looks
like the contract choosing the outcome again. It is not. On `bargain_3_9` the
buyer is told its budget and states it verbatim as its counter-offer, so
`c_inferred` = the buyer's offer = *exactly* the imposed `B/q_min`. The floor of
arm C's envelope is the platform's ceiling, by coincidence of this scenario, and
the negotiation then settles on that floor because the buyer defends it.

Two consequences, and the second is the one to keep:

- arm C's safe set is almost exactly the region arm B **forbids** — everything
  from the buyer's budget up to the seller's ask — with the single boundary
  point in common. The two contracts agree on one price and disagree everywhere
  else.
- the agreement is therefore an artefact of a disclosed budget. On
  `undisclosed_3_9` the buyer states no budget, so the envelope's floor would be
  wherever the buyer chose to open, and the funnel point would move. That run
  is the obvious follow-up and is **not** done.

## The T_max question, answered

Flagged as an explicit decision rather than an implicit one:
`--prephase-counts-against-tmax`, **default true**. Rounds spent agreeing the
contract are time spent negotiating, and exempting them would certify
termination of only the enforced half of the process.

On this data **the convention makes no difference**:

| | frozen pairs exceeding T_max = 6 |
|---|---|
| pre-phase counted (default) | 14/29 |
| pre-phase exempt | 14/29 |

The pre-phase is 1.07 rounds on average and the negotiations that overrun do so
by much more than that, so nothing crosses the threshold either way. The flag
was still worth making explicit — on a scenario with a longer pre-phase it
would matter, and a choice buried in an implementation is not auditable — but no
conclusion in this note depends on it.

## A bug this arm found, and it is the fifth

`from_text` read the buyer's counter-offer as **the seller's own quote**.
Buyers habitually restate the price on the table before naming their own:

    "The current quote of $13.76 is above my budget of $11.58."

`_MONEY.search` returns the *first* figure, so the extractor recorded a
counter-offer at $13.76 — the number the seller had just asked for — and
discarded $11.58, the only figure in the sentence the buyer owns. Both halves
are wrong: a fabricated move to the seller's own ask, and the real position
dropped.

Over the 25 stored arm A/B/D runs, **110 of 125 extracted buyer "moves" (88%)
are echoes of this kind.**

Scope of the damage, stated precisely because it is smaller than it sounds: the
corrupted surface is the **observed** trajectory. The published drift,
funnelling, compression and safety results are computed on the **binding**
trajectory (seller proposals, exact structured terms) or on database outcomes,
and are unaffected. What was affected is the section 11 convergence/termination
report, which consumes observed.

It fits the other four exactly — a plausible-looking value on a surface nobody
asserted on — and it surfaced only here because **arm C is the first thing that
reads the buyer's position rather than merely logging it**. Before arm C, an
echo and a genuine counter-offer were indistinguishable downstream. That is the
methodological point for chapter 4: the bug was latent in every arm and became
visible only when something depended on the value being right.

Its first symptom was misleading in a way worth recording. Pre-fix, four of
nine pairs reported "buyer offer 12.51 >= seller ask 12.51: no zone to
enforce" — an *exact* equality, which is what gave it away.

## Limitations

- **The envelope is only as good as the extraction.** Arm C's θ depends on a
  regex reading of free-text buyer messages, which is the residual extraction
  surface the whole thesis flags (D1) — and this arm is the one place that
  surface is load-bearing rather than merely logged. 11 of 40 pairs produced no
  usable position at all.
- **Structural terms are not negotiated.** Quantity and deadline bands come
  from the scenario, so arm C is a negotiated *price* contract with imposed
  bounds elsewhere.
- **One position each, and only the openings.** The envelope uses the first
  statement from each side and freezes. A design that updated θ on mutual
  agreement would be closer to real contracting and is not implemented; the
  freeze is what makes the object a contract rather than a running summary.
- **The funnel agreement is a coincidence of a disclosed budget**, as above,
  and would not survive `undisclosed_3_9`. Not run.
- **n = 5 seeds × 3 customers.** The 0/136 safety result is categorical. The
  1.21× looseness is 29 observations of one scenario's price structure and the
  *direction* is what transfers, not the multiple.
- **θ_negotiated ∧ θ_mandate is proposed, not tested.** The composition that
  would fix the compliance gap is one arm's work and is named rather than run.
