# Chapter 3 — Theory: contracts as controllers

**Source:** `docs/formulation.md` §1–9 (v2, definitive). This file is the
argument structure and the per-section status; it deliberately does **not**
copy the prose, so that a correction to the formulation cannot leave a stale
duplicate behind. The addendum already corrects §§1, 10 and 11, which is
exactly the drift this avoids.

---

## Section map

| § | content | state | note |
|---|---|---|---|
| 1 | objects: 𝒞 = (θ, γ, τ), safe set, refinement order | **DONE** | p_max guard dropped, addendum A.2 |
| 2 | preferences, Nash bargaining benchmark | **DONE** | closed form verified to 9.1e-6 |
| 3 | bounded-rational concession under friction | **DONE**, bridge **OPEN** | see G6 |
| 4 | Proposition 1: field zero = NBS | **DONE** | verified ‖F(x\*)‖ = 6.4e-9 |
| 5 | two certificates, Φ and G_κ | **DONE** | live evidence missing, G4 |
| 6.1 | static stability, radius ≈ 1 scaled unit | **DONE** | λ_max = −6.86 *in the metric* |
| 6.2–6.3 | Proposition 2: constant friction insufficient | **DONE** | κ\*(x₀)=15.95, κ\*(NBS)=39.78 |
| 6.4 | T_max vs surplus trade-off | **DONE**, does not transfer | proxies only, see below |
| 7 | safety layer, DCBF-QP | **DONE** + live | 0/27 governed rounds, arm B |
| 8 | coupling, Φ_proj, prices | **RERUN** | never run on live agents, G2 |
| 9 | design implications | **DONE** | |

## What is genuinely established

**Proposition 1 is the spine.** The rest point of the alternating concession
dynamics is exactly the Nash bargaining solution, so the equilibrium is a
property of the agents' preferences rather than of whatever heuristic they run.
This is what makes the whole apparatus non-circular, and it is the thing v1 got
wrong: v1 defined the equilibrium as the fixed point of a concession heuristic,
which made `NE = {G = 0}` a characterisation without content.

**The two certificates are forced, not chosen.** At x\*_NBS the individual
gradients are large and opposite — ‖∇Û_i‖_M = 79.56 each — and only their sum
vanishes. One scalar cannot answer both *does it reach the deal?* and *does it
stop?*.

**Proposition 2 makes deadlines structural.** κ\*(x) *rises* along an improving
path (15.95 → 39.78), because gradients grow as the draft gets better and
acceptance becomes likely. So no constant friction both permits progress at the
start and halts at the deal. This is counter-intuitive enough to be worth a
figure: the naive reading — far from agreement means a strong incentive to move
— is exactly backwards.

## Three open theoretical obligations

**OPEN-1 — asymmetric bargaining weights.** Proposition 1 assumes symmetry and
transferable utility. It degrades gracefully when the transfer is capped
(0.029 scaled units, §8) but has not been restated for asymmetric weights, which
is the realistic case whenever one side has an outside option.

**OPEN-2 — the drift constants (α, β) are fitted, not derived.** §5's stochastic
form is a drift condition outside a ball, `E[Φ_{k+2}|x_k] ≤ (1−α)Φ(x_k) + β`,
with α and β estimated by least squares. A derivation from the noise and
overshoot distribution would turn the noise-ball radius from a measurement into
a prediction.

**OPEN-3 — a sufficient condition on θ for C(θ) ⊆ the monotone region.** §9's
second design implication says the contract should confine the negotiation to
where the induced game is stable. The integration adds a *checkable* version
(worst-case corner of the box bounding C(θ) against the measured radius,
`contract_is_inside_monotone_region`) which is conservative and sufficient — but
it is a test, not a condition on θ in closed form.

## Two things the chapter must not overclaim

**§6.4's trade-off curve does not transfer.** The T_max/surplus table is
measured on gradient-ascent proxies at T_max = 10…320 round-pairs. Live
negotiations run 3–5 observed vectors. The shape of the trade-off is a
contribution; its numbers are not predictions for LLM agents and must not be
quoted as such.

**Φ_proj = 0 reads more weakly at a corner.** Proposition 1 identifies the
field zero with the bargaining solution *in the interior*. §8 measures the
separation at 0.029 units when one constraint binds; at a corner it is
unmeasured. So Φ_proj = 0 certifies that no admissible direction of improvement
remains — which is what convergence means operationally — but the
identification with x\*_NBS degrades as more constraints bind, by an amount not
yet quantified (formulation limitation 15).

## Figures this chapter needs

1. The two certificates on one trajectory — Φ falling to zero while G_κ stays
   positive until friction bites. *(have the data, not the figure)*
2. Proposition 2's friction window: κ\*(x) rising along the path, with the
   impossible constant-κ band shaded. *(have the numbers)*
3. `figures/figure_anchorfree_energy.png` — the anchored certificate plateauing
   at its own squared anchor error against the anchor-free one going to zero.
   *(exists)*
4. The boundary layer: settled spend against γ, showing the conservatism
   premium in term space. *(have it in `e13_dcbf.py`, needs plotting)*
