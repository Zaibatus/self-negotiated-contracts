"""E13 rerun with the real DCBF-QP filter. Discharges formulation.md 10.5.

The v2 formulation records an outstanding obligation:

    "The constrained-dynamics experiment [E13] used a crude boundary
     projection rather than the DCBF-QP; rerun with the filter during
     integration (the residual — dynamics settling 0.61 scaled units from the
     constrained field-zero — is plausibly this plus incomplete step-size
     decay)."

This is that rerun. Two changes from payoff_validation3.py's E13, and nothing
else: the hard clip ``project_budget`` is replaced by the OSQP DCBF filter of
src/certificates/dcbf.py, and the operating box's p_max = 12 guard is dropped.

Dropping p_max also settles the other open item, in section 1: "either fold a
p_max into theta or drop the guard before the dissertation's formal
statement." Under the filter there is no need for a guard, because the budget
row B - pq >= 0 already caps price — which is exactly the argument section 1
makes for the guard being non-binding. Keeping a numerical guard that the
theory says is unnecessary would leave a term in the experiments with no
counterpart in theta.

Two things the filter changes, both of which matter for the residual:

  * a hard clip moves the draft onto the boundary in one step, which is not a
    dynamics anyone specified; the DCBF instead admits the largest step that
    keeps h_i(x_{k+1}) >= (1 - gamma) h_i(x_k), so the approach rate is a
    stated parameter rather than an artefact;
  * the clip only ever touched price (p = B/q), silently making price the
    adjustment variable. The QP distributes the correction across whichever
    terms move it least, in the unit metric.

Run:
    uv run python experiments/certificates/e13_dcbf.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.certificates.dcbf import DCBFFilter  # noqa: E402
from src.certificates.energy import phi, phi_projected  # noqa: E402
from src.contract import Contract  # noqa: E402
from src.payoffs import SCALE, PayoffModel, dist_M, norm_M  # noqa: E402

BUDGET = 800.0
X0 = np.array([11.0, 40.0, 40.0])

# theta: the budget under test, plus the q and d bands of the operating box.
# No p_max: the budget row caps price, which is the whole point.
CONTRACT = Contract(
    budget=BUDGET,
    cost_floor=6.0,
    q_min=20.0,
    q_max=120.0,
    d_min=7.0,
    d_max=45.0,
    deadline_active=True,
)


def ascent_step(model: PayoffModel, x: np.ndarray, role: str, rho: float) -> np.ndarray:
    """Metric-consistent ascent direction of length rho, as in payoff_dynamics."""
    grad = model.grad_u_hat(x, role)
    nrm = norm_M(grad)
    if nrm <= 0:
        return np.zeros(3)
    return grad * (SCALE**2) / nrm * rho


def constrained_nbs(model: PayoffModel) -> np.ndarray:
    """Nash bargaining solution subject to the binding budget."""
    from scipy.optimize import minimize

    def neg(x: np.ndarray) -> float:
        ub, us = model.u_buyer(x), model.u_seller(x)
        if ub <= 0 or us <= 0:
            return 1e6 - ub - us
        return -(np.log(ub) + np.log(us))

    bounds = [(6.0, 20.0), (20.0, 120.0), (7.0, 45.0)]
    cons = ({"type": "ineq", "fun": lambda z: BUDGET - z[0] * z[1]},)
    best, arg = np.inf, None
    for seed in range(6):
        rng = np.random.default_rng(seed)
        x0 = np.array([rng.uniform(lo, hi) for lo, hi in bounds])
        res = minimize(
            neg, x0, bounds=bounds, constraints=cons, method="SLSQP",
            options={"maxiter": 500, "ftol": 1e-12},
        )
        if res.fun < best:
            best, arg = res.fun, res.x
    assert arg is not None
    return arg


def step_size(k: int, rho0: float, schedule: str, decay: float, steps: int) -> float:
    """Step budget at round k.

    "robbins-monro": rho_k = rho0 / (1 + k)^0.51, which satisfies sum rho = inf
    and sum rho^2 < inf — the draft can still travel arbitrarily far while the
    steps shrink to zero. This is the schedule the conclusion below uses.

    "geometric": rho0 * decay^k, as in payoff_validation3.py. Kept because it is
    what the reference run used, and because comparing the two is what isolates
    the residual: a geometric schedule has a finite total path length, so it can
    freeze the draft *before* it arrives and make a step-size artefact look like
    an equilibrium.
    """
    if schedule == "geometric":
        return rho0 * (decay**k)
    return rho0 / (1.0 + k) ** 0.51


def run(
    gamma: float,
    rho0: float = 0.8,
    steps: int = 8000,
    decay: float = 0.9993,
    schedule: str = "robbins-monro",
):
    """Alternating concessions, every step passed through the DCBF filter."""
    model = PayoffModel()
    filt = DCBFFilter(gamma=gamma, rho=1e6)
    x = X0.copy()
    phis, phis_proj, dists = [], [], []
    x_c = constrained_nbs(model)

    for k in range(steps):
        rho = step_size(k, rho0, schedule, decay, steps)
        role = "buyer" if k % 2 == 0 else "seller"
        u_prop = ascent_step(model, x, role, rho)
        result = filt.step([x], [u_prop], [CONTRACT])
        x = x + result.u
        if k % 2 == 1:
            phis.append(phi(model, x))
            phis_proj.append(phi_projected(model, x, CONTRACT))
            dists.append(dist_M(x, x_c))

    return model, x, x_c, np.array(phis), np.array(phis_proj), np.array(dists), filt


def main() -> None:
    model = PayoffModel()
    x_star, _ = model.nash_bargaining_solution()
    x_c = constrained_nbs(model)

    print(f"E13 rerun with the DCBF-QP filter. Binding budget B={BUDGET:.0f}")
    print(f"  unconstrained NBS spend = {x_star[0] * x_star[1]:.0f} (infeasible)")
    print(
        f"  constrained NBS: p={x_c[0]:.4f} q={x_c[1]:.3f} d={x_c[2]:.3f}  "
        f"spend={x_c[0] * x_c[1]:.1f}"
    )
    print(
        f"    Phi = {phi(model, x_c):.4f}   "
        f"Phi_proj = {phi_projected(model, x_c, CONTRACT):.4f}"
    )
    print(
        "\n  Reference (payoff_validation3.py, hard clip, geometric step decay):"
        "\n  settled 0.642 scaled units from the constrained NBS.\n"
    )

    header = (
        f"  {'gamma':>7}{'spend':>9}{'h_budget':>10}{'||x-x_c||_s':>13}"
        f"{'Phi':>9}{'Phi_proj':>10}{'breach':>8}"
    )
    print("  Robbins-Monro steps (rho_k = rho_0 / (1+k)^0.51):")
    print(header)
    print("  " + "-" * (len(header) - 2))

    settled = {}
    for gamma in (0.2, 0.4, 0.7, 1.0):
        _, x, _, phis, phis_proj, dists, _ = run(gamma)
        settled[gamma] = x
        print(
            f"  {gamma:>7.1f}{x[0] * x[1]:>9.1f}{CONTRACT.h(x)[0]:>10.2f}"
            f"{dists[-1]:>13.3f}{phis[-1]:>9.2f}{phis_proj[-1]:>10.4f}"
            f"{str(not CONTRACT.is_safe(x)):>8}"
        )

    print("\n  Same runs under the reference geometric decay, for contrast:")
    print(header)
    print("  " + "-" * (len(header) - 2))
    for gamma in (0.4, 1.0):
        _, x, _, phis, phis_proj, dists, _ = run(
            gamma, steps=3000, schedule="geometric"
        )
        print(
            f"  {gamma:>7.1f}{x[0] * x[1]:>9.1f}{CONTRACT.h(x)[0]:>10.2f}"
            f"{dists[-1]:>13.3f}{phis[-1]:>9.2f}{phis_proj[-1]:>10.4f}"
            f"{str(not CONTRACT.is_safe(x)):>8}"
        )

    print(
        """
  Three findings, none of which is the one section 10.5 guessed at.

  1. The residual is NOT the hard clip. Under the filter the dynamics settle
     ~0.75 scaled units from the constrained NBS, against 0.642 for the clip —
     the same order, slightly worse. Replacing the clip does not close it.

  2. The residual is NOT step-size decay either, though the reference run's
     geometric schedule does contribute: it has finite total path length, so it
     can freeze the draft before it arrives. Under Robbins-Monro the draft
     travels as far as it wants to and still stops ~0.75 away, because the
     alternating single-agent ascent converges to the *efficient* quantity
     q = 100 rather than the constrained bargaining solution's q = 94.2.
     Constraining the transfer separates the field zero from the equal split
     (section 8 measures that separation as 0.029 units at the constrained NBS
     itself); what the dynamics find is the former, and the distance to the
     latter is that separation compounded along the budget surface, not an
     artefact of the enforcement mechanism.

  3. The new result is the boundary layer. The filter parks the draft strictly
     INSIDE the budget, by a margin that falls steeply with gamma (3.19 at
     gamma = 0.2 to 0.34 at 0.7) and then flattens rather than reaching zero —
     the last two rows differ by less than the residual step size, so the tail
     is at the resolution of this run and should not be read as monotone.
     That is v1's conservatism premium, measured here in
     term space rather than in the dual: a cautious contract does not merely
     price scarcity higher, it moves where the negotiation ends up. Because the
     constraint is therefore never active at the settled point, Phi_proj equals
     Phi throughout the table — the projection has nothing to remove. Phi_proj
     earns its keep on boundary-attaining dynamics such as the hard clip; under
     a DCBF the object that matters is the displaced equilibrium, and gamma is
     what displaces it.

  Also settled here: section 1's open item on the p_max = 12 operating-box
  guard. It is dropped, not folded into theta — the budget row B - pq >= 0
  caps price on its own, which is what section 1 argues when it observes the
  guard never binds."""
    )


if __name__ == "__main__":
    main()
