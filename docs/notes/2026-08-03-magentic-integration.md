# Magentic integration — findings worth not rediscovering

**Date:** 2026-08-03
**Scope:** integrating formulation v2 (payoff-based) with the Magentic Marketplace testbed.

Everything here cost time to establish and is invisible from the code. Numbers
that merely reproduce the formulation are not repeated; only the things that
differ from what one would assume.

---

## 1. Where the contract can be enforced

`SimpleMarketplaceProtocol.execute_action` is the single funnel every
agent-to-agent `SendMessage` passes through, and `MarketplaceLauncher` takes an
arbitrary protocol. So a `GovernedMarketplaceProtocol` subclass governs the
whole marketplace **without forking a single agent class**, which is what backs
the claim that the guarantee is a property of the game rather than of the
negotiators.

The alternative — wrapping `BaseSimpleMarketplaceAgent.send_message` — cannot
work for the coupled results. An agent sees only its own pair; the joint
filter, the shared-capacity clause and its shadow price need a view of every
live negotiation at once, and only the protocol has that.

One thing does *not* follow. `run_marketplace_experiment` hardcodes
`BusinessAgent`/`CustomerAgent`, so a governed run needs its own runner
(`src/marketplace_integration/runner.py`, a ~120-line mirror of the upstream
body with the protocol injected).

## 2. theta has ground truth in the scenario data

`Business.min_price_factor` is in every business YAML in every Magentic dataset
and **is read by no code path and no prompt**. It is the seller's cost floor as
a fraction of list price — exactly the c of theta. `Customer.menu_features`
maps requested item to the buyer's reservation price, which gives B.

So theta needs no hand-tuning, and neither does the payoff calibration:
requiring the efficient quantity to equal the requested quantity, and marginal
value to equal the reservation price there, determines a and e uniquely from
the same two numbers (`PayoffModel.from_scenario`). The only free parameter
left is the buyer curvature b, and it is named as a modelling choice in the
model's own `provenance` dict.

A corollary worth stating: because the seller was never *told* it could
discount, it never did. Disclosing `min_price_factor` in the business
description is a disclosure, not an invention, and it is the whole content of
the bargaining scenario.

## 3. Terms are structured on one side and prose on the other

`OrderProposal` carries `items[].unit_price`, `items[].quantity`,
`total_price` and `estimated_delivery`, so the seller's term vector is *read*,
not extracted. Aggregating as q = sum of quantities and p = total/q makes
h1 = B - p·q exactly B - total_price.

The buyer's counter-offers are free-text `TextMessage`. That is the entire
residual trusted-computing-base surface of formulation §10.6 — and it is
one-sided, which is better than the formulation assumes. `tests/test_terms.py`
keeps a deliberately failing phrasing ("I'd take a couple at $6") asserted, so
the surface stays visible instead of being regex'd away.

## 4. `mexican_3_9` has no coupling structure

Nine businesses, three customers, and exactly **nine definable pairs** — each
business stocks the items of precisely one customer. So no business ever serves
two customers concurrently, and the shared-capacity clause, the GNE shift and
the shadow prices **cannot be reproduced on this scenario at all**.

| scenario | pairs | max customers per business |
|---|---|---|
| `mexican_3_9` | 9 | 1 |
| `mexican_10_30` | 36 | 2 |
| `mexican_33_99` | 153 | 3 |
| `contractors_10_30` | 42 | 2 |

The coupling experiments must point at `mexican_33_99` or `contractors_10_30`.
This was not obvious: the arm-A logs show three businesses proposing to each
customer, which looks like overlap and is not — it is three sellers per buyer,
not two buyers per seller.

## 5. Some pairs have an *empty* safe set

In `data/bargain_3_9`, four of nine definable pairs have C(theta) = {}: the
seller's cost floor sits above the buyer's budget, because the budget is set
from the *cheapest* business that can serve the basket and the others are
dearer. In stock `mexican_3_9` one pair is already like this
(`business_0009|customer_0003`) — which means Angela Ng's v5 purchase at $37.53
was a deal that could not satisfy her own stated reservation prices.

This is economically correct — no deal should close — but it matters
operationally in two ways:

- projecting into an empty set is not a safety operation, so the regulator
  detects it (`Contract.is_satisfiable`, closed form: c·q_min <= B) and drops
  to monitor mode for those pairs. Otherwise every step degrades onto slack and
  reads in aggregate as a filter that cannot hold its constraints;
- a breach on such a pair is the *correct* outcome, so it is counted
  separately in the reports rather than folded into the breach rate.

## 6. Two units bugs in the safety layer, of one family

Both were found while chasing the E13 rerun, and both are the error §1 of the
formulation introduces the metric M = diag(1, 10, 5)⁻¹ to prevent.

- **The QP minimised ‖u − u_prop‖ in raw Euclidean norm**, i.e. it treated one
  day of deadline as exactly as intrusive as one pound of price. Now minimised
  in the metric.
- **`is_monotone` took eigenvalues of the unscaled symmetric part.** The
  headline stability number is −6.86 in the metric and −0.07 without it. Both
  are negative, so a sign check passes either way and the error survives
  review — which is why `tests/test_energy.py` asserts the magnitude.

## 7. Preconditioning the QP is not the same as re-weighting it

Fixing the objective metric made the u-block of P as small as 2/σ² = 0.08
against a slack block of 2ρ = 2×10⁴, and OSQP started hitting max-iter at the
default ρ. The constraint rows also carry mixed units (budget row in £,
cost-floor row in £/unit).

The tempting fix — divide each row by s_i = ‖∇h_i‖_M and penalise the
*relative* violation — is dimensionally principled and **silently changes the
filter**. Slack on the budget row becomes ~10⁶ times cheaper, and the
trajectory drifts out of C(theta) through it; two invariance tests caught this
immediately.

What is correct is the same division as a **change of variables**,
δ_i = s_i·δ̄_i, with the objective weight becoming ρ·s_i². The problem is
bit-for-bit the one that was there before; only its conditioning improves. The
unsatisfiable-contract QP went from max-iter to solved in 4850 iterations.

## 8. E13 rerun: what the residual actually was (§10.5 discharged)

The formulation guessed the 0.61-unit residual was the hard clip plus
incomplete step decay. Measured under the real DCBF-QP
(`experiments/certificates/e13_dcbf.py`), it is neither:

| γ | spend at settle | h_budget | ‖x − x_c‖_M |
|---|---|---|---|
| 0.2 | 796.8 | 3.19 | 0.765 |
| 0.4 | 798.8 | 1.20 | 0.750 |
| 0.7 | 799.7 | 0.34 | 0.746 |
| 1.0 | 799.6 | 0.37 | 0.746 |

- **Not the clip.** Under the filter the dynamics settle ~0.75 units from the
  constrained NBS against 0.642 for the clip — same order, slightly worse.
- **Not step decay**, though the reference run's geometric schedule
  contributes: it has finite total path length and can freeze the draft before
  it arrives. Under Robbins–Monro (ρ_k = ρ₀/(1+k)^0.51) the draft travels as
  far as it likes and still stops ~0.75 away, because the alternating
  single-agent ascent converges to the *efficient* quantity q = 100 rather than
  the constrained bargaining solution's q = 94.2.
- **The new result is the boundary layer.** The filter parks the draft strictly
  *inside* the budget by a γ-dependent margin. That is v1's conservatism
  premium measured in term space rather than in the dual. Because the
  constraint is therefore never active at the settled point, Φ_proj = Φ
  throughout — the projection has nothing to remove. **Φ_proj earns its keep on
  boundary-attaining dynamics such as the hard clip; under a DCBF the object
  that matters is the displaced equilibrium, and γ is what displaces it.**

Also settled: §1's open item on the p_max = 12 operating-box guard. Dropped,
not folded into theta — the budget row caps price on its own, which is what §1
argues when it observes the guard never binds.

## 9. Reproducibility is against a pinned scipy, not just pinned seeds

`experiments/certificates/` is kept byte-identical and the seeds are fixed, but
`audit.py`'s SLSQP probe now reports **7/60 status failures where the
formulation quotes 6.7% (4/60)**. The files did not change; scipy did (1.18
here). This does not weaken any claim — it makes the SLSQP hygiene problem
worse, not better, and strengthens the case for OSQP — but "bit-reproducible"
should read "bit-reproducible against a pinned environment", and the
environment is not currently pinned.

## 10. What section 11 can actually be asked of a transcript

Fitting (a, b, c, e, λ) jointly is what §11 says literally; §11's own practical
warning (5–15 rounds) is why it will not identify. The split implemented is:
structure from the scenario exactly, λ from the transcript by one-parameter
MLE, and cost-benefit rationalizability **tested** rather than assumed.

The test is the valuable part and is cheap: every round the agent moved caps κ,
every stall floors it, and if the floor exceeds the cap then no κ explains the
behaviour and the transfer from the gradient-ascent proxies does not hold. An
empty interval is a finding, not a bug.

One counter-intuitive fact that fell out of building it: **‖∇Û_i‖ is larger at
the bargaining solution (79.56) than at a far start (16.63)**. Gradients grow
as the draft improves, because acceptance becomes likely and the deal becomes
worth having. Any intuition of the form "far from agreement means a strong
incentive to move" is backwards, and that asymmetry is the mechanism behind
Prop. 2.
