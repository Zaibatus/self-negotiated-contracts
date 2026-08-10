# Dissertation outline — status map

**Started:** 2026-08-05. **Marks refreshed 2026-08-10** after the undisclosed-budget and arm C commits (G1 and G7 closed; G8 and G9 opened). Structure only; chapters point at their sources rather
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

## Chapters

| # | file | source | state |
|---|---|---|---|
| 1 | `10-introduction.md` | new prose | **DRAFTED 2026-08-10** — leads with the G4 asymmetry |
| 2 | `60-related-work.md` | new prose | **DONE**, CBF-LLM re-verified |
| 3 | `30-theory.md` | → `formulation.md` §1–9 | mostly DONE, 3 OPEN |
| 4 | `20-method.md` | new prose | **DRAFTED 2026-08-10** — includes all five integration bugs |
| 5 | `40-results.md` | the nine arm notes | **DONE** for A/B/C/D + γ + models + undisclosed |

Chapters 1, 4 and 7 were marked DONE on 2026-08-07 before they had been
written — the marks recorded the *plan* for them rather than their state. They
exist as of 2026-08-10 and are marked DRAFTED, which means written and
sourced but not revised against a full read-through.
| 6 | `50-limitations.md` | dedup of 6 sources | DONE |
| 7 | `70-conclusion.md` | new prose | **DRAFTED 2026-08-10** — remaining work ordered by impact |

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

**G9 — the negotiated and imposed contracts are never composed.** *(RERUN,
new 2026-08-10)* Arm C shows θ_negotiated sitting *above* θ_mandate in the
refinement order in every case, so enforcing it alone permits exactly what the
mandate forbids. The fix is the meet, θ_negotiated ∧ θ_mandate — parties may
agree their own terms, but only inside the platform's rules — which is one
arm's work on machinery that already exists (`Contract.refines`; the meet is
componentwise). Proposed, not tested.

## Not blocking, but worth a paragraph each

- ~~Arm B's trajectories predate the reconciliation fix~~ — **resolved
  2026-08-07**: the γ = 0.4 cell of the γ sweep is arm B re-run post-fix.
- **Five** integration bugs are methodological material for chapter 4, not two:
  the wire copy, currency quantisation, the Φ_proj active-row test, the
  intervention-rate logging gap, and **the buyer-counter echo** (2026-08-10 —
  `from_text` took the *first* money figure, which is the seller's quote the
  buyer was restating in order to reject it; 88% of extracted buyer moves were
  echoes). All five passed a full test suite because the tests asserted on the
  wrong surface; one produced a *false finding* ("enforcement is prevention")
  that stood for two days, and the echo stayed latent in every arm until arm C
  became the first thing to *read* the buyer's position rather than log it.
- The environment is not pinned, so "bit-reproducible" is currently false as
  stated (limitation 13).
