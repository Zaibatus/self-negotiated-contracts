"""Shared CLI and reporting for the experiment arms.

Every arm is the same governed run with a different regulator mode and a
different theta source, so the knobs live here once. Keeping them shared is
also what makes the arms comparable: an arm that quietly used a different
gamma, scenario or contract spec would not be a treatment, it would be a
different experiment.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from src.certificates.energy import contraction_transient, g_realised_series
from src.certificates.metrics import time_to_contract
from src.contract import ContractSpec


def build_parser(description: str) -> argparse.ArgumentParser:
    """The arm-invariant knobs."""
    parser = argparse.ArgumentParser(description=description)
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
        "shadow prices",
    )
    parser.add_argument("--rho", type=float, default=1e4, help="QP slack penalty")
    parser.add_argument(
        "--capacity-factor",
        type=float,
        default=None,
        help="shared capacity per business as a fraction of the demand it "
        "faces; below 1.0 the coupling clause binds. Needs a scenario where "
        "some business can serve more than one customer",
    )
    parser.add_argument("--solver", default="osqp", choices=["osqp", "slsqp"])
    parser.add_argument("--t-max", type=int, default=12, help="theta's T_max")
    parser.add_argument("--q-max-factor", type=float, default=2.0)
    parser.add_argument("--max-steps", type=int, default=100)
    parser.add_argument("--results", default="results")
    parser.add_argument("--override", action="store_true")
    return parser


def contract_spec(args: argparse.Namespace) -> ContractSpec:
    return ContractSpec(q_max_factor=args.q_max_factor, t_max=args.t_max)


def run_arm(args: argparse.Namespace, mode: str) -> dict[str, Any]:
    """Run one governed arm and print the certificate summary."""
    # Imported here so that --help works without a database driver present.
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
    print_report(outcome["report"])
    convergence = summarise_convergence(protocol, t_max=args.t_max)
    print_convergence(convergence)

    path = Path(args.results) / args.experiment / "convergence.json"
    path.write_text(json.dumps(convergence, indent=2, default=str), encoding="utf-8")
    return outcome


def print_report(report: dict[str, float]) -> None:
    print("\n" + "=" * 62)
    print("SAFETY LAYER")
    print("=" * 62)
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
        if key in report:
            print(f"  {key:<28}{report[key]:>12.4f}")
    print("  --- solver reliability (never omitted) ---")
    for key in sorted(k for k in report if k.startswith("solver_")):
        print(f"  {key:<28}{report[key]:>12.4f}")
    print(f"  {'certificate_gap_rate':<28}{report.get('certificate_gap_rate', 0):>12.4f}")


def summarise_convergence(protocol: Any, t_max: int) -> dict[str, Any]:
    """Realised-displacement energy, its decay, and the liveness certificate.

    Uses the observed trajectory (seller proposals interleaved with extracted
    buyer counter-offers), because the round-pair energy is defined over a
    *pair* of moves and a proposals-only trajectory would measure the seller's
    concessions alone.

    Returns "insufficient data" rather than a number when a negotiation was too
    short to fit a decay rate. A contraction fitted on two points is not an
    estimate.
    """
    trajectories = protocol.trajectories(binding=False)
    usable = {k: v for k, v in trajectories.items() if len(v) >= 3}

    out: dict[str, Any] = {
        "pairs_total": len(trajectories),
        "pairs_with_a_round_pair": len(usable),
        "trajectory_lengths": {k: len(v) for k, v in trajectories.items()},
    }

    if not usable:
        out["status"] = (
            "insufficient data: no negotiation produced a complete round-pair, "
            "so no energy series exists. Expected on the stock scenarios, "
            "which settle in two or three messages — this is what "
            "data/bargain_3_9 exists to change."
        )
        return out

    series = g_realised_series(usable)
    out["energy_series"] = series
    out["g_initial"] = series[0] if series else None

    if len(series) < 3:
        out["status"] = (
            f"insufficient data: {len(series)} round-pairs, need at least 3 to "
            "fit a contraction. Reporting the raw energy series only."
        )
        return out

    contraction = contraction_transient(series)
    certificate = time_to_contract(
        g_initial=series[0],
        contraction=contraction,
        t_max=t_max,
        realised_rounds=max(len(v) for v in usable.values()),
    )
    out["status"] = "ok"
    out["contraction"] = contraction
    out["liveness"] = certificate.__dict__
    return out


def print_convergence(convergence: dict[str, Any]) -> None:
    print("\n" + "=" * 62)
    print("CONVERGENCE LAYER")
    print("=" * 62)
    print(f"  pairs with a complete round-pair: "
          f"{convergence['pairs_with_a_round_pair']}/{convergence['pairs_total']}")
    if convergence.get("status") != "ok":
        print(f"  {convergence.get('status', 'no status')}")
        return
    print(f"  G_0                     {convergence['g_initial']:>12.4f}")
    print(f"  contraction (transient) {convergence['contraction']:>12.4f}")
    live = convergence["liveness"]
    if live["certified_rounds"] is None:
        print(f"  time-to-contract:       no certificate — {live['reason']}")
    else:
        print(f"  certified rounds        {live['certified_rounds']:>12.2f}")
        print(f"  T_max                   {live['t_max']:>12d}")
        print(f"  T_max honoured          {str(live['honoured']):>12}")
        print(f"  realised rounds         {str(live['realised_rounds']):>12}")


def main_for(mode: str, description: str) -> Callable[[], None]:
    """Build a main() for a straightforward governed arm."""

    def main() -> None:
        args = build_parser(description).parse_args()
        run_arm(args, mode=mode)

    return main
