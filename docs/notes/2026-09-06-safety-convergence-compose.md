# Safety and convergence compose, and a contract's welfare cost is a priori

**Date:** 2026-09-06
**Data:** synthetic, reference calibration. **No API calls, no cost.**
**Code:** `experiments/contract_welfare_cost.py`. Numbers in
`results/summary/contract_welfare_cost.json` (tracked).
**Depends on** `2026-09-06-potential-and-lyapunov.md` (Ψ = P·W) and
`2026-09-06-constrained-rest-point.md` (Proposition 4).

## Result 1 — the filter preserves the Lyapunov ascent

The sweep's update is u = η·∇Ψ·SCALE², preconditioned ascent on the potential.
The DCBF-QP is a **minimum-intervention** projection, not a projected-gradient
step, so there is no a-priori reason it should preserve ascent. It does:

| B/q_min | binds | Ψ-up, filtered | worst drop |
|---|---|---|---|
| 6.12 | yes | **1.0000** | 9.1e−11 |
| 7.52 | yes | **1.0000** | 3.4e−11 |
| 8.46 | yes | **1.0000** | 7.5e−11 |
| 8.93 | no | **1.0000** | 7.8e−11 |
| 13.60 | no | **1.0000** | 7.9e−11 |

Noise-free, Ψ never decreases under filtering, at any budget, binding or not.
With proposal noise 0.02 the filtered and unfiltered fractions are the same
(0.539/0.557, 0.510/0.557, 0.566/0.557), so **the filter contributes nothing to
the non-monotonicity** — the noise does.

Enforcement does not buy safety at the cost of convergence. This is the first
place in the project where the two halves of the title meet on the same object.

> **Bounded 2026-09-07.** This result is for the **joint preconditioned step** —
> one move computed from the whole field and filtered once. Under the
> **alternating** protocol the formulation actually specifies, agents move one
> at a time on their own \(\hat U_i\), and a *binding* contract then breaks
> round-pair ascent badly (0.45 and 0.31 at B = 700 and 800, worst pair change
> −11.3). See `2026-09-07-lyapunov-granularity.md` and
> `2026-09-07-optimal-contract-placement.md`. The compose claim holds for a
> filter acting on the joint move; it does **not** transfer unaltered to a
> filter acting on individual messages, which is what the marketplace runs.

## Result 2 — the welfare gap decomposes, and the dynamics term is zero

    Ψ* − Ψ_final  =  [Ψ* − Ψ_c*]   +   [Ψ_c* − Ψ_final]
                     price of the       failure of the
                     contract           dynamics

with Ψ_c\* = max{Ψ(x) : x ∈ C(θ)}. Measured across the sweep the second term is
**0.0000** — the filtered dynamic reaches the best the contract permits, to
optimiser tolerance, at every budget.

**Essentially all realised welfare loss is attributable to where θ was written,
and none to the negotiation.** The 50× harm of the funnel sweep is entirely
contract cost, not a dynamics failure.

## Result 3 — the price of a contract, before anything runs

With quantity pinned and the deadline row inactive,

    L(θ) = Ψ* − Ψ( p̄, q_min, d₄(p̄) ),      p̄ = min(B/q_min, p*)

where d₄ is Proposition 4's displaced deadline. Against numerical maximisation
over the whole sweep:

| B/q_min | L closed form | L numeric |
|---|---|---|
| 6.12 | 149.0960 | 149.0960 |
| 7.06 | 77.9605 | 77.9605 |
| 7.99 | 10.9558 | 10.9558 |
| 8.46 | 0.0679 | 0.0679 |
| ≥ 8.50 | **0.0000** | **0.0000** |

**Max error 1.2 × 10⁻¹¹.** L(θ) = 0 exactly when C(θ) contains the bargaining
solution.

This is a design rule with a formula. Chapter 7 says the designer "cannot see"
which side of the crossover they are on. That is true of the designer as
currently equipped, and false of a platform that computes p\* — which it can,
from the same `menu_features` and `min_price_factor` that already produce θ.
The harm the funnel sweep measures is avoidable, and this says how.

## Result 4 (negative) — ρ is not explained by the geometry

The measured contraction rate ρ ≈ 0.62 is invariant to everything the game
supplies:

| varied | range | effect on ρ |
|---|---|---|
| enforcement | arm A vs arm C | 0.621 vs 0.624 |
| price curvature \|λ\|max across pairs | 6.34 → 40.39 (**6.4×**) | correlation with condition number **−0.09** |
| price level p\* | 5.68 → 10.42 | none detectable |

Per-pair ρ: 0.644, 0.629, 0.622, 0.612, 0.702 — overall 0.639 ± 0.048.

And the assumed dynamic does not reproduce it. Preconditioned gradient ascent
on Ψ with the sweep's η predicts a per-round contraction of **0.93**, with no
stable step size giving 0.62.

So ρ looks like a property of the model's concession behaviour rather than of
the negotiation: roughly 38% of the remaining gap closed per round, whatever is
being negotiated over. That **sharpens limitation C5**, which records
cost-benefit rationalizability as "the bridge, and barely tested": here the
bridge is tested on rate and does not hold.

**The test that would settle it cannot be run.** Whether ρ is a constant of the
model needs cross-model trajectories, and only 1 of the non-`gemini-2.5-flash`
runs has enough points to fit (ρ = 0.171, n = 1, worthless). Those negotiations
are too short. Recorded as open.

## Limitations

- **One calibration, scripted agents** for Results 1–3. The forms do not depend
  on the numbers; the magnitudes do.
- **C(θ) is not convex** (bilinear budget row), so Result 1 is an empirical
  finding on this geometry, not a theorem. A proof would need the projected
  gradient argument adapted to the barrier constraint set.
- **L(θ) assumes quantity pinned and the deadline row inactive**, which is what
  the live scenarios do, and would need extending otherwise.
- Result 4 is one model. See above.
