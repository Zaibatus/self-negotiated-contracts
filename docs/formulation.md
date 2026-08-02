# Contracts as Controllers

### A formal model of safe, convergent negotiation between bounded-rational agents

*Formulation note v2 (definitive, pre-simulation). Every quantitative claim below is verified in `/experiments`; the experiment is named in brackets. Claims asserted in v1 that failed verification are marked **[corrected]**. v1 is archived as `formulation_v1.md`.*

---

## 0. What changed from v1, and why it matters

v1 defined the equilibrium as the fixed point of a concession *heuristic*. That was circular: the "Nash point" was a property of the update rule, not of the agents' preferences. There were no payoffs in the model, so `NE = {G = 0}` was a characterisation without content — not computable, and the static-stability hypothesis it needed was not checkable.

v2 derives everything from utilities. The consequences are substantial: the rest point of the concession dynamics turns out to be **exactly the Nash bargaining solution** (provable, §4); the convergence and termination guarantees **separate into two different certificates** (§5); and constant friction is provably **insufficient**, making deadline pressure structurally necessary rather than a convenience (§6.3).

---

## 1. Objects

**Terms.** x = (p, q, d) ∈ ℝ³ — unit price, quantity, delivery deadline.

**Contract.** 𝒞 = (θ, γ, τ) where

- θ = (B, c, q_min, q_max, d_min, d_max) ∈ ℝ⁶ — constraint parameters defining the safe set
 **C(θ) = {x : h(x; θ) ≥ 0}**, h = (B − pq, p − c, q − q_min, q_max − q, d − d_min, d_max − d);
- γ ∈ (0,1] — enforcement rate of the safety filter (§7);
- τ = (T_max, ε) — liveness specification: agreement to tolerance ε within T_max round-pairs.

*The contract is the vector θ together with the controller parameters (γ, τ).* Composition is concatenation of constraint blocks; coupling adds shared rows; renegotiation is a move in θ-space; refinement order 𝒞′ ⊑ 𝒞 iff C(θ′) ⊆ C(θ).

**Protocol.** Single negotiating text: agents alternately propose modifications to a shared draft x_k. (Matches the prototype and real mediation practice; the two-stance variant is a generalisation, §10.)

**Unit metric.** Terms have incommensurable units, so all norms use M = diag(σ_p, σ_q, σ_d)⁻¹ with σ = (1, 10, 5): one *scaled unit* = £1 of price, 10 units of quantity, or 5 days.

**Operating box.** The experiments additionally confine the draft to a box p ∈ [6, 12], q ∈ [20, 120], d ∈ [7, 45]. The lower price bound is the cost floor c and the q, d bounds are θ's; the *upper* price bound 12 is a numerical guard, not a contract term (the budget constraint B − pq ≥ 0 is what caps price in θ). It never binds at any reported result: the bargaining solution sits at p = 8.50 with spend 850 < B = 1000, and both the far start and x\*_NBS are strictly interior to C(θ) (verified). Either fold a p_max into θ or drop the guard before the dissertation's formal statement.

## 2. Preferences and the bargaining benchmark

Quasi-linear utilities, concave in quantity, quadratic deadline preferences, price a pure transfer:

- **U_B(x) = aq − (b/2)q² − pq − (γ_B/2)(d − d_B°)²**
- **U_S(x) = pq − cq − (e/2)q² − (γ_S/2)(d − d_S°)²**

with disagreement payoffs normalised to 0. Calibration used throughout: a = 12, b = 0.04, c = 6, e = 0.02, γ_B = γ_S = 0.3, d_B° = 40, d_S° = 12.

Joint surplus **W = U_B + U_S is independent of p** — price is distributive; quantity and deadline are efficiency-relevant. Hence

q_eff = (a − c)/(b + e) = 100,  d_eff = (γ_B d_B° + γ_S d_S°)/(γ_B + γ_S) = 26,  W_max = 241.20.

**Nash bargaining solution** (symmetric, transferable utility): efficient (q, d) plus equal split of W, giving p\* = [W/2 + C(q_eff) + Φ_S(d_eff)]/q_eff.

> **x\*_NBS = (8.500, 100.00, 26.00), U_B = U_S = 120.60.**
> Closed form vs numerical maximisation of the Nash product: agreement to 9.1 × 10⁻⁶ [`payoff_model.py`].

This is the economic ground truth against which all dynamics are measured — for the economics, the analogue of v1's exact contraction check.

## 3. Behaviour: bounded-rational concession under friction

Agents are **not** assumed optimal and their decision rules are **not** assumed known — the necessary posture for LLM agents. We assume only *cost-benefit rationalizability* (Zusai, arXiv:1805.04898): an agent revises iff the best available improvement, net of friction, is positive.

**Acceptance.** A draft closes only if both sides find it acceptable:
**P(x) = σ(U_B(x)/λ)·σ(U_S(x)/λ)**, λ = 60. This creates the concession trade-off: demanding more raises U_i but lowers the chance of a deal.

**Objective.** **Û_i(x) = P(x)·U_i(x)** — expected value of the deal.

**Revision.** At its turn, agent i ascends Û_i, limited by step budget ρ (in the M-metric) and switching cost κ ≥ 0:

move iff **ρ‖∇Û_i(x)‖_M > κ**, then step ρ in the metric ascent direction.

Any cost-benefit rationalizable heuristic — tempered best response, pairwise comparison, better-reply, Zeuthen-style risk comparison — fits this template. *Guarantees are conditions on the game, not on the agents.*

*Economic anchor:* κ and ρ are the friction of labour-market search-and-matching theory (Diamond–Mortensen–Pissarides), whose wage-setting benchmark is exactly the Nash bargaining solution of §2.

## 4. The Nash formulation

**Definition (joint concession field).** F(x) = ∇Û_B(x) + ∇Û_S(x) — the net force the two agents exert on the draft over a round-pair. Its zeros are the rest points of the frictionless dynamics.

> **Proposition 1 (the rest point is the Nash bargaining solution).**
> Under transferable utility via price, symmetric logistic acceptance, equal bargaining weights and W > 0, any interior zero of F coincides exactly with x\*_NBS. (Local monotonicity, §6.1, makes it the unique zero in its neighbourhood; global uniqueness is not claimed.)
>
> *Proof.* W is independent of p, and ∂U_B/∂p = −q, ∂U_S/∂p = +q, so
> ∂(PW)/∂p = W(q/λ)[σ(U_B/λ)σ′(U_S/λ) − σ′(U_B/λ)σ(U_S/λ)] = 0 ⟺ (σ′/σ)(U_B/λ) = (σ′/σ)(U_S/λ).
> For the logistic, σ′/σ = 1 − σ is strictly decreasing, so this holds iff **U_B = U_S** — the equal split. Given U_B = U_S, ∂P/∂q = (σσ′/λ)·∂W/∂q, hence ∂(PW)/∂q = ∂W/∂q·[P + Wσσ′/λ] = 0 ⟺ ∂W/∂q = 0 (the bracket is strictly positive for W > 0), i.e. q = q_eff; identically for d. Efficient (q, d) with equal split is x\*_NBS. ∎
>
> *Verified:* ‖rest point − x\*_NBS‖ = 0.0000; ‖F(x\*_NBS)‖ = 6.4 × 10⁻⁹ [E1].

This answers *"trovare una buona formulazione nel Nash equilibrium"*: the equilibrium is not an artefact of the update rule but the classical bargaining solution, reached by boundedly-rational agents who merely push their own expected payoff uphill.

**Note.** At x\*_NBS the *individual* gradients are large and opposite (‖∇Û_i‖_M = 79.56 each) — each side still wants to push price its way. Only their *sum* vanishes. This asymmetry is why one scalar cannot do both jobs.

## 5. Two certificates

| | **Φ — convergence** | **G_κ — termination** |
|---|---|---|
| definition | Φ(x) = ‖F(x)‖_M | G_κ(x) = Σ_i [ρ‖∇Û_i(x)‖_M − κ]₊ |
| meaning | force imbalance on the draft | residual private incentive net of friction |
| zero set | {x\*_NBS} (Prop. 1) | frictional NE set NE_κ = {x : ρ‖∇Û_i‖_M ≤ κ ∀i} |
| answers | *does it reach the deal?* | *does it stop, and when?* |
| anchor-free | yes — built from current gradients | yes |

Both are computed from *current* quantities only: neither requires knowing where agreement will land. This is the payoff-based realisation of the equilibrium-independence that v1's coupled experiment showed to be necessary.

**Φ is a valid merit function** [E11]: zero exactly at the equilibrium; along the dynamics it decreases on **96%** of round-pairs while distance to x\*_NBS falls 6.45 → 0.199 scaled units, reaching **99.98% of maximal surplus** (W = 241.149 vs 241.200). Locally Φ ≈ L‖x − x\*‖ with measured L ≈ 80 — Φ is equivalent to distance up to constants, which is what a merit function requires. *Φ is not a distance:* it is steep, and its units are payoff-gradient units.

**Stochastic form [corrected].** With noisy proposals, global decrease-in-expectation is false (v1 measured E[ΔV] = −56 far from equilibrium but **+6.4** at mid-range, driven by heavy-tailed overshoots). The correct statement is a drift condition outside a ball:
**E[Φ(x_{k+2}) | x_k] ≤ (1 − α)Φ(x_k) + β**, giving convergence to and recurrence of {Φ ≤ β/α} (Foster–Lyapunov / Robbins–Siegmund). Friction ball and noise ball compose; the radius is an explicit function of agent erraticism and is itself a reportable safety metric.

## 6. Termination, and why deadlines are structural

### 6.1 Stability (the hypothesis, now checkable)

Convergence of any cost-benefit rationalizable dynamic requires the induced game to be *statically stable* — equivalently F monotone (Rosen's diagonally-strict concavity; equivalently passive; equivalently a stable game in the Hofbauer–Sandholm / Fox–Shamma sense). With payoffs in hand this is testable:

> λ_max(sym ∇F) at x\*_NBS = **−6.86** (strongly monotone).
> Monotone at **100%** of sampled states within **1.0 scaled unit** of x\*_NBS; 92.7% at 1.5; 77.3% at 2.0; 42.7% at 3.0. Globally over the box: only 18% [E9, E4].

**The game is locally, not globally, stable, with certified stability radius ≈ 1 scaled unit.** This is a design instruction, not a caveat: *the contract should confine the negotiation to the region where the induced game is monotone.* Restricting C(θ) is how the contract discharges its convergence-side obligation.

### 6.2 The termination threshold

Motion stops when friction exceeds each side's remaining incentive: κ ≥ ρ‖∇Û_i(x)‖_M for both i. The threshold is therefore **state-dependent**: κ\*(x) = ρ·max_i‖∇Û_i(x)‖_M. Measured [E12]: κ\*(x₀) = 15.95 at a far start, κ\*(x\*_NBS) = 39.78 at the deal — so stopping *at* the deal requires κ ≥ 39.78, while permitting motion *from* x₀ requires κ < 15.95.

### 6.3 Proposition 2: constant friction cannot work

> Because ‖∇Û_i‖ grows as the draft improves (larger q, higher acceptance probability), κ\*(x) is increasing along an improving path: κ\*(x₀) = 15.95 < κ\*(x\*_NBS) = 39.78. Any κ small enough to permit motion at x₀ (κ < 15.95) is far too small to halt motion at the deal (which needs κ ≥ 39.78), and any κ large enough to halt at the deal freezes the draft at x₀. Hence **no constant κ both permits progress from x₀ and terminates near x\*_NBS**; termination requires time-varying friction.
>
> *Verified [E12]:* κ = 7.97 → moves but never stops (ends 0.76 from NBS, 0.51% surplus loss); κ = 14.35 → stalls at k = 2 with 59% surplus loss; κ ≥ 19.89 → never moves at all.

This turns "max time to contract" from a parameter into a **structural necessity**. We model the deadline as escalating friction, κ_k = κ₀/(1 − k/T_max), forcing G_κ → 0 by T_max: termination becomes a theorem, not an assumption.

### 6.4 The price of guaranteed termination

Deadline pressure freezes the draft wherever it happens to be, so the guarantee costs efficiency [E8; κ₀ = 2, ρ = 0.5]:

| T_max (round-pairs) | 10 | 20 | 40 | 80 | 160 | 320 |
|---|---|---|---|---|---|---|
| ‖x − x\*_NBS‖ (scaled) | 5.13 | 3.96 | 2.57 | 1.48 | 0.82 | 0.68 |
| surplus loss | 33.8% | 20.7% | 7.79% | 2.42% | 0.84% | 0.57% |

Clean and monotone — a quantified trade-off between certified speed and efficiency, and a strong thesis figure. **Fairness, however, is not monotone:** |U_B − U_S| at the stopping point is erratic across T_max (67.5, 2.97, 69.1, 72.4, 19.7, 20.5). Deadline pressure predictably costs efficiency and *unpredictably* redistributes surplus — reported as-is.

## 7. Safety layer

**Condition** (discrete-time exponential CBF; Agrawal–Sreenath): h_i(x_{k+1}) ≥ (1 − γ)h_i(x_k). Inside C(θ): forward invariance. From outside: geometric recovery only.

**Filter:** u^safe, δ = argmin ‖u − u^prop‖² + ρ_δ‖δ‖² s.t. ∇h_i·u + γh_i + δ_i ≥ 0, δ ≥ 0 — minimally invasive, always defined (slack prevents lock-up), agent-agnostic. Empirically: breach rate 9.9% → **0%**, settlement and surplus preserved, convergence cost ≈1% [v1 F1, F4].

**Invariance ≠ convergence** — a standing counterexample exists of trajectories that stay perfectly safe forever and never settle [v1 F2]. Hence two layers.

**Implementation standard [corrected]:** OSQP with explicit status checks and a conservative fallback. SciPy/SLSQP showed a measured **6.7%** solver-status failure rate (solutions feasible to ~10⁻⁶, but unreported convergence is unacceptable in a safety component); OSQP additionally returns exact duals for §8.

## 8. Coupling, constrained equilibria, and prices

When a constraint binds, the equilibrium moves — and the certificate must be **projected onto the tangent cone of the active constraints**:

**Φ_proj(x) = ‖Π_{T_C(x)} F(x)‖_M.**

> Binding budget B = 800 (unconstrained NBS spend = 850) [E13 + focused check]:
> constrained field-zero at (8.469, 94.47, 25.71); there **Φ = 5.99 but Φ_proj = 0.00000**.
> At the constrained NBS, Φ_proj = 1.34 — small but nonzero: with the transfer capped, equal split and field-zero no longer coincide exactly. Their separation is **0.029 scaled units**, so Proposition 1's coincidence survives constraint-binding to good approximation, not exactly.

This is the payoff-based version of v1's headline: anchored certificates stall at their own anchoring error under coupling (measured 510.3 vs 509.9 predicted), while the anchor-free certificate — here Φ_proj — vanishes exactly at the *generalised* equilibrium, wherever it lies. **Safety composes unconditionally** (stacked rows, one QP); **liveness composes only with anchor-free, projected certificates.**

**Prices.** The KKT multiplier of a coupling constraint is its shadow price: λ_measured = scarcity price + conservatism premium(γ), the premium vanishing as γ → 1, with the filter's conservatism displacing the closed-loop equilibrium into the interior [v1 F6]. Magnitudes indicative pending OSQP duals. Consequence: **γ is an economic policy parameter, not only a safety one.**

## 9. What the contract must do (design implications)

1. **Safety** — choose θ so C(θ) encodes the hard limits; the DCBF filter discharges invariance unconditionally from inside C(θ).
2. **Stability** — choose C(θ) inside the monotone region (≈1 scaled unit around the expected agreement zone, §6.1). This is how a contract *earns* its convergence guarantee.
3. **Termination** — schedule friction κ_k rather than fixing it (Prop. 2); pick T_max on the §6.4 trade-off curve against tolerable surplus loss.
4. **Price policy** — set γ knowing it shifts both the equilibrium and the shadow prices.

## 10. Assumptions and limitations (single source of truth)

1. Quantitative terms only; qualitative clauses ("good faith") are out of scope. Contrast: CBF-LLM (LLM-judged textual constraints — flexibility without guarantees); *re-verify its current content before finalising related work.*
2. Utilities are quadratic/quasi-linear with symmetric logistic acceptance. Proposition 1 depends on transferable utility, symmetry and interiority; it degrades gracefully (0.029 units) when the transfer is capped, and needs restating for asymmetric bargaining weights.
3. Convergence is **local**: monotone within ≈1 scaled unit, not globally (18% globally) [E9].
4. Termination is achieved by escalating friction, not by convergence of the frictionless dynamics; the two guarantees are separate (§5).
5. The constrained-dynamics experiment [E13] used a crude boundary projection rather than the DCBF-QP; rerun with the filter during integration (the residual — dynamics settling 0.61 scaled units from the constrained field-zero — is plausibly this plus incomplete step-size decay).
6. Extraction layer is in the trusted computing base; h₁ = B − pq is linearised per round (large-jump exploitation is a stated attack surface); invariance holds from inside C(θ).
7. Contraction/convergence estimates require a genuine transient (far-start protocol); noise-ball fits are not evidence [corrected].
8. Agents here are gradient-ascent proxies for LLM negotiators. The bridge assumption is only cost-benefit rationalizability (§3) — to be *tested*, not assumed, in Magentic (§11).

## 11. Simulation protocol (what Magentic must measure)

**Estimate from transcripts:** utilities via the extraction layer (offers reveal p, q, d; acceptance/rejection informs the acceptance model), then Û_i and ∇Û_i by finite differences over observed offers.

**Report per negotiation:** (i) breach rate, filtered vs ungoverned; (ii) Φ and Φ_proj trajectories — decreasing?; (iii) G_κ and stopping round vs certified T_max; (iv) distance of settled terms to x\*_NBS from estimated utilities — *does an LLM negotiation land on the Nash bargaining solution?*; (v) realised surplus vs W_max (the §6.4 trade-off on live agents); (vi) shadow prices via OSQP duals.

**Test, don't assume:** does LLM behaviour satisfy cost-benefit rationalizability — do agents move when ρ‖∇Û_i‖ > κ and stall otherwise? This single assumption carries the whole transfer, and it is empirically checkable.

**Practical warning:** LLM negotiations are short (5–15 rounds). Design scenarios with far-apart opening positions so there is a genuine transient; otherwise the estimates measure noise.

## 12. Dictionary (Pietro ↔ maths ↔ code)

| Pietro's term | Formal object | Where |
|---|---|---|
| energy state (friction + disagreement + payoffs) | Φ (imbalance) and G_κ (residual incentive net of friction) | §5; `payoff_validation2/3.py` |
| funzione di Lyapunov | Φ with drift condition; G_κ with escalating friction | §5; E11, E2 |
| Nash equilibrium, "buona formulazione" | zero of the concession field = **Nash bargaining solution** (Prop. 1); constrained case = zero of the projected field | §4, §8; E1, E13 |
| the sum is the sum of the functions | additive certificates over pairs; coupling via shared rows | §8 |
| contract as controller, start from safety | DCBF-QP filter beneath everything | §7 |
| max time to contract | escalating friction; T_max trade-off curve | §6.3–6.4; E8 |
| bounded-rational heuristic updates | cost-benefit rationalizable revision with (ρ, κ) | §3 |
| labour-market game theory | search-and-matching friction; Nash bargaining wage benchmark | §2–3 |

---

*Status: formulation complete and verified; simulation may proceed. Open theoretical obligations: asymmetric bargaining weights; formal derivation of the drift constants (α, β); a sufficient condition on θ guaranteeing C(θ) ⊆ monotone region.*
