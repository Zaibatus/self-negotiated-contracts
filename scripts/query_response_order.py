"""Query Postgres to extract proposal-reception order per customer per seed.

Usage (from repo root, with magentic .env sourced):
    source ../multi-agent-marketplace/.env
    uv run python scripts/query_response_order.py

Reads from the Postgres instance started by docker compose in
../multi-agent-marketplace/.  Does not make any LLM API calls.
"""
from __future__ import annotations

import asyncio
import json
import os
from collections import defaultdict
from dataclasses import dataclass, field

import asyncpg


SCHEMAS = ["baseline_v1", "baseline_v2", "baseline_v3", "baseline_v4", "baseline_v5"]

# Map agent IDs to human names (from mexican_3_9 data)
CUSTOMER_NAMES: dict[str, str] = {
    "customer_0001": "Susan Young",
    "customer_0002": "Jackson Miller",
    "customer_0003": "Angela Ng",
}


@dataclass
class ProposalEvent:
    row_index: int
    created_at: str
    from_agent: str
    to_agent: str
    msg_type: str
    price: float | None = None


@dataclass
class CustomerTrial:
    schema: str
    customer_id: str
    proposals_in_order: list[ProposalEvent] = field(default_factory=list)
    payment_to: str | None = None
    payment_amount: float | None = None

    @property
    def first_proposer(self) -> str | None:
        return self.proposals_in_order[0].from_agent if self.proposals_in_order else None

    @property
    def first_proposer_won(self) -> bool | None:
        if self.first_proposer is None or self.payment_to is None:
            return None
        return self.first_proposer == self.payment_to


async def query_schema(conn: asyncpg.Connection, schema: str) -> list[CustomerTrial]:
    # Fetch all SendMessage actions ordered by insertion index
    rows = await conn.fetch(
        f"""
        SELECT
            row_index,
            created_at,
            data->'request'->'parameters'->>'from_agent_id'  AS from_agent,
            data->'request'->'parameters'->>'to_agent_id'    AS to_agent,
            data->'request'->'parameters'->'message'->>'type' AS msg_type,
            data->'request'->'parameters'->'message'          AS msg_json
        FROM {schema}.actions
        WHERE data->'request'->>'name' = 'SendMessage'
        ORDER BY row_index ASC
        """
    )

    # Build per-customer trial objects
    trials: dict[str, CustomerTrial] = {
        cid: CustomerTrial(schema=schema, customer_id=cid)
        for cid in CUSTOMER_NAMES
    }

    for r in rows:
        from_agent: str = r["from_agent"]
        to_agent: str = r["to_agent"]
        msg_type: str = r["msg_type"]

        # order_proposal sent by a business TO a customer
        if msg_type == "order_proposal" and to_agent in trials:
            msg = json.loads(r["msg_json"])
            price = msg.get("total_price")
            trials[to_agent].proposals_in_order.append(
                ProposalEvent(
                    row_index=r["row_index"],
                    created_at=str(r["created_at"]),
                    from_agent=from_agent,
                    to_agent=to_agent,
                    msg_type=msg_type,
                    price=float(price) if price is not None else None,
                )
            )

        # payment sent by a customer TO a business
        if msg_type == "payment" and from_agent in trials:
            msg = json.loads(r["msg_json"])
            trials[from_agent].payment_to = to_agent
            trials[from_agent].payment_amount = msg.get("amount") or msg.get("total_price")

    return list(trials.values())


async def main() -> None:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres")
    database = os.getenv("POSTGRES_DB", "marketplace")

    conn = await asyncpg.connect(
        host=host, port=port, user=user, password=password, database=database
    )

    all_trials: list[CustomerTrial] = []
    available_schemas: list[str] = []

    for schema in SCHEMAS:
        exists = await conn.fetchval(
            "SELECT 1 FROM information_schema.schemata WHERE schema_name = $1", schema
        )
        if not exists:
            print(f"[skip] schema '{schema}' not found")
            continue
        available_schemas.append(schema)
        trials = await query_schema(conn, schema)
        all_trials.extend(trials)

    await conn.close()

    print(f"\nAnalysed {len(available_schemas)} schemas: {available_schemas}")
    print(f"Total customer trials: {len(all_trials)}\n")

    # ── Per-customer-per-seed proposal order table ────────────────────────────
    print("=" * 72)
    print("PROPOSAL RECEPTION ORDER BY CUSTOMER AND SEED")
    print("=" * 72)

    for cid, cname in CUSTOMER_NAMES.items():
        print(f"\n{cname} ({cid})")
        print("-" * 60)
        first_won = 0
        total = 0
        for trial in [t for t in all_trials if t.customer_id == cid]:
            proposals_str = " → ".join(
                f"{p.from_agent}(${p.price:.2f})" if p.price else p.from_agent
                for p in trial.proposals_in_order
            )
            won = trial.first_proposer_won
            flag = "✓ first won" if won else ("✗ first lost" if won is False else "?")
            print(
                f"  {trial.schema}: proposals [{proposals_str}] "
                f"→ paid {trial.payment_to} ${trial.payment_amount}  [{flag}]"
            )
            if won is not None:
                total += 1
                if won:
                    first_won += 1

        if total > 0:
            print(f"  First-proposer win rate: {first_won}/{total} ({100*first_won/total:.0f}%)")

    # ── Aggregate summary ─────────────────────────────────────────────────────
    print("\n" + "=" * 72)
    print("AGGREGATE SUMMARY")
    print("=" * 72)
    total_trials = sum(1 for t in all_trials if t.first_proposer_won is not None)
    first_won_total = sum(1 for t in all_trials if t.first_proposer_won is True)
    print(f"Trials with data:          {total_trials}")
    print(f"First-proposer won:        {first_won_total} / {total_trials} "
          f"({100*first_won_total/total_trials:.0f}%)" if total_trials else "no data")


if __name__ == "__main__":
    asyncio.run(main())
