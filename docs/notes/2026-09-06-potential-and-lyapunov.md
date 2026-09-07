# The concession field is integrable, and Φ was the wrong certificate

**Date:** 2026-09-06
**Data:** analytic, plus re-analysis of stored live trajectories. **No API
calls, no marketplace, no cost.**
**Code:** `experiments/potential_certificate.py`. Numbers in
`results/summary/potential_certificate.json` (tracked).

## The observation

The formulation defines the joint concession field as F = ∇Û_B + ∇Û_S with
Û_i = P·U_i. A sum of gradients is a gradient:

    F = ∇(P U_B) + ∇(P U_S) = ∇(P(U_B + U_S)) = ∇Ψ,    **Ψ := P·W**

Ψ is the **expected joint surplus**. Naming it is the whole of this note,
because the object itself was already present in three places:

- `formulation.md` §3, Proposition 1's proof, differentiates `∂(PW)/∂p` and
  `∂(PW)/∂q` directly;
- `chapters/03-theory.tex` carries the same two lines into the thesis;
- `experiments/certificates/payoff_dynamics.py::e1_balance_point` is documented
  as *"zero of joint concession field = stationary point of Uhat_B+Uhat_S =
  P(x) * W(x)"* — the identity, stated outright, in a docstring.

So this is not a discovery of PW. It is the observation that PW is the
**potential of the field**, which none of the three notices, and that three
consequences follow which all of them miss. Against that, §2.5 of the thesis
still says potential games "ask that incentives admit a scalar function whose
maxima are the equilibria, **and nothing guarantees that here**" — while the
scalar is being differentiated two chapters later.

Verified numerically, 400 random states around x\*_NBS:

| check | result |
|---|---|
| ‖F − ∇Ψ‖ / ‖F‖, worst | **3.0 × 10⁻⁸** |
| asymmetry of ∇F, worst | **2.6 × 10⁻⁶** |
| Hessian of Ψ at x\*_NBS | (−108.77, −0.687, −0.069), **negative definite** |

## Four consequences

**1. ∇F is symmetric everywhere**, because it is the Hessian of Ψ. The
formulation's λ_max(**sym** ∇F) takes a symmetric part that was already
symmetric.

**2. Three conditions collapse into one.** "F monotone" (§3.6.1), "F passive"
(Fox–Shamma), "stable game" (Hofbauer–Sandholm) and "Ψ concave" are the same
statement. The radius table of §3.6.1 is a concavity table for Ψ:

| radius (scaled) | F monotone | Ψ concave |
|---|---|---|
| 1.0 | 100.0% | 100.0% |
| 1.5 | 90.2% | 90.2% |
| 2.0 | 73.3% | 73.3% |
| 3.0 | 47.7% | 47.7% |

**3. Ψ is a Lyapunov function, and it is anchor-free.** Its maximiser is
x\*_NBS (Proposition 1, restated: the interior stationary point of Ψ). So
V := Ψ\* − Ψ decreases along the ascent dynamic. More usefully, **Ψ alone is a
monotonicity certificate**: checking Ψ_{k+1} ≥ Ψ_k requires no x\*, which is
exactly what §3.8 says an anchored certificate cannot deliver. Ψ survives a
binding constraint because the constrained problem is max Ψ s.t. x ∈ C(θ) and
the projected step still ascends it.

**4. Φ = ‖F‖ = ‖∇Ψ‖ is a gradient-norm merit function**, so it is near zero at
*every* stationary point and on the plateau where acceptance collapses and Ψ
flattens. That is the second zero of §3.5.1, and it is a property of the
certificate, not of the negotiation.

## The size of the defect

Sampling 200,000 states and keeping the 180,958 further than 3 scaled units
from x\*_NBS:

| certificate | reads "converged" (< 1.0) far from the solution |
|---|---|
| Φ = ‖∇Ψ‖ | **71,303 of 180,958 — 39.4%** |
| V = Ψ\* − Ψ | **0 of 180,958 — 0.0%** |

On a price scan at efficient (q, d), Φ reads **0.0701 at p = 2.00** and
**0.0000 at p = 20.00** — 6.5 and 11.5 scaled units out — against 0.0000 at the
solution. V reads 187.5 and 187.6 against 0.

## Live, on the stored trajectories

Same trajectories, same pairs, three instruments:

| arm | traj | distance to x\* ↓ | **Ψ ↑** | Φ ↓ |
|---|---|---|---|---|
| C | 17 | 144/145 (0.993) | **144/145 (0.993)** | 67/145 (**0.462**) |
| A | 11 | 30/31 (0.968) | **30/31 (0.968)** | 14/31 (**0.452**) |

**Φ is at chance on live data.** That is the measured reason the thesis reports
no live convergence result: not that the negotiations fail to converge, but
that the certificate chosen to detect it cannot.

Ψ tracks distance exactly — which is expected, since Ψ is maximised at x\* and
locally concave. **The gain is not a new empirical fact about the trajectories.
It is that Ψ needs no x\* to compute**, so it is deployable where distance is
not, and it is a certificate rather than a descriptive statistic.

## What this does NOT establish

- **Not that the convergence theorem is verified.** Live agents do not run the
  gradient dynamic. Ψ rising on 144 of 145 steps is a measurement, not a proof
  that the certificate's hypotheses hold.
- **Not convergence to x\*_NBS.** Ψ is concave only within ≈1 scaled unit, so
  monotone ascent does not by itself imply reaching the maximiser. The right
  object remains practical stability, and trajectories settle at a positive
  floor (0.029–0.183).
- **Not convergence under enforcement.** Arm C is the weak-governance arm; 205
  of its 219 rounds breach the mandate's budget row. Unchanged by this note.
- **Not a Monderer–Shapley potential game.** Both parties act on the same
  shared draft rather than on separate strategy sets. The claim is the weaker
  and cleaner one: the joint field is exactly integrable.

## What it changes in the write-up

1. §2.5's "Potential games would supply one, but they ask that incentives admit
   a scalar function whose maxima are the equilibria, **and nothing guarantees
   that here**" is wrong, and constructively so. Ψ is that scalar.
2. §3.5's "one certificate cannot do both jobs" survives — Ψ answers *does it
   reach the deal*, G_κ answers *does it stop* — but the convergence half
   should be Ψ, not Φ.
3. §3.5.1's second zero stops being a fact about negotiation and becomes a fact
   about gradient-norm merit functions.
4. §5.11 and §8.2 can report a live, anchor-free, certificate-based
   monotonicity result in place of a descriptive distance statistic.
