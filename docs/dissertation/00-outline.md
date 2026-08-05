# Dissertation outline — status map

**Started:** 2026-08-05. Structure only; chapters point at their sources rather
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
| 1 | *(introduction — not started)* | — | thin |
| 2 | `60-related-work.md` | new prose | **DONE**, CBF-LLM re-verified |
| 3 | `30-theory.md` | → `formulation.md` §1–9 | mostly DONE, 3 OPEN |
| 4 | *(method/testbed — not started)* | integration notes | thin |
| 5 | `40-results.md` | the four arm notes | DONE for A/B/D |
| 6 | `50-limitations.md` | dedup of 6 sources | DONE |
| 7 | *(conclusion — not started)* | — | thin |

## The argument in one page

1. LLM agents negotiating on a marketplace routinely propose terms that violate
   the contract their own scenario implies — **86%** of proposals when the
   budget binds, **96%** of governed rounds flagged.
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

**G1 — the benefit side is untested, and the scenario is why.** *(DECISION)*
`bargain_3_9` gives the filter almost nothing to prevent: the edit that makes
the budget bind also tells the buyer what it is, and the buyer then polices it
(arm A note). So step 3 above is demonstrated as a *bound*, not as harm
averted. A scenario where the constraint is **not** disclosed to the buyer
would test the benefit properly. This is the single most valuable experiment
not yet run.

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

**G4 — no live evidence for the convergence certificate.** *(OPEN)*
Φ's 96%-decrease result is under a tuned diminishing step; live agents have no
step schedule, so Φ trajectories are collected but not claimed. As it stands
the dissertation proves convergence on gradient-ascent proxies and demonstrates
*safety* on LLMs. That asymmetry needs stating in the introduction, not
discovered by an examiner.

**G5 — n = 5 seeds × 3 customers throughout.** *(RERUN)*
Every empirical claim is five draws of three situations. The safety result
clears the noise floor by ~12× so it survives; nothing else does. More seeds
are cheap (~$0.10/run); more *customers* needs a larger scenario, which is G2.

**G6 — cost-benefit rationalizability is the bridge and is barely tested.**
*(RERUN)* §3 assumes only that agents move iff ρ‖∇Û_i‖ > κ, and §11 says to
test it. The machinery exists (`payoff_estimation.assess_rationalizability`)
but λ is unidentified at 5–15 rounds, so it falls back to the scenario prior
every time. Either accept it as untested or pool acceptance events across many
more runs.

**G7 — arm C and arm E do not exist.** *(DECISION)* Arm C is the *central*
treatment in the original design — θ negotiated rather than imposed — and the
dissertation currently has no self-negotiated contract in it at all, which sits
awkwardly with the repository's name. Blocked on whether the θ-negotiation
pre-phase counts against T_max.

## Not blocking, but worth a paragraph each

- Arm B's trajectories predate the reconciliation fix (`8696016`); outcome
  numbers stand, paths do not. A rerun would tidy this.
- Two integration bugs (the wire copy, currency quantisation) are good
  methodological material for the method chapter: both passed a full test suite
  because the tests asserted on the wrong surface.
- The environment is not pinned, so "bit-reproducible" is currently false as
  stated (limitation 13).
