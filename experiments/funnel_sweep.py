"""Where does the filter funnel outcomes to, as theta's boundary moves?

`docs/notes/2026-08-06-drift-and-funnelling.md` establishes that arm B collapses
every settled price onto theta's budget boundary, and then makes a claim it does
not test:

    Arm B's settled terms look closer to x*_NBS (0.085 against arm A's 0.221)
    only because on this calibration the boundary happens to sit ~0.11 scaled
    units from the NBS. That is a coincidence of bargain_3_9, not a property of
    the mechanism, and a scenario where the budget binds far from the efficient
    split would show the filter pushing the outcome away from the bargaining
    solution.

That is a conjecture stated as an aside, and it is load-bearing: it is the only
thing standing between "the filter improves outcomes" and "the filter improves
outcomes here, by luck". Live it cannot be tested, because building a scenario
whose budget binds far from the efficient split means rewriting `menu_features`
and re-running the marketplace, and the experimental programme is closed.

In simulation it is one sweep. The negotiation is the concession dynamic the
formulation actually assumes -- x_{k+1} = x_k + eta * F(x_k) + noise, whose rest
point is x*_NBS by Proposition 1 -- run with and without the shipped DCBF
filter, over a budget that slides the funnel point B/q_min from far below the
bargaining price to far above it.

What it can and cannot show. These are scripted agents, so this says nothing
about whether LLMs converge; that is the separate, unresolved question. What it
tests is a property of the *mechanism*: given that outcomes collapse onto the
boundary, does that help or hurt, and does it depend on where the boundary is?
Because the dynamic is exactly the one the theory assumes, a negative result
here cannot be blamed on the agents.

Quantity is pinned (q_min = q_max) because that is what the live scenarios do:
the basket is the customer's, the filter never moves it, and every arm B settled
quantity has SD 0.000.

Reproduce:

    uv run python experiments/funnel_sweep.py --seeds 200
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import DCBFFilter, project_into_safe_set  # noqa: E402
from src.contract import Contract  # noqa: E402
from src.payoffs import SCALE, PayoffModel, dist_M  # noqa: E402


def negotiate(
    model: PayoffModel,
    contract: Contract | None,
    x0: np.ndarray,
    rng: np.random.Generator,
    gamma: float,
    eta: float,
    noise: float,
    t_max: int,
) -> tuple[np.ndarray, int, int]:
    """Run one negotiation. Returns (settled terms, rounds, filter bites)."""
    filt = DCBFFilter(gamma=gamma) if contract is not None else None
    x = x0.copy()
    bites = 0

    # The opening is projected, not barrier-stepped -- same as the protocol.
    if contract is not None and not contract.is_safe(x):
        x = project_into_safe_set(x, contract)
        bites += 1

    for round_index in range(t_max):
        field = model.concession_field(x)
        u = eta * field * SCALE**2
        if noise > 0:
            u = u + rng.normal(0.0, noise, 3) * SCALE

        if filt is not None and contract is not None:
            result = filt.step([x], [u], [contract])
            if not np.allclose(result.u[:3], u, atol=1e-9):
                bites += 1
            u = result.u[:3]

        x_next = x + u
        if dist_M(x_next, x) < 1e-4:
            x = x_next
            return x, round_index + 1, bites
        x = x_next

    return x, t_max, bites


def sweep(
    seeds: int,
    gamma: float,
    eta: float,
    noise: float,
    t_max: int,
    n_points: int,
) -> dict[str, Any]:
    model = PayoffModel()
    x_star, _ = model.nash_bargaining_solution()
    p_star, q_star, d_star = float(x_star[0]), float(x_star[1]), float(x_star[2])

    # Quantity pinned at the efficient basket, as the live scenarios pin it.
    q_pin = float(round(q_star))
    cost_floor = model.c

    # The seller opens above the bargaining price, as sellers do.
    x0 = np.array([p_star * 1.5, q_pin, d_star])

    # Slide the funnel point B/q_pin across the bargaining price.
    boundaries = np.linspace(cost_floor * 1.02, p_star * 1.6, n_points)

    rows: list[dict[str, Any]] = []
    for p_boundary in boundaries:
        budget = float(p_boundary * q_pin)
        contract = Contract(
            budget=budget,
            cost_floor=cost_floor,
            q_min=q_pin,
            q_max=q_pin,
            deadline_active=False,
        )
        if not contract.is_satisfiable():
            continue

        free_d, filt_d, filt_p, free_p, bites_all, rounds_all = [], [], [], [], [], []
        filt_dl, free_dl = [], []
        for seed in range(seeds):
            rng_free = np.random.default_rng(10_000 + seed)
            rng_filt = np.random.default_rng(10_000 + seed)  # same noise draw
            x_free, _, _ = negotiate(
                model, None, x0, rng_free, gamma, eta, noise, t_max
            )
            x_filt, rounds, bites = negotiate(
                model, contract, x0, rng_filt, gamma, eta, noise, t_max
            )
            free_d.append(dist_M(x_free, x_star))
            filt_d.append(dist_M(x_filt, x_star))
            free_p.append(float(x_free[0]))
            filt_p.append(float(x_filt[0]))
            bites_all.append(bites)
            rounds_all.append(rounds)
            filt_dl.append(float(x_filt[2]))
            free_dl.append(float(x_free[2]))

        rows.append(
            {
                "p_boundary": float(p_boundary),
                "budget": budget,
                "boundary_minus_nbs": float(p_boundary - p_star),
                "free_dist_mean": float(np.mean(free_d)),
                "free_dist_sd": float(np.std(free_d)),
                "filt_dist_mean": float(np.mean(filt_d)),
                "filt_dist_sd": float(np.std(filt_d)),
                "free_price_sd": float(np.std(free_p)),
                "filt_price_sd": float(np.std(filt_p)),
                "filt_price_mean": float(np.mean(filt_p)),
                # Pinning price displaces the terms the contract does NOT
                # constrain: once price is held off its efficient value the
                # rest point of the remaining coordinates moves too.
                "filt_deadline_mean": float(np.mean(filt_dl)),
                "free_deadline_mean": float(np.mean(free_dl)),
                "bites_mean": float(np.mean(bites_all)),
                "rounds_mean": float(np.mean(rounds_all)),
                "filter_helps": bool(np.mean(filt_d) < np.mean(free_d)),
            }
        )

    return {
        "x_star": x_star.tolist(),
        "p_star": p_star,
        "q_pin": q_pin,
        "cost_floor": cost_floor,
        "x0": x0.tolist(),
        "gamma": gamma,
        "eta": eta,
        "noise": noise,
        "t_max": t_max,
        "seeds": seeds,
        "rows": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=200)
    parser.add_argument("--gamma", type=float, default=0.4)
    parser.add_argument("--eta", type=float, default=1e-2)
    parser.add_argument("--noise", type=float, default=0.02)
    parser.add_argument("--t-max", type=int, default=300)
    parser.add_argument("--points", type=int, default=17)
    parser.add_argument("--out", default="results/summary/funnel_sweep.json")
    args = parser.parse_args()

    report = sweep(
        args.seeds, args.gamma, args.eta, args.noise, args.t_max, args.points
    )
    p_star = report["p_star"]
    print(f"x*_NBS = {[round(v, 3) for v in report['x_star']]}   "
          f"p* = {p_star:.3f}   q pinned at {report['q_pin']:.0f}   "
          f"seeds = {report['seeds']}\n")

    print(f"{'B/q_min':>9}{'vs p*':>8}{'free d':>9}{'filt d':>9}"
          f"{'verdict':>10}{'filt SD':>10}{'free SD':>9}{'deadline':>10}")
    for row in report["rows"]:
        verdict = "helps" if row["filter_helps"] else "HURTS"
        if row["bites_mean"] < 1e-9:
            verdict = "inert"
        print(
            f"{row['p_boundary']:>9.2f}{row['boundary_minus_nbs']:>8.2f}"
            f"{row['free_dist_mean']:>9.3f}{row['filt_dist_mean']:>9.3f}"
            f"{verdict:>10}{row['filt_price_sd']:>10.4f}"
            f"{row['free_price_sd']:>9.4f}{row['filt_deadline_mean']:>10.2f}"
        )

    print(f"\n  deadline = settled deadline under the filter; unfiltered it is "
          f"{report['rows'][0]['free_deadline_mean']:.2f}, and d* = "
          f"{report['x_star'][2]:.0f}. The contract does not constrain the "
          f"deadline at all.")

    binding = [r for r in report["rows"] if r["bites_mean"] > 1e-9]
    helps = [r for r in binding if r["filter_helps"]]
    hurts = [r for r in binding if not r["filter_helps"]]
    print(f"\nof {len(binding)} budgets where the filter binds: "
          f"{len(helps)} help, {len(hurts)} hurt")
    if hurts:
        worst = max(hurts, key=lambda r: r["filt_dist_mean"] - r["free_dist_mean"])
        print(f"worst case  B/q_min = {worst['p_boundary']:.2f} "
              f"({worst['boundary_minus_nbs']:+.2f} vs p*): "
              f"distance {worst['free_dist_mean']:.3f} -> "
              f"{worst['filt_dist_mean']:.3f}, "
              f"{worst['filt_dist_mean'] / max(worst['free_dist_mean'], 1e-9):.1f}x worse")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
