# Where the unconstrained coordinates go when the contract binds

**Date:** 2026-09-06
**Data:** analytic, validated against stored synthetic results. **No API calls,
no marketplace, no cost.**
**Code:** `experiments/constrained_rest_point.py`. Numbers in
`results/summary/constrained_rest_point.json` (tracked).
**Closes** the gap named in `docs/notes/2026-08-28-funnel-sweep.md`: *"The
deadline displacement is measured at settlement, not proved. A closed form for
the constrained rest point would be a genuine addition and is not attempted
here."*

## Reproduce

```bash
uv run python experiments/constrained_rest_point.py
```

## The claim being tested

The funnel sweep measured that binding the *price* row drags the settled
*deadline* from 26.00 to 17.74 on a contract with `deadline_active=False` —
a coordinate θ never mentions. It recorded the displacement and offered a
one-line mechanism ("the constrained equilibrium is not the unconstrained one
restricted to the boundary") without deriving it. That left the sharpest
finding in the sweep as an observation with no theory attached.

## The derivation

The d-component of the joint concession field, with `Û_i = P·U_i`:

    F_d = ∂(P U_B)/∂d + ∂(P U_S)/∂d = P ∂W/∂d + W ∂P/∂d.

With P = σ(U_B/λ)·σ(U_S/λ) and σ' = σ(1−σ),

    ∂P/∂d = (P/λ)[ w_B ∂U_B/∂d + w_S ∂U_S/∂d ],    w_i := 1 − σ(U_i/λ).

Substituting ∂U_i/∂d = −γ_i(d − d_i°) and dividing by P > 0, F_d vanishes
exactly when

    γ̃_B (d − d_B°) + γ̃_S (d − d_S°) = 0,     γ̃_i := γ_i (1 + W·w_i/λ)

which gives

    d(p) = (γ̃_B d_B° + γ̃_S d_S°) / (γ̃_B + γ̃_S).                          (*)

**(*) is the efficient deadline of Proposition 1 with each party's weight
multiplied by its acceptance slack w_i.** Where the contract does not bind,
U_B = U_S forces w_B = w_S, the slacks cancel, and (*) collapses to
d_eff = 26. Proposition 1's deadline is the special case.

## Result — the closed form reproduces the sweep

Evaluated at the price each budget actually settled on, against all 17 budgets
of the sweep:

| B/q_min | binds | measured d | closed form | error (days) |
|---|---|---|---|---|
| 6.120 | yes | 17.735 | 17.657 | −0.078 |
| 7.055 | yes | 19.532 | 19.496 | −0.036 |
| 7.990 | yes | 23.415 | 23.395 | −0.020 |
| 8.457 | yes | 25.779 | 25.776 | −0.002 |
| 8.925 | no | 26.008 | 25.921 | −0.087 |
| 13.600 | no | 26.007 | 25.934 | −0.073 |

**R² = 0.99945, max error 0.090 days, mean error 0.062 days over 17 points.**
At the unconstrained price the form returns **26.000000** against d_eff = 26.

## The mechanism, and why it generalises

The weights are the whole content. At the two ends of the sweep:

| | U_B | U_S | slack w_B | slack w_S | γ̃_B | γ̃_S | seller's share |
|---|---|---|---|---|---|---|---|
| p = p\* = 8.50 | 120.6 | 120.6 | 0.118 | 0.118 | 0.442 | 0.442 | **0.500** |
| p = 6.12 | 313.1 | −92.8 | 0.005 | 0.824 | 0.306 | 1.208 | **0.798** |

Capping the price transfers surplus to the buyer, which drops the seller's
acceptance probability. Its slack w_S rises from 0.118 to 0.824, its deadline
preference takes 80% of the weight rather than 50%, and d is pulled from 26
toward the seller's ideal d_S° = 12, landing at 17.66.

Stated generally, and this is the part that is not about deadlines:

> **Binding a transferable coordinate displaces the non-transferable ones,
> toward the ideal point of whichever party the constraint hurts, by an amount
> that grows with how much it hurts them.**

Price is a pure transfer, so a cap on it cannot be absorbed in price. The
disadvantaged party has to be compensated on the coordinates that remain, and
the acceptance channel is what does the compensating. Any safety filter that
bounds one axis of a multi-axis agreement inherits this, whatever the axes are.

## Limitations

- **One calibration**, the reference payoff model, quantity pinned. The
  functional form of (*) does not depend on those numbers; the magnitudes do.
- **Scripted agents.** This is a property of the concession dynamic the
  formulation assumes, not a measurement on language models. Whether live
  agents displace the same way is untested and needs a scenario with an active
  deadline row and enough rounds to settle.
- **The interior root.** (*) has three roots; the middle one attracts and the
  outer two repel. The script selects the interior root and the outer two are
  at d ≈ −8 and d ≈ 59, far outside any admissible deadline band.
- The validation compares against settlement means from a 200-seed sweep, so
  the ±0.09 residual is partly sweep noise rather than model error.
