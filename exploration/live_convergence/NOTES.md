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
