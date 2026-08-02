# Contracts as Controllers: a Formal Model of Safe, Convergent Negotiation between Bounded-Rational Agents

*Formulation note v1 — precedes the Magentic simulation, per supervision agreement. All empirical claims reference the experiments in `/experiments`; audit-corrected claims are marked [A].*

---

## 1. Setup

**Terms.** A bilateral negotiation is over a term vector

x = (p, q, d) ∈ ℝ³  (price per unit, quantity, deadline).

**Contract.** A contract is a parameter vector of a fixed constraint template,

θ = (B, c, q_min, q_max, d_min, d_max, T_max) ∈ ℝ⁷,

where B = buyer budget, c = seller cost floor, q_min/q_max = quantity bounds, d_min/d_max = deadline bounds, and T_max = maximum time to contract (rounds). The first six parameters define the **safe set**

C(θ) = { x : h_i(x; θ) ≥ 0, i = 1..6 },  with h₁ = B − p·q, h₂ = p − c, h₃ = q − q_min, h₄ = q_max − q, h₅ = d − d_min, h₆ = d_max − d.

T_max is not a constraint on x; it is a **liveness obligation** discharged by the convergence certificate (§5.4). All h_i are affine except the bilinear h₁, which is linearised per round inside the filter and verified post hoc on the true constraint (Exp. 1: zero violations of the true h across all runs; the linearisation gap remains a stated attack surface for large per-round jumps).

**Dynamics.** Rounds k = 0, 1, 2, … alternate between the two agents. The active agent proposes an adjustment u_k; the realised transition is

x_{k+1} = x_k + u_k^safe,

where u^safe is the proposal after the safety filter (§3). Multiple concurrent negotiations j = 1..n stack into a joint state (x¹, …, xⁿ), optionally coupled by shared constraints (e.g. capacity: h_sh = Q − Σ_j q^j ≥ 0).

## 2. Agents: bounded-rational concessions with friction

Agents are **not** assumed optimal, and their decision rules are **not** assumed known — the correct posture for LLM agents. We assume only *cost-benefit rationalizability* (Zusai, arXiv:1805.04898): each agent's revision behaviour is explainable as improvement-seeking after accounting for hidden **friction** — a switching/concession cost κ ≥ 0 and a bounded set of available moves per round (step budget ρ). Formally, at a revision opportunity the agent moves iff the best available payoff improvement net of friction is positive, and then takes (one of) the best available moves.

Two consequences we rely on:

(A1) **Revealed gains.** The move an agent makes is a measurement of its remaining net gain: no worthwhile move ⇒ no move. This licenses the operational energy of §5.2.

(A2) **Heuristic-independence.** Convergence guarantees will be conditions on the *game*, not the agents; any cost-benefit rationalizable heuristic (tempered best response, pairwise comparison, better-reply, …) inherits them. This is what makes the framework deployable on agents whose internals we cannot certify.

*Economic anchor:* friction is the load-bearing concept of labor-market search-and-matching theory (Diamond–Mortensen–Pissarides; wage setting by Nash bargaining), which we cite as the economic interpretation of κ and ρ.

## 3. Safety layer: the contract as a barrier

**Condition (discrete-time exponential CBF; Agrawal–Sreenath).** For each constraint, with rate γ ∈ (0, 1]:

h_i(x_{k+1}) ≥ (1 − γ) h_i(x_k).

Inside C(θ) this guarantees forward invariance (no breach, ever); from outside it forces geometric recovery of the violation at rate (1 − γ). [Stated scope: invariance holds *from inside*; Exp. 3 exhibits the recovery mode explicitly.]

**Filter (minimally invasive QP with graceful degradation).**

u^safe, δ = argmin ‖u − u^prop‖² + ρ_δ ‖δ‖²  s.t.  ∇h_i(x_k)·u + γ h_i(x_k) + δ_i ≥ 0, δ ≥ 0.

Slack δ ensures the filter never locks up; renegotiation is a move in θ-space (a new barrier function), making commitments credible but revisable. Empirical profile (Exp. 1): breach rate 9.9% → 0%, interventions minimal, settlement and surplus preserved.

**Solver requirement [A].** The audit measured a 6.7% solver-status failure rate under SciPy/SLSQP (solutions still feasible to ~10⁻⁶, but unreported convergence is unacceptable hygiene for a safety component). The implementation standard is therefore: a dedicated QP solver (OSQP) with explicit status checks and a safe fallback (hold state / most conservative feasible step), which also returns exact dual variables (§6).

## 4. What safety cannot do

Invariance and convergence are separate obligations. Exp. 1's fixed-rate variant is a standing counterexample: trajectories that remain perfectly safe forever and never settle. A safety mechanism cannot create agreement; an agreement mechanism cannot create safety. Hence two layers.

## 5. Convergence layer: energy, Nash, and the anchoring problem

### 5.1 The Nash formulation (Pietro's "buona formulazione")

Define each agent's **ex-ante net gain** g_i(x) = [best available payoff improvement from x, net of friction κ, within step budget ρ]₊ and the **aggregate net gain**

G(x) = Σ_i g_i(x)  ("the energy state": disagreement enters as payoff gaps, friction as the deduction, payoffs as the object improved).

**Definition (frictional Nash equilibrium).** NE = { x : G(x) = 0 } — the states where no agent retains any worthwhile move once friction is accounted for. With κ > 0 this is a *set* (a friction ball), matching the economic reality that negotiations end when further haggling stops being worth it.

### 5.2 Operational energy for agents we cannot open [design decision]

G as defined needs payoffs and friction we may not observe for LLM agents. Three operational definitions, in increasing order of assumption strength:

1. **Realised displacement (assumption-free, noisy).** Ĝ_k = ‖x_{k+2} − x_k‖² over a round-pair: by (A1), agents move iff net gain is positive, so realised movement *is* revealed remaining gain, measured in term units.
2. **Model-based lookahead (used in the prototype).** G(x) = ‖f²(x) − x‖² where f² is a deterministic two-round rollout of a fitted concession model through the safety filter. Filter-inside-the-lookahead makes G's zero set the *constrained* equilibrium automatically.
3. **Payoff-based (full Zusai; strongest claims).** Extract utilities û_i from the negotiation transcript (the term-extraction layer already parses offers), estimate friction, compute G in payoff units.

The prototype validates (2); the Magentic integration will report (1) alongside (2) and treat (3) as the calibration target. Converting term-unit energies to payoff units is a stated open task, not an oversight.

### 5.3 The anchoring theorem-in-pictures (why equilibrium-independence is forced)

The classical certificate V(x) = ‖x − x*‖² requires knowing the agreement point. Under coupling, the agreement point moves to the **generalised Nash equilibrium** (GNE; Facchinei–Kanzow), which has no closed form. Empirically (Exp. 5, binding capacity, far start; audit-corrected numbers):

| energy | transient contraction (noisy) | noise-free endpoint |
|---|---|---|
| V anchored at unconstrained x* | 0.85 | **plateaus at 510.3** = squared anchor error (2 × 15.97², predicted 509.9) |
| V anchored at estimated GNE | 0.38 | → 0 (but required estimating x*) |
| **G, anchor-free** | **0.37** | **→ 0, monotone on 100% of steps, no anchor** |

The naive anchor certifies progress toward a point the system never reaches and stalls at exactly its own anchoring error; the anchor-free energy terminates at zero at the equilibrium *wherever it turns out to be*. This is the empirical mandate for equilibrium-independent certificates (EIP is the corresponding passivity notion; Zusai's G is its economically interpretable instance, δ-passive by his Corollary 1).

### 5.4 Guarantees

**Deterministic.** If the round-pair map is a contraction with factor c < 1 on the relevant region, G decreases geometrically; validated exactly on the scripted dynamics (0.3164 vs (1−r)⁴ = 0.3164, Exp. 2). **Time-to-contract certificate:** G_k ≤ ε within k ≥ log(G₀/ε) / log(1/c) round-pairs — this is how θ's T_max is *discharged* rather than merely imposed: c and G₀ give a certified upper bound on negotiation length, checked against T_max at contract time.

**Stochastic [A — audit-corrected].** With noisy, occasionally overshooting proposals, global decrease-in-expectation is FALSE: measured E[ΔV] = −56 far from equilibrium but **+6.4 at mid-range** — rare heavy-tailed overshoot events dominate the mean locally. The correct claim is a **drift condition outside a ball**:

E[ G(x_{k+2}) | x_k ] ≤ (1 − α) G(x_k) + β,  guaranteeing convergence in expectation to (and recurrence of) the ball { G ≤ β/α },

with β set by the noise and overshoot distribution (supermartingale/Foster–Lyapunov argument; Robbins–Siegmund). The friction ball of §5.1 and the noise ball compose: the negotiation certifiably ends *near* the frictional Nash set, with the ball radius an explicit function of agent erraticism — itself a reportable safety metric.

**Static stability as the contract's second obligation.** Zusai's theorem: static stability of the game (self-defeating deviations, DF ⪯ 0 — the stable-games condition) plus cost-benefit rationalizability ⇒ dynamic stability, for *any* compliant heuristic. Thus the convergence-side job of the contract-as-controller is to shape the interaction (via constraint geometry, friction design, and concession protocol) so the induced game is statically stable. We certify the game, not the agents.

## 6. Composition and prices

**Additivity.** Multi-population aggregate gains add: G_market = Σ_j G_j (Zusai §5.3 — "the sum is the sum of the functions"), with coupling entering through shared constraint rows in the joint filter. The anchor-free energy inherits validity under coupling *by construction* (§5.3), which anchored sums do not.

**Prices.** The KKT multiplier λ of a shared coupling constraint is its shadow price. Empirically (Exp. 3/4): λ rises with scarcity, and decomposes as

λ_measured = scarcity price + conservatism premium(γ),

the premium vanishing as γ → 1. Two honest caveats: (i) current multipliers are NNLS reconstructions over SLSQP solutions — indicative; OSQP duals are the calibrated replacement; (ii) the filter's conservatism displaces the closed-loop equilibrium into the interior (boundary layer, measured), so the contract is not a neutral referee: γ is an economic policy parameter, not just a safety one.

## 7. Assumptions and limitations (single source of truth)

1. Quantitative terms only; qualitative clauses ("good faith") are out of scope. Contrast: CBF-LLM (LLM-judged textual constraints; flexibility without guarantees) — *re-verify its current content before the related-work section is finalised*.
2. The term-extraction layer is in the trusted computing base; extraction noise ⇒ enforcing the wrong contract (planned robustness experiment).
3. Invariance holds from inside C(θ); from outside, geometric recovery only.
4. h₁ linearisation is per-round-valid; large-jump exploitation is a stated attack surface (Fabraix experiment).
5. Prototype G is a term-unit displacement proxy of Zusai's payoff-based net gain; friction (κ) is not yet implemented in simulation; calibration to payoff units is open.
6. Contraction estimates require a genuine transient (far-start protocol); noise-ball fits are not evidence [A].
7. Solver: OSQP with status checks is the implementation standard; SLSQP results carry a measured 6.7% status-failure rate [A].

## 8. Dictionary (Pietro ↔ maths ↔ code)

| Pietro's term | Formal object | Code |
|---|---|---|
| energy state (friction + disagreement + payoffs) | aggregate net gain G | `G_netgain` (proxy), §5.2 options |
| funzione di Lyapunov | G with drift condition §5.4 | `netgain_energy.py`, `audit.py` (C) |
| Nash equilibrium, "good formulation" | NE = {G = 0} (frictional Nash set) | noise-free G → 0.0000, Exp. 4/5 |
| the sum is the sum of the functions | G_market = Σ G_j (Zusai §5.3) | joint filter + summed energies |
| contract as controller, start from safety | DCBF-QP filter under everything | `dcbf_negotiation.py`, `lyapunov_layer.py` |
| max time to contract | certified k(ε) from decay rate, checked vs T_max | §5.4 |
| heuristics for bounded-rational agents | cost-benefit rationalizable revisions | `proposal(...)`; LLM agents in week 2 |
| friction | switching cost κ, step budget ρ; labor-market anchor | to implement (κ) |

---

*Next (week 2): OSQP swap with status checks; Magentic integration (term extraction replaces scripted `proposal`); report energies (1)+(2) of §5.2 on live LLM negotiations; T_max certificate vs realised negotiation lengths; extraction-noise robustness; Fabraix exploitation spec.*
