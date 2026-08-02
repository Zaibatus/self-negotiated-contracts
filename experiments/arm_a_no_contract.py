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
    print(f"Contract registry: {registry.summary()}\n")

    dsn = _dsn_from_env()
    out_dir = Path(args.results) / "arm_a_replay"
    out_dir.mkdir(parents=True, exist_ok=True)

    summaries: dict[str, dict[str, float]] = {}
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
        print(
            f"{schema:<16} proposals={summary['proposals_seen']:.0f} "
            f"governed={summary['proposals_governed']:.0f} "
            f"breach_rate={summary.get('breach_rate', 0.0):.3f}"
        )

    if not summaries:
        raise SystemExit("no schemas found; nothing to report")

    rates = [s.get("breach_rate", 0.0) for s in summaries.values()]
    sd = float(np.std(rates, ddof=1)) if len(rates) > 1 else 0.0
    print(
        f"\nUNGOVERNED BREACH RATE over {len(rates)} runs: "
        f"{np.mean(rates):.3f} +/- {sd:.3f}"
    )
    (out_dir / "summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    print(f"Wrote {out_dir / 'summary.json'}")


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument(
        "--replay",
        nargs="+",
        default=["baseline_v1", "baseline_v2", "baseline_v3",
                 "baseline_v4", "baseline_v5"],
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
