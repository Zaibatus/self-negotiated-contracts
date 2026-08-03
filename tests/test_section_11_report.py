"""The section 11 report, driven through the real protocol. No LLMs, no DB.

Proposals are pushed through ``GovernedMarketplaceProtocol.execute_action`` and
the resulting state is handed to the same reporting function the arm scripts
call, so what is tested is the path that actually runs — including the cases
where the report's honest answer is "not enough data".
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from magentic_marketplace.marketplace.actions import SendMessage
from magentic_marketplace.marketplace.actions.messaging import (
    OrderItem,
    OrderProposal,
    TextMessage,
)
from magentic_marketplace.marketplace.shared.models import Business, Customer
from magentic_marketplace.platform.shared.models import (
    ActionExecutionRequest,
    AgentProfile,
)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import section_11_report  # noqa: E402
from src.contract import ContractSpec, ControllerSpec  # noqa: E402
from src.marketplace_integration.protocol import (  # noqa: E402
    GovernedMarketplaceProtocol,
)
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402


class _StubAgents:
    async def get_by_id(self, agent_id: str) -> AgentProfile:
        return AgentProfile(id=agent_id)


class StubDatabase:
    def __init__(self) -> None:
        self.agents = _StubAgents()


def business() -> Business:
    return Business.model_validate(
        {
            "id": "business_0001",
            "name": "Cantina",
            "description": "A test business.",
            "rating": 1.0,
            "progenitor_customer": "customer_0001",
            "menu_features": {"Tacos": 10.0},
            "amenity_features": {"Outdoor Seating": True},
            "min_price_factor": 0.5,
        }
    )


def customer() -> Customer:
    return Customer.model_validate(
        {
            "id": "customer_0001",
            "name": "Buyer",
            "request": "Tacos please.",
            "menu_features": {"Tacos": 9.0},
            "amenity_features": ["Outdoor Seating"],
        }
    )


def registry() -> ContractRegistry:
    return ContractRegistry.from_participants(
        [business()], [customer()], spec=ContractSpec()
    )


def proposal(total: float, quantity: int = 1, pid: str = "p1") -> OrderProposal:
    return OrderProposal(
        id=pid,
        items=[
            OrderItem(
                id="Item-1",
                item_name="Tacos",
                quantity=quantity,
                unit_price=total / quantity,
            )
        ],
        total_price=total,
    )


async def send(protocol, message, sender="business_0001", recipient="customer_0001"):
    action = SendMessage(
        from_agent_id=sender,
        to_agent_id=recipient,
        created_at=datetime.now(UTC),
        message=message,
    )
    request = ActionExecutionRequest(
        name="SendMessage", parameters=action.model_dump(mode="json")
    )
    await protocol.execute_action(
        agent=AgentProfile(id=sender), action=request, database=StubDatabase()
    )


CONTROLLER = ControllerSpec(gamma=0.4, t_max=12, kappa0=2.0, rho=0.5)


class TestInsufficientData:
    async def test_a_single_proposal_reports_why_it_cannot_measure(self):
        """One term vector is not a move. The report must say so, not fit it."""
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        await send(protocol, proposal(total=8.0))

        report = section_11_report(protocol, CONTROLLER)
        negotiation = report["negotiations"][0]
        assert "insufficient data" in negotiation["status"]
        assert "phi" not in negotiation
        # The two items that need no payoff model are still reported.
        assert "breach_rate" in negotiation
        assert "shadow_prices" in negotiation
        assert report["aggregate"]["measurable"] == 0

    async def test_the_aggregate_says_what_is_still_reportable(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        await send(protocol, proposal(total=8.0))
        aggregate = section_11_report(protocol, CONTROLLER)["aggregate"]
        assert "breach rate and shadow prices only" in aggregate["status"]


class TestFullReport:
    @staticmethod
    async def _negotiation() -> GovernedMarketplaceProtocol:
        """A seller conceding across several rounds, with buyer counter-offers."""
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        for k, total in enumerate([8.6, 8.3, 8.0, 7.8]):
            await send(protocol, proposal(total=total, pid=f"p{k}"))
            await send(
                protocol,
                TextMessage(content=f"Could you do ${total - 0.4:.2f}?"),
                sender="customer_0001",
                recipient="business_0001",
            )
        return protocol

    async def test_every_section_11_item_is_present(self):
        report = section_11_report(await self._negotiation(), CONTROLLER)
        negotiation = report["negotiations"][0]
        assert negotiation["status"] == "ok"

        assert "breach_rate" in negotiation  # (i)
        assert negotiation["phi"]["series"]  # (ii)
        assert negotiation["phi_projected"]["series"]  # (ii)
        assert "stopping_round" in negotiation["g_kappa"]  # (iii)
        assert "distance_scaled_units" in negotiation["settled"]  # (iv)
        assert "surplus_loss_pct" in negotiation["settled"]  # (v)
        assert "shadow_prices" in negotiation  # (vi)
        assert "rationalizability" in negotiation  # the tested assumption

    async def test_the_settled_terms_are_compared_against_the_bargaining_solution(
        self,
    ):
        report = section_11_report(await self._negotiation(), CONTROLLER)
        settled = report["negotiations"][0]["settled"]
        assert len(settled["nash_bargaining_solution"]) == 3
        assert settled["distance_scaled_units"] >= 0.0
        assert settled["w_max"] > 0.0

    async def test_g_kappa_terminates_within_t_max_under_escalating_friction(self):
        """Whatever incentive remains, friction eventually exceeds it."""
        report = section_11_report(await self._negotiation(), CONTROLLER)
        g = report["negotiations"][0]["g_kappa"]
        assert g["stopping_round"] is not None
        assert g["within_t_max"]

    async def test_lambda_is_reported_as_unidentified_on_thin_data(self):
        """A four-round transcript with no acceptance is one-sided data."""
        report = section_11_report(await self._negotiation(), CONTROLLER)
        lam = report["negotiations"][0]["lambda"]
        assert not lam["identified"]
        assert lam["reason"]

    async def test_the_rationalizability_verdict_is_explicit(self):
        report = section_11_report(await self._negotiation(), CONTROLLER)
        rationalizability = report["negotiations"][0]["rationalizability"]
        assert isinstance(rationalizability["consistent"], bool)
        assert rationalizability["description"]

    async def test_the_report_is_json_serialisable(self):
        """It gets written to results/<experiment>/section_11.json."""
        import json

        from experiments._common import _jsonable

        report = section_11_report(await self._negotiation(), CONTROLLER)
        assert json.loads(json.dumps(report, default=_jsonable))


class TestUngovernablePairs:
    async def test_a_pair_with_no_payoff_model_says_so(self):
        """No bargaining zone: reservation at or below marginal cost."""
        expensive = business().model_copy(update={"min_price_factor": 1.0})
        reg = ContractRegistry.from_participants([expensive], [customer()])
        protocol = GovernedMarketplaceProtocol(reg, mode="monitor")
        await send(protocol, proposal(total=9.5, pid="a"))
        await send(protocol, proposal(total=9.2, pid="b"))

        negotiation = section_11_report(protocol, CONTROLLER)["negotiations"][0]
        assert "no bargaining zone" in negotiation["status"]
        assert negotiation["breach_rate"] == pytest.approx(1.0)


class TestSafetyItemIsIndependentOfThePayoffModel:
    async def test_breach_rate_survives_an_unfittable_transcript(self):
        """Item (i) must never depend on the estimation succeeding."""
        expensive = business().model_copy(update={"min_price_factor": 1.0})
        reg = ContractRegistry.from_participants([expensive], [customer()])
        protocol = GovernedMarketplaceProtocol(reg, mode="monitor")
        await send(protocol, proposal(total=50.0))

        negotiation = section_11_report(protocol, CONTROLLER)["negotiations"][0]
        assert negotiation["status"] != "ok"
        assert negotiation["breach_rate"] == pytest.approx(1.0)
        assert np.isfinite(negotiation["breach_rounds"])
