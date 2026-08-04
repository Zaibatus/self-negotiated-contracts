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
            f"{schema:<16} proposals={summary['proposals_seen']:.0f} "
            f"breach_rate={summary.get('breach_rate', 0.0):.3f}   "
            f"deals={summary['deals_settled']:.0f} "
            f"breached={summary['deals_breached']:.0f} "
            f"overspend=${summary['total_overspend']:.2f}"
        )

    if not summaries:
        raise SystemExit(
            "no schemas found. Is Postgres up, and were these experiments run "
            "against this database?"
        )

    rates = [s.get("breach_rate", 0.0) for s in summaries.values()]
    sd = float(np.std(rates, ddof=1)) if len(rates) > 1 else 0.0
    breached = [d for d in deals if d.breached]

    print(f"\n{'=' * 70}")
    print(f"UNGOVERNED BREACH RATE over {len(rates)} runs")
    print("=" * 70)
    print(f"  of proposals OFFERED:  {np.mean(rates):.3f} +/- {sd:.3f}")
    if deals:
        print(
            f"  of deals SETTLED:      {len(breached) / len(deals):.3f}  "
            f"({len(breached)}/{len(deals)})"
        )
        print(
            f"  total overspend:       ${sum(d.overspend for d in deals):.2f} "
            f"across {len(deals)} deals; worst single deal "
            f"${max((d.overspend for d in deals), default=0.0):.2f}"
        )

    print(
        "\n  Read the two rates together. The first counts contract-violating "
        "offers\n  put on the table; the second counts the ones a buyer "
        "actually accepted.\n  A large gap between them means the customer "
        "agent is already declining most\n  bad offers on its own, and the "
        "safety layer is partly redundant with its\n  judgement in this "
        "scenario — which is a finding, not a failure."
    )
    if breached:
        trivial = sum(1 for d in breached if d.overspend < 0.10)
        if trivial:
            print(
                f"\n  Of the {len(breached)} settled breaches, {trivial} are "
                f"under 10p. Report the magnitude\n  alongside the count, or "
                "the headline rate will carry more weight than it earns."
            )
    print(
        "\n  This is the number arm B has to drive to zero. If it is already "
        "zero the\n  scenario never puts the agents under enough pressure to "
        "breach and the safety\n  result has nothing to show — use "
        "data/bargain_3_9."
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
