# Live convergence — reconnaissance

**Written 2026-09-14, before anything in this folder was run.** Side
exploration, not part of the submitted dissertation. Nothing outside
`exploration/live_convergence/` is modified by this work.

Repo state at recon: `main` @ `833cc1c`, working tree clean.

---

## The question

Can convergence (Φ → 0 at the Nash bargaining solution) be observed *live*
under a **binding** contract, and does the filter change the rate?

The dissertation could not answer this. Under a binding contract deals close in
a median of one round, so there is no trajectory; arm C sustains ~9 rounds but
its self-negotiated contract does not bind, and its contraction rate (0.624) is
indistinguishable from the ungoverned 0.621.

The assumed obstacle was that price is the only live dimension, so projection
onto a tight budget lands on the final deal immediately.

**That premise is scenario-specific, and it is already falsified by data on
disk.** See finding 1.

---

## 1. The one-round problem is not universal

Rounds per pair, counted from `results/*/certificates.jsonl` (3,865
continuation rounds across 299 run directories):

| family | scenario | mode | median | max | pairs ≥4 rounds |
|---|---|---|---|---|---|
| `arm_b_off09` | `disclosed_offset_low_3_9` (f = 0.90) | **filter** | **6** | **31** | **25 of 40** |
| `arm_a_off09` | same scenario | off | 2 | 5 | 7 of 39 |
| `arm_a_adv` | `bargain_adv_3_9` | off | 5 | 35 | 28 of 40 |
| `arm_c_bargain` | `bargain_3_9` | filter (inferred θ) | 3 | 13 | 19 of 40 |
| `arm_b_bargain` | `bargain_3_9` | filter | 1–2 | 3 | 4 of 36 |

`arm_b_bargain` is the configuration the dissertation generalised from. It is
the exception, not the rule.

## 2. And on `arm_b_off09` the contract genuinely binds

| family | rounds | filter intervened | dual active | dominant row |
|---|---|---|---|---|
| `arm_b_off09` | 326 | 258 (**79.1%**) | 235 (**72.1%**) | `cost_floor` (227) |
| `arm_c_bargain` | 219 | 141 (64.4%) | 141 (64.4%) | `cost_floor` (141) |
| `arm_b_bargain` | 51 | 3 (5.9%) | 3 (5.9%) | `budget`, `q_min` (3) |

*(For `mode="off"` families the intervention figure is the counterfactual the
QP would have applied, not an applied correction — arm A forwards messages
untouched.)*

**Mechanism.** `disclosed_offset_low_3_9` is generated with
`--disclosed-budget-factor 0.90`: the buyer is *told* a budget of 0.9·B while θ
still uses the real B. So the buyer keeps pushing beneath the seller's cost
floor, the filter keeps refusing, and the negotiation does not collapse. This
is a binding contract **and** a sustained trajectory — the configuration
§8.2 of the dissertation says was never obtained.

Note the direction: here governance *lengthens* the negotiation (6 vs 2). Any
rate comparison has to account for the governed and ungoverned trajectories
having different lengths.

## 3. Non-price dimensions are deader than assumed

Across the same 3,865 continuation rounds:

| dimension | rounds in which it moved |
|---|---|
| price | 1,142 (29.5%) |
| quantity | **11 (0.3%)** |
| deadline | **0 (0.0%)** |

- `d` is `0.0` in **every** stored round. `ContractSpec.deadline_active`
  defaults to `False` (`src/contract.py:79`), is never set `True` in any live
  run, and is not exposed on the runner CLI — `experiments/_common.py:136`
  passes only `q_max_factor`. `parse_days` also returns `None` when
  `estimated_delivery` is absent, which it usually is.
- `q` takes only {1.0, 2.0, 3.0} — the basket size. The 11 "moves" are all an
  item being dropped, e.g. `[11.757, 3.0, 0.0] → [10.085, 2.0, 0.0]`. No agent
  ever haggled over quantity.

So making a non-price dimension live is not a prompt tweak. Quantity is the
cheaper of the two (band `[q_min, 2·q_min]` is real, `--q-max-factor` is
CLI-exposed); deadline additionally needs `deadline_active=True` plumbed
through a copied runner and sellers emitting a parseable delivery string.

## 4. The obvious lever is already known-dead

`docs/notes/2026-09-07-PREREGISTRATION-funnel-live.md` pre-registered P4 —
"lower `zone_position` lengthens negotiations" — ran the pilot, and falsified
it: **median 2, max 4** on `hardbargain_010_3_9`, identical to `bargain_3_9`.
Its own verdict: *"the sustained-negotiation route is closed by this … §8.3
item 1 needs a different lever than `zone_position`."*

Do not retry this lever.

## 5. How the machinery fits together

**θ = (B, c, q_min, q_max, d_min, d_max)**, from `Contract.from_scenario`
(`src/contract.py`):

| field | source |
|---|---|
| `B` | Σ `Customer.menu_features[item] × qty`, × (1 + `budget_slack`), default slack 0 |
| `c` | quantity-weighted mean of `Business.menu_features[item] × Business.min_price_factor` |
| `q_min` | total basket quantity |
| `q_max` | `ceil(q_min × q_max_factor)`, default factor 2.0 |
| `d_min`,`d_max` | `ContractSpec` constants 0.0 / 7.0, **inactive by default** |

`C(θ) = {x : h_i ≥ 0}` with `h = (B − pq, p − c, q − q_min, q_max − q,
d − d_min, d_max − d)`. Satisfiable iff `c·q_min ≤ B`. Pairs where the business
stocks none of the basket are `undefinable`; `c·q_min > B` are `unsatisfiable`
(`src/marketplace_integration/theta.py`).

**Where the filter hooks.** `GovernedMarketplaceProtocol` subclasses Magentic's
`SimpleMarketplaceProtocol` and intercepts `SendMessage`
(`src/marketplace_integration/protocol.py`): `_govern` :220 → `_on_proposal`
:230 → `_continue_negotiation` :400, which calls `self.filter.step(...)` and
rewrites the outgoing `OrderProposal`. Only seller proposals are projected;
buyer counter-offers are free text and are recorded, never rewritten. Two
trajectories per pair: `binding` (proposals only, what the barrier constrains)
and `observed` (interleaved with the buyer's extracted counters).

**Arms** — `mode` × `theta_source` are independent axes:

| arm | mode | theta_source |
|---|---|---|
| A | `off` | — |
| B | `filter` | `scenario` |
| C | `filter` | `inferred` |
| C-meet | `filter` | `meet` |
| C-meet-guarded | `filter` | `guarded_meet` |
| D | `monitor` | `scenario` |

**Certificates.** `phi` (`src/certificates/energy.py:50`), `phi_projected`
(:129), `g_kappa` (:209). Φ is anchor-free — built from current gradients, not
from a guessed equilibrium. Under an active constraint the unprojected Φ does
**not** vanish at the rest point, because the field points into the constraint;
`phi_projected` projects onto the tangent cone of the active rows and does.
Since `cost_floor` is active on 72% of `arm_b_off09` rounds, **Φ_projected is
the one to read here**, and reporting raw Φ alone would misread a constrained
rest point as non-convergence.

**Trajectory log.** One `RoundRecord` per intercepted proposal
(`src/certificates/metrics.py:33`), written to `results/<experiment>/certificates.jsonl`:
`pair_id`, `round_index`, `mode`, `x_prev`, `x_proposed`, `x_applied`,
`h_prev`, `h_applied`, `breached_rows`, `breach`, `intervention`,
`slack_total`, `duals`, `solver_status`, `solved`, `fallback`, `backtracks`,
`certificate_gap`.

**Distance metric.** `dist_M` (`src/payoffs.py:42`) under
`SCALE = [1.0, 10.0, 5.0]` — price in currency units, quantity and deadline
scaled. Row scaling is a change of variables, not a re-weighting.

---

## What this implies for the plan

The first move is **not** to author a scenario. `arm_b_off09` already supplies
25 governed pairs with ≥4 rounds under a contract that binds on 72% of rounds,
with a same-scenario ungoverned control. Both stock analysis scripts glob
`results/arm_{arm}_*/certificates.jsonl` and take `--data`, so they point at it
unchanged and read from disk — **zero API cost**.

Open question the existing data may not settle: the ungoverned control has only
**7** fittable pairs. If that is too few to separate ρ, saying so is the
result, not a failure.

---

# RESULTS — phase 2, from data already on disk

**Run 2026-09-14. Zero API calls; both stock scripts and `analyse_off09.py`
read `results/*/certificates.jsonl`. No new Postgres schema, no network.**

Sanity check first: `fit_contraction.py --arms c_bargain` reproduces
**median ρ = 0.624** over 16 trajectories, the figure in the dissertation. The
pipeline is reading what it read before.

## Headline: convergence is observable live under a binding contract

**On the right certificate.** The two measures disagree, and the disagreement is
the result:

| measure (arm B, governed) | n | down | flat | up | net down |
|---|---|---|---|---|---|
| Φ | 261 steps | 0.421 | 0.387 | 0.192 | 19/23 traj |
| **Φ_projected** | 261 steps | **0.475** | 0.387 | 0.138 | **23/23 traj** |
| distance to x*_NBS | 261 steps | 0.065 | 0.387 | 0.548 | 2/23 traj |

Φ_projected falls net over **every one of the 23 governed trajectories**, while
distance to x*_NBS rises on 21 of 23 and `fit_contraction` puts median
**ρ = 1.111** (range 0.865–1.411, 21 fits) — formally a *divergence* rate.

Both are true and consistent. The `cost_floor` row is active on 72% of these
rounds, so the negotiation settles at a **constrained** rest point on the
boundary, not at the unconstrained bargaining solution. Φ_projected is built to
vanish there (`energy.py:129` — the field at a constrained equilibrium is
nonzero but points into the constraint); distance-to-NBS is not, and reading it
alone would call a converged negotiation divergent.

This is the funnel effect seen *dynamically*. The dissertation measured it on
settled terms only; here the whole path is visible walking off the bargaining
solution onto the boundary and stopping there. See `off09_trajectories.png`.

## The ungoverned control does the opposite

| measure (arm A, ungoverned) | n | down | flat | up | net down |
|---|---|---|---|---|---|
| Φ | 39 steps | 0.231 | 0.179 | 0.590 | 2/20 traj |
| Φ_projected | **0 steps** | — | — | — | — |
| distance to x*_NBS | 39 steps | 0.590 | 0.179 | 0.231 | 16/20 traj |

Ungoverned negotiations drift *toward* x*_NBS (ρ = 0.883, 5 fits) while their
force imbalance *grows*. And Φ_projected is defined on only **13 of 64**
ungoverned states, never on two consecutive rounds — the states sit outside
C(θ), where the tangent cone does not exist. The empty panel in the figure is
that fact, not a missing series.

## Three cautions on these numbers

1. **The comparison is underpowered on one side.** 261 governed steps against
   39; 23 governed trajectories against 20, but the ungoverned ones are 2–5
   rounds long. The direction of the contrast is unambiguous; a rate
   *difference* is not something 39 steps should be asked to carry.
2. **38.7% of governed steps are exactly flat** — the filter pins terms on the
   boundary and the seller re-proposes the same point. This matters when
   reading the stock table: `analyse_trajectories.py` prints one "frac dec"
   column computed as `diff <= 1e-9`, which counts a flat step as a decrease
   and so reports 0.81 where the strict figure is 0.421. `analyse_off09.py`
   separates down/flat/up for this reason.
3. **Still a one-dimensional trajectory.** Quantity is constant on every one of
   these paths and deadline is 0.0 throughout. Convergence here is convergence
   in price alone.

## What this answers, and what it does not

Answered: *can convergence be observed live under a binding contract?* **Yes** —
23 of 23 governed trajectories contract in Φ_projected, on a contract whose cost
floor is active on 72% of rounds, at a median of 10.5 rounds.

Not answered: *does the filter change the convergence rate?* The arms are not
comparable as they stand. Governance changes the destination (constrained rest
point vs bargaining solution), the certificate that is even defined
(Φ_projected exists on 285/285 governed states, 13/64 ungoverned), and the
length (median 10.5 vs 2.0). There is no common quantity to compare rates on,
which is a stronger statement than "the rates are similar".

## Next, if this is taken further

A scenario with a live non-price dimension would make the trajectory
two-dimensional and the rest point interior on at least one axis, which is what
a rate comparison needs. Quantity is the cheaper route (finding 3).
`zone_position` is not the lever (finding 4). No run has been made and none
should be without a go — cost would be ~£0.15 for a 1-seed pilot, ~£1 for a
5-seed A/B.

---

# RESULTS — phase 3, the quantity pilot

**Run 2026-09-14 on `quantity_off09_3_9`, arms A and B, 1 seed each, γ = 0.4,
T_max = 6, gemini-2.5-flash minimal reasoning.** Predictions were registered in
`PREREGISTRATION-quantity.md` and committed (`3d708f0`) before the first run.

## Scoring the registered predictions

| | prediction | threshold | observed | verdict |
|---|---|---|---|---|
| **P1** | arm A moves quantity | ≥ 10% of continuation rounds | 12.5% (2 of 16) | **held literally, failed in substance** |
| **P2** | quantity duals active in arm B | ≥ 20% of governed rounds | **0.0%** (0 of 40) | **falsified** |
| **P3** | a rest point with `cost_floor` + a quantity row both active | ≥ 1 pair | 0 pairs (one pair had `budget` + `cost_floor`) | **falsified** |
| **P4** | Φ_projected net down in arm B | ≥ 80% of trajectories | 75% (3 of 4) | **falsified** |
| **P5** | median arm B length | ≥ 4 rounds | 2.5 | **falsified** |

Four of five falsified. P1 needs the qualification, and the reason it needs one
matters more than the score.

**P1 held on the number and not on the intent.** Both arm A quantity moves were
*downward* — `3 → 1` and `3 → 2`, an item being dropped from the basket. That is
the identical artefact the baseline shows across the 3,865 thesis rounds. **The
ungoverned agents never once proposed a larger order**: 0 of 16 rounds carried
`q` above `q_min`. The volume clause did not make the buyer bulk-buy. I set the
threshold on "quantity moves" when what I meant was "quantity is negotiated
upward", and the looser wording let a null pass.

## What actually happened, which no prediction anticipated

**In arm B the seller did upsell, and the filter cut it back.** Seven of 40
governed rounds carried `q` above `q_min`, and the filter changed quantity on
**6 of 40 rounds (15.0%)** — the first active quantity control anywhere in this
project:

| pair | proposed | applied | duals active |
|---|---|---|---|
| b0002\|c0001 | p 5.58, q 4 | p 5.79, **q 2** | budget, cost_floor |
| b0002\|c0001 | p 5.79, **q 6** | p 5.79, **q 2** | budget |
| b0004\|c0002 | p 6.71, q 2 | p 7.19, **q 1** | — (opening projection) |
| b0004\|c0002 ×3 | p 6.71, q 2 | p ~7.3, **q 1** | budget, cost_floor |

**And this is why P2 was falsified while its underlying reasoning held.** The
pre-registration argued the QP would be forced to cut quantity because price is
floored at `c` and `c·(q_min+1) > B`. That is exactly what happened. But the row
doing the work is the **budget** row, not a quantity row: `h₁ = B − pq` is
itself bilinear in `(p, q)`, so it delivers a two-dimensional correction on its
own. The `q_min`/`q_max` box rows never bind, because the agents sit at `q_min`
by construction and approach the box from the inside. P2 measured the wrong
instrument for a mechanism that did occur.

Note `b0002|c0001` proposing `q = 6` against `q_max = 4` and being returned to
`q = 2` rather than to 4 — the nearest point on the `q` axis. The budget row,
not the box, decides where it lands.

## Three cautions, and one confound worth naming

1. **n = 1 seed.** P4 is 3 of 4 trajectories: a single path decides an 80%
   threshold. Setting that threshold for a one-seed pilot was a design error on
   my part, not an informative result.
2. **Arm A showed 0 upsells and arm B showed 7, on identical prompts.** That
   difference should not exist — θ and the scenario text are the same, and only
   the filter differs. Either it is one-seed variance, or the filter's rewritten
   proposals change what the seller sees on the next turn and so change its
   behaviour. **This is a confound in the design, not a finding**, and it cannot
   be separated without seeds.
3. **Negotiations got shorter, not longer.** Median 2.5 rounds against off09's
   10.5 on identical θ. The volume clause gives the seller a concession that is
   not a price cut, and the negotiation appears to end sooner as a result.

## What this answers

The 2-D route is **not** closed by the agents — the seller will upsell when
told it may, and the filter will correct it. But quantity is not *negotiated*:
it is proposed once and clipped, rather than converging over rounds. The
trajectory is still one-dimensional in the sense that matters for a rate,
because the second axis is a step, not a path.

A rate comparison still has no common quantity between arms, for the reasons
in phase 2, and now for a fourth: the arms differ in how often the seller
upsells at all.

## Cost

Two live runs, 1 seed each. Prior notes put a 1-seed pilot at ~£0.15, so
**≈ £0.30 total**, against the £5 ask-first threshold. I do not have exact
per-run token telemetry — the `client_metrics_*.json` counters are cumulative
for the client, not per-run — so this is an estimate from the historical
figures, not a measurement.

One wasted invocation cost nothing: `arm_a_no_contract.py` defaults to
**replay**, not live, so the first arm A call re-evaluated θ against the
pre-recorded `baseline_v1..v5` schemas (run on stock `mexican_3_9`) instead of
running my scenario. No API spend, and no result; it was re-run with `--live`.

## If this goes further

The next question is whether the arm A/arm B upsell asymmetry is real. That is
5 seeds per arm, ~£1.50, and it is worth more than adding a third dimension.
Nothing has been run beyond the two pilots above.

---

# RESULTS — phase 4, the upsell asymmetry

**Run 2026-09-14, seeds v2–v5 added to the v1 pilot, 5 per arm.** Predictions
registered and committed (`02e6bc3`) before the first new run. 57 arm A rounds,
204 arm B rounds.

## All five predictions held

| | prediction | threshold | observed | verdict |
|---|---|---|---|---|
| P6 | arm A upsells at all | ≥ 1 round | 4 | **held** |
| P7 | arm B rate > arm A, Fisher | p < 0.05 | **p = 8.7 × 10⁻⁹** | **held** |
| P8 | upsells follow a price alteration | ≥ 2/3 | 87 of 94 = 0.926 | **held** |
| P9 | quantity duals stay quiet | < 5% | **0 of 204** | **held** |
| P10 | the shortening replicates | median < 6 | 2.5 | **held** |

Upsell rate, `q > q_min` on `x_proposed`: **arm A 4 of 57 (7.0%)**, **arm B 94
of 204 (46.1%)**. The pilot's 0-of-16 was small-sample — ungoverned sellers do
upsell occasionally — but the asymmetry is real and large.

## P8 is not vacuous, and the stronger test is cleaner

P8 as registered is weak: the filter alters price on most governed rounds, so
"preceded by a price alteration" could be near-automatic. Checking the base
rate:

| | preceded by a price alteration |
|---|---|
| upsell rounds | 87 of 94 = **92.6%** |
| non-upsell rounds | 69 of 110 = **62.7%** |
| all rounds | 156 of 204 = 76.5% |

Upsells are markedly more likely to follow a price alteration than other rounds
are, so the test carries information. The sharper version — upsell rate
conditional on whether the filter has yet touched price in that pair:

| | upsell rate |
|---|---|
| **before** any price alteration | 7 of 48 = **14.6%** |
| **after** a price alteration | 87 of 156 = **55.8%** |

Fisher exact **p = 3.4 × 10⁻⁷**. The seller's upsell rate **quadruples** once
the filter has altered its price. And 14.6% before alteration sits close to arm
A's unconditional 7.0%, which is what a baseline propensity should look like.

## The finding

**H_redirect is supported and H_noise is rejected.** The contract does not only
constrain the negotiation, it **redirects it onto a different axis**: holding
price at the cost floor pushes the seller to the volume lever the scenario told
it about. The filter changes *what the agents negotiate over*, not merely what
they are permitted to agree.

Nothing in the dissertation measures this. It is a claim about mechanism rather
than about safety, and it is the most interesting thing this exploration found.

Two qualifications it needs:

1. **It is a property of this scenario's prompts.** The seller had a volume
   lever because `VOLUME_SELLER_CLAUSE` gave it one. What generalises is
   "blocked on one axis, an agent will use another it has been offered" — not a
   claim about quantity specifically.
2. **5 seeds × 3 customers is 5 draws of the same 3 situations.** The p-values
   describe seed variance under a fixed scenario, not sampling error over
   baskets. The effect is large enough that this is unlikely to overturn it,
   but the caveat is the same one that applies everywhere in this project.

## The budget row is still doing all the work

`q_min`/`q_max` duals: **0 of 204 governed rounds**, confirming the pilot.
Active duals are `cost_floor` (137) and `budget` (87). Quantity is corrected —
often — but always through `h₁ = B − pq`, which is bilinear in `(p, q)` and so
delivers a two-dimensional correction without any quantity row ever binding.

This has a design consequence worth recording: **the box rows on quantity are
inert in this testbed.** They were specified, they are checked, and they have
never once bound in any run in this project. A reader of θ would reasonably
assume `q_max` is what stops an upsell. It is not.

## Cost

Eight live runs at roughly £0.15 each, **≈ £1.20**, against the £5 ask-first
threshold. Cumulative for the whole exploration: **≈ £1.50**. Estimated from
the historical per-run figures in `docs/notes/`, not measured — the
`client_metrics_*.json` counters are cumulative for the client rather than
per-run.

## Where this would go next, not run

The claim to test is the general one, and it needs a scenario where the second
axis is *not* quantity — delivery speed is the obvious candidate, and it needs
`deadline_active=True` plumbed through a copied runner (finding 3). If blocking
price redirects onto whatever lever exists, that is a property of contract
enforcement worth stating. If it only works for quantity, it is a quirk of the
budget row being bilinear.

---

# RESULTS — phase 5, the delivery axis. The redirection does NOT generalise.

**Run 2026-09-14, 5 seeds per arm on `delivery_off09_3_9`.** θ byte-identical
to off09, `deadline_active` False, so the filter cannot touch `d`
(`rewrite_proposal` carries `estimated_delivery` through untouched). Predictions
registered and committed (`8b7a214`) before the first run. 136 arm A rounds,
228 arm B.

| | prediction | threshold | observed | verdict |
|---|---|---|---|---|
| P11 | delivery axis is alive | ≥ 50% observed | **100%** (228/228) | **held** |
| P12 | `d` moves | ≥ 10% of continuations | 29.4% (55/187) | **held** |
| P13 | **`d` moves more after price is blocked** | p < 0.05, upward | **47.1% → 25.5%, reversed** | **falsified** |
| P14 | arm B moves `d` more than arm A | p < 0.05 | A 40.8% > B 29.4% | **falsified** |
| P15 | control: no volume clause → no upsell | < 15% | **0 of 228 (0.0%)** | **held** |

## The delivery axis opened, and nothing redirected onto it

P11 is a result in its own right: `estimated_delivery` was populated on **228 of
228** proposals, against **0 of 4,126** rounds in every prior run in this
project. The field was always available and optional; nothing had ever asked for
it. `d` took values 1, 2 and 3 days and moved on 29.4% of continuation rounds.

But P13 reversed. Deadline movement **falls** after the filter alters price —
47.1% before, 25.5% after, p = 0.021 — where the quantity run rose 14.6% → 55.8%.

## Ruling out the obvious confound

If the filter simply froze everything, a fall in `d` would mean nothing. It does
not. Within arm B of the delivery scenario, before vs after the filter alters
price in that pair:

| dimension | before | after | Fisher p |
|---|---|---|---|
| price | 47.1% | **83.0%** | 3.1 × 10⁻⁵ |
| quantity | 0.0% | 0.0% | 1.0 |
| deadline | 47.1% | **25.5%** | 2.1 × 10⁻² |

Price movement *rises* sharply while deadline movement falls. There is no
general freeze; the seller stays engaged and stays on price.

## So H_general is rejected, and the refined claim is narrower

Blocking price does **not** push the seller onto whatever lever it has been
offered. It pushed it onto quantity and not onto delivery, with both clauses
written the same way and both axes offered the same way.

The plausible reason is structural. **Quantity sits inside the binding
constraint and delivery sits outside every constraint.** `h₁ = B − pq` is
bilinear in `(p, q)`, so when price is pinned at the cost floor and the budget
still binds, altering `q` is the only remaining way to change whether a deal
fits. Delivery changes nothing about feasibility, so a seller in a price fight
has no reason to reach for it.

The claim that survives is therefore **not** "enforcement displaces activity
onto unmonitored axes". It is the narrower and more mechanical:

> **When a filter pins one term of a multiplicative constraint, agents explore
> the other term of that same constraint. Axes outside the constraint set are
> not taken up.**

Less sweeping than the phase-4 write-up implied, and better supported: it now
rests on a positive case and a negative control rather than on one scenario.

## A measurement distinction that could produce a false contradiction

Phase 4 counted upsells on `x_proposed`; the table above counts movement on
`x_applied`. On the **quantity** scenario these diverge sharply:

| quantity scenario, arm B | before | after |
|---|---|---|
| agent **proposes** `q > q_min` (`x_proposed`) | 14.6% | **55.8%** |
| applied `q` **moves** (`x_applied`) | 35.7% | **0.0%** |

Both are correct and they are not in conflict. After the filter starts binding,
the agent proposes upsells far more often *and* the filter clips every one of
them back to `q_min`, so the applied quantity stops moving entirely. The first
measures what the agent tried; the second measures what the market saw.

For delivery the distinction is empty — the filter never rewrites `d`, so
applied and proposed are the same series. The pre-registration fixed
`x_proposed` for upsell and `x_applied` for deadline movement, which is why the
two analyses use different fields.

## What P15 settles about phase 4

Arm B upsell rate on this scenario, with no volume clause: **0 of 228 rounds**,
against 46.1% on `quantity_off09_3_9`. The quantity behaviour was caused by the
clause, exactly as the phase-4 write-up assumed. A seller blocked on price does
not invent a second axis; it uses one it has been given, and only if that axis
is coupled to the constraint.

## Cost

Ten runs, ≈ £1.50. Cumulative for the exploration: **≈ £3.00**, estimated from
the historical per-run figures rather than measured.
