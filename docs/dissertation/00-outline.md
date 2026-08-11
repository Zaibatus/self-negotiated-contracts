# Dissertation outline — status map

**Started:** 2026-08-05. **Marks refreshed 2026-08-11** after arm C-meet (G1, G7 and G9 closed; G8 opened and now more pressing). **The experimental programme is closed.** Structure only; chapters point at their sources rather
than copying them, so a correction to `formulation.md` cannot silently diverge
from a chapter.

The point of writing this now is to surface argument gaps while there is still
time to run experiments that fill them. Every section carries one of:

| mark | meaning |
|---|---|
| **DONE** | written or measured, nothing outstanding |
| **RERUN** | needs an experiment, and which one is named |
| **OPEN** | theoretical obligation, not fixable by running anything |
| **DECISION** | blocked on supervision |

---

## Chapters — send-readiness

**Refreshed 2026-08-11.** "DRAFT COMPLETE" means the chapter says everything it
is meant to say, is consistent with the notes it draws on, and can go to a
supervisor as it stands. It does **not** mean prose-polished or figure-complete;
where a figure is still to be drawn that is named, because a missing figure does
not stop a chapter being read.

| # | file | state | send? | what is missing |
|---|---|---|---|---|
| 1 | `10-introduction.md` | **DRAFT COMPLETE** | **yes** | nothing blocking. Leads with the safety/convergence asymmetry and the four axes it is replicated on |
| 2 | `60-related-work.md` | **DRAFT COMPLETE** | **yes** | nothing blocking. CBF-LLM re-verified 2026-08-05 |
| 3 | `30-theory.md` | **DRAFT COMPLETE** | **yes, with a caveat** | it is a *section map* onto `formulation.md`, not standalone prose — send both, or say so. Three OPEN theoretical obligations are named in it |
| 4 | `20-method.md` | **DRAFT COMPLETE** | **yes** | nothing blocking. Includes all seven integration bugs |
| 5 | `40-results.md` | **DRAFT COMPLETE** | **yes** | all five arms and both scenarios. Figures 1–7 are specified but **not drawn** — the data exists for all of them |
| 6 | `50-limitations.md` | **DRAFT COMPLETE** | **yes** | nothing blocking. Single consolidated list, deduplicated from every source |
| 7 | `70-conclusion.md` | **DRAFT COMPLETE** | **yes** | nothing blocking. Remaining work ordered by impact; three deliberate gaps named separately |

**Send order, if sending piecemeal:** 5 → 1 → 7 first. Chapter 5 carries the
evidence and is where a supervisor's objections will land; 1 and 7 frame what it
does and does not establish. Chapters 2, 3, 4 and 6 are reference material and
will generate fewer questions.

**Nothing is blocked on an experiment.** The programme closed 2026-08-11 with
arm C-meet. Everything outstanding is drawing figures and prose.

## The argument in one page

1. LLM agents negotiating on a marketplace routinely propose terms that violate
   the contract their own scenario implies — **86%** of proposals when the
   budget binds, **73%** of governed rounds flagged under monitoring.
2. Nothing about the agents guarantees anything. A competent buyer declines
   almost all of it, so realised harm is small; but a tendency is not a bound.
3. A contract can be treated as a *controller*: a DCBF-QP at the marketplace
   protocol takes per-round exposure to **zero** without forking any agent.
4. Convergence and termination are separate obligations needing separate
   certificates, because at the bargaining solution the two agents' gradients
   are large and opposite and only their sum vanishes.
5. The rest point of the concession dynamics **is** the Nash bargaining
   solution, so the equilibrium is a property of preferences, not of the
   update rule.

## Gaps this exercise surfaced

Ordered by how much they threaten the argument.

**G1 — the benefit side is untested, and the scenario is why.** *(**CLOSED
2026-08-10** — `2026-08-10-undisclosed-budget.md`)*
`bargain_3_9` gave the filter almost nothing to prevent: the edit that makes the
budget bind also tells the buyer what it is, and the buyer then polices it. So
step 3 was demonstrated as a *bound*, not as harm averted. `undisclosed_3_9`
drops the buyer clause and changes nothing else. Result: ungoverned, **15/15
settled deals breach and £21.70 (7.93% of value) is transacted above a ceiling
only the platform knows**; under the filter, on governable pairs, **0/13 and
£0.00**. Categorical in every seed. That is the harm-averted number the thesis
lacked.

Two things it also produced, both propagated: **zero settled dispersion is not
diagnostic of enforcement** (arm A funnels too, to list price — G-funnel caveat
in the drift note), and **£6.15 of residual harm sits on an unsatisfiable pair
the filter deliberately does not act on**, which is now open design question
**G8**.

**G2 — coupling is entirely unexercised on live agents.** *(RERUN)*
§8's shared-capacity clause, the GNE displacement and the shadow prices — the
whole economic half of the thesis — have never run outside simulation, because
`mexican_3_9` has no business serving two customers. `mexican_33_99` does.
Blocked on the scale-vs-depth decision.

**G3 — termination is measured, never enforced.** *(OPEN)*
§6.3 says termination is *achieved* by escalating friction; the integration
computes G_κ from a schedule the agents never experience. So the liveness half
of §5 has no live evidence at all. Either enforce it and accept a second
intervention confounding arm B, or restate §6.3 as conditional.

**G4 — no live evidence for the convergence certificate, and it is harder than
it looked.** *(OPEN)* Φ's 96%-decrease result is under a tuned diminishing
step; live agents have no step schedule. **Worse, as of 2026-08-06: Φ has a
second zero far from the deal**, where acceptance collapses and both gradients
vanish, so a low Φ is ambiguous between "at the solution" and "nowhere near
it" — and live trajectories begin at 0.97–1.00 scaled units, right at the edge
of the certified monotone radius. Any live Φ reading needs a radius check
first. The dissertation proves convergence on gradient-ascent proxies and
demonstrates *safety* on LLMs; that asymmetry is now stated in chapter 1
rather than left for an examiner.

**G5 — n = 5 seeds × 3 customers throughout.** *(RERUN)*
Every empirical claim is five draws of three situations. The safety result
clears the noise floor (4.4 SD on the offered-breach contrast) so it
survives; nothing else does. More seeds
are cheap (~$0.10/run); more *customers* needs a larger scenario, which is G2.

**G6 — cost-benefit rationalizability is the bridge and is barely tested.**
*(RERUN)* §3 assumes only that agents move iff ρ‖∇Û_i‖ > κ, and §11 says to
test it. The machinery exists (`payoff_estimation.assess_rationalizability`)
but λ is unidentified at 5–15 rounds, so it falls back to the scenario prior
every time. Either accept it as untested or pool acceptance events across many
more runs.

**G7 — arm C now exists; arm E does not.** *(arm C **CLOSED 2026-08-10** —
`2026-08-10-arm-c-negotiated-contract.md`; arm E still DECISION)* θ is
**inferred from opening positions** — the envelope of the seller's ask and the
buyer's counter — so no message type is added and the agent-agnostic claim
survives.

Result, and it is not the one the design expected. **The guarantee transfers
intact: 0 breaches of the agreed θ over 136 enforced rounds.** But **the
negotiated θ refines the imposed one in 0 of 29 cases** — it is looser on the
budget row by 1.21× on average — so arm C settles *more* breaching deals than
arm A (0.143 vs 0.083) and is the only arm on `bargain_3_9` that overspends
(£0.48). Enforcing what the parties agreed is not a substitute for governance.

This turns the refinement order of §9 from a formal nicety into the arm's main
finding, and points at the composition the thesis should propose: enforce
**θ_negotiated ∧ θ_mandate**. Named as **G9**, not run.

Two further results: arm C **does not compress** the negotiation (167 governed
rounds against arm B's 27) and **14 of 29 agreed contracts run past T_max** —
the sharpest liveness signal in the project, against a bound that has barely
bound anywhere else. The pre-phase T_max convention was made an explicit flag
(default: counts) and turns out to change nothing here, 14/29 either way.

**G8 — unsatisfiable pairs are detected and then allowed to trade.** *(DECISION,
new 2026-08-10)* Where c·q_min > B no compliant deal exists, so the filter
declines to act (limitation B4) and the pair runs ungoverned. On
`undisclosed_3_9` that is the entire £6.15 of residual harm under arm B, and it
is the one case where the platform knows with certainty that no admissible deal
exists. Refusing the trade would take marketplace-wide overspend to £0.00 and
forbid nothing that should have been allowed. Not implemented, because blocking
is a different intervention from filtering and would confound arm B.

**G9 — the negotiated and imposed contracts are never composed.** *(**CLOSED
2026-08-11** — `2026-08-11-arm-c-meet.md`)* Arm C showed θ_negotiated sitting
*above* θ_mandate in the refinement order on every pair, so enforcing it alone
permits exactly what the mandate forbids. Arm C-meet enforces the meet.

**The guarantee is recovered and closure is not the price:** 0 of 15 settled
deals breach the mandate, £0.00 overspent (arm C: 2/14, £0.48), with 15 deals
closing against arm B's 16 and arm A's 12. The enforced contract refines the
mandate in 27/27 instances and the negotiated envelope in 27/27, so what the
parties agreed survives inside what is enforced. `Contract.meet` and
Proposition 3 (C(θ₁∧θ₂) = C(θ₁)∩C(θ₂), exactly) are now formulation §9.5.

Three things it also produced: the **intervention rate fell** rather than rose
(0.82 vs arm B's 0.89 — a tighter contract governing a shorter window);
composition can **destroy feasibility** (one seed, buyer counter-offered above
its own budget, meet empty, pair unfiltered — which sharpens G8); and the
property tests written to underwrite the algebra found `Contract.refines`
**wrong** on the deadline case, which had been asserted and never checked.

## Not blocking, but worth a paragraph each

- ~~Arm B's trajectories predate the reconciliation fix~~ — **resolved
  2026-08-07**: the γ = 0.4 cell of the γ sweep is arm B re-run post-fix.
- **Seven** integration bugs are methodological material for chapter 4, not two:
  the wire copy, currency quantisation, the Φ_proj active-row test, the
  intervention-rate logging gap, the buyer-counter echo, **the negotiated arms
  raising on every governed round**, and **the projection returning the breach
  on a degenerate safe set** (both 2026-08-11). All seven passed a full test
  suite because the tests asserted on the wrong surface. One produced a *false
  finding* ("enforcement is prevention") that stood for two days; the echo
  stayed latent in every arm until arm C became the first thing to *read* the
  buyer's position rather than log it; and the sixth produced **five seeds of
  clean, interpretable, wholly false data** that only an A/B control on an
  untouched code path caught.
- The environment is not pinned, so "bit-reproducible" is currently false as
  stated (limitation 13).
