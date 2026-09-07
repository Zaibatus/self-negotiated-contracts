# Literature check on this week's findings — what is ours, what is not

**Date:** 2026-09-07. Desk research, ~1 hour. No runs, no cost.
**Purpose:** several findings from 2026-09-06/07 were written up without checking
prior art. This is that check. **Three of them are known theory** and must be
cited rather than claimed.

## A. Known theory — cite, do not claim

### A1. Ψ = P·W as a potential, V = Ψ\* − Ψ as a Lyapunov function

`2026-09-06-potential-and-lyapunov.md` presents the integrability of the
concession field as an observation. It is an instance of a standard result in
the evolutionary-game literature: for potential games, the (perturbed) potential
is a strict global Lyapunov function for the logit dynamic, and η-logit
equilibria are stationary points of the potential plus an entropy term.

The relevant source is **already reference [8] of the thesis** — Hofbauer &
Sandholm, *Stable games and their dynamics*, JET 2009, together with their work
on perturbed best-response dynamics. Stable games are noted there to subsume
concave potential games.

**What survives as ours:** not the theorem, but two things.

1. **§2.5 is wrong and should be corrected.** It says potential games "ask that
   incentives admit a scalar function whose maxima are the equilibria, **and
   nothing guarantees that here**", citing Monderer & Shapley [7]. Ψ = P·W is
   that scalar, it is differentiated two chapters later in Proposition 1's own
   proof, and the theorem that makes it a Lyapunov function is in a paper the
   thesis already cites.
2. **The certificate choice.** Building Φ = ‖∇Ψ‖ rather than using Ψ is a design
   error with a measured cost (39.4% false "converged" readings synthetically,
   46% — chance — live). That measurement is ours.

### A2. The coupled results — variational equilibrium theory

`2026-09-07-coupled-gne-and-gamma.md` results 1–3 (the coupled dynamic reaching
argmax Ψ_total subject to capacity; the allocation equalising marginal
potential; the multiplier being the shadow price) are the **variational
equilibrium** of a generalised Nash game with shared constraints — Rosen's
normalised equilibrium, and the VE-as-GNE-refinement literature.

The defining property of the VE is stated in that literature as: *the GNE at
which the Lagrange multipliers corresponding to the shared constraints are
identical across players*, with the reading that all agents face the same shadow
price for the shared resource. That is exactly the equalised-marginal result,
already known.

**What survives as ours:** that a **DCBF-QP safety filter**, which is not a
game-solver and was not designed for this, drives the system to the VE; and
result 4, the γ correction, which is a correction to the thesis's own §3.8 and
is not in that literature.

### A3. Ψ's maximiser being the bargaining solution

Prop 1's conclusion has a long pedigree — Binmore, Rubinstein & Wolinsky (1986)
give the risk-of-breakdown microfoundation for the Nash bargaining solution, and
the logit/QRE bargaining literature derives symmetric logit equilibria
converging to the axiomatic Nash solution as noise vanishes.

**Worth checking before claiming:** the thesis's Prop 1 appears to hold at
**finite** λ (the proof uses only that σ′/σ is strictly decreasing, with no
λ → 0 limit), whereas the QRE results are typically vanishing-noise limits. If
that reading is right it is a small sharpening, not a new result, and it should
be stated that way. **Not yet verified against the primary sources.**

## B. Literature that validates and names a finding

### B1. Proposition 4 is an instance of a named CBF failure mode

**Choi, Tomlin, Sastry & Sreenath, "When are safety filters safe? On minimum
phase conditions of control barrier functions", arXiv:2508.07684, 11 Aug 2025**
(submitted to IEEE, not yet published).

Abstract: *"although CBFs guarantee safety by enforcing state constraints, they
can inadvertently be 'unsafe' by causing the internal state to diverge."*

That is Proposition 4's phenomenon: binding the price row displaces the
**deadline**, a coordinate θ does not constrain. Their condition for avoiding it
is a **minimum phase** property of the internal dynamics. The thesis has no
analogue and does not know it needs one.

**Koushil Sreenath is a co-author**, and Agrawal & Sreenath 2017 is the thesis's
reference [13] — the source of its discrete-time CBF condition. The same group
that supplied the machinery has since named the failure mode the thesis
independently measured.

**This is the strongest citation found today.** It moves Prop 4 from "an
unexpected effect we noticed" to "an instance of a recognised CBF failure mode,
measured on live language-model agents".

**And it hands us a research question.** In Prop 4 the deadline moves to a new
*finite* rest point (26.00 → 17.66). Choi et al. are concerned with
**divergence**. Is there a regime of this model where the displacement is
unbounded — i.e. where the negotiation is non-minimum-phase? That is testable
synthetically, today, and would be a genuine contribution rather than a
re-derivation.

## C. Positioning

### C1. A June 2026 survey does not cover this approach

**Dantas, Cordeiro, Nowroozi & Norbert, "Toward Safe LLM Agents: A Survey of
Specification, Verification, and Enforcement", arXiv:2608.14590, 22 Jun 2026** —
38 studies, 2022–2026, taxonomy of specification / verification / enforcement.

Checked against its content: it does **not** reference control barrier
functions, contracts as constraints, marketplace or negotiation settings, or
formal per-step guarantees. Its stated gaps include *"no existing approach
simultaneously achieves soundness, scalability, semantic correctness, and
task-level safety preservation"*.

Read two ways, and both belong in Chapter 2. The approach is genuinely
unoccupied ground; and it is unoccupied partly because it is not legible to that
community, which is an argument for citing the survey and positioning against
its taxonomy explicitly.

### C2. The verifier tax supports projection-over-rejection

The same survey reports that *"blocking 94% of unsafe actions can still result
in less than 5% safe task completion because agents exploit alternative unsafe
paths"*.

That is direct empirical support for the design argument in §1.4 and §2.2.3 —
that a layer which *rejects* stalls the exchange, and the corrective step must
return the nearest admissible terms. The thesis currently argues this from first
principles. It can now cite a measurement.

### C3. "Contract" is overloaded three ways

- **reward transfers** in multi-agent RL — Christoffersen et al., cited as [4];
- **assume-guarantee specifications** in formal verification — Bensalem et al.,
  *"Position: A Three-Layer Probabilistic Assume-Guarantee Architecture Is
  Structurally Required for Safe LLM Agent Deployment"*, arXiv:2605.18672,
  18 May 2026. A position paper; no CBFs, no per-step invariance, and it does
  **not** address negotiation, marketplaces or bargaining. Adjacent, not
  competing.
- **commercial terms as a control-barrier safe set** — this thesis.

Chapter 2 distinguishes the first. It should distinguish the second.

### C4. No competitor on per-round bounds

**LLM-X (Lorenzoni, Alencar & Cowan, arXiv:2605.11376, 12 May 2026)** is a
negotiation-*oriented* exchange but is infrastructure — message bus, routing,
schema validity, policy levels. No formal per-round bound on what agents may
agree to. It is a testbed alternative to Magentic Marketplace, not a competing
mechanism.

## D. Bibliography fix

**AgentSpec — reference [1] — now has a venue.** The thesis cites
arXiv:2503.18666; it has since appeared as an ICSE 2026 paper
(`cposkitt.github.io/files/publications/agentspec_llm_enforcement_icse26.pdf`).
Update the entry. Verify the exact venue string against the published version
before citing.

## What this changes, in one line

The theory is less novel and better grounded than the write-up assumed; the
*measurements* are untouched. Nothing measured this week is invalidated. What
changes is which sentences may say "we show" and which must say "we apply".
