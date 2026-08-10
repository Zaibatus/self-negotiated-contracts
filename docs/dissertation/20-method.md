# Chapter 4 — Method and testbed

**State: DRAFT, 2026-08-10.** Sources: `src/marketplace_integration/`, the arm
notes, and `formulation.md` §7. Numbers and reproduction commands stay in the
notes; this chapter is the design and its justification.

---

## 4.1 The testbed

All live experiments run on **Magentic Marketplace** (Microsoft Research), a
two-sided marketplace simulator in which LLM-backed buyer and seller agents
exchange messages through a server, propose structured orders and settle deals.
It is used unmodified: the agent classes, the prompts, the search algorithm and
the message schema are the shipped ones. The only artefacts this work adds are
a protocol subclass, a contract layer beneath it, and scenario YAML.

That restraint is not fastidiousness — it is what the central claim requires.
If the guarantee held only for agents this work had also written, it would be a
statement about those agents. Because nothing in the enforcement path inspects
the agent, the prompt or the model, the guarantee is a property of the
marketplace, and the model-dependence experiment (chapter 5) is a test of that
rather than a formality.

### The enforcement point, and why it is the protocol

`SimpleMarketplaceProtocol.execute_action` is the single funnel through which
every agent-to-agent `SendMessage` passes, and `MarketplaceLauncher` accepts a
protocol instance by injection. `GovernedMarketplaceProtocol` subclasses it,
intercepts `SendMessage`, and applies the contract layer before delegating to
the stock implementation.

Placing enforcement here rather than in the agents buys three things:

- **A view of every concurrent negotiation at once.** The coupling clause of
  §8 — a shared seller capacity — is one constraint row touching several pairs
  simultaneously, and its dual is a market-wide shadow price. Only the protocol
  can see the pairs it couples.
- **Agent-agnosticism**, as above.
- **A single auditable surface.** Everything the regulator does is one code
  path, so "what was enforced" is a question with one answer.

Magentic's own `run_marketplace_experiment` hardcodes its agent classes, so
this work supplies its own runner (`src/marketplace_integration/runner.py`)
that constructs the same components with the governed protocol injected. This
is a wiring difference, not a behavioural one.

### Three deliberate asymmetries

These are results about what can be governed, not shortcuts.

**Only seller moves are projected.** An `OrderProposal` is a structured message
carrying `items[].unit_price`, `quantity`, `total_price` and
`estimated_delivery`; its terms are *read*, not inferred, so the extraction
risk that §7.2 flags does not apply to the side emitting the binding numbers. A
buyer's counter-offer is prose. Rewriting it would mean putting words in an
agent's mouth, and this work restricts itself to quantitative terms.

**Two trajectories are kept per pair.** The *binding* trajectory holds only
proposal terms and is what the barrier constrains — the state of the contract
is what is actually on the table. The *observed* trajectory interleaves the
buyer's extracted counter-offers and is what the round-pair energy consumes.
Keeping them separate is what allowed the fifth bug in §4.5 to be scoped
precisely rather than invalidating everything.

**The first proposal is projected, not recovered.** A DCBF governs
*transitions* and needs a previous state; an opening offer has none. Forwarding
a breaching opener while the barrier recovered geometrically over subsequent
rounds would be a knowing breach, so the opening state is projected into C(θ)
once, using γ = 1 by construction. This has a consequence worth stating plainly
because it explains a null result: since the great majority of governed rounds
*are* openings, and openings are projected at γ = 1, the arm's configured γ
never touches the deciding step in this regime. That is why the γ sweep finds
no γ-dependence, and it is a property of short negotiations rather than
evidence that γ does not matter.

## 4.2 From scenario data to θ

Nothing here invents a number the data does not already contain. Two fields,
both present in every shipped Magentic dataset and — before this work — read by
no code path and no prompt:

| field | becomes | why |
|---|---|---|
| `Business.min_price_factor` | cost floor **c** | the seller's floor as a fraction of list price |
| `Customer.menu_features` | budget **B** | the sum of the buyer's stated reservation prices |

Quantity bounds come from the requested basket (q_min = requested quantity,
q_max = a configurable multiple); the deadline band is a modelling parameter.
`ContractRegistry` builds θ for every (business, customer) pair.

Two classes of pair are then separated rather than defaulted, because a
contract that constrains nothing and a contract that cannot be satisfied both
look like governance in an aggregate:

- **Undefinable** — the business stocks none of the customer's requested items.
  18 of 27 pairs on the working scenario. Their messages pass ungoverned and
  are counted.
- **Unsatisfiable** — c·q_min > B, so C(θ) is empty and no terms could ever
  comply. 4 of the 9 definable pairs. Projecting into an empty set is not a
  safety operation, so these run in monitor mode and their breaches are
  reported separately.

The satisfiability test is closed form (c·q_min ≤ B), which matters because it
is checked on every proposal.

## 4.3 The filter

Each governed transition solves a quadratic program: find the correction u
nearest to the agent's proposed move, in the metric M = diag(σ)⁻¹ with
σ = (1, 10, 5), subject to the DCBF row for every active constraint plus a
penalised slack. One scaled unit is £1, or 10 units of quantity, or 5 days.

Three implementation points are load-bearing and each cost a debugging cycle:

**The objective is in the metric.** An early version minimised the raw
Euclidean norm, which silently weights a pound against a day.

**Row scaling is a change of variables, not a re-weighting.** Constraint rows
differ in magnitude by orders of magnitude, so the QP is preconditioned by
writing δ = s·δ̄ and giving the slack weight ρ·s². Implementing the same idea as
a *re-weighting* of the slack penalties instead made budget-row slack roughly
10⁶ times cheaper than the others, and trajectories left C(θ) while the solver
reported success. The distinction is the difference between a guarantee and a
plausible-looking log.

**The budget row is bilinear and is linearised per round**, so a large
single-round jump is an attack surface. It is closed by backtracking on the
true h, which makes "zero violations of the true h" hold by construction rather
than by luck.

Terms are written back onto the proposal at currency precision, quantising
*into* the safe set — see §4.5.

## 4.4 Scenarios

Three, forming a deliberate progression. Only YAML differs; the marketplace,
the agents and the prompts are untouched throughout.

| scenario | construction | role |
|---|---|---|
| `mexican_3_9` | shipped with Magentic | the stock control |
| `bargain_3_9` | `menu_features` rewritten so B binds; buyer told its budget | the working scenario |
| `undisclosed_3_9` | identical, **minus** the sentence telling the buyer | isolates the benefit |

`bargain_3_9` exists because on the stock scenario the budget does not bind and
the safety layer has almost nothing to do. Authoring it produced the most
instructive negative result in this dissertation: **it changed more than the
variable it was authored to change.** The edit that makes the budget bind also
*tells the buyer what the budget is*, and the buyer then polices it — so offers
got much worse (86% breaching) while settled deals got much *cleaner* (1 in 12,
£0.00 overspent). The scenario built to demonstrate the benefit of enforcement
demonstrated instead that an informed counterparty substitutes for it.

`undisclosed_3_9` is the correction, and it is constructed as a one-variable
difference by construction rather than by inspection: the same generator with
`--no-disclose-budget`, which suppresses exactly one appended sentence. θ is
derived from `menu_features`, which is untouched, so the platform knows the
same ceiling. Verified before use — θ identical on all 9 pairs, the
unsatisfiable set identical, the business descriptions byte-identical, and the
customer request differing only by the removed clause.

Standard configuration unless stated: γ = 0.4, T_max = 6, 5 seeds,
`gemini-2.5-flash` at minimal reasoning effort.

### The arms

| arm | mode | θ from | question |
|---|---|---|---|
| A | `off` | — | what does an ungoverned marketplace do? |
| B | `filter` | scenario | does enforcement bound exposure? |
| C | `filter` | **inferred from the agents** | does a self-negotiated contract govern? |
| D | `monitor` | scenario | how much of arm B is detection, how much correction? |
| E | RL-AR | — | deferred |

Arms A and D are behaviourally identical by construction — the monitor changes
no message — which makes every A/D difference an estimate of the noise floor.
This is the only reason any effect in chapter 5 can be called large.

## 4.5 Five integration bugs, and why they belong in a methods chapter

Each of the following passed a complete test suite. Each was invisible for the
same reason: **the tests asserted on a plausible-looking surface rather than the
one that decides what the counterparty actually receives.** Reporting them is
not confession; for anyone building a safety layer it is the most transferable
content in this dissertation, because the failure mode is systematic rather
than incidental.

**1. The wire copy — enforcement that enforced nothing.**
The regulator computed the corrected proposal and returned it as
`action.model_copy(update=...)`. But the server route persists the request
object it was *handed* (`ActionRowData(request=request, ...)`), and the
recipient reads the message back out of the database. So every correction was
computed, logged, and discarded; the counterparty received the original terms.
Five seeds of arm B enforced nothing while the certificate log recorded
corrections to 11.58 and 11.40 and the database, the buyer and the seller's own
confirmation all showed 13.76 and 11.12. The tests passed because they asserted
on `result.content`, which does carry the rewrite, rather than on what the
caller was left holding. Fixed by mutating the request in place — which is the
enforcement point, not a shortcut around one — and pinned by a test that
asserts on the request object *after* the call.

**2. Currency quantisation.** Prices round to the cent; the safe set does not.
The QP's exact answer generally is not on a cent boundary, and rounding it
outward breached by exactly −0.01 on ten of ten governed rounds of one pair.
Fixed by quantising *into* C(θ). Any "zero breaches" claim has to state whether
it survives writing the terms back in the currency's own precision; this one
does now, and did not before.

**3. The Φ_proj active-row test.** The projected certificate selected
constraint rows with h_i ≤ tol, which includes rows the state has already
*violated*. The tangent cone of a constraint you are outside is not a
meaningful object, and the function returned a confident 0.00 at the opening of
nearly every ungoverned negotiation — which reads as instant convergence.
Fixed: active means |h_i| ≤ tol, and Φ_proj returns NaN outside C(θ), because a
state in breach needs recovery rather than convergence and NaN propagates
loudly through any aggregate that forgets to exclude it. Two existing tests
failed on the fix; both had fixtures sitting outside their own contract's
deadline band and had passed only because the old code never checked.

**4. The intervention logging gap — which produced a false finding.**
Opening projections were recorded with `intervention = 0`, because they do not
pass through the barrier QP and so arrive with no solver result. They are
unambiguously interventions: the terms the buyer receives differ from those the
seller sent. The consequence was a published claim. The filter was reported as
binding on 11.1% of governed rounds — a "light touch" — when the true figure is
**88.9%**, of which 21 of 24 are opening projections. That number was the
evidence for a headline finding, "enforcement is prevention", which stood for
two days before recomputation showed the enforced arm's continuation-round flag
rate (0.75) is in fact the *highest* of the three arms (A 0.72, D 0.54). The
finding is retracted in chapter 5.

**5. The buyer's counter-offer was the seller's own quote.**
Buyers habitually restate the price on the table before naming their own:
*"The current quote of $13.76 is above my budget of $11.58."* The extractor took
the first money figure, so it recorded a counter-offer at $13.76 — the number
the seller had just asked for — and discarded $11.58, the only figure in the
sentence the buyer owns. Both halves are wrong: a fabricated move to the
seller's own ask, and the real position dropped. Across the 25 stored runs,
**110 of 125 extracted buyer moves (88%) were echoes of this kind.** Fixed by
considering every figure, discarding those equal to the price on the table, and
taking the first survivor.

Its scope is smaller than the rate suggests, and saying so precisely matters:
the corrupted surface is the *observed* trajectory. The drift, funnelling,
compression and safety results are computed on the *binding* trajectory or on
database outcomes and are unaffected; the section 11 convergence report is not.

**What the fifth one adds to the lesson.** It was latent in every arm from the
first run and became visible only when arm C became the first component to
*read* the buyer's position rather than merely log it. A value that nothing
depends on is a value that nothing checks. A safety layer accumulates such
values — logged, plotted, never load-bearing — and each is a finding waiting to
be wrong.

**The common thread, and the discipline it implies.** In every case a
reasonable-looking test passed. The tests that would have caught them assert on
the surface the counterparty is exposed to: the request object after the call,
the terms at currency precision, the certificate at a state known to be in
breach, the intervention magnitude on a round known to have been rewritten, the
extracted position against a message known to quote two prices. The rule this
work adopted after the first bug and has applied since is *pin behaviour on the
surface that decides the outcome, and prefer a test that fails loudly on a
known-hard case to one that passes on a happy path*.

## 4.6 Measurement

Outcomes are measured by **replaying the database**, not by trusting the
regulator's own log — a regulator that believes it enforced something is
exactly the failure mode of bug 1. `replay_schema` reads the settled deals and
recomputes breach against θ independently.

Reported per arm: proposals offered and the fraction breaching; deals settled
and the fraction breaching; overspend and value transacted; and, from the
certificate log, breaches and corrections per governed round. Deals are
classified as *within*, *trivial* (breaching by less than a cent), *meaningful*
or *infeasible* (on an unsatisfiable pair), so that a breach of £0.001 and a
breach of £6.15 are never averaged together.

Statistical practice, stated because this work got it wrong twice and corrected
it twice: differences are expressed against the **standard deviation of a
difference** computed from per-arm seed SDs, never as a ratio to a single
observed A/D gap — one realisation is not an estimate of spread. Where an
effect is categorical (every seed 15/15 against every seed 0/13) it is reported
as categorical, which is a stronger and simpler statement than any multiple of
a noise estimate.
