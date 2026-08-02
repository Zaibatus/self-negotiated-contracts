"""
Discrete-time CBF-QP contract filter for bilateral negotiation — minimal prototype.

Thesis unit under test: does a discrete-time control barrier function (DCBF)
condition, enforced by a minimally-invasive QP, keep negotiation trajectories
inside a contract-defined safe set without destroying convergence?

State: term vector x = (price, quantity, deadline)
Dynamics: x_{k+1} = x_k + u_k   (u_k = joint offer adjustment this round)
Contract (safe set C = {x : h_i(x) >= 0} for all i), affine constraints:
    h1: buyer budget       B - price*quantity        >= 0
    h2: seller cost floor  price - c                 >= 0
    h3: min quantity       quantity - q_min          >= 0
    h4: max quantity       q_max - quantity          >= 0
    h5: deadline floor     deadline - d_min          >= 0
    h6: deadline ceiling   d_max - deadline          >= 0

DCBF condition (Agrawal & Sreenath, discrete-time exponential CBF):
    h_i(x_{k+1}) >= (1 - gamma) * h_i(x_k)      for all i,  gamma in (0,1]

Filter: QP that minimally perturbs the proposed adjustment u_prop, with slack
for graceful degradation (never infeasible):
    min_{u, d}  ||u - u_prop||^2 + rho * ||d||^2
    s.t.        h_i(x + u) >= (1-gamma) h_i(x) - d_i,   d_i >= 0

h1 is bilinear in (price, quantity); we linearise it around x_k each round
(valid for the small per-round adjustments typical of negotiation) and
verify satisfaction on the true nonlinear h after the step.
"""

import numpy as np
from scipy.optimize import minimize

rng = np.random.default_rng(0)

# ----------------------------- Contract -----------------------------------

class Contract:
    """Affine-ish contract over term vector x = (price, quantity, deadline)."""

    def __init__(self, budget=1000.0, cost_floor=6.0,
                 q_min=20.0, q_max=120.0, d_min=7.0, d_max=45.0):
        self.B, self.c = budget, cost_floor
        self.q_min, self.q_max = q_min, q_max
        self.d_min, self.d_max = d_min, d_max

    def h(self, x):
        p, q, d = x
        return np.array([
            self.B - p * q,        # h1 budget (bilinear)
            p - self.c,            # h2 cost floor
            q - self.q_min,        # h3
            self.q_max - q,        # h4
            d - self.d_min,        # h5
            self.d_max - d,        # h6
        ])

    def grad_h(self, x):
        """Jacobian of h at x (h1 linearised)."""
        p, q, _ = x
        return np.array([
            [-q, -p, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, -1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.0, 0.0, -1.0],
        ])


# --------------------------- DCBF-QP filter --------------------------------

def dcbf_filter(x, u_prop, contract, gamma=0.4, rho=1e4):
    """Minimally perturb u_prop so the DCBF condition holds (with slack).

    Returns (u_safe, slack_used, intervention_norm).
    """
    h0 = contract.h(x)
    J = contract.grad_h(x)
    m = len(h0)

    # decision variable z = [u (3), d (m)]
    def obj(z):
        u, d = z[:3], z[3:]
        return np.sum((u - u_prop) ** 2) + rho * np.sum(d ** 2)

    def obj_grad(z):
        u, d = z[:3], z[3:]
        return np.concatenate([2 * (u - u_prop), 2 * rho * d])

    cons = []
    # DCBF: h(x) + J u >= (1-gamma) h(x) - d   <=>   J u + gamma h(x) + d >= 0
    for i in range(m):
        cons.append({
            "type": "ineq",
            "fun": (lambda z, i=i: J[i] @ z[:3] + gamma * h0[i] + z[3 + i]),
            "jac": (lambda z, i=i: np.concatenate(
                [J[i], np.eye(m)[i]])),
        })
    # slack nonnegative
    for i in range(m):
        cons.append({
            "type": "ineq",
            "fun": (lambda z, i=i: z[3 + i]),
            "jac": (lambda z, i=i: np.concatenate(
                [np.zeros(3), np.eye(m)[i]])),
        })

    z0 = np.concatenate([u_prop, np.zeros(m)])
    res = minimize(obj, z0, jac=obj_grad, constraints=cons, method="SLSQP",
                   options={"maxiter": 200, "ftol": 1e-10})
    u_safe, d = res.x[:3], res.x[3:]
    return u_safe, float(np.sum(d)), float(np.linalg.norm(u_safe - u_prop))


# ------------------------- Scripted negotiators -----------------------------

def make_proposal(x, k, role, targets, noise=1.0):
    """Concession-based proposal with decaying rate (a contraction), so the
    ungoverned dynamics naturally converge — isolating the filter's effect
    on invariance. Occasionally overshoots (violating the contract) —
    the behaviour an ungoverned LLM negotiator exhibits."""
    tp, tq, td = targets[role]
    rate = 0.25 * (0.90 ** k)          # decaying concession -> contraction
    u = rate * (np.array([tp, tq, td]) - x) + \
        rng.normal(0, noise * (0.93 ** k), 3)
    # occasional aggressive overshoot (10% of rounds)
    if rng.random() < 0.10:
        u *= rng.uniform(2.5, 4.0)
    return u


def run_episode(contract, filtered, T=40, gamma=0.4):
    """One bilateral negotiation. Buyer and seller alternate adjustments.
    Returns metrics dict."""
    # start from a feasible but tense point
    x = np.array([9.0, 90.0, 30.0])
    targets = {
        "buyer":  (6.5, 110.0, 40.0),   # low price, high qty, late deadline
        "seller": (11.5, 60.0, 12.0),   # high price, low qty, early deadline
    }
    breaches, interventions, slack_total = 0, [], 0.0
    traj = [x.copy()]
    for k in range(T):
        role = "buyer" if k % 2 == 0 else "seller"
        u_prop = make_proposal(x, k, role, targets)
        if filtered:
            u, s, dv = dcbf_filter(x, u_prop, contract, gamma=gamma)
            slack_total += s
            interventions.append(dv)
        else:
            u = u_prop
            interventions.append(0.0)
        x = x + u
        traj.append(x.copy())
        if np.any(contract.h(x) < -1e-6):
            breaches += 1
    # convergence proxy: mean step size over the last 5 rounds is small
    tail = [np.linalg.norm(traj[i + 1] - traj[i]) for i in range(T - 5, T)]
    settled = float(np.mean(tail)) < 2.5
    p, q, _ = x
    surplus = (targets["buyer"][0] * 0 + (contract.B / max(q, 1e-9)) - p) * q \
        if np.all(contract.h(x) >= -1e-6) else 0.0  # crude welfare proxy
    return {
        "breach_rounds": breaches,
        "breach_rate": breaches / T,
        "settled": settled,
        "final_x": x,
        "mean_intervention": float(np.mean(interventions)),
        "slack_total": slack_total,
        "surplus_proxy": max(surplus, 0.0),
    }


# --------------------------------- Main -------------------------------------

def main(episodes=50):
    contract = Contract()
    results = {}
    for mode, filtered in [("ungoverned", False), ("dcbf_filtered", True)]:
        runs = [run_episode(contract, filtered) for _ in range(episodes)]
        results[mode] = {
            "breach_rate": np.mean([r["breach_rate"] for r in runs]),
            "episodes_with_breach": np.mean(
                [r["breach_rounds"] > 0 for r in runs]),
            "settle_rate": np.mean([r["settled"] for r in runs]),
            "mean_intervention": np.mean(
                [r["mean_intervention"] for r in runs]),
            "mean_slack": np.mean([r["slack_total"] for r in runs]),
            "surplus_proxy": np.mean([r["surplus_proxy"] for r in runs]),
        }

    print(f"{'metric':<28}{'ungoverned':>14}{'dcbf_filtered':>16}")
    print("-" * 58)
    for key in ["breach_rate", "episodes_with_breach", "settle_rate",
                "mean_intervention", "mean_slack", "surplus_proxy"]:
        a, b = results["ungoverned"][key], results["dcbf_filtered"][key]
        print(f"{key:<28}{a:>14.4f}{b:>16.4f}")


if __name__ == "__main__":
    main()
