"""Term extraction and proposal rewriting.

Two properties carry the design and are asserted here directly:

  * aggregation is chosen so that h1 = B - p*q is *exactly* B - total_price,
    which is what makes the budget row exact rather than nearly exact;
  * a rewritten proposal stays internally consistent, because the marketplace
    validates total_price against sum(unit_price * quantity) and matches
    payments by proposal id — an inconsistent rewrite would be rejected by the
    testbed itself.
"""

from __future__ import annotations

import numpy as np
import pytest
from magentic_marketplace.marketplace.actions.messaging import (
    OrderItem,
    OrderProposal,
    TextMessage,
)

from src.marketplace_integration.terms import (
    from_order_proposal,
    from_text,
    parse_days,
    rewrite_proposal,
)


def proposal(**overrides) -> OrderProposal:
    data = {
        "id": "business_0001_customer_0001_1",
        "items": [
            OrderItem(id="Item-1", item_name="Tacos", quantity=2, unit_price=5.0),
            OrderItem(id="Item-2", item_name="Agua", quantity=1, unit_price=3.0),
        ],
        "total_price": 13.0,
        "estimated_delivery": "2-3 business days",
    }
    data.update(overrides)
    return OrderProposal.model_validate(data)


class TestDeadlineParsing:
    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("2-3 business days", 3.0),
            ("3 days", 3.0),
            ("about 1 week", 7.0),
            ("24 hrs", 1.0),
            ("45 minutes", 45.0 / 1440.0),
            ("2 months", 60.0),
        ],
    )
    def test_durations_parse_to_days(self, text, expected):
        assert parse_days(text) == pytest.approx(expected)

    def test_ranges_take_the_upper_end(self):
        """The deadline a customer would actually be held to."""
        assert parse_days("1-5 days") == pytest.approx(5.0)

    @pytest.mark.parametrize("text", [None, "", "next Tuesday", "same day", "asap"])
    def test_unparseable_returns_none_rather_than_a_guess(self, text):
        assert parse_days(text) is None


class TestSellerTerms:
    def test_aggregation_makes_the_budget_row_exact(self):
        terms = from_order_proposal(proposal())
        assert terms.quantity == pytest.approx(3.0)
        assert terms.price * terms.quantity == pytest.approx(13.0)
        assert terms.exact and terms.source == "order_proposal"

    def test_multi_item_orders_collapse_to_r3(self):
        multi = proposal(
            items=[
                OrderItem(id="Item-1", item_name="A", quantity=2, unit_price=10.0),
                OrderItem(id="Item-2", item_name="B", quantity=3, unit_price=4.0),
                OrderItem(id="Item-3", item_name="C", quantity=1, unit_price=8.0),
            ],
            total_price=40.0,
        )
        terms = from_order_proposal(multi)
        assert terms.vector.shape == (3,)
        assert terms.quantity == pytest.approx(6.0)
        assert terms.price * terms.quantity == pytest.approx(40.0)

    def test_missing_deadline_is_flagged_not_defaulted(self):
        terms = from_order_proposal(proposal(estimated_delivery=None))
        assert terms.deadline is None
        assert not terms.deadline_observed
        # The vector still has three slots; the caller masks the rows off.
        assert terms.vector[2] == 0.0

    def test_unparseable_deadline_is_also_flagged(self):
        terms = from_order_proposal(proposal(estimated_delivery="whenever, really"))
        assert not terms.deadline_observed


class TestBuyerTerms:
    def test_a_total_is_divided_by_quantity(self):
        terms = from_text(
            TextMessage(content="Can you do $10 total for the 2 units?"),
            fallback_quantity=3.0,
        )
        assert terms is not None
        assert terms.quantity == pytest.approx(2.0)
        assert terms.price == pytest.approx(5.0)
        assert not terms.exact

    def test_a_per_unit_price_is_taken_as_is(self):
        terms = from_text(
            TextMessage(content="I'll pay $4 each for 3 of them"),
            fallback_quantity=1.0,
        )
        assert terms is not None
        assert terms.price == pytest.approx(4.0)
        assert terms.quantity == pytest.approx(3.0)

    def test_quantity_falls_back_to_what_is_on_the_table(self):
        terms = from_text(
            TextMessage(content="Could you do $12?"), fallback_quantity=4.0
        )
        assert terms is not None
        assert terms.quantity == pytest.approx(4.0)
        assert terms.price == pytest.approx(3.0)

    def test_the_regex_surface_is_narrow_and_that_is_the_known_risk(self):
        """Pins a phrasing the regex genuinely misses.

        The quantity is read as whatever is on the table rather than as the
        stated "a couple", so the extracted term vector is wrong — not absent,
        wrong. This is the residual trusted-computing-base surface of
        formulation.md section 7.2, and the extraction-noise robustness
        experiment exists to measure how much it costs. Keeping a failing case
        asserted is how that stays visible; broadening the regex until every
        phrasing parses would hide the surface rather than remove it.
        """
        terms = from_text(
            TextMessage(content="I'd take a couple at $6"), fallback_quantity=1.0
        )
        assert terms is not None
        assert terms.quantity == pytest.approx(1.0)  # not 2

    def test_a_message_with_no_terms_is_not_a_move(self):
        """Returning None, not a fabricated point.

        A fabricated term vector would enter the trajectory and the round-pair
        energy would read the fabrication as revealed remaining gain.
        """
        assert from_text(TextMessage(content="Thanks, sounds good!"), 2.0) is None
        assert from_text(TextMessage(content="Do you have parking?"), 2.0) is None

    def test_llm_fallback_is_only_consulted_when_regex_finds_nothing(self):
        calls: list[str] = []

        def extractor(text: str):
            calls.append(text)
            return None

        from_text(TextMessage(content="How about $9?"), 1.0, llm_extractor=extractor)
        assert calls == []

        from_text(TextMessage(content="a bit cheaper please"), 1.0,
                  llm_extractor=extractor)
        assert calls == ["a bit cheaper please"]


class TestRewrite:
    def test_rewritten_proposal_is_internally_consistent(self):
        original = proposal()
        rewritten = rewrite_proposal(original, np.array([4.0, 3.0, 2.0]))
        line_sum = sum(i.unit_price * i.quantity for i in rewritten.items)
        assert rewritten.total_price == pytest.approx(line_sum, abs=0.011)

    def test_proposal_id_is_preserved(self):
        """Payments are matched by id; changing it would break the payment."""
        original = proposal()
        rewritten = rewrite_proposal(original, np.array([4.0, 3.0, 2.0]))
        assert rewritten.id == original.id

    def test_quantity_is_redistributed_over_line_items(self):
        rewritten = rewrite_proposal(proposal(), np.array([3.0, 6.0, 0.0]))
        assert sum(i.quantity for i in rewritten.items) == 6

    def test_no_line_item_is_dropped(self):
        """Removing an item changes what is bought; the filter has no mandate."""
        rewritten = rewrite_proposal(proposal(), np.array([2.0, 2.0, 0.0]))
        assert len(rewritten.items) == 2
        assert all(i.quantity >= 1 for i in rewritten.items)

    def test_rewrite_then_extract_round_trips_to_cents(self):
        target = np.array([4.25, 4.0, 0.0])
        rewritten = rewrite_proposal(proposal(), target)
        back = from_order_proposal(rewritten)
        assert back.quantity == pytest.approx(target[1])
        assert back.price * back.quantity == pytest.approx(
            target[0] * target[1], abs=0.02
        )
