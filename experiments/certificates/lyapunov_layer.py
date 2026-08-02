"""
Lyapunov/Nash layer over the DCBF-filtered negotiation — prototype v2.

Framing (Pietro's language):
  * Agreement point x* = Nash equilibrium: the fixed point of the alternating
    concession (best-response-like) map — at x*, neither side's update moves
    the state, i.e. mutual stationarity of the bargaining dynamics.
  * Contract certificate = Lyapunov function V(x) = ||x - x*||^2 with the
    discrete-time decrease condition  V(x_{k+1}) <= (1-alpha) V(x_k).
  * Composition is additive: V_market = sum_i V_i ("the sum is the sum of
    the functions"). Tested for independent AND coupled pairs (shared
    supplier capacity), enforced by a joint DCBF filter.
  * The contract is a controller of the interaction, starting from safety:
    the DCBF layer runs underneath; we measure the CLF-CBF tension (steps
    where the safety intervention increases V) = the price of safety.

Theory for the scripted dynamics (noise-free): alternating updates
    x <- (1-r) x + r t_role
give the two-round composite map
    x_{k+2} = (1-r)^2 x_k + r(1-r) t_first + r t_second
an affine contraction with factor (1-r)^2, unique fixed point
    x* = [ r(1-r) t_first + r t_second ] / (1 - (1-r)^2)
and exact decrease  V_{k+2} = (1-r)^4 V_k .

NOTE (EIP hook): here x* is known in closed form because the dynamics are
scripted. With LLM agents x* is unknown a priori — that is precisely the
equilibrium-independent passivity (EIP) motivation for the full thesis.
"""

import numpy as np
from scipy.optimize import minimize

from dcbf_negotiation import Contract

rng = np.random.default_rng(1)

R = 0.25          # constant concession rate (contraction)
NOISE = 0.5       # proposal noise std
OVERSHOOT_P = 0.10

TARGETS = {
    "buyer":  np.array([6.5, 110.0, 40.0]),
    "seller": np.array([11.5, 60.0, 12.0]),
}


# ------------------------- Nash point & Lyapunov ----------------------------

def nash_point(r=R, first="buyer", second="seller"):
    """Fixed point of the two-round composite concession map."""
    tf, ts = TARGETS[first], TARGETS[second]
    return (r * (1 - r) * tf + r * ts) / (1 - (1 - r) ** 2)


def V(x, x_star):
    return float(np.sum((x - x_star) ** 2))


# --------------------------- Scripted proposals -----------------------------

def proposal(x, role, noisy=True):
    u = R * (TARGETS[role] - x)
    if noisy:
        u = u + rng.normal(0, NOISE, 3)
        if rng.random() < OVERSHOOT_P:
            u = u * rng.uniform(2.5, 4.0)
    return u


# ------------------------ Joint DCBF filter (n pairs) -----------------------

def joint_dcbf_filter(xs, u_props, contracts, shared_capacity=None,
                      gamma=0.4, rho=1e4):
    """DCBF-QP over n pairs simultaneously. Optional shared constraint:
        h_sh = Q - sum_i quantity_i >= 0
    demonstrating contract composition: stacked constraints, one filter.

    xs, u_props: lists of 3-vectors. Returns (u_safes, total_slack,
    interventions list).
    """
    n = len(xs)
    h_blocks, J_blocks = [], []
    for x, c in zip(xs, contracts):
        h_blocks.append(c.h(x))
        J_blocks.append(c.grad_h(x))

    rows = []      # (grad over full 3n u-vector, h0 value)
    for i in range(n):
        for j in range(len(h_blocks[i])):
            g = np.zeros(3 * n)
            g[3 * i:3 * i + 3] = J_blocks[i][j]
            rows.append((g, h_blocks[i][j]))
    if shared_capacity is not None:
        Q = shared_capacity
        h_sh = Q - sum(x[1] for x in xs)
        g = np.zeros(3 * n)
        for i in range(n):
            g[3 * i + 1] = -1.0
        rows.append((g, h_sh))

    m = len(rows)
    u_prop_flat = np.concatenate(u_props)

    def obj(z):
        u, d = z[:3 * n], z[3 * n:]
        return np.sum((u - u_prop_flat) ** 2) + rho * np.sum(d ** 2)

    def obj_grad(z):
        u, d = z[:3 * n], z[3 * n:]
        return np.concatenate([2 * (u - u_prop_flat), 2 * rho * d])

    cons = []
    for idx, (g, h0) in enumerate(rows):
        cons.append({
            "type": "ineq",
            "fun": (lambda z, g=g, h0=h0, idx=idx:
                    g @ z[:3 * n] + gamma * h0 + z[3 * n + idx]),
        })
        cons.append({"type": "ineq", "fun": (lambda z, idx=idx: z[3 * n + idx])})

    z0 = np.concatenate([u_prop_flat, np.zeros(m)])
    res = minimize(obj, z0, jac=obj_grad, constraints=cons, method="SLSQP",
                   options={"maxiter": 300, "ftol": 1e-10})
    u = res.x[:3 * n]
    d = res.x[3 * n:]
    u_safes = [u[3 * i:3 * i + 3] for i in range(n)]
    interventions = [float(np.linalg.norm(u_safes[i] - u_props[i]))
                     for i in range(n)]
    return u_safes, float(np.sum(d)), interventions


# ------------------------------ Experiments ---------------------------------

def run_pair(T=40, filtered=True, noisy=True, contract=None, seed_state=None):
    """Single pair. Returns V trajectory (per round-pair), breach count,
    per-step (intervention, dV) records for tension analysis."""
    contract = contract or Contract()
    x = np.array([9.0, 90.0, 30.0]) if seed_state is None else seed_state.copy()
    x_star = nash_point()
    Vs = [V(x, x_star)]
    breaches = 0
    tension = []          # (intervened?, dV_over_round_pair)
    for k in range(T):
        role = "buyer" if k % 2 == 0 else "seller"
        u_prop = proposal(x, role, noisy=noisy)
        if filtered:
            (u,), _, (dv,) = joint_dcbf_filter([x], [u_prop], [contract])
        else:
            u, dv = u_prop, 0.0
        x = x + u
        if np.any(contract.h(x) < -1e-6):
            breaches += 1
        if k % 2 == 1:                       # end of a buyer+seller round pair
            Vs.append(V(x, x_star))
            tension.append((dv > 1e-3, Vs[-1] - Vs[-2]))
    return np.array(Vs), breaches, tension


def contraction_rate(Vs):
    """Empirical per-round-pair contraction factor via log-linear fit,
    restricted to the segment above the noise floor."""
    Vs = np.maximum(Vs, 1e-12)
    k = np.arange(len(Vs))
    mask = Vs > max(1.0, Vs[-1] * 2)         # ignore the noise-ball tail
    if mask.sum() < 3:
        mask = k < max(3, len(k) // 2)
    coef = np.polyfit(k[mask], np.log(Vs[mask]), 1)[0]
    return float(np.exp(coef))


def experiment_single(episodes=50):
    theory = (1 - R) ** 4
    out = {}
    for label, filtered, noisy in [("noise-free ungoverned", False, False),
                                   ("noisy ungoverned", False, True),
                                   ("noisy filtered", True, True)]:
        rates, decs, brs, tens_up = [], [], [], []
        for _ in range(episodes if noisy else 1):
            Vs, br, tension = run_pair(filtered=filtered, noisy=noisy)
            rates.append(contraction_rate(Vs))
            dV = np.diff(Vs)
            decs.append(np.mean(dV <= 1e-9))
            brs.append(br)
            up_on_interv = [dv for (iv, dv) in tension if iv and dv > 0]
            tens_up.append(len(up_on_interv) / max(len(tension), 1))
        out[label] = {
            "empirical_contraction": np.mean(rates),
            "frac_steps_V_decreasing": np.mean(decs),
            "breach_rounds_mean": np.mean(brs),
            "frac_pairs_tension(V_up_on_intervention)": np.mean(tens_up),
        }
    return theory, out


def experiment_composition(episodes=30, T=40, capacity=170.0):
    """Two pairs. (a) independent: V_sum decrease is additive by construction
    — verify numerically. (b) coupled by shared capacity Q < q1*+q2*:
    the joint filter must trade quantities off; does V_sum still decrease?"""
    results = {}
    for label, cap in [("independent (no coupling)", None),
                       (f"coupled (shared capacity Q={capacity})", capacity)]:
        rates, dec_fracs, breaches, cap_viol = [], [], [], []
        for _ in range(episodes):
            c1, c2 = Contract(), Contract()
            x1 = np.array([9.0, 90.0, 30.0])
            x2 = np.array([8.5, 95.0, 25.0])
            xs = nash_point()
            Vs = [V(x1, xs) + V(x2, xs)]
            br = 0
            for k in range(T):
                role = "buyer" if k % 2 == 0 else "seller"
                ups = [proposal(x1, role), proposal(x2, role)]
                (u1, u2), _, _ = joint_dcbf_filter(
                    [x1, x2], ups, [c1, c2], shared_capacity=cap)
                x1, x2 = x1 + u1, x2 + u2
                if np.any(c1.h(x1) < -1e-6) or np.any(c2.h(x2) < -1e-6):
                    br += 1
                if cap is not None and x1[1] + x2[1] > cap + 1e-6:
                    cap_viol.append(1)
                if k % 2 == 1:
                    Vs.append(V(x1, xs) + V(x2, xs))
            Vs = np.array(Vs)
            rates.append(contraction_rate(Vs))
            dec_fracs.append(np.mean(np.diff(Vs) <= 1e-9))
            breaches.append(br)
        results[label] = {
            "V_sum_contraction": np.mean(rates),
            "frac_steps_Vsum_decreasing": np.mean(dec_fracs),
            "breach_rounds_mean": np.mean(breaches),
            "capacity_violations_total": int(np.sum(cap_viol)),
        }
    return results


def main():
    theory, single = experiment_single()
    print(f"Theoretical contraction per round-pair (1-r)^4 = {theory:.4f}\n")
    for label, m in single.items():
        print(f"[{label}]")
        for k, v in m.items():
            print(f"    {k:<44}{v:>10.4f}")
        print()

    comp = experiment_composition()
    print("=== Composition: V_market = V_1 + V_2 ===\n")
    for label, m in comp.items():
        print(f"[{label}]")
        for k, v in m.items():
            print(f"    {k:<44}{v:>10.4f}")
        print()


if __name__ == "__main__":
    main()
