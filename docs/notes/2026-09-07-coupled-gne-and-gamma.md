# Coupling, the GNE, and what γ actually prices

**Date:** 2026-09-07
**Data:** synthetic, two buyers and one seller. **No API calls, no cost.**
**Code:** `experiments/coupled_gne.py`. Numbers in
`results/summary/coupled_gne.json` (tracked).
**Depends on** `2026-09-06-potential-and-lyapunov.md` for Ψ = P·W.
**Addresses** limitation C4 ("coupling has never run on live agents … exists
only in simulation") and **corrects** §3.8's economic claim.

## Setup

Two buyers, one seller, shared capacity q₁ + q₂ ≤ Q. Per-pair contracts are
deliberately loose, so the only coupling is the capacity row. Since each pair's
field is ∇Ψ_j and the pairs interact only through the constraint, the coupled
system is a **potential game with a coupled constraint**, of total potential

    Ψ_total(x₁, x₂) = Ψ₁(x₁) + Ψ₂(x₂).

## Result 1 — the filtered dynamic lands on the variational GNE

`argmax Ψ_total s.t. q₁ + q₂ ≤ Q` is the variational (Rosen) equilibrium. The
coupled DCBF-filtered dynamic reaches it:

| Q | q₁ dyn | q₁ GNE | q₂ dyn | q₂ GNE | Ψ gap |
|---|---|---|---|---|---|
| 180 | 81.411 | 81.411 | 98.589 | 98.589 | −8.0e−07 |
| 160 | 70.201 | 70.201 | 89.799 | 89.799 | −2.0e−06 |
| 150 | 64.352 | 64.352 | 85.648 | 85.648 | −2.7e−06 |
| 140 | 58.207 | 58.207 | 81.793 | 81.793 | −3.5e−06 |
| 130 | 51.554 | 51.554 | 78.446 | 78.446 | −4.3e−06 |

Uncoupled, the negotiation rests at the Nash **bargaining** solution
(Proposition 1). Coupled and filtered, it rests at the variational **Nash
equilibrium** of the constrained game. Same potential, one constraint apart.

## Result 2 — the allocation equalises marginal potential

At every interior solution ∂Ψ₁/∂q₁ = ∂Ψ₂/∂q₂ — the classical
efficient-allocation condition — and the common value is the shadow price,
verified against dΨ\*_total/dQ by the envelope theorem:

| Q | equalised marginal | dΨ\*/dQ | rel. err |
|---|---|---|---|
| 180 | 1.26551 | 1.26551 | 8.6e−08 |
| 150 | 2.32826 | 2.32826 | 1.2e−07 |
| 130 | 2.93081 | 2.93081 | 6.3e−08 |

## Result 3 — the filter's own dual is that shadow price

At rest the multiplier on the capacity row is **exactly 2·η·λ_econ**:

| η | dual_rest / (2ηλ) |
|---|---|
| 5e−4 | 0.9999996 |
| 1e−3 | 0.9999996 |
| 2e−3 | 0.9999996 |
| 4e−3 | 0.9999995 |
| 8e−3 | 0.9999995 |

Over a **16× range of step size**, to 4×10⁻⁷ relative. The controller's Lagrange
multiplier and the economic shadow price of capacity are the same number, up to
the step scaling. §3.8's reading of the multiplier as a price is correct.

## Result 4 — but the conservatism premium runs the other way

§3.8 says the multiplier "decomposes into a scarcity price and a conservatism
premium **that vanishes as γ → 1**". Measured at Q = 140:

| γ | peak/base | peak/(base·γ) | **rest/base** | q₁ at rest | q₁ GNE | rounds |
|---|---|---|---|---|---|---|
| 0.1 | 7.008 | 70.085 | **1.000000** | 58.2072 | 58.2072 | 1366 |
| 0.2 | 14.017 | 70.085 | **1.000000** | 58.2072 | 58.2072 | 1357 |
| 0.4 | 28.034 | 70.085 | **1.000000** | 58.2072 | 58.2072 | 1351 |
| 0.7 | 49.059 | 70.085 | **1.000000** | 58.2072 | 58.2072 | 1356 |
| 1.0 | 70.085 | 70.085 | **1.000000** | 58.2072 | 58.2072 | 1349 |

Two corrections, and they point the same way.

**The premium is zero at equilibrium for every γ**, not only as γ → 1. The
resting multiplier equals the scarcity price exactly, at every enforcement rate.

**Where the premium exists — in the transient — it is exactly proportional to
γ.** peak/(base·γ) = 70.085 at all five values, constant to three decimals. It
therefore *grows* with γ rather than vanishing.

So γ is not an economic policy parameter at equilibrium. It scales the
transient and nothing that survives it.

## What this does to §5.7

The live γ-sweep found no boundary layer: margin 0.000 at every γ, which §5.7
and §4.1.2 attribute to short negotiations — almost every governed round is an
opening projection, which runs at γ = 1 by construction.

That explanation is now insufficient. **Here negotiations run ~1350 rounds and
γ is still exactly inert** in both the resting allocation and the resting
multiplier. The inertness is structural, not a consequence of the live regime
being short. Short negotiations hide a null that would have been there anyway.

## Limitations

- **Synthetic, two pairs, one calibration.** The forms are general; the
  constant 70.085 is not — it depends on η, the preconditioner and the
  curvature at the rest point.
- **Scripted agents** running the concession dynamic the formulation assumes.
  Nothing here is a claim about language models, and coupling still has no live
  evidence: C4 stands, narrowed from "exists only in simulation" to "exists in
  simulation with a potential-theoretic account and a tested shadow price".
- **Loose per-pair contracts** by construction, so the interaction between a
  binding per-pair budget and a binding capacity row is untested.
- The premium is measured as peak dual along the approach. A different transient
  statistic would give a different constant, though not a different sign.
