# Chapter 1 — Introduction

**State: DRAFT COMPLETE, 2026-08-11.** Sources: `formulation.md` §1–2, the nine arm
notes, and `00-outline.md` for the gaps this chapter must not paper over.

---

## 1.1 The problem

Autonomous agents built on large language models are beginning to transact on
each other's behalf. Microsoft's Magentic Marketplace is a research platform
built exactly for this: buyer agents and seller agents exchange messages,
propose orders and settle deals with no human in the loop. The immediate
question it raises is not whether such agents can negotiate — they can — but
whether anything about the resulting transactions can be *guaranteed*.

The answer, on the evidence in this dissertation, is that nothing about the
agents guarantees anything. On an authored bargaining scenario where the
buyer's budget binds, **86% of the order proposals a seller agent emits violate
the contract its own scenario data implies**. Under a monitor that detects but
does not correct, **73% of governed rounds are flagged**. These are not
adversarial agents or jailbreak prompts; they are stock agents running stock
prompts on a stock marketplace, and the constraint they breach is one the
platform could read directly out of its own configuration files.

What stops most of that becoming realised harm is the counterparty. A buyer
that knows its budget declines offers above it, and on the disclosed-budget
scenario only one settled deal in twelve breaches. But a tendency to decline is
not a bound. The distinction is the whole subject of this dissertation, and the
sharpest illustration of it is what happens when the counterparty *cannot*
police the constraint: on a scenario identical in every respect except that the
buyer is not told its own ceiling, **every settled deal breaches, and 7.9% of
the value transacted changes hands above a limit the platform knew and the
buyer did not**.

## 1.2 The proposal: a contract is a controller

The claim this work develops is that a commercial contract, restricted to its
quantitative terms, is not merely a document to be checked after the fact but a
*control specification* that can be enforced continuously during negotiation.

Formally, terms are a vector x = (p, q, d) — price, quantity, deadline — and a
contract is a parameter vector

    θ = (B, c, q_min, q_max, d_min, d_max) ∈ ℝ⁶

defining a safe set C(θ) = {x : h(x; θ) ≥ 0} through six affine or bilinear
constraint rows. A *discrete-time control barrier function* condition,

    h_i(x_{k+1}) ≥ (1 − γ) h_i(x_k),

is then imposed on every transition by a minimally-invasive quadratic program
sitting at the marketplace protocol. Whatever terms an agent proposes, the
nearest admissible terms — nearest in a metric that makes a pound, ten units
and five days comparable — are what the counterparty receives.

Two things follow, and they are the reason the framing is worth the machinery.
First, γ and the liveness specification τ = (T_max, ε) are *not* part of θ.
They live in a separate `ControllerSpec`, which keeps the refinement order on
contracts meaningful: one contract refines another when it is componentwise
tighter, independently of how aggressively either is enforced. Second, the
enforcement point is the protocol, not the agent. No agent class is forked, no
prompt is edited, and nothing in the filter's path inspects which model
produced the proposal — which is what licenses the claim that the guarantee is
a property of the *game*, not of the agents playing it.

## 1.3 The asymmetry this dissertation leads with

A thesis about safety *and* convergence guarantees should say at the outset
which of the two it actually demonstrates, because they are not equally
supported and an examiner will find the gap if the introduction does not.

> **Safety is demonstrated on live LLM agents, across models, enforcement
> rates, scenarios and contract provenances. Convergence is proved on
> gradient-ascent proxies and is not demonstrated live.**

The safety half is strong and replicated along four independent axes:

| varied | held | result |
|---|---|---|
| **model** — 3 Gemini models | γ = 0.4, `bargain_3_9` | 0 breaches / 100 governed rounds |
| **enforcement rate** — γ ∈ {0.2, 0.4, 0.7, 1.0} | model, scenario | 0 / 126 |
| **scenario** — `bargain_3_9`, `undisclosed_3_9` | model, γ | 0 / 27 and 0 / 22 |
| **contract provenance** — imposed, negotiated, composed | model, γ, scenario | 0 / 27, 0 / 136, 0 / 16 |

The result does not vary because nothing in the mechanism can vary with what it
governs: the filter reads terms, solves a QP and rewrites, and no branch of that
path inspects the model, the prompt, or where θ came from.

The convergence half is not in that position, for three reasons that compound:

1. **The theorem is about a dynamic these agents are not running.** The 96%
   decrease in the convergence certificate Φ is measured under a tuned
   diminishing step size. Live agents have no step schedule, so a decrease
   fraction computed on live data would test something the theory never
   claimed.
2. **Negotiations are too short to have a trajectory.** Under enforcement the
   median binding trajectory is *one* round: the opening proposal is projected
   onto the boundary and the buyer accepts. There is no path left to test for
   convergence.
3. **Φ has a second zero far from the deal, so a low reading is ambiguous.**
   Far from agreement the acceptance probability collapses, the expected
   utilities go flat, and *both* agents' gradients vanish — the field is zero
   because nobody has any incentive, not because everyone is satisfied.
   Measured on one pair, Φ is 0.00 at the bargaining solution (p = 5.68) and
   0.16 at p = 6.18 where the acceptance probability is 0.009. Live
   trajectories begin at 0.97–1.00 scaled units, right at the edge of the
   certified monotone radius of ≈1 unit, so any live Φ reading needs a radius
   check before it can be interpreted at all.

**What would close it**, stated concretely rather than promised:

1. **A scenario that sustains six to ten rounds of genuine concession.** Far
   apart opening positions and no early acceptance, so there is a transient to
   measure rather than a single projected step. Arm C already shows such
   negotiations exist — it ran 219 proposals where arm B ran 51 — so the
   ingredient is a contract loose enough to leave a bargaining zone.
2. **A radius check before every Φ reading**, rejecting any value taken more
   than ≈1 scaled unit from the agreement zone, since Φ is a merit function only
   inside the certified monotone region.
3. **A step-size proxy**, or an explicit statement that the convergence theorem
   is about a dynamic LLM agents do not run and is offered as a design
   principle rather than a prediction.

Chapter 7 orders this against the other outstanding work.

## 1.4 Contributions

1. **A formalisation of the quantitative core of a contract as a control
   barrier specification**, with the enforcement rate and the liveness
   specification deliberately separated from the contract parameters, so that
   refinement between contracts remains well defined.

2. **Two certificates, and an argument that one cannot do both jobs.** A
   convergence certificate Φ and a termination certificate G_κ are needed
   separately because at the bargaining solution the two agents' gradients are
   large and opposite — 79.56 each in the reference calibration — and only
   their *sum* vanishes. A single scalar that detects agreement cannot also
   detect that motion has stopped. It is further shown (Proposition 2) that the
   friction threshold κ* rises along an improving path, from 15.95 at the
   opening to 39.78 at the solution, so no *constant* friction both permits
   progress and halts at the deal; termination requires an escalating schedule.

3. **Proposition 1: the rest point of the concession dynamics is the Nash
   bargaining solution.** The equilibrium is therefore a property of the
   agents' preferences rather than of the update rule, which is what makes the
   convergence target meaningful rather than an artefact.

4. **A working enforcement layer for a real LLM marketplace**, at the protocol
   rather than in the agents, demonstrating per-round contract exposure of zero
   on live negotiations with no agent forked and no fallback tier ever firing.

5. **A measurement of what enforcement is worth, in currency.** On a scenario
   where the constraint is not disclosed to the counterparty, enforcement takes
   value transacted above the ceiling from £21.70 (7.9%) to £0.00 on governable
   pairs. On a scenario where the buyer *is* told its budget, the same
   mechanism averts nothing measurable, because the buyer already refuses. The
   benefit of a safety layer is a function of how informed the counterparty is,
   and this dissertation brackets that axis rather than asserting a number.

6. **A negotiated contract, and a negative result about it.** Arm C infers θ
   from the agents' own opening positions and enforces it. The guarantee
   transfers intact — zero breaches over 136 rounds — but the negotiated
   contract **refines the platform's mandate in none of 29 cases**, so
   enforcing what the parties agreed permits more harm than doing nothing. This
   makes the refinement order the operationally important idea and identifies
   the composition that a real marketplace needs: enforce the *meet* of the
   negotiated contract and the mandate.

7. **Composition, and the arm that needed it.** The refinement order on
   contracts is made precise, the meet is shown to be *exact* — C(θ₁ ∧ θ₂) is
   the intersection, not an inner approximation, because the bilinear budget row
   is linear in B — and arm C-meet enforces θ_negotiated ∧ θ_mandate. The
   guarantee is recovered (0 of 15 settled deals breach, £0.00 overspent) with
   closure preserved (15 deals against 16 and 12). This is the dissertation's
   answer to its own title: a self-negotiated contract is safe to *permit*
   precisely when it is not enforced alone.

8. **Seven integration bugs, reported as methodological material.** Each passed
   a full test suite; each was invisible because the tests asserted on a
   plausible surface rather than the one that determines what the counterparty
   receives. One produced a headline finding that stood for two days before
   being retracted; another produced five seeds of clean, interpretable, wholly
   false data that an A/B control caught and the logs did not. Chapter 4 argues
   this is the central practical lesson in building a safety layer, not an
   embarrassment to be omitted.

## 1.5 What this dissertation does not claim

Stated here rather than deferred, because each bears on how the results should
be read.

- **Not that the filter prevents violations from arising.** It does not.
  Measured per continuation round, the enforced arm's flag rate is the *highest*
  of the three. What enforcement does is correct — almost everything it sees,
  concentrated at the opening — and thereby shorten the negotiation.
- **Not that the mechanism is neutral.** Enforcement funnels settled terms onto
  the constraint boundary, which is where the buyer spends its entire budget,
  and not onto the bargaining solution. A contract designer choosing θ
  determines the outcome to the cent.
- **Not that the numbers generalise.** Every empirical claim is five seeds of
  three customers on one authored scenario. The safety results are categorical
  and survive; the closure, surplus and settled-breach differences do not clear
  the noise floor and are not claimed.
- **Not that coupling has been exercised.** The shared-capacity clause, the
  generalised Nash displacement and the shadow prices — the economic half of
  the formalism — have never run outside simulation, because the scenario has
  no seller serving two buyers.

## 1.6 Structure

Chapter 2 places the work against control-barrier approaches to LLM safety,
mechanism design and the automated-negotiation literature. Chapter 3 develops
the formalism and proves the two propositions. Chapter 4 describes the testbed,
the enforcement point and the scenario construction, and reports the five
integration bugs. Chapter 5 presents the four arms. Chapter 6 is the single
consolidated limitations list. Chapter 7 concludes and orders the remaining
work.
