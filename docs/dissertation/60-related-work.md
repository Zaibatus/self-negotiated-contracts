# Chapter 2 — Related work

**State: DONE.** CBF-LLM re-verified 2026-08-05 against its current published
form, which `formulation.md` §10.1 has carried as an outstanding action since
v1. The re-verification **changes the characterisation** — see below.

---

## The differentiation, in one sentence

Prior work treats contracts as **incentive modifications that make good
equilibria exist**; this thesis treats a contract as a **control certificate**
guaranteeing per-step safety and convergence of the negotiation dynamics
themselves, compositionally.

## CBF-LLM — the closest near-miss, and the earlier characterisation was wrong

**References.** Miyaoka & Inoue, *CBF-LLM: Safe Control for LLM Alignment*,
[arXiv:2408.15625](https://arxiv.org/abs/2408.15625) (2024); extended as
*Control Barrier Function for Aligning Large Language Models*,
[arXiv:2511.03121](https://arxiv.org/abs/2511.03121) (2025).

**What it does.** Applies a CBF safety filter to the *predicted token* from a
baseline LLM, intervening in text generation. Add-on: no fine-tuning of the
base model. Implemented with Llama 3 and a RoBERTa sentiment classifier.

**The correction.** `formulation.md` §10.1 describes it as "LLM-judged textual
constraints — flexibility without guarantees". That is **not accurate and
should be fixed in the next formulation revision.** The paper *does* state a
forward-invariance theorem:

> "Suppose that x(τ₀) ∈ 𝒮, and the control input u = u(τ) satisfies the CBF
> constraint (2b) for all τ ≥ τ₀. Then, the state x(τ) ∈ 𝒮 holds for all
> τ ≥ τ₀." — Theorem 1

So it is not that they lack a guarantee. **It is that the guarantee is
conditional on a barrier function they construct from a neural classifier**,

> h(x(k)) = s₊(x(k)) − max(s₋(x(k)), s±(x(k)))

with s from a RoBERTa sentiment model — and the authors say plainly that this
antecedent cannot be relied on:

> "Generally, building the L-CF that perfectly distinguishes between desirable
> and undesirable texts is challenging… the RoBERTa model… may not accurately
> evaluate the text input 'It is a'."

**The sharpened contrast, which is stronger than the old one.** Both works
apply the same discrete-time CBF machinery, and both prove forward invariance.
The difference is entirely in where h comes from:

| | CBF-LLM | this thesis |
|---|---|---|
| state | predicted token | term vector x = (p, q, d) |
| barrier h | RoBERTa classifier score | explicit algebraic h(x; θ) |
| guarantee | Theorem 1, conditional on h being correct | same theorem, h exact by construction |
| the gap | h is learned and admittedly imperfect | h is arithmetic on the agreed terms |
| scope | any text | quantitative clauses only |
| agents | one generating model | two, negotiating |
| convergence | not addressed | second certificate, §5 |

So the honest framing is not "they have flexibility, we have guarantees". It is
that **a CBF is only as good as its barrier function**, and the contribution is
to identify a class — structured contractual terms — where h is exact, so the
theorem's antecedent actually holds. The price is A1: qualitative clauses are
out of scope. CBF-LLM buys generality by accepting a barrier its own authors
say may be wrong; we buy a real guarantee by restricting the domain. Stating it
that way is both more accurate and more favourable, because it makes the
restriction a deliberate design choice rather than a shortcoming.

Neither CBF-LLM paper addresses multi-agent negotiation, equilibria, or
convergence — those are entirely ours.

## Christoffersen et al., AAMAS 2023 — contracts as reward transfers

Agents negotiate a *contract* that redistributes reward, chosen so that the
resulting game has a welfare-improving equilibrium. The guarantee is about
**equilibrium welfare**: with the contract in place, the good outcome is an
equilibrium.

**Differentiation.** That is a statement about the *fixed points* of the induced
game. Ours is about the *trajectory*: no round breaches, and the dynamics reach
agreement. A reward transfer says nothing about what happens on the way, and in
particular nothing about a round in which an agent proposes terms outside the
contract — which is 86% of proposals in our measurements.

Strong candidate baseline; code is public. Whether to implement it or compare
conceptually remains an open question for supervision.

## Zhu et al., AISTATS 2025 — Markov commitment games

Learnable commitment protocols between agents; convergence is demonstrated
**empirically**.

**Differentiation.** Ours is a certificate, not a demonstration — Φ and G_κ are
computed from current gradients and their zero sets are characterised
(Prop. 1). The honest caveat is that our *live* evidence is for safety, not
convergence (G4): on LLM agents we currently demonstrate what they demonstrate,
and prove more only on the gradient-ascent proxies.

## Positioning against the safety literature

- **Hammond et al. 2025**, *Multi-Agent Risks from Advanced AI*
  ([arXiv:2502.14143](https://arxiv.org/abs/2502.14143)) — the motivation
  section, essentially pre-written. §3.4 asks for stabilising dynamics via
  conservation-law-like objects (a storage/Lyapunov function is exactly that);
  §3.5 asks for credible commitments. Also the source of the dual-use critique
  — rigid commitments enable extortion — which became design decisions: slack
  in the QP, renegotiation as a move in θ-space.
- **AgentSpec-style runtime monitors** — arm D *is* this baseline, and the
  measured answer is that detection without enforcement leaves 96% of governed
  rounds flagged and unfixed.

## Control-theoretic lineage

Potential games (Monderer–Shapley) → stable games (Hofbauer–Sandholm) → stable
games are passive (Fox–Shamma 2013) → passivity-based Nash seeking
(Gadjov–Pavel 2019) → equilibrium-independent passivity (Hines–Arcak–Packard),
with Agrawal–Sreenath for the discrete-time exponential CBF and Zusai
([arXiv:1805.04898](https://arxiv.org/abs/1805.04898)) for cost-benefit
rationalizability. Bürger–Zelazo–Allgöwer for prices as duals of coupling
constraints (MEIP) — the claim §8 instantiates, and the one still unexercised
on live agents (C4).

## To do

- **Re-verify Christoffersen and Zhu** against their current published versions,
  as was just done for CBF-LLM. The characterisations above are from a June
  2026 reading and have not been rechecked.
- Decide implement-vs-compare for the Christoffersen baseline.
- Fix `formulation.md` §10.1 to the corrected CBF-LLM characterisation.

## Sources

- [CBF-LLM: Safe Control for LLM Alignment (arXiv:2408.15625)](https://arxiv.org/abs/2408.15625)
- [Control Barrier Function for Aligning Large Language Models (arXiv:2511.03121)](https://arxiv.org/abs/2511.03121)
