# Thesis progress brief — meeting with Pietro

*Formal guarantees for LLM-agent negotiation: contracts as controllers. Two weeks of progress.*

---

## 1. The framing: Nash equilibrium + Lyapunov function (your suggestion, now the spine)

I reframed the whole architecture in the language from our last meeting. A negotiation is a discrete-time dynamical system: the state is the term vector x = (price, quantity, deadline), and each round an agent adjusts it, x_{k+1} = x_k + u_k.

**Nash equilibrium** = the agreement point x\*. It is the fixed point of the alternating concession map — the point where neither side wants to move any more (mutual best-response stationarity of the bargaining dynamics).

**Lyapunov function** = the certificate of convergence. V(x) = ‖x − x\*‖² is a "distance to agreement" that must shrink every round: V(x_{k+1}) ≤ (1−α)V(x_k). A ball rolling downhill into a bowl; the Nash point is the bottom of the bowl.

**The contract is a controller with two layers, starting from safety:**

1. **Safety layer (control barrier function).** The contract defines a safe set of terms, C = {x : h_i(x) ≥ 0} — budget respected, price above cost, quantity and deadline in bounds. The discrete-time CBF condition h_i(x_{k+1}) ≥ (1−γ)h_i(x_k) says: you may approach the limits, but only at a controlled rate, and you may never cross them. It is enforced by a small optimisation (QP) that perturbs each proposed offer *as little as possible* to keep the condition true, with slack variables so it degrades gracefully instead of locking up.
2. **Convergence layer (Lyapunov).** Separately certifies that the haggling actually terminates at the Nash point.

The literature bridge from classical game theory to exactly our setting, in five stops: potential games (Monderer–Shapley: the potential is a Lyapunov function) → stable games (Hofbauer–Sandholm) → *stable games are passive systems* (Fox–Shamma 2013) → passivity-based Nash-seeking over networks (Gadjov–Pavel 2019) → equilibrium-independent passivity (Hines–Arcak–Packard), for when the equilibrium is unknown in advance — which is our case.

---

## 2. What I built and why there are no LLMs yet

A synthetic prototype: two scripted agents (buyer/seller) making noisy concession-based offers, with occasional aggressive overshoots that violate the contract — mimicking ungoverned LLM behaviour. The whole pipeline is ~400 lines of Python (numpy/scipy), three files, each component mapping one-to-one onto the real system: `Contract` → the term schema extracted from LLM negotiation; `dcbf_filter` → the runtime safety layer; `make_proposal` → to be replaced by Magentic Marketplace agents.

**Why synthetic first:** the load-bearing technical risk is whether the discrete-time barrier and Lyapunov conditions work on negotiation-shaped dynamics at all — most of this theory is continuous-time. Scripted agents give *ground truth*: the Nash point and the contraction rate are computable in closed form, so I can validate the certificate against exact theory. With LLMs in the loop, a failure could be maths or plumbing and I couldn't tell which. De-risk the maths first; then Magentic is integration work, not research risk.

---

## 3. Findings (50-episode experiments)

**F1 — The safety layer works and is nearly free.** Ungoverned: breaches in 9.9% of rounds, 54% of episodes. Filtered: **zero breaches**, convergence fully preserved, interventions tiny (the QP barely touches compliant offers), and deal surplus unchanged (marginally higher — breaching trajectories waste rounds).

**F2 — Safety and convergence are genuinely separate jobs.** My first agents (fixed concession rates, distant targets) produced a permanent tug-of-war: zero breaches under the filter, but no settlement, ever. Invariance ≠ convergence. The two-layer architecture is a necessity, not a design choice — and I have the counterexample demonstrating it.

**F3 — The Lyapunov certificate is exact.** Noise-free, the measured contraction of V per round-pair is **0.3164 vs a theoretical (1−r)⁴ = 0.3164** — four decimal places. With noise, V decreases on ~69% of steps: the guarantee becomes decrease-in-expectation (convergence to a noise ball); the write-up will need the stochastic discrete Lyapunov variant.

**F4 — The price of safety is quantified and small.** Contraction with filter 0.926 vs 0.916 without. Safety interventions coincide with V rising on only **9.6% of round-pairs** — the CBF and Lyapunov layers barely fight.

**F5 — Composition ("the sum is the sum of the functions") works, with one crucial twist.** Two independent pairs: V_market = V₁ + V₂ contracts at the single-pair rate — additivity confirmed. But when the pairs are *coupled* through a shared capacity constraint (both buying from limited supply), the naive composed certificate fails (fitted contraction 1.02 > 1). Diagnosis: the coupling **moves the equilibrium** — the agreement point shifts to the *generalised* Nash equilibrium (GNE), and V anchored at the old point reads false instability. Re-anchoring V at the (empirically estimated) GNE restores the certificate: contraction 0.983, decrease fraction back to the uncoupled level. The refined principle: *the sum of the functions certifies the composed system iff each function is anchored at the coupled equilibrium — which has no closed form, which is exactly why the final theory must be equilibrium-independent (EIP).* The prototype demonstrated why the thesis's central tool is necessary.

**F6 — Prices emerge from the contract maths, and they carry a "safety premium".** The KKT multiplier (dual variable) of the shared-capacity constraint behaves like a price: it rises as capacity tightens (12.3 binding vs 7.4 slack). This is the MEIP claim (Bürger–Zelazo–Allgöwer: prices as duals of coupling constraints) in miniature. Bonus discovery: a γ-sweep decomposes the measured multiplier into **scarcity price + conservatism premium(γ)** — a cautious filter (low γ) parks negotiations at a standoff distance from the limits (equilibrium at q₁+q₂ = 147.3 instead of 162.9) and inflates the price; the premium vanishes as γ → 1. In one sentence: **the price of safety literally appears in the prices.** If this survives in Magentic, it is a headline figure.

Honest caveats: forward invariance holds from inside the safe set (from outside, the DCBF gives geometric recovery instead); the budget constraint is bilinear and linearised per round (held here; a candidate attack surface for large jumps); multipliers extracted via NNLS on SLSQP solutions are indicative, not solver-grade.

---

## 4. The report you shared (Hammond et al. 2025, "Multi-Agent Risks from Advanced AI")

Three takeaways. **(a) It is our motivation section, essentially pre-written.** §3.4 (Destabilising Dynamics) calls for stabilising multi-agent dynamics via conservation-law-like objects — a storage/Lyapunov function is exactly that; §3.5 (Commitment and Trust) calls for credible commitments between agents. Our architecture answers both, and the report is from the exact community we target (NeurIPS Cooperative AI workshop). **(b) It surfaced the dual-use critique** — rigid commitments enable extortion and "Dead Hand" failures — which I turned into design decisions: slack in the QP (graceful degradation, no lock-up), renegotiation as a first-class operation (a renegotiated contract is just a new barrier function), and a planned *safety-filter exploitation* experiment with Fabraix: can an adversary steer a constrained agent into the worst corner of its own safe set — zero breaches, terrible welfare? **(c) Novelty re-verified.** I checked the two closest papers it cites: Christoffersen et al. (AAMAS 2023 — contracts as reward transfers; guarantee is equilibrium welfare) and Zhu et al. (AISTATS 2025 — learnable commitment protocols; convergence is empirical). Differentiation in one sentence: *prior work treats contracts as incentive modifications that make good equilibria exist; we treat contracts as control certificates guaranteeing per-step safety and convergence of the negotiation dynamics themselves, compositionally.* Christoffersen is a strong candidate baseline.

---

## 5. Your question from last time: "how can you turn a contract into a vector?"

Two different things get vectorised — separating them makes the answer clean.

**The deal state is a vector.** What is currently being negotiated is the term vector x = (price, quantity, deadline) ∈ ℝ³, extracted from the natural-language dialogue. This is the *state* of the dynamical system, not the contract.

**The contract becomes a vector of parameters.** The contract is the rulebook: a set of conditions h_i(x) ≥ 0 the deal must always satisfy (spend ≤ budget: h₁ = B − p·q; price ≥ cost: h₂ = p − c; quantity and deadline bounds: h₃…h₆). Once the *template* of rules is fixed, the whole contract is pinned down by six numbers:

θ = (B, c, q_min, q_max, d_min, d_max) ∈ ℝ⁶

where **B** = the buyer's budget (maximum total spend), **c** = the seller's cost floor (minimum acceptable price per unit), **q_min, q_max** = the smallest and largest quantity either side will accept, and **d_min, d_max** = the earliest and latest acceptable delivery deadline. One number per blank in the rule template — nothing else is needed to reconstruct the whole contract.

**The contract *is* θ.** The safe set is C(θ) = {x : h(x; θ) ≥ 0}; the certificates (barrier condition, Lyapunov function) are built on top. In the prototype this is literally the `Contract` class — its six fields are θ. Negotiating a contract means the agents agree on θ; negotiating *within* one means the controller keeps x inside C(θ). A signed agreement is then the pair (x\*, θ): what was agreed, under which invariant rules.

**This vectorisation is what creates the algebra.** Composition = concatenation (θ₁ ⊕ θ₂ stacks constraints; a coupling clause like shared capacity is one appended row — exactly what the joint filter in F5 implements). Certificates add (V_market = V₁ + V₂). Renegotiation = a move in θ-space (a renegotiated contract is a new point, not a new kind of object). Distance between contracts = ‖θ₁ − θ₂‖, which you cannot ask of two paragraphs of prose.

*Honest scope limit (pre-empting the follow-up):* clauses with no numeric template ("delivery in good faith") have no h(x). The thesis deliberately restricts to structured quantitative terms — the economically binding core of marketplace transactions, and the load-bearing assumption flagged in the novelty review. The CBF-LLM near-miss is the natural contrast: LLM-judged textual constraints give flexibility without guarantees; we give guarantees within a restricted-but-central class.

---

## 6. Next steps (my side)

Immediate: swap SLSQP for a proper QP solver (OSQP) — faster and gives exact dual variables for free; produce the γ-sweep figure (price vs caution, extrapolating the true scarcity price); replace pointwise ΔV with the decrease-in-expectation metric. Then: formalise the equilibrium-independent certificate (storage function without knowing x\*) for the write-up — this is where the EIP/MEIP theory enters properly; begin Magentic Marketplace integration (term-extraction layer replacing the scripted agents); spec the Fabraix exploitation experiment. Baselines for evaluation remain: ungoverned, runtime-monitor (ABC-style), and possibly Christoffersen-style reward-transfer contracts.

**Questions for you:** (1) For the discrete-time theory, do you prefer discrete storage inequalities or discrete-time exponential CBFs (Agrawal–Sreenath) as the canonical form? (2) Is the GNE-shift / equilibrium-displacement finding worth a dedicated section, or a remark? (3) Is the Christoffersen baseline worth implementing, or is a conceptual comparison enough for AAMAS?
