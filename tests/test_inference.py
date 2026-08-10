"""Arm C: the envelope inferred from opening positions.

These assert on the object the filter actually enforces, not on whether the
inference ran. The arm B wire bug is the reason: a test that checks a
computation happened, rather than what the counterparty is held to, passes
while the arm measures nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.contract import Contract
from src.marketplace_integration.inference import InferenceReport, Positions

BASE = Contract(budget=60.0, cost_floor=6.0, q_min=10.0, q_max=20.0,
                d_min=0.0, d_max=7.0)


def freeze(ask: float, offer: float, quantity: float = 10.0,
           base: Contract = BASE) -> Positions:
    p = Positions()
    p.note_seller(ask, quantity)
    p.note_buyer(offer)
    p.try_freeze(base, round_index=1)
    return p


class TestTheEnvelopeIsTheAgentsOwnPositions:
    def test_budget_row_is_the_sellers_own_opening_ask(self):
        """p <= p_s: the seller cannot later demand more than it opened at."""
        p = freeze(ask=8.0, offer=5.0, quantity=10.0)
        assert p.contract is not None
        assert p.contract.budget == pytest.approx(80.0)  # 8.0 * 10
        # The opening ask is on the boundary, so it is safe by construction.
        assert p.contract.is_safe(np.array([8.0, 10.0, 3.0]))

    def test_cost_floor_row_is_the_buyers_own_counter(self):
        """p >= p_b: the buyer cannot later offer less than it counter-offered."""
        p = freeze(ask=8.0, offer=5.0)
        assert p.contract is not None
        assert p.contract.cost_floor == pytest.approx(5.0)
        assert not p.contract.is_safe(np.array([4.99, 10.0, 3.0]))

    def test_the_safe_set_is_non_empty_by_construction(self):
        """Unlike the imposed theta, an envelope of two live positions overlaps.

        This is the structural difference from arms B and D, where four of the
        nine definable pairs have c*q_min > B and cannot be filtered at all.
        """
        for ask, offer in ((8.0, 5.0), (100.0, 99.0), (6.0, 0.5)):
            p = freeze(ask=ask, offer=offer)
            assert p.contract is not None
            assert p.contract.is_satisfiable()

    def test_structural_terms_carry_over_untouched(self):
        """Quantity and deadline bands are the subject of the negotiation, not
        positions taken in it, so they are not inferred."""
        p = freeze(ask=8.0, offer=5.0)
        assert p.contract is not None
        assert p.contract.q_min == BASE.q_min
        assert p.contract.q_max == BASE.q_max
        assert p.contract.d_min == BASE.d_min
        assert p.contract.d_max == BASE.d_max


class TestTheEnvelopeIsFrozen:
    def test_later_positions_do_not_move_the_boundary(self):
        """A contract that tracked the latest offers would constrain nothing —
        each concession would drag the boundary along behind it."""
        p = freeze(ask=8.0, offer=5.0)
        before = p.contract
        p.note_seller(7.0, 10.0)
        p.note_buyer(6.0)
        p.try_freeze(BASE, round_index=5)
        assert p.contract is before
        assert p.contract is not None
        assert p.contract.budget == pytest.approx(80.0)
        assert p.frozen_at_round == 1

    def test_nothing_is_frozen_until_both_sides_have_spoken(self):
        p = Positions()
        p.note_seller(8.0, 10.0)
        assert p.try_freeze(BASE, 0) is None
        assert not p.is_frozen
        p.note_buyer(5.0)
        assert p.try_freeze(BASE, 1) is not None
        assert p.is_frozen


class TestTheHonestFailures:
    def test_a_buyer_offer_above_the_ask_yields_no_contract(self):
        """There is no zone to enforce, and c >= B/q would be an empty safe
        set — filtering into which is not a safety operation."""
        p = freeze(ask=5.0, offer=8.0)
        assert p.contract is None
        assert not p.is_frozen
        assert p.failure is not None and "no zone" in p.failure

    def test_a_silent_buyer_leaves_the_pair_ungoverned_and_counted(self):
        report = InferenceReport()
        quiet = Positions()
        quiet.note_seller(8.0, 10.0)
        report.pairs["b|c"] = quiet
        report.pairs["b|d"] = freeze(ask=8.0, offer=5.0)

        assert report.summary()["freeze_rate"] == pytest.approx(0.5)
        failures = report.failures()
        assert [f["pair"] for f in failures] == ["b|c"]
        assert "never stated a price" in failures[0]["reason"]


class TestHowItDiffersFromTheImposedContract:
    def test_the_envelope_need_not_refine_the_platforms_mandate(self):
        """The finding arm C exists to surface: a pair can honour the contract
        it agreed and still breach the one the platform would have imposed,
        because the seller's opening ask sits above the customer's reservation.
        """
        p = freeze(ask=8.0, offer=5.0, quantity=10.0)  # B = 80 vs imposed 60
        assert p.contract is not None
        assert not p.contract.refines(BASE)
        assert p.contract.budget > BASE.budget

        # And a state can be safe under the envelope while breaching the mandate.
        x = np.array([7.0, 10.0, 3.0])
        assert p.contract.is_safe(x)
        assert not BASE.is_safe(x)


class TestTheEchoIsNotACounterOffer:
    """A buyer quoting the seller's own price to reject it states no position.

    Pinned with the exact phrasing that produced the bug on
    `business_0007|customer_0003`, arm C seed 1, where it made the buyer look
    like it had counter-offered at precisely the ask and so left four of nine
    pairs with no zone to enforce.
    """

    ECHO = (
        "The price of $37.53 for 1 Southwest Chicken Enchiladas, 1 Coconut "
        "Lime Tres Leches, and 1 Chargrilled Carne Asada is too high. Can you "
        "offer a better price?"
    )

    def test_the_echo_is_read_as_no_move(self):
        from src.marketplace_integration.terms import from_text

        assert from_text(self.ECHO, fallback_quantity=3.0, current_price=12.51) is None

    def test_without_the_current_price_it_is_still_misread(self):
        """The defect is in what the caller supplies, not in the regex, and
        this pins that so the argument cannot be quietly dropped again."""
        from src.marketplace_integration.terms import from_text

        terms = from_text(self.ECHO, fallback_quantity=3.0)
        assert terms is not None
        assert terms.price == pytest.approx(12.51)

    def test_a_genuine_counter_offer_still_registers(self):
        from src.marketplace_integration.terms import from_text

        terms = from_text(
            "That is too high. I can do $30.00 for the three.",
            fallback_quantity=3.0,
            current_price=12.51,
        )
        assert terms is not None
        assert terms.price == pytest.approx(10.0)

    def test_the_buyers_own_figure_is_recovered_from_behind_the_echo(self):
        """The half of the defect that *loses* data rather than inventing it.

        "The current quote of $13.76 is above my budget of $11.58" states a
        real position — $11.58 — which `.search()` discarded in favour of the
        seller's own quote. Pinned with the phrasing from arm C seed 1,
        `business_0002|customer_0001`, ask 6.88/unit on 2 units.
        """
        from src.marketplace_integration.terms import from_text

        terms = from_text(
            "The current quote of $13.76 is above my budget of $11.58. Would "
            "you be able to offer a lower price?",
            fallback_quantity=2.0,
            current_price=6.88,
        )
        assert terms is not None
        assert terms.price == pytest.approx(5.79)  # 11.58 / 2

    def test_without_the_current_price_the_sellers_quote_wins(self):
        from src.marketplace_integration.terms import from_text

        terms = from_text(
            "The current quote of $13.76 is above my budget of $11.58.",
            fallback_quantity=2.0,
        )
        assert terms is not None
        assert terms.price == pytest.approx(6.88)  # the seller's own ask
