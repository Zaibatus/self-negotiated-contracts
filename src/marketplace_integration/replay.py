"""Replay a finished experiment through the contract layer. No LLM calls.

Arm A has already been run five times (``baseline_v1``..``baseline_v5``), and
every proposal those runs produced is sitting in Postgres. Reading it back and
evaluating theta against it answers, for free, the question the synthetic
prototype could only answer in simulation: *how often does an ungoverned LLM
marketplace actually breach the contract its own scenario implies?* That is
the Magentic counterpart of F1's 9.9%.

Replay is also the honest way to size the problem before spending anything on
governed runs: if real agents never breach, the safety layer has nothing to
show, and it is better to learn that from data already paid for.

Usage:
    source ../multi-agent-marketplace/.env
    uv run python -m src.marketplace_integration.replay \\
        --schemas baseline_v1 baseline_v2 baseline_v3 baseline_v4 baseline_v5 \\
        --data ../multi-agent-marketplace/data/mexican_3_9
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..certificates.metrics import RoundRecord, summarise
from ..contract import ContractSpec
from .terms import from_order_proposal, from_text
from .theta import ContractRegistry, pair_key

_MESSAGE_QUERY = """
SELECT
    row_index,
    data->'request'->'parameters'->>'from_agent_id'   AS from_agent,
    data->'request'->'parameters'->>'to_agent_id'     AS to_agent,
    data->'request'->'parameters'->'message'->>'type' AS msg_type,
    data->'request'->'parameters'->'message'          AS msg_json
FROM {schema}.actions
WHERE data->'request'->>'name' = 'SendMessage'
ORDER BY row_index ASC
"""


@dataclass
class SettledDeal:
    """A proposal that was actually paid for, and whether it broke theta.

    Distinct from a breaching *proposal*, and the distinction is the whole
    point. A seller can put an impossible offer on the table and a competent
    buyer can decline it; the contract was strained but nobody was harmed.
    What matters for welfare is whether money changed hands outside C(theta).
    """

    pair_id: str
    proposal_id: str
    terms: list[float]
    spend: float
    budget: float
    breached_rows: list[str]

    @property
    def breached(self) -> bool:
        return bool(self.breached_rows)

    @property
    def overspend(self) -> float:
        """How far over budget, in currency. Zero when within."""
        return max(self.spend - self.budget, 0.0)


@dataclass
class ReplayResult:
    """What one finished schema looked like through the contract layer."""

    schema: str
    records: list[RoundRecord] = field(default_factory=list)
    trajectories: dict[str, list[list[float]]] = field(default_factory=dict)
    proposals_seen: int = 0
    proposals_governed: int = 0
    deals: list[SettledDeal] = field(default_factory=list)
    ungoverned: list[dict[str, str]] = field(default_factory=list)

    def summary(self) -> dict[str, float]:
        out = summarise(self.records)
        out["proposals_seen"] = float(self.proposals_seen)
        out["proposals_governed"] = float(self.proposals_governed)
        out["proposals_ungoverned"] = float(len(self.ungoverned))

        breached = [d for d in self.deals if d.breached]
        out["deals_settled"] = float(len(self.deals))
        out["deals_breached"] = float(len(breached))
        if self.deals:
            out["deal_breach_rate"] = len(breached) / len(self.deals)
        # Magnitude, not just count. Four three-cent overspends and one 22%
        # overspend are the same number of breaches and not the same event, so
        # a rate reported without a magnitude invites the wrong conclusion.
        out["total_overspend"] = float(sum(d.overspend for d in self.deals))
        overspends = [d.overspend for d in self.deals]
        out["max_overspend"] = float(max(overspends, default=0.0))
        return out


def replay_messages(
    rows: list[dict[str, object]],
    registry: ContractRegistry,
) -> ReplayResult:
    """Evaluate theta against a recorded message stream. Pure, testable.

    Deliberately *does not* filter: replay measures what the ungoverned
    marketplace did. Filtering a recorded trajectory would produce a
    counterfactual whose later rounds never happened, which is exactly the
    kind of number that reads as evidence and is not.
    """
    from magentic_marketplace.marketplace.actions.messaging import (
        OrderProposal,
        TextMessage,
    )

    result = ReplayResult(schema="")
    states: dict[str, list[np.ndarray]] = {}
    rounds: dict[str, int] = {}
    # proposal id -> everything needed to judge it if it is later paid for.
    offered: dict[str, tuple[str, np.ndarray, object]] = {}

    for row in rows:
        msg_type = row.get("msg_type")
        payload = row.get("msg_json")
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            continue

        if msg_type == "order_proposal":
            business_id = str(row["from_agent"])
            customer_id = str(row["to_agent"])
            key = pair_key(business_id, customer_id)
            result.proposals_seen += 1

            contract = registry.get(business_id, customer_id)
            if contract is None:
                result.ungoverned.append(
                    {"pair": key, "reason": "no definable contract"}
                )
                continue

            try:
                proposal = OrderProposal.model_validate(payload)
                terms = from_order_proposal(proposal)
            except Exception as exc:  # noqa: BLE001 - recorded data is untrusted
                result.ungoverned.append({"pair": key, "reason": str(exc)})
                continue

            effective = (
                contract if terms.deadline_observed else contract.without_deadline()
            )
            x = terms.vector
            traj = states.setdefault(key, [])
            x_prev = traj[-1] if traj else x

            k = rounds.get(key, 0)
            rounds[key] = k + 1
            result.proposals_governed += 1

            from ..certificates.metrics import make_round_record

            result.records.append(
                make_round_record(
                    pair_id=key,
                    round_index=k,
                    mode="off",
                    contract=effective,
                    x_prev=x_prev,
                    x_proposed=x,
                    x_applied=x,
                    result=None,
                    business_id=business_id,
                    customer_id=customer_id,
                    extraction={
                        "source": terms.source,
                        "exact": str(terms.exact),
                        "deadline_observed": str(terms.deadline_observed),
                    },
                )
            )
            traj.append(x)
            offered[proposal.id] = (key, x, effective)

        elif msg_type == "payment":
            # A payment names the proposal it accepts, so the settled terms are
            # exactly the terms of that proposal — no inference needed.
            proposal_id = payload.get("proposal_message_id")
            if proposal_id not in offered:
                continue
            key, x, effective = offered[proposal_id]
            result.deals.append(
                SettledDeal(
                    pair_id=key,
                    proposal_id=str(proposal_id),
                    terms=[float(v) for v in x],
                    spend=float(x[0] * x[1]),
                    budget=float(effective.budget),
                    breached_rows=effective.violations(x),
                )
            )

        elif msg_type == "text":
            customer_id = str(row["from_agent"])
            business_id = str(row["to_agent"])
            key = pair_key(business_id, customer_id)
            traj = states.get(key)
            if not traj:
                continue
            try:
                message = TextMessage.model_validate(payload)
            except Exception:  # noqa: BLE001
                continue
            terms = from_text(message, fallback_quantity=float(traj[-1][1]))
            if terms is not None:
                traj.append(terms.vector)

    result.trajectories = {
        key: [list(map(float, x)) for x in traj] for key, traj in states.items()
    }
    return result


async def replay_schema(
    schema: str,
    registry: ContractRegistry,
    dsn: dict[str, object],
) -> ReplayResult:
    """Pull one schema out of Postgres and replay it."""
    import asyncpg

    conn = await asyncpg.connect(**dsn)
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = $1", schema
        )
        if not exists:
            raise LookupError(f"schema {schema!r} not found in the database")
        rows = await conn.fetch(_MESSAGE_QUERY.format(schema=schema))
    finally:
        await conn.close()

    result = replay_messages([dict(r) for r in rows], registry)
    result.schema = schema
    return result


def _dsn_from_env() -> dict[str, object]:
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", "postgres"),
        "password": os.getenv("POSTGRES_PASSWORD", "postgres"),
        "database": os.getenv("POSTGRES_DB", "marketplace"),
    }


async def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schemas", nargs="+", required=True)
    parser.add_argument(
        "--data",
        default="../multi-agent-marketplace/data/mexican_3_9",
        help="scenario folder the schemas were run against",
    )
    parser.add_argument("--out", default="results/replay")
    parser.add_argument(
        "--budget-slack",
        type=float,
        default=0.0,
        help="headroom above the customer's stated reservation price",
    )
    args = parser.parse_args()

    registry = ContractRegistry.from_data_dir(
        args.data, spec=ContractSpec(budget_slack=args.budget_slack)
    )
    print(f"Contract registry: {registry.summary()}\n")

    dsn = _dsn_from_env()
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    all_summaries: dict[str, dict[str, float]] = {}
    for schema in args.schemas:
        try:
            result = await replay_schema(schema, registry, dsn)
        except LookupError as exc:
            print(f"[skip] {exc}")
            continue
        summary = result.summary()
        all_summaries[schema] = summary
        print(
            f"{schema:<16} proposals={summary['proposals_seen']:.0f} "
            f"governed={summary['proposals_governed']:.0f} "
            f"breach_rate={summary.get('breach_rate', 0.0):.3f} "
            f"breaches={summary.get('breach_rounds', 0.0):.0f}"
        )
        (out_dir / f"{schema}.json").write_text(
            json.dumps(
                {"summary": summary, "trajectories": result.trajectories},
                indent=2,
            ),
            encoding="utf-8",
        )

    if all_summaries:
        rates = [s.get("breach_rate", 0.0) for s in all_summaries.values()]
        sd = float(np.std(rates, ddof=1)) if len(rates) > 1 else 0.0
        print(
            f"\nUngoverned breach rate across {len(rates)} runs: "
            f"mean={np.mean(rates):.3f} sd={sd:.3f}"
        )
        (out_dir / "summary.json").write_text(
            json.dumps(all_summaries, indent=2), encoding="utf-8"
        )


if __name__ == "__main__":
    asyncio.run(main())
