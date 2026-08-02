# Handover — MSc thesis session recap (14 July 2026)

## Context
Paolo's MSc thesis (Imperial, supervisor Pietro Ferraro, co-supervisor Haozhe Tian): formal safety guarantees for LLM-agent negotiation in multi-agent marketplaces. Architecture: a contract is a controller with two layers — a discrete-time CBF-QP safety filter (per-step no-breach invariance) plus a Lyapunov/passivity layer (convergence to agreement). Testbed: Microsoft Magentic Marketplace (not yet integrated). Targets: AAMAS + NeurIPS Cooperative AI workshop. Novelty verdict from June deep review: GO-WITH-CAVEATS; CBF-LLM is the closest near-miss. Fabraix collaboration agreed for adversarial evaluation. **Primary framing now adopted: Lyapunov/Nash** (Pietro's suggestion) — agreement point = Nash equilibrium (fixed point of the concession map), certificate = Lyapunov function V = ‖x − x*‖² with discrete decrease condition; passivity/EIP is the equilibrium-independent generalisation.

## What happened this session
1. Synthesised Pietro's reading pointers (Lyapunov in game theory, discrete games, Nash) into the framing above; bridge literature: Monderer–Shapley → Hofbauer–Sandholm stable games → Fox–Shamma (stable games are passive) → Gadjov–Pavel (passivity-based NE seeking) → Hines–Arcak–Packard (EIP).
2. Summarised the report Pietro shared (Hammond et al. 2025, "Multi-Agent Risks from Advanced AI", arXiv:2502.14143): motivation pre-written (§3.4 stabilising dynamics, §3.5 commitments); dual-use/rigidity critique adopted as design decisions (slack QP, renegotiation = new barrier function, planned Fabraix "safety-filter exploitation" experiment: adversary steers a constrained agent to the worst corner of its safe set — zero breaches, terrible welfare).
3. Verified the two closest papers: Christoffersen et al. (AAMAS 2023, contracts as reward transfers, equilibrium-welfare guarantee — candidate baseline, code public) and Zhu et al. (AISTATS 2025, Markov Commitment Games, empirical convergence). Neither collapses novelty. Differentiation sentence: *prior work treats contracts as incentive modifications that make good equilibria exist; we treat contracts as control certificates guaranteeing per-step safety and convergence of the negotiation dynamics themselves, compositionally.*
4. Built and ran a synthetic prototype (scripted buyer/seller, no LLMs — deliberate: closed-form ground truth de-risks the discrete-time maths before Magentic plumbing).

## Prototype findings (files in outputs)
- **F1** DCBF-QP filter: breaches 9.9% of rounds → 0%, convergence preserved, tiny interventions, surplus unchanged. (`dcbf_negotiation.py`)
- **F2** Invariance ≠ convergence: fixed-rate agents produced an endless tug-of-war under a perfectly safe filter → the two layers are separately necessary (counterexample in hand).
- **F3** Lyapunov certificate exact: empirical contraction 0.3164 vs theory (1−r)⁴ = 0.3164. With noise: decrease on ~69% of steps → needs the stochastic (decrease-in-expectation) variant. (`lyapunov_layer.py`)
- **F4** Price of safety: CLF–CBF tension on 9.6% of round-pairs; contraction 0.926 filtered vs 0.916 ungoverned.
- **F5** Composition: additive for independent pairs; under a shared-capacity coupling the naive certificate fails (contraction 1.02) because the equilibrium shifts to the **generalised Nash equilibrium**; re-anchoring V at the empirically estimated GNE restores it (0.983, decrease fraction back to uncoupled level). GNE has no closed form → empirical demonstration of why EIP is necessary. (`gne_shadow_price.py`)
- **F6** Shadow prices emerge as KKT multipliers of the coupling constraint: rise with scarcity (12.3 binding vs 7.4 slack); γ-sweep decomposes measured λ = scarcity price + **conservatism premium(γ)** (premium vanishes as γ→1). Bonus: the filter displaces the equilibrium (boundary layer: q-sum 147.3 vs unconstrained 162.9 at γ=0.4; 156.5 at γ=0.9). Headline phrasing: *the price of safety appears in the prices.*
- Caveats logged: invariance holds from inside the set (geometric recovery from outside); bilinear budget constraint linearised per round (candidate attack surface); duals via NNLS on SLSQP are indicative → move to OSQP for exact duals.

## Contract-as-vector answer (Pietro's open question, now answered + in brief §5)
Two vectorisations: deal state x = (price, quantity, deadline) ∈ ℝ³; the contract itself is the parameter vector θ = (B, c, q_min, q_max, d_min, d_max) ∈ ℝ⁶ of a fixed constraint template, safe set C(θ) = {x : h(x;θ) ≥ 0}. Vectorisation creates the algebra: composition = concatenation (+ coupling rows), certificates add, renegotiation = move in θ-space; signed agreement = (x*, θ). Scope limit: quantitative terms only; qualitative clauses out of scope (contrast: CBF-LLM).

## Artifacts (all in /outputs of the previous session)
`dcbf_negotiation.py`, `lyapunov_layer.py`, `gne_shadow_price.py`, `pietro_meeting_brief.md` (6 sections incl. contract-as-vector §5 and three questions for Pietro: canonical discrete-time form — storage inequalities vs Agrawal–Sreenath DCBFs; GNE-shift finding section vs remark; Christoffersen baseline implement vs conceptual).

## Next steps (agreed order)
1. Swap SLSQP → OSQP (speed + exact dual variables for F6).
2. γ-sweep figure: shadow price vs caution, extrapolate true scarcity price at γ→1.
3. Decrease-in-expectation metric replacing pointwise ΔV.
4. Formalise the equilibrium-independent certificate (EIP storage function, unknown x*).
5. Magentic Marketplace integration (term-extraction layer replaces scripted agents).
6. Spec the Fabraix exploitation experiment. Baselines: ungoverned, ABC-style runtime monitor, possibly Christoffersen reward-transfer contracts.

Meeting with Pietro is 15 July — fold any outcomes (framing choice, scope confirmation, baseline decision) back into the plan.
