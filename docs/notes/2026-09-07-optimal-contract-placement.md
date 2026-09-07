# There is an interior optimal contract, and it beats no contract

**Date:** 2026-09-07
**Data:** synthetic, alternating protocol with proposal noise.
**No API calls, no cost.**
**Code:** `experiments/optimal_contract_placement.py`. Numbers in
`results/summary/optimal_contract_placement.json` (tracked).
**Depends on** `2026-09-06-potential-and-lyapunov.md` (Ψ),
`2026-09-06-safety-convergence-compose.md` (L(θ)) and
`2026-09-07-lyapunov-granularity.md` (round-pair granularity).

## Why earlier attempts found nothing

A first attempt at this question found no interior optimum: every binding
contract cost welfare and the best contract was no contract. That was run on
the **joint preconditioned dynamic**, which converges cleanly and never
overshoots. On that dynamic the result is correct and uninteresting — there is
nothing for a contract to protect against.

The **alternating** protocol is different, and it is the one the formulation
specifies and the marketplace runs. Agents move one at a time on their own
\(\hat U_i\), so the path is not a Ψ-ascent (Ψ rises on 100% of round-pairs but
only 52–72% of rounds), and with proposal noise the trajectory wanders. That
wandering is what a contract can clip.

## Result — an inverted U, with the optimum above the efficient spend

γ = 0.4, ρ = 0.5, noise 0.02, **50 runs per point** (5 starts × 10 seeds).
Efficient spend p\*q\* = **850**.

| budget | mean Ψ/Ψ\* | SE | vs no contract | σ |
|---|---|---|---|---|
| 820 | 0.9014 | 0.0052 | −0.0435 | **−4.51** |
| 850 | 0.9076 | 0.0062 | −0.0374 | **−3.66** |
| 870 | 0.9360 | 0.0055 | −0.0089 | −0.91 |
| 890 | 0.9712 | 0.0035 | +0.0263 | +2.97 |
| 900 | 0.9773 | 0.0029 | +0.0323 | +3.74 |
| **910** | **0.9815** | **0.0021** | **+0.0365** | **+4.35** |
| 930 | 0.9770 | 0.0021 | +0.0320 | +3.81 |
| 950 | 0.9664 | 0.0040 | +0.0215 | +2.37 |
| 980 | 0.9541 | 0.0061 | +0.0092 | +0.90 |
| 1050 | 0.9449 | 0.0081 | −0.0000 | −0.00 |

No contract: **0.9449 ± 0.0081**.

**The optimum also cuts variance roughly fourfold**: SE 0.0021 at B = 910
against 0.0081 unfiltered. That is the same signature as the live arm B result,
whose per-seed SD falls from 0.054 to 0.014.

## The mechanism, and what it means for contract design

Placement trades two quantities this project has now measured separately:

- **Below the efficient spend** the cost is **L(θ)**, the a-priori welfare price
  of the contract, available in closed form
  (`2026-09-06-safety-convergence-compose.md`, exact to 1.2 × 10⁻¹¹).
- **Above it** the benefit is **variance clipping** — the contract removes the
  upper tail of a noisy alternating path without moving the target.

The optimum is where the two balance, here about **7% above the efficient
spend**. Below 870 the contract is pure cost; above 980 it never binds and does
nothing.

The location moves with γ. Full sweep, 50 runs per point, B/spend in brackets:

| γ | best budget | best Ψ/Ψ\* | σ | **B / efficient spend** |
|---|---|---|---|---|
| 0.2 | 1050 † | 0.9821 | **+4.43** | **≥ 1.235** † |
| 0.4 | 910 | 0.9815 | **+4.35** | **1.071** |
| 0.7 | 850 | 0.9801 | **+4.16** | **1.000** |

† At γ = 0.2 the sweep is still rising at the grid edge, so 1050 is a
**truncation, not an argmax** — the true optimum lies above it. At γ = 0.7 the
optimum sits at the efficient spend and B = 820 is still +0.42σ, so that one is
near the lower edge too. Only γ = 0.4 is a clean interior optimum on this grid.

**The achievable gain is nearly invariant to γ** (+4.43, +4.35, +4.16σ; 3.5–3.7
percentage points of Ψ\*). What γ changes is *where* the optimum sits, and it
moves monotonically: **higher enforcement rate, tighter optimal contract.** A
larger γ lets the barrier permit a faster approach to the boundary, so the same
damping needs a nearer boundary. Higher γ lets the barrier permit a faster approach
to the boundary, so a tighter boundary buys the same damping. **θ and γ are not
separable design choices**, which is a direct qualification of §3.1's decision
to keep γ out of θ so that contracts can be compared independently of how hard
they are enforced. They can be compared that way for *safety*; they cannot for
*welfare*.

That is consistent with `2026-09-07-coupled-gne-and-gamma.md`, where γ is
exactly inert at equilibrium and scales the transient. Here the transient is
what settles, so γ matters.

## The mechanism, tested: headroom tracks agent noise

If the benefit above the efficient spend is variance clipping, the optimal
headroom should grow with how noisy the agents are. It does, monotonically
(best of a 10-budget grid, 40 runs per point):

| proposal noise | no contract | best B | best Ψ/Ψ\* | σ | **B / efficient spend** |
|---|---|---|---|---|---|
| 0.00 | 0.9599 | 870 | 0.9906 | 13.14 | **1.024** |
| 0.01 | 0.9598 | 890 | 0.9870 | 5.59 | **1.047** |
| 0.02 | 0.9478 | 910 | 0.9808 | 3.76 | **1.071** |
| 0.04 | 0.9257 | 950 | 0.9650 | 2.85 | **1.118** |
| 0.08 | 0.9036 | 950 | 0.9558 | 3.00 | **1.118** |

**Required headroom rises 2.4% → 11.8% as noise rises 0 → 0.08**, and the
contract beats no contract at every level.

Two components, and the noise = 0 row separates them. At zero noise there is
still a **13.1σ** gain, so part of the benefit is **damping the alternating
protocol's intrinsic oscillation** — the same oscillation that puts per-round
Ψ-ascent at 52% while per-pair is 100%. The rest is variance clipping, and that
is the part that grows with noise.

So the design rule has two terms: enough headroom to clear the protocol's own
overshoot, plus enough to clear the agents' noise. A contract tighter than the
sum is pure L(θ) cost.

## Limitations

- **Synthetic, one calibration, scripted agents.** Nothing here is a claim about
  language models. The live agents fall outside the bargaining family entirely
  (`2026-09-06-rational-seller-floor.md`), so this does not predict a live
  optimum.
- **The optimum's location is calibration-specific.** "About 7% above the
  efficient spend" is one number from one payoff model; the *existence* of an
  interior optimum is the transferable part, and it requires knowing p\*q\*,
  which is exactly what §7.1 says a designer cannot see.
- **Effect sizes are small** — the best contract recovers 0.037 of Ψ\*, about
  3.7 percentage points. The 4.35σ reflects 50 runs, not a large effect.
- **The noise sweep uses the best of a 10-budget grid**, so the reported optimum
  is grid-resolution, not a fitted argmax; 950 appears twice because the grid
  ends there, and the true optimum at noise 0.08 may lie above it.
