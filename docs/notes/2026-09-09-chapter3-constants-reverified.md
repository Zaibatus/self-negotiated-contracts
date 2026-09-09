# Chapter 3's simulation constants, re-run against the pinned environment

**Date:** 2026-09-09. **Cost:** £0.00 (proxy simulation only, no API calls).

Every numeric constant Chapter 3 and Appendix B.6 quote was re-run from the
scripts rather than checked against earlier notes. All but one reproduce
exactly.

## Reproduces exactly

| Claim | Where | Script | Value |
|---|---|---|---|
| `q_eff`, `d_eff`, `W_max`, `p*` | 3.2 | closed form | 100, 26, 241.20, 8.50 |
| `x*_NBS` | 3.2 | `payoff_model.nbs_closed_form` | (8.5, 100, 26) |
| `‖F(x*_NBS)‖_M` | 3.4 | `payoff_dynamics.concession_field` | 6.39e-09 → "6.4e-9" |
| `‖∇Û_i‖_M` both sides | 3.5 | `payoff_validation2` E7 | 79.5560 → "79.56" |
| `κ*(x0)`, `κ*(NBS)` | 3.6.2 | `payoff_validation3` E12 | 15.95, 39.78 |
| κ = 7.97 moves, ends 0.76, 0.51% loss | 3.6.2 | E12 | 0.760, 0.51% |
| κ = 14.35 stalls at round-pair 2, 59% loss | 3.6.2 | E12 | k=2, 59.04% |
| κ ≥ 19.89 never moves | 3.6.2 | E12 | confirmed at 19.89–43.76 |
| `λmax(sym ∇F)` at NBS | 3.6.1 | `payoff_validation2` E9 | −6.8632 → "−6.86" |
| monotone fraction at r = 1.0/1.5/2.0/3.0 | 3.6.1 | E9 | 100%, 92.7%, 77.3%, 42.7% |
| Φ decreases on 96% of round-pairs | C6 | `payoff_validation3` E11 | 96% |
| Table B.6, all six columns | B.6 | E8 | all cells |
| constrained NBS, `Φ_proj` there | 3.8 | `e13_dcbf` | (8.488, 94.25, 25.70), 1.3418 |
| constrained field-zero | 3.8 | solved below | (8.4688, 94.4646, 25.7114) |
| `Φ` and `Φ_proj` at the field-zero | 3.8 | solved below | 5.9946 → "5.99", 0.00000000 |
| separation field-zero ↔ constrained NBS | 3.8 | `payoffs.dist_M` | 0.0290 → "0.029" |
| Table B.8, all seven rows; R², max err | 3.8 | `constrained_rest_point` | R²=0.99945, 0.090 |
| `d(8.5)` unconstrained | 3.8 | same | 26.000000 |

The field-zero is not printed by any script, so it was re-solved: minimise
`phi_projected` over the budget surface `pq = 800`. It lands at
Φ_proj = 0 to eight decimals, which is what "field-zero" means, and the
coordinates and Φ then match the thesis.

## Does not reproduce: the Nash-product agreement

Section 3.2 recorded the closed form and a numerical maximisation of the Nash
product agreeing to **9.1e-6** (`docs/formulation.md` line 54). Against the
pinned environment the figure is **2.9e-6 scaled units** (2.9e-5 in raw
coordinates), stable across repeated runs.

`nbs_numeric` is a multi-start SLSQP solve, so this is the same class of
environment-dependence that limitation D3 already records for the solver-status
probe (4 of 60 → 7 of 60). The thesis now quotes the reproducible figure and
says so. Nothing downstream depends on it: it is a coincidence check on
Proposition 1, and both values confirm the coincidence.

## Reproduce

```bash
uv run python experiments/certificates/payoff_validation2.py   # E7, E8, E9
uv run python experiments/certificates/payoff_validation3.py   # E11, E12, E13
uv run python experiments/certificates/e13_dcbf.py             # constrained NBS
uv run python experiments/constrained_rest_point.py            # Table B.8
```

The field-zero, which no script prints:

```bash
cd experiments/certificates && uv run python - <<'PY'
import numpy as np
from scipy.optimize import minimize
import sys; sys.path.insert(0, "../..")
from src.payoffs import PayoffModel, dist_M
from src.certificates.energy import phi, phi_projected
from experiments.certificates.e13_dcbf import CONTRACT, constrained_nbs

m, B = PayoffModel(), 800.0
def obj(v):
    q, d = v
    x = np.array([B / q * (1 - 1e-12), q, d])
    val = phi_projected(m, x, CONTRACT)
    return 1e6 if not np.isfinite(val) else val

best = min((minimize(obj, [q0, 25.7], method="Nelder-Mead",
                     options=dict(xatol=1e-10, fatol=1e-12,
                                  maxiter=20000, maxfev=20000))
            for q0 in (94.0, 94.5, 95.0, 96.0)), key=lambda r: r.fun)
q, d = best.x
x = np.array([B / q * (1 - 1e-12), q, d])
print(x, phi(m, x), phi_projected(m, x, CONTRACT),
      dist_M(x, np.asarray(constrained_nbs(m), float)))
PY
```

Expected: `[8.4688 94.4646 25.7114] 5.9946 0.0 0.0290`.
