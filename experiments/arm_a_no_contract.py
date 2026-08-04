"""Arm A — ungoverned baseline. What an LLM marketplace does with no contract.

Two ways to get the number, and the cheap one comes first.

**Replay (default, no API spend).** Arm A has already been run five times
(baseline_v1..baseline_v5, welfare 62.46 +/- 1.99). Every proposal those runs
produced is in Postgres. Evaluating theta against them answers "how often does
an ungoverned LLM marketplace breach the contract its own scenario implies?"
for free — the Magentic counterpart of the prototype's 9.9%. No new agents run,
so this is a measurement of the recorded past, not a simulation of it.

**Live (--live).** Runs the marketplace with the regulator in "off" mode: it
records the term trajectory and evaluates theta, and changes nothing. Use this
when the arm needs to be on the same scenario as the other arms — the recorded
baselines were run on stock mexican_3_9, not on data/bargain_3_9.

    source ../multi-agent-marketplace/.env
    uv run python experiments/arm_a_no_contract.py --replay baseline_v1 baseline_v2 \
        --data ../multi-agent-marketplace/data/mexican_3_9
    uv run python experiments/arm_a_no_contract.py --live --experiment arm_a_bargain_v1
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from experiments._common import build_parser, contract_spec, run_arm  # noqa: E402
from src.marketplace_integration.replay import (  # noqa: E402
    TRIVIAL_BREACH_FRACTION,
)
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402


def replay(args) -> None:
    """Evaluate theta against finished experiment schemas."""
    from dotenv import load_dotenv

    from src.marketplace_integration.replay import _dsn_from_env, replay_schema

    load_dotenv()
    registry = ContractRegistry.from_data_dir(args.data, spec=contract_spec(args))
    print(f"Contract registry: {registry.summary()}")
    if registry.unsatisfiable:
        print(
            f"  {len(registry.unsatisfiable)} pairs have an empty safe set "
            "(the seller's cost floor sits above the buyer's budget). Those are "
            "deals that should never close, so a breach there is the correct "
            "outcome rather than a governance failure."
        )
    print()

    dsn = _dsn_from_env()
    out_dir = Path(args.results) / "arm_a_replay"
    out_dir.mkdir(parents=True, exist_ok=True)

    header = (
        f"{'run':<18}{'props':>7}{'breach':>9}{'deals':>8}{'infeas':>7}"
        f"{'trivial':>9}{'meaningful':>12}{'overspend':>11}"
    )
    print(header)
    print("-" * len(header))

    summaries: dict[str, dict[str, float]] = {}
    deals: list = []
    for schema in args.replay:
        try:
            result = asyncio.run(replay_schema(schema, registry, dsn))
        except LookupError as exc:
            print(f"[skip] {exc}")
            continue
        except OSError as exc:
            raise SystemExit(
                f"cannot reach Postgres ({exc}). Start it with "
                "`docker compose up -d` in ../multi-agent-marketplace and "
                "source that project's .env."
            ) from exc
        summary = result.summary()
        summaries[schema] = summary
        deals.extend(result.deals)
        print(
            f"{schema:<18}{summary['proposals_seen']:>7.0f}"
            f"{summary.get('breach_rate', 0.0):>9.3f}"
            f"{summary['deals_settled']:>8.0f}"
            f"{summary['deals_infeasible']:>7.0f}"
            f"{summary['deals_trivial']:>9.0f}"
            f"{summary['deals_meaningful']:>12.0f}"
            f"{summary['total_overspend']:>11.2f}"
        )

    if not summaries:
        raise SystemExit(
            "no schemas found. Is Postgres up, and were these experiments run "
            "against this database?"
        )

    rates = [s.get("breach_rate", 0.0) for s in summaries.values()]
    sd = float(np.std(rates, ddof=1)) if len(rates) > 1 else 0.0
    breached = [d for d in deals if d.breached]
    spend = sum(d.spend for d in deals)
    over = sum(d.overspend for d in deals)
    classes = {c: sum(1 for d in deals if d.classification == c)
               for c in ("within", "infeasible", "trivial", "meaningful")}

    print(f"\n{'=' * 74}")
    print(f"UNGOVERNED BREACH RATE over {len(rates)} runs")
    print("=" * 74)
    print(f"  of proposals OFFERED:   {np.mean(rates):.3f} +/- {sd:.3f}")
    if deals:
        print(
            f"  of deals SETTLED:       {len(breached) / len(deals):.3f}  "
            f"({len(breached)}/{len(deals)})"
        )
        print(f"  overspend / value:      {100 * over / spend:.2f}%  "
              f"(${over:.2f} of ${spend:.2f})")
        print(f"\n  settled deals by class ({TRIVIAL_BREACH_FRACTION:.0%} "
              "trivial threshold):")
        print(f"    within theta          {classes['within']:>4}")
        print(f"    structurally infeasible {classes['infeasible']:>2}   "
              "empty safe set: no deal could have complied")
        print(f"    trivial breach        {classes['trivial']:>4}   "
              f"< {TRIVIAL_BREACH_FRACTION:.0%} of budget")
        print(f"    MEANINGFUL breach     {classes['meaningful']:>4}   "
              "<- what a filter would have to prevent")

    print(
        "\n  Read the rates together. The first counts contract-violating "
        "offers put on\n  the table; the second counts the ones a buyer "
        "actually accepted. A large gap\n  means the customer agent is "
        "already declining most bad offers unaided, and\n  the safety layer "
        "is partly redundant with its judgement here — a finding,\n  not a "
        "failure.\n"
        "\n  Structurally infeasible deals are NOT a governance failure: no "
        "terms could\n  have satisfied those contracts, so a filter cannot "
        "improve them and must not\n  be credited for them."
    )
    n_customers = len({d.pair_id.split("|")[1] for d in deals}) or 1
    print(
        f"\n  SAMPLE SIZE. {len(rates)} seeds x {n_customers} customers. These "
        f"are {len(rates)} draws of the same\n  {n_customers} situations, not "
        f"{len(deals)} independent observations. The +/- above is seed\n  "
        "variance under a fixed scenario, not sampling error over pairs, and "
        "says\n  nothing about how these figures would generalise to other "
        "baskets."
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    print(f"\nWrote {out_dir / 'summary.json'}")


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument(
        "--replay",
        nargs="+",
        default=[f"baseline_v{i}" for i in range(1, 6)],
        help="finished experiment schemas to evaluate theta against",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="run the marketplace ungoverned instead of replaying (costs API calls)",
    )
    # --experiment is only meaningful for a live run.
    for action in parser._actions:
        if action.dest == "experiment":
            action.required = False
    args = parser.parse_args()

    if args.live:
        if not args.experiment:
            raise SystemExit("--live requires --experiment")
        run_arm(args, mode="off")
    else:
        replay(args)


if __name__ == "__main__":
    main()
