"""End-to-end plumbing for the governed marketplace, without LLMs or Postgres.

Messages are pushed through ``GovernedMarketplaceProtocol.execute_action`` —
the same entry point the real server calls — against a stub database. So these
tests exercise the actual interception path, message rewriting included,
rather than a parallel implementation that could drift from it.
"""

from __future__ import annotations

from datetime import UTC, datetime

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

from src.contract import ContractSpec
from src.marketplace_integration.protocol import GovernedMarketplaceProtocol
from src.marketplace_integration.replay import (
    TRIVIAL_BREACH_FRACTION,
    SettledDeal,
    replay_messages,
)
from src.marketplace_integration.terms import from_order_proposal
from src.marketplace_integration.theta import ContractRegistry

# --------------------------------------------------------------------------
# Stubs
# --------------------------------------------------------------------------


class _StubAgents:
    async def get_by_id(self, agent_id: str) -> AgentProfile:
        return AgentProfile(id=agent_id)


class StubDatabase:
    """Just enough database for ``execute_send_message`` to accept a message."""

    def __init__(self) -> None:
        self.agents = _StubAgents()


def business(**overrides) -> Business:
    data = {
        "id": "business_0001",
        "name": "Cantina",
        "description": "A test business.",
        "rating": 1.0,
        "progenitor_customer": "customer_0001",
        "menu_features": {"Tacos": 10.0, "Agua": 4.0},
        "amenity_features": {"Outdoor Seating": True},
        "min_price_factor": 0.5,
    }
    data.update(overrides)
    return Business.model_validate(data)


def customer(**overrides) -> Customer:
    data = {
        "id": "customer_0001",
        "name": "Buyer",
        "request": "Tacos and an agua please.",
        "menu_features": {"Tacos": 8.0, "Agua": 3.0},
        "amenity_features": ["Outdoor Seating"],
    }
    data.update(overrides)
    return Customer.model_validate(data)


def registry(businesses=None, customers=None, **kwargs) -> ContractRegistry:
    return ContractRegistry.from_participants(
        businesses or [business()],
        customers or [customer()],
        spec=ContractSpec(),
        **kwargs,
    )


def proposal(total: float, quantity: int = 2, pid: str = "p1") -> OrderProposal:
    unit = total / quantity
    return OrderProposal(
        id=pid,
        items=[
            OrderItem(
                id="Item-1", item_name="Tacos", quantity=quantity, unit_price=unit
            )
        ],
        total_price=total,
    )


def envelope(message, sender: str, recipient: str) -> ActionExecutionRequest:
    action = SendMessage(
        from_agent_id=sender,
        to_agent_id=recipient,
        created_at=datetime.now(UTC),
        message=message,
    )
    return ActionExecutionRequest(
        name="SendMessage", parameters=action.model_dump(mode="json")
    )


async def send(protocol, message, sender="business_0001", recipient="customer_0001"):
    """Push one message through the real interception path.

    Returns what the caller is left holding, NOT what the protocol returned.
    The server route persists the request object it was handed and the
    recipient reads the message back from the database, so the request is the
    surface that decides what actually reaches the counterparty. Asserting on
    ``result.content`` instead is what let a regulator that filtered nothing
    pass its whole test suite.
    """
    request = envelope(message, sender, recipient)
    await protocol.execute_action(
        agent=AgentProfile(id=sender), action=request, database=StubDatabase()
    )
    return SendMessage.model_validate(request.parameters)


# --------------------------------------------------------------------------
# Tests
# --------------------------------------------------------------------------


class TestFilterMode:
    async def test_a_compliant_proposal_is_forwarded_untouched(self):
        # theta: B = 8 + 3 = 11, q_min = 2, c = 0.5 * (10 + 4) / 2 = 3.5
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        sent = await send(protocol, proposal(total=10.0, quantity=2))
        assert sent.message.total_price == pytest.approx(10.0)
        assert protocol.report()["breach_rate"] == 0.0

    async def test_an_opening_proposal_over_budget_is_projected_into_C(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        sent = await send(protocol, proposal(total=30.0, quantity=2))

        assert sent.message.total_price < 30.0
        contract = protocol.registry.get("business_0001", "customer_0001")
        terms = from_order_proposal(sent.message)
        assert contract.without_deadline().is_safe(terms.vector)
        # The pair is recorded as having opened outside the safe set.
        assert protocol.report()["pairs_opened_outside_C"] == 1.0

    async def test_a_rewritten_proposal_stays_internally_consistent(self):
        """Otherwise the marketplace's own validators would reject it."""
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        sent = await send(protocol, proposal(total=40.0, quantity=3))
        line_sum = sum(i.unit_price * i.quantity for i in sent.message.items)
        assert sent.message.total_price == pytest.approx(line_sum, abs=0.011)
        assert sent.message.id == "p1"

    async def test_later_proposals_are_governed_by_the_barrier(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter", gamma=0.4)
        await send(protocol, proposal(total=10.0, quantity=2, pid="p1"))
        sent = await send(protocol, proposal(total=25.0, quantity=2, pid="p2"))

        assert sent.message.total_price < 25.0
        records = protocol.records
        assert len(records) == 2
        assert records[1].intervention > 0.0
        assert records[1].solved

    async def test_no_breach_across_a_long_erratic_negotiation(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        rng = np.random.default_rng(5)
        await send(protocol, proposal(total=10.0, quantity=2, pid="p0"))
        for k in range(30):
            total = float(rng.uniform(1.0, 40.0))
            await send(protocol, proposal(total=total, quantity=2, pid=f"p{k + 1}"))
        report = protocol.report()
        assert report["breach_rate"] == 0.0
        assert report["solver_solver_failure_rate"] == 0.0
        assert report["certificate_gap_rate"] == 0.0


class TestTheRewriteReachesTheWire:
    """The regulator has to modify what the SERVER persists, not a copy.

    platform/server/routes/actions.py builds its database row from the request
    object it was handed, and the recipient fetches messages out of that
    database. A regulator that rewrites a copy computes a correction, logs it,
    and lets the original terms through — which is exactly what the first arm B
    run on bargain_3_9 did for five seeds before this was caught.
    """

    async def test_the_caller_request_carries_the_filtered_terms(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        request = envelope(
            proposal(total=30.0, quantity=2), "business_0001", "customer_0001"
        )
        await protocol.execute_action(
            agent=AgentProfile(id="business_0001"),
            action=request,
            database=StubDatabase(),
        )
        persisted = SendMessage.model_validate(request.parameters)
        assert persisted.message.total_price < 30.0, (
            "the request the server will persist still holds the unfiltered "
            "terms, so the customer would receive them"
        )

    async def test_the_returned_result_and_the_request_agree(self):
        """If these ever diverge, one of the two surfaces is lying."""
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        request = envelope(
            proposal(total=40.0, quantity=2), "business_0001", "customer_0001"
        )
        result = await protocol.execute_action(
            agent=AgentProfile(id="business_0001"),
            action=request,
            database=StubDatabase(),
        )
        returned = SendMessage.model_validate(result.content)
        persisted = SendMessage.model_validate(request.parameters)
        assert returned.message.total_price == pytest.approx(
            persisted.message.total_price
        )

    async def test_monitor_mode_leaves_the_request_untouched(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="monitor")
        request = envelope(
            proposal(total=30.0, quantity=2), "business_0001", "customer_0001"
        )
        before = dict(request.parameters)
        await protocol.execute_action(
            agent=AgentProfile(id="business_0001"),
            action=request,
            database=StubDatabase(),
        )
        assert request.parameters == before


class TestMonitorMode:
    async def test_monitor_records_breaches_without_changing_the_message(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="monitor")
        sent = await send(protocol, proposal(total=30.0, quantity=2))
        assert sent.message.total_price == pytest.approx(30.0)
        report = protocol.report()
        assert report["breach_rate"] == 1.0
        assert report["mean_intervention"] == 0.0

    async def test_off_mode_records_the_trajectory_only(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="off")
        await send(protocol, proposal(total=30.0, quantity=2))
        assert protocol.records[0].breach
        assert protocol.records[0].mode == "off"


class TestUngovernableCases:
    async def test_a_pair_with_no_contract_passes_through_and_is_counted(self):
        reg = registry(customers=[customer(menu_features={"Something Else": 5.0})])
        protocol = GovernedMarketplaceProtocol(reg, mode="filter")
        sent = await send(protocol, proposal(total=99.0, quantity=2))
        assert sent.message.total_price == pytest.approx(99.0)
        assert protocol.report()["ungoverned_messages"] == 1.0

    async def test_an_unsatisfiable_contract_is_not_projected_into_nothing(self):
        """C(theta) empty: record the breach, forward untouched, flag the pair.

        Projecting into an empty set is not a safety operation, and letting
        every step degrade onto slack would read in aggregate as a filter that
        cannot hold its constraints.
        """
        expensive = business(min_price_factor=1.0, menu_features={"Tacos": 50.0})
        reg = registry(
            businesses=[expensive],
            customers=[customer(menu_features={"Tacos": 8.0})],
        )
        assert reg.unsatisfiable == ["business_0001|customer_0001"]

        protocol = GovernedMarketplaceProtocol(reg, mode="filter")
        sent = await send(protocol, proposal(total=60.0, quantity=1))
        assert sent.message.total_price == pytest.approx(60.0)
        report = protocol.report()
        assert report["pairs_unsatisfiable"] == 1.0
        assert report["breach_rate"] == 1.0


class TestBuyerMoves:
    async def test_a_counter_offer_extends_the_observed_trajectory_only(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        await send(protocol, proposal(total=10.0, quantity=2))
        await send(
            protocol,
            TextMessage(content="Could you do $8 total?"),
            sender="customer_0001",
            recipient="business_0001",
        )
        state = protocol.states["business_0001|customer_0001"]
        assert len(state.binding) == 1  # buyer prose is not a binding term
        assert len(state.observed) == 2  # but it is a move for the energy

    async def test_prose_without_terms_is_not_a_move(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        await send(protocol, proposal(total=10.0, quantity=2))
        await send(
            protocol,
            TextMessage(content="Thanks, let me think about it."),
            sender="customer_0001",
            recipient="business_0001",
        )
        state = protocol.states["business_0001|customer_0001"]
        assert len(state.observed) == 1

    async def test_a_buyer_message_is_never_rewritten(self):
        protocol = GovernedMarketplaceProtocol(registry(), mode="filter")
        await send(protocol, proposal(total=10.0, quantity=2))
        text = "I'll pay $1 total, final offer."
        sent = await send(
            protocol,
            TextMessage(content=text),
            sender="customer_0001",
            recipient="business_0001",
        )
        assert sent.message.content == text


class TestCoupling:
    """Coupling is isolated here: budget and per-pair quantity bounds are made
    slack on purpose, so that whatever clamps the trajectory is the shared
    capacity clause and not one of the private rows."""

    @staticmethod
    def _uncoupled_registry(**kwargs) -> ContractRegistry:
        rich = customer(menu_features={"Tacos": 500.0, "Agua": 500.0})
        return ContractRegistry.from_participants(
            [business()],
            [
                rich.model_copy(update={"id": "customer_0001"}),
                rich.model_copy(update={"id": "customer_0002", "name": "Second"}),
            ],
            spec=ContractSpec(q_max_factor=10.0),
            **kwargs,
        )

    async def test_a_business_serving_two_customers_shares_capacity(self):
        """The clause binds on whoever is moving, and carries a shadow price.

        Only the in-flight message can be adjusted — a proposal already sent to
        the other customer cannot be retracted — so the coupling clause acts as
        a residual-capacity constraint on the current mover.
        """
        # Q = 1.5 * (2 + 2) = 6, so both pairs can open at q = 2.
        reg = self._uncoupled_registry(capacity_factor=1.5)
        capacity = reg.capacity_for("business_0001")
        protocol = GovernedMarketplaceProtocol(reg, mode="filter", couple=True)

        await send(protocol, proposal(total=2.0, quantity=2, pid="a1"),
                   recipient="customer_0001")
        await send(protocol, proposal(total=2.0, quantity=2, pid="b1"),
                   recipient="customer_0002")
        assert sum(
            float(s.binding[-1][1]) for s in protocol.states.values()
        ) <= capacity + 1e-6

        # Pair 1 now wants 6 units; with the peer holding 2 that would be 8.
        await send(protocol, proposal(total=6.0, quantity=6, pid="a2"),
                   recipient="customer_0001")

        record = protocol.records[-1]
        assert record.duals["shared:capacity"] > 0.0
        total_q = sum(
            float(state.binding[-1][1]) for state in protocol.states.values()
        )
        assert total_q <= capacity + 1e-6

    async def test_without_coupling_the_same_move_is_unconstrained(self):
        """Isolates the clause: same trajectory, no capacity, no clamp."""
        reg = self._uncoupled_registry()  # no capacities at all
        protocol = GovernedMarketplaceProtocol(reg, mode="filter", couple=True)

        await send(protocol, proposal(total=2.0, quantity=2, pid="a1"),
                   recipient="customer_0001")
        await send(protocol, proposal(total=2.0, quantity=2, pid="b1"),
                   recipient="customer_0002")
        await send(protocol, proposal(total=6.0, quantity=6, pid="a2"),
                   recipient="customer_0001")

        assert "shared:capacity" not in protocol.records[-1].duals
        total_q = sum(
            float(state.binding[-1][1]) for state in protocol.states.values()
        )
        assert total_q > 6.0


class TestReplay:
    def test_replay_measures_the_ungoverned_breach_rate(self):
        """Replay reports what happened; it must not filter."""
        reg = registry()
        rows = [
            {
                "from_agent": "business_0001",
                "to_agent": "customer_0001",
                "msg_type": "order_proposal",
                "msg_json": proposal(total=t, quantity=2, pid=f"p{i}").model_dump(
                    mode="json"
                ),
            }
            for i, t in enumerate([10.0, 30.0, 9.0, 25.0])
        ]
        result = replay_messages(rows, reg)
        assert result.proposals_seen == 4
        assert result.proposals_governed == 4
        # Two of the four exceed the budget of 11.
        assert result.summary()["breach_rounds"] == 2.0
        # The recorded terms are the ones actually sent, unmodified.
        traj = result.trajectories["business_0001|customer_0001"]
        assert traj[1][0] == pytest.approx(15.0)

    def test_replay_counts_pairs_it_cannot_govern(self):
        reg = registry(customers=[customer(menu_features={"Something Else": 5.0})])
        rows = [
            {
                "from_agent": "business_0001",
                "to_agent": "customer_0001",
                "msg_type": "order_proposal",
                "msg_json": proposal(total=10.0).model_dump(mode="json"),
            }
        ]
        result = replay_messages(rows, reg)
        assert result.proposals_seen == 1
        assert result.proposals_governed == 0
        assert result.ungoverned[0]["reason"] == "no definable contract"


class TestSettledDeals:
    """A breaching offer and a breaching deal are different events.

    The gap between the two rates is a measurement of how much the customer
    agent already refuses on its own, which is the part of the safety result
    the filter cannot claim credit for.
    """

    @staticmethod
    def _rows(totals: list[float], paid_index: int | None):
        rows = [
            {
                "from_agent": "business_0001",
                "to_agent": "customer_0001",
                "msg_type": "order_proposal",
                "msg_json": proposal(total=t, quantity=2, pid=f"p{i}").model_dump(
                    mode="json"
                ),
            }
            for i, t in enumerate(totals)
        ]
        if paid_index is not None:
            rows.append(
                {
                    "from_agent": "customer_0001",
                    "to_agent": "business_0001",
                    "msg_type": "payment",
                    "msg_json": {
                        "type": "payment",
                        "proposal_message_id": f"p{paid_index}",
                    },
                }
            )
        return rows

    def test_a_declined_breaching_offer_is_not_a_breaching_deal(self):
        """theta: B = 11. The seller offers 30, the buyer pays for the 10."""
        result = replay_messages(self._rows([30.0, 10.0], paid_index=1), registry())
        summary = result.summary()
        assert summary["breach_rounds"] == 1.0  # the offer breached
        assert summary["deals_settled"] == 1.0
        assert summary["deals_breached"] == 0.0  # the deal did not
        assert summary["total_overspend"] == 0.0

    def test_an_accepted_breaching_offer_is_a_breaching_deal(self):
        result = replay_messages(self._rows([30.0, 10.0], paid_index=0), registry())
        summary = result.summary()
        assert summary["deals_breached"] == 1.0
        assert summary["deal_breach_rate"] == pytest.approx(1.0)
        assert summary["total_overspend"] == pytest.approx(19.0)

    def test_magnitude_is_reported_beside_the_count(self):
        """Four trivial breaches and one large one are not the same event."""
        result = replay_messages(self._rows([11.03], paid_index=0), registry())
        summary = result.summary()
        assert summary["deals_breached"] == 1.0
        assert summary["max_overspend"] == pytest.approx(0.03, abs=1e-9)

    def test_a_negotiation_with_no_payment_settles_nothing(self):
        result = replay_messages(self._rows([30.0, 20.0], paid_index=None), registry())
        summary = result.summary()
        assert summary["deals_settled"] == 0.0
        assert "deal_breach_rate" not in summary  # no rate over zero deals

    def test_a_payment_for_an_unknown_proposal_is_ignored(self):
        rows = self._rows([10.0], paid_index=None)
        rows.append(
            {
                "from_agent": "customer_0001",
                "to_agent": "business_0001",
                "msg_type": "payment",
                "msg_json": {"type": "payment", "proposal_message_id": "nonexistent"},
            }
        )
        assert replay_messages(rows, registry()).summary()["deals_settled"] == 0.0


class TestBreachClassification:
    """Three classes, because one bucket makes the headline mean the wrong thing.

    A structurally infeasible pair cannot be improved by any filter, and a
    three-pence overspend on a $13 basket is not the same event as a 3% one.
    Folding all of them together inflates the ungoverned rate and then credits
    the safety layer for "fixing" situations it never could have.
    """

    @staticmethod
    def _deal(
        spend: float,
        budget: float,
        satisfiable: bool = True,
        rows: list[str] | None = None,
    ) -> SettledDeal:
        if rows is None:
            rows = ["budget"] if spend > budget + 1e-9 else []
        return SettledDeal(
            pair_id="business_0001|customer_0001",
            proposal_id="p1",
            terms=[spend, 1.0, 0.0],
            spend=spend,
            budget=budget,
            breached_rows=rows,
            satisfiable=satisfiable,
        )

    def test_a_deal_within_budget_is_not_a_breach(self):
        assert self._deal(spend=10.0, budget=11.0).classification == "within"

    def test_an_empty_safe_set_is_infeasible_not_a_breach(self):
        """No terms could have complied, so this is a scenario property."""
        deal = self._deal(spend=50.0, budget=11.0, satisfiable=False)
        assert deal.breached
        assert deal.classification == "infeasible"

    def test_the_threshold_is_a_fraction_of_budget_not_an_absolute(self):
        """Three pence on $13 and three pence on $370 are different events."""
        assert self._deal(spend=13.51, budget=13.48).classification == "trivial"
        big = self._deal(spend=370.03, budget=370.00)
        assert big.overspend == pytest.approx(0.03)
        assert big.classification == "trivial"  # still 0.008% of budget

    def test_the_real_mexican_breaches_land_where_expected(self):
        """The data that motivated the 1% threshold, pinned.

        Susan Young's recurring overspend is 0.22% and arises by construction;
        the two substantive breaches are 2.1% and 2.9%. If the threshold ever
        moves across that gap this test says so.
        """
        assert self._deal(13.51, 13.48).classification == "trivial"  # 0.22%
        assert self._deal(13.76, 13.48).classification == "meaningful"  # 2.1%
        assert self._deal(37.53, 36.47).classification == "meaningful"  # 2.9%

    def test_the_threshold_boundary_is_exclusive_below(self):
        assert TRIVIAL_BREACH_FRACTION == 0.01
        assert self._deal(100.99, 100.0).classification == "trivial"
        assert self._deal(101.0, 100.0).classification == "meaningful"

    def test_a_non_budget_breach_is_never_trivial(self):
        """Zero overspend does not make a cost-floor breach small.

        This is a real deal from arm_a_bargain_v1: the seller sold 2 items
        instead of the 3 requested, at $9.05 against a $10.19 cost floor. The
        budget overspend is zero — it came in well under — and measuring
        magnitude by overspend alone classified the most serious breach in the
        dataset as trivial.
        """
        deal = self._deal(
            spend=18.10, budget=31.38, rows=["cost_floor", "q_min"]
        )
        assert deal.overspend == 0.0
        assert deal.classification == "meaningful"

    def test_only_the_budget_row_has_a_de_minimis_notion(self):
        """The other rows are categorical: any breach counts."""
        assert self._deal(11.0, 100.0, rows=["q_max"]).classification == "meaningful"
        assert self._deal(11.0, 100.0, rows=["d_max"]).classification == "meaningful"
        # Budget alone, and small, is the only trivial case.
        assert self._deal(100.5, 100.0, rows=["budget"]).classification == "trivial"
        # Budget plus anything else is not.
        assert (
            self._deal(100.5, 100.0, rows=["budget", "q_min"]).classification
            == "meaningful"
        )

    def test_summary_counts_every_deal_exactly_once(self):
        reg = registry()
        rows = [
            {
                "from_agent": "business_0001",
                "to_agent": "customer_0001",
                "msg_type": "order_proposal",
                "msg_json": proposal(total=t, quantity=2, pid=f"p{i}").model_dump(
                    mode="json"
                ),
            }
            for i, t in enumerate([10.0, 30.0])
        ] + [
            {
                "from_agent": "customer_0001",
                "to_agent": "business_0001",
                "msg_type": "payment",
                "msg_json": {"type": "payment", "proposal_message_id": "p1"},
            }
        ]
        summary = replay_messages(rows, reg).summary()
        classes = sum(
            summary[f"deals_{c}"]
            for c in ("within", "infeasible", "trivial", "meaningful")
        )
        assert classes == summary["deals_settled"]
