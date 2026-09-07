# Ψ is a Lyapunov function for the round-pair, not for the round

**Date:** 2026-09-07
**Data:** synthetic, on the formulation's own alternating friction dynamic.
**No API calls, no cost.**
**Code:** `experiments/lyapunov_granularity.py`. Numbers in
`results/summary/lyapunov_granularity.json` (tracked).
**Refines** `2026-09-06-potential-and-lyapunov.md` and bounds
`2026-09-06-safety-convergence-compose.md`.

## The point

§3.4 defines the joint concession field as *"the net force the two agents exert
on the draft **over a round-pair**"*. Its potential Ψ = P·W therefore ascends on
round-pairs. It does **not** ascend on single rounds: each agent ascends its own
Û_i, and a unilateral move that helps one side can cost the other more than it
gains.

Measured on `payoff_dynamics.py::step_agent`, the formulation's own dynamic:

| κ | ρ | per-round up | worst round | **per-pair up** | worst pair | final Ψ/Ψ\* |
|---|---|---|---|---|---|---|
| 0.0 | 0.50 | 0.5250 | **−6.970** | **1.0000** | +1.5e−04 | 0.9516 |
| 2.0 | 0.50 | 0.5250 | **−6.970** | **1.0000** | +1.5e−04 | 0.9516 |
| 0.0 | 0.20 | 0.5575 | **−3.470** | **1.0000** | +4.6e−03 | 0.9778 |
| 0.0 | 0.05 | 0.7150 | **−0.661** | **1.0000** | +1.3e−01 | 0.9226 |
| 2.0 | 0.05 | 1.0000 | 0.000 | 1.0000 | 0.000 | 0.1590 |

Per round the ascent fraction is 0.525 to 0.715 — barely better than chance —
with single-round drops of up to **−6.97 out of Ψ\* = 187.57**. Per round-pair
it is **1.0000 everywhere**, with the worst change strictly positive.

The last row is the halting case: at ρ = 0.05, κ = 2.0 friction stops the
negotiation after a handful of rounds at 16% of the optimum, so the ascent
fraction is 1.0 vacuously. That is Proposition 2 seen through the potential —
enough friction to halt is enough to halt early.

## Two things this settles

**The granularity of any live diagnostic.** A convergence certificate read
per round will look like noise even when the negotiation is converging cleanly.
This is the granularity the live measurement already happens to use: the binding
trajectory holds seller proposals only, so consecutive points span a complete
round-pair. Live, Ψ rises on **144 of 145** such steps (0.993) against 1.000
here — consistent, and not comparable to any per-round figure.

**A bound on the compose result.** `contract_welfare_cost.py` showed the DCBF
filter preserving Ψ-ascent on 100% of steps. That was the **joint preconditioned
step** — one move computed from the whole field. The alternating protocol breaks
monotonicity on its own, before any filter is applied. So "enforcement does not
buy safety at the cost of convergence" is true at round-pair granularity and
must be stated that way.

## Limitations

- **One calibration, scripted agents**, on the reference payoff model.
- **The alternating protocol here is strict** (buyer, seller, buyer, …). Live
  agents do not alternate so cleanly, and a run of same-side messages would be
  a partial round-pair with no guarantee attached.
- Says nothing about whether live agents ascend Ψ *because* they are doing
  anything like this dynamic — see the ρ result, which says they are not.
