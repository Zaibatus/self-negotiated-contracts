# self-negotiated-contracts

Formal safety and convergence guarantees for LLM-agent negotiation: **contracts
as controllers**. MSc thesis, Imperial College London.
Supervisor: Dr Pietro Ferraro; co-supervisor: Haozhe Tian.

**In one line.** A negotiated contract is a controller for the negotiation
itself: a discrete-time control barrier function guarantees no contract breach
at any round, and two anchor-free certificates built from current payoff
gradients certify that the haggling reaches an agreement and that it stops.

**In one more.** The rest point of the concession dynamics turns out to be
exactly the Nash bargaining solution, so the equilibrium is a property of the
agents' preferences rather than of whatever update rule they happen to run.

Theory: [`docs/formulation.md`](docs/formulation.md) (v2, definitive).
v1 is archived as [`docs/formulation_v1.md`](docs/formulation_v1.md); it defined
the equilibrium as the fixed point of a concession *heuristic*, which was
circular, and is superseded.

---

## The architecture

A contract is **C = (θ, γ, τ)**:

| | | |
|---|---|---|
| **θ** ∈ ℝ⁶ | `(B, c, q_min, q_max, d_min, d_max)` | the agreement — defines the safe set C(θ) = {x : h(x; θ) ≥ 0} over terms x = (p, q, d) |
| **γ** ∈ (0,1] | DCBF enforcement rate | how fast the filter lets the draft approach the boundary. Also an economic policy parameter: it displaces where the negotiation settles and moves the shadow prices |
| **τ** | `(T_max, ε)` | the liveness obligation, discharged by escalating friction |

Two layers, because invariance and convergence are separate obligations and
there is a standing counterexample of trajectories that stay perfectly safe
forever and never settle:

- **Safety** — a minimally-invasive QP enforcing `h_i(x_{k+1}) ≥ (1−γ)h_i(x_k)`
  on every proposal. Inside C(θ) this is forward invariance; from outside,
  geometric recovery.
- **Convergence and termination** — two certificates, because one scalar cannot
  do both jobs: at the equilibrium the two agents' gradients are large and
  opposite, and only their *sum* vanishes.
  - **Φ(x) = ‖F(x)‖_M** — force imbalance on the draft. Zero exactly at the
    Nash bargaining solution. Answers *does it reach the deal?*
  - **G_κ(x) = Σ_i [ρ‖∇Û_i(x)‖_M − κ]₊** — residual private incentive net of
    friction. Answers *does it stop, and when?*

Both are built from current quantities only — neither needs to know where the
agreement will land, which matters because under a binding constraint it lands
somewhere with no closed form.

---

## Layout

```
src/
  contract.py                theta, ControllerSpec, the safe set, refinement order
  payoffs.py                 utilities, acceptance model, concession field, NBS
  certificates/
    dcbf.py                  OSQP filter: status checks, exact duals, true-h backtracking
    energy.py                Phi, Phi_proj, G_kappa, friction window, stability radius
    metrics.py               per-round records and liveness bookkeeping
  marketplace_integration/
    terms.py                 OrderProposal/TextMessage -> x = (p, q, d)
    theta.py                 scenario YAML -> a contract per (business, customer) pair
    payoff_estimation.py     lambda by MLE; cost-benefit rationalizability, tested
    protocol.py              GovernedMarketplaceProtocol: filter | monitor | off
    runner.py                run_governed_experiment
    replay.py                evaluate theta against a finished run, no LLM calls
experiments/
  arm_a..arm_e.py            the five arms
  _common.py                 the section 11 report
  certificates/              the prototype experiments, kept byte-identical
data/bargain_3_9/            the bargaining scenario (generated, YAML only)
docs/                        formulation, supervision docs, integration notes
```

## Arms

| arm | contract | regulator | status |
|---|---|---|---|
| **A** no contract | — | `off` | measured on both scenarios ([mexican](docs/notes/2026-08-04-arm-a-ungoverned-breach-rate.md), [bargain](docs/notes/2026-08-05-arm-a-bargain-scenario.md)) |
| **B** imposed | θ from scenario data | `filter` | runnable |
| **C** negotiated | θ agreed by the agents | `filter` | **scaffold** — the θ-negotiation pre-phase is the open piece |
| **D** monitored | θ from scenario data | `monitor` | runnable |
| **E** RL-AR | θ from scenario data | learned β(s) | **deferred** — π_reg *is* the filter output, β(s) a state-dependent γ |

B against D is what isolates *projecting* from *flagging*: same θ, same
bookkeeping, and the only difference is whether the regulator rewrites the
proposal. Any welfare gap between them is the price of the correction, not of
the contract.

## Experiments → findings

| file | finding |
|---|---|
| `certificates/dcbf_negotiation.py` | **F1** DCBF-QP filter: breaches 9.9% → 0%, convergence and surplus preserved. **F2** invariance ≠ convergence counterexample |
| `certificates/lyapunov_layer.py` | **F3** contraction exact vs theory (0.3164 = (1−r)⁴). **F4** CBF–Lyapunov tension ≈ 9.6% of round-pairs. **F5** naive composed certificate fails under coupling |
| `certificates/gne_shadow_price.py` | **F6** shadow prices from KKT multipliers; scarcity + conservatism-premium decomposition |
| `certificates/farstart_experiment.py` | naive anchor plateaus at its own squared anchor error (510.3 vs 509.9 predicted); the anchor-free energy → 0 unaided |
| `certificates/payoff_model.py` | utilities; NBS closed form verified against numerical Nash-product maximisation |
| `certificates/payoff_dynamics.py` | **E1** concession-field zero = Nash bargaining solution exactly (Prop. 1) |
| `certificates/payoff_validation2.py` | **E8** T_max vs surplus-loss trade-off. **E9** stability radius ≈ 1 scaled unit, λ_max = −6.86 at the NBS |
| `certificates/payoff_validation3.py` | **E11** Φ decreases on 96% of round-pairs, 99.98% of max surplus. **E12** Prop. 2: no constant friction works. **E13** projected certificate |
| `certificates/e13_dcbf.py` | **E13 rerun under the real filter** (discharges §10.5). The residual is neither the clip nor step decay; the new result is the γ-dependent boundary layer |
| `certificates/audit.py` | reliability probes: transient-only contraction estimator, SLSQP status failures, drift-outside-a-ball |

Corrected claims and scope: `docs/formulation.md` §10.

---

## Running it

```bash
uv sync --extra dev          # Python 3.13; magentic-marketplace as a path dep
uv run pytest -q             # 154 tests, no API calls, no database
```

Offline, no API spend:

```bash
# the propositions, under the real filter
uv run python experiments/certificates/e13_dcbf.py

# theta against the five recorded ungoverned runs
# (needs docker compose up in ../multi-agent-marketplace, and its .env sourced)
uv run python experiments/arm_a_no_contract.py \
    --data ../multi-agent-marketplace/data/mexican_3_9
```

Arm A reports three numbers and they do not say the same thing:

| | `mexican_3_9` (stock) | `bargain_3_9` (authored) |
|---|---|---|
| proposals **offered** breaching θ | 0.593 ± 0.029 | 0.858 ± 0.050 |
| deals **settled** breaching θ | 0.400 (6/15) | 0.083 (1/12) |
| overspend / value transacted | 0.52% | 0.00% |

The gap between the first two rows is the customer agent declining bad offers
unaided. The third row is magnitude: most settled breaches are a few pence.

`bargain_3_9` was authored to make the budget bind and **inverted the deal-side
result** — offers got much worse, deals got much cleaner. Every settled deal
lands exactly on the budget, because the edit that makes the budget bind also
tells the customer what it is, and the customer then polices it. Benefit of the
safety layer and buyer diligence are substitutes; the
[note](docs/notes/2026-08-05-arm-a-bargain-scenario.md) works through what
survives.

**Read the ± as seed variance, not sampling error.** Both scenarios have 3
customers, so 5 seeds are 5 draws of the same 3 situations — not 15 or 37
independent observations. Nothing here speaks to generalisation across baskets
or price levels.

The first live governed run:

```bash
uv run python experiments/arm_b_imposed.py \
    --data data/bargain_3_9 --gamma 0.4 --experiment arm_b_v1
```

Regenerating the bargaining scenario (YAML only — the marketplace, the agents
and the prompt templates are stock):

```bash
uv run python scripts/make_bargain_scenario.py --force
```

## Reading the results

Every run writes `results/<experiment>/`:

- `certificates.jsonl` — one record per intercepted proposal: terms before and
  after, the true (non-linearised) barrier values, intervention, slack, duals,
  solver status, and any fallback;
- `section_11.json` — the six measurements formulation §11 asks for, plus the
  cost-benefit rationalizability verdict.

Each §11 item either reports a number or states why the data does not support
one. On short transcripts most of them will not — a five-round negotiation
cannot identify an acceptance temperature — and saying so is the point. Items
(i) breach rate and (vi) shadow prices need no payoff model and survive
transcripts the model cannot be fitted to.

## Known scope limits

- **Quantitative terms only.** Clauses with no numeric template ("good faith")
  have no h(x) and are out of scope.
- **Coupling needs a scenario that has it.** In `mexican_3_9` each business
  serves exactly one customer, so the shared-capacity clause and the shadow
  prices cannot be reproduced there — use `mexican_33_99`.
- **The bargaining scenario is authored by us**, so it is a designed rather
  than naturally occurring negotiation. The stock scenario is the control that
  guards that claim.
- **Convergence is local** — the induced game is monotone within about one
  scaled unit of the agreement, not globally. That is a design instruction:
  the contract should confine the negotiation to the stable region.
- **Extraction is asymmetric.** Seller terms are read from structured fields;
  buyer counter-offers are regex-extracted from prose, and that is the whole
  residual trusted-computing-base surface.
