# Extended literature sweep — outside the current bibliography

**Date:** 2026-09-07. Desk research. No runs, no cost.
**Extends** `2026-09-07-literature-check.md`, which covered the theory behind
this week's findings. This one searched *outside* the thesis's 15 references for
competitors, missing alternatives, and positioning.

**Verdict: the core contribution is unoccupied and the project can move forward.
Four things must be fixed first, three would materially strengthen it, and one
is a ready-made route through the biggest remaining gap.**

---

## MUST FIX — four literature gaps a marker could reasonably find

### 1. Shielding is missing, and it is the closest ancestor of the mechanism

**Alshiekh, Bloem, Ehlers, Könighofer, Niekum & Topcu, "Safe Reinforcement
Learning via Shielding", AAAI 2018, arXiv:1708.08611.**

*Post-decision shielding* monitors an agent's proposed action in real time,
vetoes it, and substitutes **the closest safe action**, under an explicit
**minimum-interference** principle — "the shield restricts the agent as little
as possible". Correction in continuous spaces is done by **minimal deviation**
optimisation.

That is the thesis's mechanism, stated in 2018. §2.2 evaluates five alternatives
(prompt, alignment, guardrails, runtime monitoring, CBF-on-tokens) and shielding
is not among them, while §1.4 and §2.2.3 argue for minimum-intervention
projection from first principles as though it were novel.

**The differentiation is real and must be written down:**

| | shielding | this work |
|---|---|---|
| specification | synthesised from LTL_safe | read from the contract; no synthesis step |
| domain | discrete/finite abstractions | continuous commercial terms |
| object | reactive automaton | QP with a barrier *rate* condition |
| setting | single-agent RL | two-party bargaining, no learning |

The rate condition matters: a shield enforces set membership, the DCBF enforces
h(x_{k+1}) ≥ (1−γ)h(x_k), which constrains the *approach* and not just the set.
That is a genuine difference and §22's γ results are about exactly it.

### 2. Contract-based compositional shielding — the closest concurrent work

**Adalat, Hamel-De le Court & Belardinelli, "Contract-Based Compositional
Shielding for Safe Multi-Agent Reinforcement Learning", EUMAS 2026,
arXiv:2606.14130** (submitted 12 Jun 2026).

Contracts + composition + shielding + multi-agent, at a multi-agent systems
venue three months before submission. Distinguishable, but only if stated:

- their **contract** is an assume-guarantee LTL_safe obligation; ours is the
  numeric core of a commercial agreement;
- their **composition** decomposes a *global* specification into local
  obligations whose conjunction implies it (top-down); ours takes the **meet of
  two independently-arising** contracts, one negotiated and one imposed, with an
  exactness result C(θ₁∧θ₂) = C(θ₁)∩C(θ₂);
- theirs is **cooperative** MARL optimising team reward; ours is bilateral
  bargaining with opposed interests and no learning;
- no CBFs — LTL plus a bandit over obligation libraries.

Not citing this would be the single most visible gap in Chapter 2.

### 3. §2.5's potential-games claim is wrong

Covered in `2026-09-07-literature-check.md`. §2.5 says potential games require
"a scalar function whose maxima are the equilibria, **and nothing guarantees
that here**". Ψ = P·W is that scalar, and the Lyapunov theorem for it is in
Hofbauer & Sandholm — **already reference [8]**.

### 4. Constrained decoding is a sixth alternative, and the thesis can dismiss it with its own data

Grammar/schema-constrained decoding masks the next-token distribution so output
is *guaranteed* to satisfy a grammar. It is a real enforcement point and §2.2
does not mention it.

**The dismissal is unusually strong here, because the thesis already ran the
experiment.** Order proposals in Magentic are *structured messages* — schema
validity is already guaranteed — and **86% of them still breach the contract**.
Constrained decoding enforces the *shape* of a message, not the *admissibility*
of its terms; a bilinear relation like p·q ≤ B across two fields is not a
grammar constraint. The open-weight preflight makes the same point from the
other side: Llama scored **5/5 on schema compliance** and then transacted
nothing.

---

## SHOULD ADD — three upgrades

### 5. The motivation is now a deployed fact, not a projection

Chapter 1 says agents "are beginning to be given commercial authority". As of
2026 that understates it:

- **AP2** (Google's Agent Payments Protocol) uses cryptographically signed
  **mandates** specifying *"scope, limits, actor identity, and permitted
  conditions"* — a deployed θ.
- **x402** (Coinbase, launched May 2025) processed **>100M payments** within
  seven months and roughly **$600M annualised** by Q1 2026, described as the
  first payment primitive agents can use **natively, without human approval, at
  machine speed**.
- AWS AgentCore Payments ships "policy-based spending controls"; an IMF note
  (2026) covers agentic payments; Gartner projects 40% of enterprise
  applications carrying task-specific agents by end-2026.

**And the gap is exact.** Checked across AP2, ACP, x402 and MPP: mandates are
verified **at authorisation and settlement**. Limits are embedded in single-use
tokens. *No deployed protocol constrains the terms an agent may agree to before
payment authorisation.*

> A mandate bounds what an agent may **pay**. Nothing bounds what it may
> **agree to**. That is the gap this dissertation fills, and it is now a
> statement about production infrastructure rather than a hypothetical.

### 6. Chapter 7's dual-use section can stop arguing from first principles

§7.5 argues that a filter enforcing a budget would enforce a collusive price
floor just as reliably. The literature now supplies both halves:

- **Calvano et al. (2020)**: Q-learning pricing agents learn tacit collusion.
- **Fish et al. (2025)**: **LLM** agents collude too, converge *faster* than RL,
  robustly across prompt variations, reaching prices up to **200% above Nash**.
- A senior **DOJ** official has warned of *"fully automated cartels operating
  without any human involvement"*; the **CMA** published on AI and collusion in
  March 2026.
- Deployment is real: Anthropic's Project Vend gave Claude price-setting
  authority; Delta uses generative AI for part of its domestic pricing.

**The sharper argument the thesis can now make.** Recent work
(*"On the Fragility of AI Agent Collusion"*, arXiv:2603.20281) finds collusion
among LLM agents is **fragile** — asymmetric time horizons disrupt it. A
protocol-level enforcement layer would remove exactly that fragility, because
compliance would no longer depend on any participant continuing to want it.
**The mechanism's contribution to collusion is not that it enables it, but that
it makes it durable.** That is a much stronger and more uncomfortable claim than
the one currently in §7.5, and it is defensible.

Also relevant: *"Institutional AI: Governing LLM Collusion in Multi-Agent
Cournot Markets via Public Governance Graphs"* (arXiv:2601.11369) — an
Oracle-plus-Controller monitor-and-penalise design, directly comparable to arms
D and F.

### 7. Position against the survey's taxonomy

**Dantas, Cordeiro, Nowroozi & Norbert, arXiv:2608.14590** (22 Jun 2026), 38
studies, taxonomy specification / verification / **enforcement**. It does not
cover CBFs, contracts-as-constraints, negotiation settings, or per-step
guarantees — and its **verifier-tax** finding (*blocking 94% of unsafe actions
still yields <5% safe task completion, because agents route around the block*)
is direct empirical support for projection-over-rejection.

---

## THE OPENING — a ready-made route through §8.3 item 1

**TERMS-Bench** — Zhang, Zhang, Pappu, El, Blanchet, Athey, Liu & Zou,
*"TERMS-Bench: Diagnosing LLM Negotiation Agents Beyond Deal Rate"*,
arXiv:2605.13909 [cs.GT] (May/Jun 2026), project site
`terms-bench.github.io`, 13 frontier models evaluated.

It is a Bayesian-game framework that **makes the environment the verifier** by
specifying the counterpart's latent type, policy and payoff structure, with
**alternating offers over up to 10 rounds** and price bounds, monotone
concession and a turn budget **enforced by the environment**. It reports
**"oracle-reference optimality gaps"**.

Three things follow.

1. **It solves the problem `zone_position` could not.** Today's pilot showed
   tightening the bargain does not lengthen negotiations (median 2 → 2, then 1
   undisclosed). TERMS-Bench supplies 10 alternating rounds by construction —
   which is precisely the "scenario that sustains six to ten rounds" of §8.3
   item 1, the gap that blocks convergence, the liveness bound, payoff
   identification, overshoot-vs-timeout **and** coupling (§27).
2. **It solves C5 by construction.** The payoff structure is specified rather
   than inferred, so the assumption the thesis calls "the bridge, and barely
   tested" would not need to be assumed at all.
3. **"Oracle-reference optimality gap" is Ψ/Ψ\* independently invented**, which
   is corroboration of the measurement choice.

It must be cited as concurrent related work regardless. As **future work it is
the single highest-value item in the project**, and worth naming explicitly in
§8.3 rather than leaving item 1 as "build a scenario".

---

## Corroboration for two of this week's findings

- **§20's rational-seller floor.** Davidson et al., *"Evaluating Language Model
  Agency through Negotiations"*, ICLR 2024, arXiv:2401.04536, find LLM
  negotiators are often "very agreeable" and accept poor outcomes — independent
  evidence that live agents behave non-strategically, which is what §20 measures
  against a formal floor.
- **§25's ρ invariance.** Bianchi et al., *NegotiationArena*, ICML 2024, report
  **limited strategic diversity across models** — consistent with a concession
  rate that does not vary with the game.

## Checked and not competing

- **LLM-X** (arXiv:2605.11376) — negotiation-oriented exchange, but
  infrastructure: message bus, routing, schema validity, policy levels. No
  per-round bound on agreeable terms.
- **Bensalem et al.** (arXiv:2605.18672) — position paper, assume-guarantee
  contracts, no CBFs, no negotiation.
- **Device-Native Autonomous Agents** (arXiv:2601.00911, IEEE SoutheastCon
  2026) — privacy/ZK focus, empirical success rates, no formal guarantee.
- **Ng Yi Sheng & Shen** (arXiv:2607.08652) — marketplace simulation with 18
  DeepSeek agents; the "provable ceiling under incomplete contracts" phrasing
  came from a search snippet, **not** from the paper. No impossibility theorem
  found. Do not cite as one.
- No work found building a safety-enforcement layer on Magentic Marketplace.
  **That niche is unoccupied.**

## Bibliography maintenance

- **AgentSpec (ref [1])** now has a venue — ICSE 2026. Update from the arXiv
  preprint; verify the venue string against the published version.

## Honest caveat on this sweep

All of the above is from search results and abstracts. **Nothing here has been
read in full.** Before any of it enters the thesis, the claim attributed to each
paper must be checked against the paper itself — the Ng Yi Sheng item above is
exactly why.

---

# SECOND ROUND — searched to exhaustion

Twenty-one areas swept. The last several returned confirmations and adjacent
work rather than new categories, which is where I stopped.

## ‼️ THE MOST SERIOUS GAP — foundational bargaining citations are absent

Checked directly against `references.bib` and the chapter sources:

| | |
|---|---|
| "Nash bargaining solution" / "bargaining solution" / "NBS" in the chapters | **28 mentions** |
| citations anywhere near them | **0** |
| **Nash (1950)** in the bibliography | **absent** |
| **Rubinstein (1982)** in the bibliography | **absent** |
| any automated-negotiation reference (Faratin, Baarslag, ANAC, Jennings, Sierra) | **absent** |

**Proposition 1's headline result is that the rest point is the Nash bargaining
solution, and Nash is not cited.** The protocol is alternating offers, and
Rubinstein is not cited. This is trivially fixable and disproportionately
damaging if left — it reads as not knowing the field being theorised about.

Minimum additions:

- **Nash, J. F. (1950). "The Bargaining Problem." *Econometrica* 18(2):155–162.**
- **Rubinstein, A. (1982). "Perfect Equilibrium in a Bargaining Model."
  *Econometrica* 50(1):97–109.**
- **Binmore, Rubinstein & Wolinsky (1986). "The Nash Bargaining Solution in
  Economic Modelling." *RAND Journal of Economics* 17(2):176–188** — also the
  breakdown-risk microfoundation that grounds the acceptance factor P.
- At least one automated-negotiation reference: Faratin, Sierra & Jennings
  (1998) on negotiation decision functions, and/or Baarslag et al. on
  concession-based classification of bidding strategies.

## Automated negotiation gives §25 a proper home — and a free experiment

The ANAC literature classifies strategies by **concession behaviour**:
time-dependent tactics such as **Boulware** (β ≈ 0.2, concede late, sharply
near the deadline) and **Conceder** (β ≈ 2, concede early), plus
behaviour-dependent tactics like relative tit-for-tat.

§25 measures ρ ≈ 0.62 — roughly 38% of the remaining gap closed per round,
invariant to enforcement, to a 6.4× range of payoff curvature, and to price
level. In this taxonomy that is a **fixed proportional concession**, which is
*not* time-dependent: Boulware and Conceder are functions of remaining time.

**Testable today, free, on stored data:** does ρ vary with round index or with
proximity to T_max? If it is flat, the claim becomes *"LLM negotiators concede
a fixed fraction of the remaining gap per round, independent of the deadline —
unlike the time-dependent tactics that dominate automated negotiation"*, which
is a sharper and more citable statement than "it is a property of the model".

## Incomplete contracts — A1 is a framing, not an apology

Assumption A1 restricts enforcement to quantitative terms: *"clauses with no
numeric template have no h(x)"*. That is exactly the **verifiable / unverifiable**
distinction of incomplete contract theory — Grossman & Hart (1986), Hart & Moore
(1990), Aghion & Bolton (1992) on control rights conditioned on verifiability,
and Hart's Nobel lecture on residual control.

The thesis enforces the verifiable subset, which is what any third-party
enforcer — including a court — can do. The rest is governed by residual control
rights and renegotiation, and the thesis *already* makes renegotiation
first-class in its answer to Hammond. A1 should be presented in those terms.

**Zhang & Xu, "Delegation Rights: Property, Agency, and Investment Incentives in
the Age of AI Agents", arXiv:2606.31935 (30 Jun 2026)** applies incomplete
contracts to AI agents directly, with three parties (User, Agent provider,
Platform) and "certified delegation" conditioned on verifiable authorisation,
revocability, auditability and rate-limits. Its line —

> *"Certification is therefore not merely a technical safety screen; it is a
> conditional allocation of residual control."*

— is the sharpest available statement of §7.1's point that whoever writes θ
decides the outcome.

## §7.4.1 can name the actual legal instruments

The chapter asks "who made the offer the buyer received" and answers that it is
"a question about agency and authority rather than about control theory". The
machinery exists and can be named:

- **UETA** recognises "electronic agents"; a contract can form through their
  actions with no human review.
- **ESIGN** provides a contract may not be denied effect because an electronic
  agent acted **"so long as the action of any such electronic agent is legally
  attributable to the person to be bound"**.
- The **Law Commission's 2021 smart-contracts report** flags that *truly
  autonomous* systems raise attribution questions that do not arise for
  conventional automated systems.
- **Singapore's Model AI Governance Framework for Agentic AI** (January 2026) —
  first national framework for agentic systems.

That sharpens the question precisely: **the filter composes terms the seller
never sent, so the accepted offer is not straightforwardly attributable to the
party to be bound** — which is the unresolved case the Law Commission names.

Adjacent: *"Acting with AI: An Interaction-Based Framework for Agentic Tort
Liability"* (arXiv:2606.00518); *"From Logic Monopoly to Social Contract"*
(arXiv:2603.25100), which proposes a legislation/execution/adjudication
separation — a candidate answer to §7.1's "the mechanism supplies no check on
that party at all".

## B3 is a recognised limitation, with named remedies

The discrete-time CBF literature states the problem outright: **CBFs that are
non-concave in their argument require solving non-convex programs to compute
safety-preserving inputs**, which is why real-time implementations linearise.
That is B3 exactly — the bilinear budget row makes C(θ) non-convex, the filter
linearises per round, and fuzzing found set membership failing on 14.8% of
large-jump draws.

Remedies exist and are not implemented here: iterative-convex-optimisation CBFs
for non-convex sets, matrix/dual-algebraic CBFs, and **zero-order CBFs for
sampled-data systems**, which guarantee safety *between* sampling instants where
discrete-time conditions guarantee it only *at* them — directly relevant to a
per-round guarantee.

B3 should be restated as a known limitation of the method with named fixes,
rather than as a defect discovered by fuzzing.

## The closest domain transfer, and it stops short of this work

**"Stochastic Control Barrier Functions for Economics", arXiv:2312.12612** —
states that *"the field of finance and economics has yet to take advantage of
CBFs"* and applies them to optimal advertising and Merton portfolio
optimisation. **Single-agent optimal control.** No bargaining, no second party,
no contract. It establishes CBFs-in-economics as nascent and leaves the
multi-agent negotiation case open, which is a clean positioning citation.

## Proposition 4 has a name in negotiation research

Multi-issue negotiation studies **logrolling**: trading loss on one issue for
gain on another. Prop 4 is that mechanism made **involuntary** — constraining a
transferable coordinate forces compensation on the coordinates left free, chosen
by neither party and on an axis θ never mentions. Normally logrolling is a
mutual-gains device; here a third party induces it. That is a better sentence
for §7.1 than the one currently there.

## Where the sweep stopped

Twenty-one areas: shielding; compositional contract shielding; potential games;
variational GNE; CBF minimum-phase; LLM-agent safety surveys; agentic commerce
protocols; algorithmic collusion; LLM negotiation benchmarks; constrained
decoding; mechanism design for LLM agents; Magentic follow-ups; incomplete
contracts; delegation rights; automated negotiation/ANAC; foundational
bargaining citations; non-convex CBFs; legal attribution; institutional
separation of powers; multi-issue logrolling; CBFs in economics.

The last five returned confirmations and adjacent work, not new categories.
**No competitor was found that constrains, per round, the terms LLM agents may
agree to.** The niche is real.

**The same caveat as round one applies with equal force: all of this is from
search results and abstracts. Nothing has been read in full. Verify each claim
against the paper before it enters the thesis.**
