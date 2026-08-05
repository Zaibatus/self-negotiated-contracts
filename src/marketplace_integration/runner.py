"""Experiment runner with an injectable protocol.

``magentic_marketplace.experiments.run_experiment.run_marketplace_experiment``
hardcodes ``SimpleMarketplaceProtocol``, ``BusinessAgent`` and
``CustomerAgent``, so a governed run cannot go through it. This mirrors its
body with those three made parameters, and adds the certificate output
alongside the standard analytics.

Nothing about the agents is changed: they are the stock Magentic agents,
unaware that a contract layer exists. That is the point — the guarantee is a
property of the marketplace, not of the negotiators.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path

from magentic_marketplace.experiments.utils import (
    load_businesses_from_yaml,
    load_customers_from_yaml,
)
from magentic_marketplace.marketplace.agents import BusinessAgent, CustomerAgent
from magentic_marketplace.platform.database import connect_to_postgresql_database
from magentic_marketplace.platform.launcher import AgentLauncher, MarketplaceLauncher

from ..certificates.metrics import write_jsonl
from .agents import ReconcilingAgentMixin
from .protocol import GovernedMarketplaceProtocol, Mode
from .theta import ContractRegistry


class GovernedBusinessAgent(ReconcilingAgentMixin, BusinessAgent):
    """The stock business agent, with its books kept in sync with the server.

    The mixin adds no negotiation logic — it only records what the marketplace
    accepted instead of what the agent asked for. Without it, a filtered
    proposal leaves the seller reasoning from, and invoicing, a price the buyer
    never saw.
    """


async def run_governed_experiment(
    data_dir: str | Path,
    experiment_name: str,
    *,
    mode: Mode = "filter",
    gamma: float = 0.4,
    rho: float = 1e4,
    capacity_factor: float | None = None,
    couple: bool = True,
    solver: str = "osqp",
    contract_spec=None,
    results_dir: str | Path = "results",
    search_algorithm: str = "simple",
    search_bandwidth: int = 10,
    customer_max_steps: int | None = 100,
    postgres_host: str = "localhost",
    postgres_port: int = 5432,
    postgres_password: str = "postgres",
    db_pool_min_size: int = 2,
    db_pool_max_size: int = 10,
    server_host: str = "127.0.0.1",
    server_port: int = 0,
    override: bool = False,
) -> dict[str, object]:
    """Run one arm of the experiment under a governed marketplace.

    Args:
        data_dir: Magentic scenario folder (businesses/ and customers/).
        experiment_name: Postgres schema name for this run.
        mode: "filter" (arm B/C), "monitor" (arm D) or "off" (arm A).
        gamma: DCBF rate.
        rho: QP slack penalty.
        capacity_factor: shared capacity per business as a fraction of the
            demand it faces; below 1.0 the coupling clause binds. None leaves
            the pairs independent.
        couple: enforce the coupling clause when capacities are present.
        solver: "osqp" or "slsqp".
        contract_spec: ContractSpec overriding the modelling knobs.
        results_dir: where certificates.jsonl and the report are written.

    Returns:
        The regulator's report plus the paths written.
    """
    data_path = Path(data_dir)
    businesses = load_businesses_from_yaml(data_path / "businesses")
    customers = load_customers_from_yaml(data_path / "customers")
    print(f"Loaded {len(customers)} customers and {len(businesses)} businesses")

    registry = ContractRegistry.from_participants(
        businesses,
        customers,
        spec=contract_spec,
        capacity_factor=capacity_factor,
    )
    print(f"Contract registry: {registry.summary()}")
    if registry.undefinable:
        print(
            f"  {len(registry.undefinable)} pairs have no definable contract "
            "(business stocks none of the customer's requested items); their "
            "messages pass ungoverned and are counted in the report."
        )

    protocol = GovernedMarketplaceProtocol(
        registry=registry,
        mode=mode,
        gamma=gamma,
        rho=rho,
        couple=couple,
        solver=solver,
    )

    def database_factory():
        return connect_to_postgresql_database(
            schema=experiment_name,
            host=postgres_host,
            port=postgres_port,
            password=postgres_password,
            min_size=db_pool_min_size,
            max_size=db_pool_max_size,
            mode="override" if override else "create_new",
        )

    if server_port == 0:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind((server_host, 0))
            server_port = sock.getsockname()[1]

    marketplace_launcher = MarketplaceLauncher(
        protocol=protocol,
        database_factory=database_factory,
        host=server_host,
        port=server_port,
        server_log_level="warning",
        experiment_name=experiment_name,
    )

    async with marketplace_launcher:
        logger = await marketplace_launcher.create_logger("governed_experiment")
        logger.info(
            f"Governed experiment started: mode={mode} gamma={gamma} "
            f"capacity_factor={capacity_factor} data_dir={data_path} "
            f"experiment_name={experiment_name}"
        )

        business_agents = [
            GovernedBusinessAgent(business, marketplace_launcher.server_url)
            for business in businesses
        ]
        customer_agents = [
            CustomerAgent(
                customer,
                marketplace_launcher.server_url,
                search_algorithm=search_algorithm,
                search_bandwidth=search_bandwidth,
                max_steps=customer_max_steps,
            )
            for customer in customers
        ]

        async with AgentLauncher(marketplace_launcher.server_url) as agent_launcher:
            try:
                await agent_launcher.run_agents_with_dependencies(
                    primary_agents=customer_agents, dependent_agents=business_agents
                )
            except KeyboardInterrupt:
                logger.warning("Simulation interrupted by user")

    out_dir = Path(results_dir) / experiment_name
    certificates_path = write_jsonl(protocol.records, out_dir / "certificates.jsonl")

    report = protocol.report()
    report_path = out_dir / "report.json"
    report_path.write_text(
        json.dumps(
            {
                "experiment": experiment_name,
                "mode": mode,
                "gamma": gamma,
                "capacity_factor": capacity_factor,
                "solver": solver,
                "registry": registry.summary(),
                "report": report,
                "ungoverned": protocol.ungoverned,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\nCertificates: {certificates_path}")
    print(f"Report:       {report_path}")
    print(f"Analytics:    magentic-marketplace analyze {experiment_name}")
    return {
        "report": report,
        "certificates_path": str(certificates_path),
        "report_path": str(report_path),
        "protocol": protocol,
    }
