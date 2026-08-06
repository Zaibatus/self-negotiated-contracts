"""Shared CLI and the section 11 report.

Every arm is the same governed run with a different regulator mode, so the
knobs live here once. Keeping them shared is also what makes the arms
comparable: an arm that quietly used a different gamma, scenario or contract
spec would not be a treatment, it would be a different experiment.

The report is formulation.md v2 section 11, item by item:

    (i)   breach rate, filtered against ungoverned
    (ii)  Phi and Phi_proj trajectories — decreasing?
    (iii) G_kappa and the stopping round against the certified T_max
    (iv)  distance of the settled terms to x*_NBS from the estimated utilities
    (v)   realised surplus against W_max
    (vi)  shadow prices, from the OSQP duals

plus the one thing section 11 says to test rather than assume: whether the
agents' move/stall pattern is cost-benefit rationalizable at all. Every item
either reports a number or says why the data does not support one. A live
negotiation of five rounds cannot support all six, and printing a plausible
figure anyway is the failure mode this layout exists to prevent.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from src.certificates.energy import (
    contraction_transient,
    g_kappa,
    g_realised_series,
    phi,
    phi_projected,
)
from src.contract import ContractSpec, ControllerSpec
from src.marketplace_integration.payoff_estimation import (
    AcceptanceEvent,
    assess_rationalizability,
    calibrate,
    rounds_from_trajectory,
)
from src.payoffs import PayoffModel, dist_M

INSUFFICIENT = "insufficient data"


def build_parser(description: str) -> argparse.ArgumentParser:
    """The arm-invariant knobs."""
    parser = argparse.ArgumentParser(
        description=description, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--data",
        default="data/bargain_3_9",
        help="scenario folder; data/bargain_3_9 is the bargaining scenario, "
        "../multi-agent-marketplace/data/mexican_3_9 the stock control",
    )
    parser.add_argument("--experiment", required=True, help="Postgres schema name")
    parser.add_argument(
        "--gamma",
        type=float,
        default=0.4,
        help="DCBF rate; also the conservatism knob that shows up in the "
        "shadow prices and displaces where the negotiation settles",
    )
    parser.add_argument("--rho", type=float, default=1e4, help="QP slack penalty")
    parser.add_argument(
        "--capacity-factor",
        type=float,
        default=None,
        help="shared capacity per business as a fraction of the demand it "
        "faces; below 1.0 the coupling clause binds. Needs a scenario where "
        "some business can serve more than one customer — mexican_3_9 does "
        "not, mexican_33_99 does",
    )
    parser.add_argument("--solver", default="osqp", choices=["osqp", "slsqp"])
    parser.add_argument(
        "--t-max", type=int, default=12, help="liveness bound, in round-pairs"
    )
    parser.add_argument(
        "--kappa0", type=float, default=2.0, help="initial friction (deadline pressure)"
    )
    parser.add_argument(
        "--step-budget", type=float, default=0.5, help="rho of the agents, scaled units"
    )
    parser.add_argument("--q-max-factor", type=float, default=2.0)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--results", default="results")
    parser.add_argument("--override", action="store_true")
    return parser


def contract_spec(args: argparse.Namespace) -> ContractSpec:
    return ContractSpec(q_max_factor=args.q_max_factor)


def controller_spec(args: argparse.Namespace) -> ControllerSpec:
    return ControllerSpec(
        gamma=args.gamma,
        t_max=args.t_max,
        kappa0=args.kappa0,
        rho=args.step_budget,
    )


def run_arm(args: argparse.Namespace, mode: str) -> dict[str, Any]:
    """Run one governed arm and print the section 11 report."""
    # Imported here so --help works without a database driver present.
    from dotenv import load_dotenv

    from src.marketplace_integration.runner import run_governed_experiment

    load_dotenv()

    outcome = asyncio.run(
        run_governed_experiment(
            data_dir=args.data,
            experiment_name=args.experiment,
            mode=mode,
            gamma=args.gamma,
            rho=args.rho,
            capacity_factor=args.capacity_factor,
            solver=args.solver,
            contract_spec=contract_spec(args),
            results_dir=args.results,
            customer_max_steps=args.max_steps,
            override=args.override,
        )
    )

    protocol = outcome["protocol"]
    report = section_11_report(protocol, controller_spec(args))
    print_report(outcome["report"], report)

    path = Path(args.results) / args.experiment / "section_11.json"
    path.write_text(json.dumps(report, indent=2, default=_jsonable), encoding="utf-8")
    print(f"\nSection 11 report: {path}")
    return outcome


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------


def section_11_report(protocol: Any, controller: ControllerSpec) -> dict[str, Any]:
    """Per-negotiation measurements, or an explicit reason there are none."""
    registry = protocol.registry
    trajectories = protocol.trajectories(binding=False)

    negotiations: list[dict[str, Any]] = []
    as_arrays: dict[str, list[np.ndarray]] = {}
    for key, trajectory in sorted(trajectories.items()):
        as_arrays[key] = [np.asarray(x, dtype=float) for x in trajectory]
        business_id, customer_id = key.split("|", 1)
        negotiations.append(
            _one_negotiation(
                key=key,
                trajectory=as_arrays[key],
                business=registry.businesses.get(business_id),
                customer=registry.customers.get(customer_id),
                contract=registry.get(business_id, customer_id),
                records=[r for r in protocol.records if r.pair_id == key],
                controller=controller,
            )
        )

    return {
        "controller": {
            "gamma": controller.gamma,
            "t_max": controller.t_max,
            "kappa0": controller.kappa0,
            "rho": controller.rho,
        },
        "negotiations": negotiations,
        "aggregate": _aggregate(negotiations, as_arrays),
    }


def _one_negotiation(
    *,
    key: str,
    trajectory: list[np.ndarray],
    business: Any,
    customer: Any,
    contract: Any,
    records: list[Any],
    controller: ControllerSpec,
) -> dict[str, Any]:
    out: dict[str, Any] = {"pair": key, "rounds": len(trajectory)}

    # (vi) shadow prices come straight off the duals and need no payoff model.
    out["shadow_prices"] = _shadow_prices(records)

    # (i) breach rate is a property of the contract alone.
    if records:
        out["breach_rate"] = sum(r.breach for r in records) / len(records)
        out["breach_rounds"] = sum(r.breach for r in records)

    if business is None or customer is None:
        out["status"] = "no scenario profile for this pair"
        return out
    if len(trajectory) < 2:
        out["status"] = (
            f"{INSUFFICIENT}: {len(trajectory)} observed term vectors, so there "
            "is no move to measure. Expected on the stock scenarios, which "
            "settle in two or three messages — that is what data/bargain_3_9 "
            "exists to change"
        )
        return out

    try:
        model = PayoffModel.from_scenario(business, customer)
    except ValueError as exc:
        out["status"] = f"payoff model not definable: {exc}"
        return out

    # Structure from the scenario; lambda from the transcript when the data
    # supports it. A paid proposal is an acceptance; the rest are rejections.
    events = _acceptance_events(trajectory, records)
    model, lam_fit = calibrate(model, events)
    out["lambda"] = {
        "value": model.lam,
        "identified": lam_fit.identified,
        "n_events": lam_fit.n_events,
        "reason": lam_fit.reason,
    }

    x_star, w_max = model.nash_bargaining_solution()
    settled = trajectory[-1]

    # (ii) Phi and Phi_proj along the observed trajectory.
    phis = [phi(model, x) for x in trajectory]
    # Phi_proj is NaN wherever the state is outside C(theta) — the tangent
    # cone is not defined there, and most ungoverned openings breach. Those
    # points are reported as null and excluded from the statistics rather than
    # being folded in, which would average a defined quantity with an
    # undefined one.
    phis_proj = [phi_projected(model, x, contract) for x in trajectory]
    defined = [v for v in phis_proj if np.isfinite(v)]

    out["phi"] = {
        "series": phis,
        "final": phis[-1],
        "fraction_decreasing": float(np.mean(np.diff(phis) <= 1e-9)),
    }
    out["phi_projected"] = {
        "series": [None if not np.isfinite(v) else v for v in phis_proj],
        "defined_at": len(defined),
        "of_rounds": len(phis_proj),
        "final": defined[-1] if defined else None,
        "fraction_decreasing": (
            float(np.mean(np.diff(defined) <= 1e-9)) if len(defined) >= 2 else None
        ),
        "note": (
            "null where the state is outside C(theta): the projected "
            "certificate is undefined in breach, and a state in breach needs "
            "recovery rather than convergence"
        ),
    }

    # (iii) G_kappa under the escalating schedule, and where motion stopped.
    g_series = [
        g_kappa(model, x, controller.kappa(k), controller.rho)
        for k, x in enumerate(trajectory)
    ]
    stopped = next((k for k, g in enumerate(g_series) if g == 0.0), None)
    out["g_kappa"] = {
        "series": g_series,
        "stopping_round": stopped,
        "t_max": controller.t_max,
        "within_t_max": None if stopped is None else stopped <= controller.t_max,
        "realised_rounds": len(trajectory) - 1,
    }

    # (iv) and (v): where it landed, and what that cost.
    out["settled"] = {
        "terms": settled.tolist(),
        "nash_bargaining_solution": x_star.tolist(),
        "distance_scaled_units": dist_M(settled, x_star),
        "surplus": model.surplus(settled),
        "w_max": w_max,
        "surplus_loss_pct": (
            100.0 * (w_max - model.surplus(settled)) / w_max if w_max > 0 else None
        ),
    }

    # The assumption the whole transfer rests on, tested.
    report = assess_rationalizability(
        model, rounds_from_trajectory(trajectory), rho=controller.rho
    )
    out["rationalizability"] = {
        "consistent": report.consistent,
        "kappa_interval": report.interval,
        "n_rounds": report.n_rounds,
        "n_moved": report.n_moved,
        "n_inconsistent_rounds": report.n_inconsistent_rounds,
        "description": report.describe(),
    }

    out["status"] = "ok"
    return out


def _acceptance_events(
    trajectory: list[np.ndarray], records: list[Any]
) -> list[AcceptanceEvent]:
    """Every proposal is an acceptance opportunity; the last one, if the pair
    settled, is the acceptance.

    Deliberately crude, and flagged as such by the identification check
    downstream: a pair that never settled produces all-rejections, which is
    one-sided data and will be reported as not identifying lambda.
    """
    if not trajectory:
        return []
    settled = any(getattr(r, "settled", False) for r in records)
    return [
        AcceptanceEvent(x=x, accepted=settled and i == len(trajectory) - 1)
        for i, x in enumerate(trajectory)
    ]


def _shadow_prices(records: list[Any]) -> dict[str, float]:
    """Mean dual per constraint row over the rounds where it was priced."""
    totals: dict[str, list[float]] = {}
    for record in records:
        for label, value in record.duals.items():
            totals.setdefault(label, []).append(float(value))
    return {label: float(np.mean(values)) for label, values in totals.items()}


def _aggregate(
    negotiations: list[dict[str, Any]],
    trajectories: dict[str, list[np.ndarray]],
) -> dict[str, Any]:
    usable = [n for n in negotiations if n.get("status") == "ok"]
    out: dict[str, Any] = {
        "negotiations": len(negotiations),
        "measurable": len(usable),
    }
    if not usable:
        out["status"] = (
            f"{INSUFFICIENT}: no negotiation produced enough observed moves to "
            "measure. Report the breach rate and shadow prices only"
        )
        return out

    distances = [n["settled"]["distance_scaled_units"] for n in usable]
    losses = [
        n["settled"]["surplus_loss_pct"]
        for n in usable
        if n["settled"]["surplus_loss_pct"] is not None
    ]
    consistent = [n["rationalizability"]["consistent"] for n in usable]

    out["mean_distance_to_nbs_scaled"] = float(np.mean(distances))
    if losses:
        out["mean_surplus_loss_pct"] = float(np.mean(losses))
    out["rationalizable_fraction"] = float(np.mean(consistent))

    # The market energy, as the assumption-free fallback. Labelled, because it
    # measures movement rather than incentive and cannot tell a negotiation
    # that agreed from one that gave up.
    usable_trajectories = {
        n["pair"]: trajectories[n["pair"]]
        for n in usable
        if len(trajectories.get(n["pair"], [])) >= 3
    }
    series = g_realised_series(usable_trajectories)
    if len(series) >= 3:
        out["fallback_realised_displacement"] = {
            "series": series,
            "contraction": contraction_transient(series),
            "note": "assumption-free; weaker than G_kappa",
        }
    return out


# --------------------------------------------------------------------------
# Printing
# --------------------------------------------------------------------------


def print_report(safety: dict[str, float], section11: dict[str, Any]) -> None:
    print("\n" + "=" * 66)
    print("SAFETY LAYER  (section 11 item i)")
    print("=" * 66)
    for key in (
        "rounds",
        "pairs",
        "breach_rate",
        "breach_rounds",
        "mean_intervention",
        "intervention_rate",
        "slack_total",
        "pairs_opened_outside_C",
        "pairs_unsatisfiable",
        "ungoverned_messages",
    ):
        if key in safety:
            print(f"  {key:<30}{safety[key]:>14.4f}")
    print("  --- solver reliability (never omitted) ---")
    for key in sorted(k for k in safety if k.startswith("solver_")):
        print(f"  {key:<30}{safety[key]:>14.4f}")
    gap = safety.get("certificate_gap_rate", 0.0)
    print(f"  {'certificate_gap_rate':<30}{gap:>14.4f}")

    print("\n" + "=" * 66)
    print("CONVERGENCE AND TERMINATION  (section 11 items ii-vi)")
    print("=" * 66)

    for negotiation in section11["negotiations"]:
        print(f"\n  {negotiation['pair']}  ({negotiation['rounds']} term vectors)")
        if negotiation.get("status") != "ok":
            print(f"    {negotiation.get('status')}")
            if negotiation.get("shadow_prices"):
                print(f"    shadow prices: {negotiation['shadow_prices']}")
            continue

        settled = negotiation["settled"]
        print(
            f"    Phi      {negotiation['phi']['series'][0]:>9.3f} -> "
            f"{negotiation['phi']['final']:<9.3f} "
            f"decreasing on {negotiation['phi']['fraction_decreasing']:.0%}"
        )
        proj = negotiation["phi_projected"]
        if proj["fraction_decreasing"] is None:
            print(
                f"    Phi_proj defined at {proj['defined_at']}/{proj['of_rounds']} "
                "rounds — too few in C(theta) to report a trend"
            )
        else:
            print(
                f"    Phi_proj -> {proj['final']:<9.3f} "
                f"decreasing on {proj['fraction_decreasing']:.0%} "
                f"(defined at {proj['defined_at']}/{proj['of_rounds']} rounds)"
            )
        stop = negotiation["g_kappa"]["stopping_round"]
        print(
            f"    G_kappa stops at round {stop} (T_max "
            f"{negotiation['g_kappa']['t_max']}, realised "
            f"{negotiation['g_kappa']['realised_rounds']})"
        )
        print(
            f"    settled {np.round(settled['terms'], 3).tolist()} vs NBS "
            f"{np.round(settled['nash_bargaining_solution'], 3).tolist()}"
        )
        print(
            f"    distance {settled['distance_scaled_units']:.3f} scaled units; "
            f"surplus {settled['surplus']:.2f} of {settled['w_max']:.2f}"
            + (
                f" ({settled['surplus_loss_pct']:.2f}% lost)"
                if settled["surplus_loss_pct"] is not None
                else ""
            )
        )
        if not negotiation["lambda"]["identified"]:
            print(f"    lambda not identified: {negotiation['lambda']['reason']}")
        print(f"    {negotiation['rationalizability']['description']}")
        if negotiation["shadow_prices"]:
            print(f"    shadow prices: {negotiation['shadow_prices']}")

    print("\n  " + "-" * 62)
    print(f"  aggregate: {section11['aggregate']}")


def _jsonable(value: Any) -> Any:
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    return str(value)


def main_for(mode: str, description: str) -> Callable[[], None]:
    """Build a main() for a straightforward governed arm."""

    def main() -> None:
        args = build_parser(description).parse_args()
        run_arm(args, mode=mode)

    return main
