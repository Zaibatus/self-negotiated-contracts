"""The reward-transfer baseline, pinned on the properties its theorem needs.

Christoffersen et al.'s Definition 2.2 requires a contract to be a *zero-sum*
state-dependent transfer, and Theorem 3.1's richness condition bounds it. Those
are the two things that make the mechanism what it is, so they are tested as
properties over a grid rather than asserted on one example.

The third test class is the one that matters for the thesis's argument. A
transfer redistributes an overspend; it does not prevent one. That is not a
criticism of the baseline — it is what an equilibrium guarantee *is* — but it
has to be pinned, because the whole comparison in Chapter 5 turns on it and an
implementation that quietly clipped the terms would make the baseline look like
the filter.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import numpy as np
import pytest

from src.contract import Contract
from src.marketplace_integration.transfers import (
    BUYER,
    SELLER,
    TransferSchedule,
    settle,
    summarise,
)

# The working scenario's shape: a budget that binds, a floor the seller holds.
THETA = Contract(budget=11.58, cost_floor=5.79, q_min=2.0, q_max=4.0,
                 d_min=1.0, d_max=14.0)

# Straddles the budget row in both directions at several quantities.
GRID = [
    np.array([p, q, d])
    for p, q, d in itertools.product(
        [4.0, 5.0, 5.79, 6.755, 8.0, 12.0], [2.0, 3.0, 4.0], [3.0, 7.0]
    )
]


class TestTheTransferIsZeroSum:
    """Definition 2.2: the range of the contract consists of zero-sum vectors."""

    def test_it_sums_to_zero_on_every_point_of_the_grid(self):
        s = TransferSchedule(THETA)
        for x in GRID:
            assert s.transfer(x).sum() == pytest.approx(0.0, abs=1e-12), x

    def test_it_sums_to_zero_under_every_rate_and_cap(self):
        for rate, cap in itertools.product([0.0, 0.5, 1.0, 3.0], [None, 0.01, 5.0]):
            s = TransferSchedule(THETA, rate=rate, cap=cap)
            for x in GRID:
                assert s.transfer(x).sum() == pytest.approx(0.0, abs=1e-12)

    def test_the_seller_pays_and_the_buyer_receives(self):
        """Direction is not arbitrary: the seller proposes the breach."""
        s = TransferSchedule(THETA)
        x = np.array([6.755, 2.0, 7.0])          # 13.51 against a budget of 11.58
        tr = s.transfer(x)
        assert tr[SELLER] < 0 < tr[BUYER]

    def test_a_settlement_records_a_zero_sum_residual_of_exactly_zero(self):
        s = TransferSchedule(THETA)
        st = settle(s, "b|c", np.array([6.755, 2.0, 7.0]))
        assert st.zero_sum_residual == 0.0


class TestItFiresExactlyOnBreach:
    """A transfer that fired inside C(theta) would be a tax, not a contract."""

    def test_it_is_null_everywhere_inside_the_safe_set(self):
        s = TransferSchedule(THETA)
        for x in GRID:
            if THETA.is_safe(x):
                assert s.is_null(x), f"transfer fired on compliant terms {x}"

    def test_it_is_nonzero_wherever_the_budget_row_is_breached(self):
        s = TransferSchedule(THETA)
        fired = 0
        for x in GRID:
            over = x[0] * x[1] - THETA.budget
            if over > 1e-9:
                assert s.amount(x) > 0, f"no transfer on breaching terms {x}"
                fired += 1
        assert fired > 0, "grid no longer exercises the breach case"

    def test_the_amount_is_the_overshoot_at_unit_rate(self):
        s = TransferSchedule(THETA, rate=1.0)
        x = np.array([6.755, 2.0, 7.0])
        assert s.amount(x) == pytest.approx(13.51 - 11.58, abs=1e-9)

    def test_the_cap_is_theorem_3_1s_richness_bound(self):
        s = TransferSchedule(THETA, rate=1.0, cap=0.50)
        x = np.array([12.0, 4.0, 7.0])           # a large breach
        assert s.amount(x) == pytest.approx(0.50)

    def test_a_negative_rate_is_refused(self):
        """It would pay the seller for breaching."""
        with pytest.raises(ValueError):
            TransferSchedule(THETA, rate=-1.0)


class TestATransferRedistributesAndDoesNotPrevent:
    """The comparison the thesis turns on, pinned so it cannot drift.

    Arm B takes settled breaches to zero. A transfer leaves the breach in place
    and moves money afterwards. If this ever starts passing for the wrong
    reason — because the schedule began clipping terms — the arm F result would
    silently become an arm B result.
    """

    BREACHING = np.array([6.755, 2.0, 7.0])      # 13.51 on an 11.58 budget

    def test_the_terms_are_returned_unchanged(self):
        """The schedule has no method that rewrites terms, and must not."""
        s = TransferSchedule(THETA)
        assert not hasattr(s, "project"), "a transfer must not project terms"
        assert not hasattr(s, "rewrite"), "a transfer must not rewrite terms"

    def test_the_deal_still_breaches_after_the_transfer_settles(self):
        s = TransferSchedule(THETA)
        st = settle(s, "b|c", self.BREACHING)
        assert st.violation > 0
        assert not THETA.is_safe(self.BREACHING)

    def test_residual_overspend_survives_even_at_a_punitive_rate(self):
        """Money moves; the terms do not."""
        for rate in [1.0, 5.0, 100.0]:
            s = TransferSchedule(THETA, rate=rate)
            out = summarise([settle(s, "b|c", self.BREACHING)])
            assert out["residual_overspend"] == pytest.approx(1.93, abs=1e-9)
            assert out["deals_breaching"] == 1.0

    def test_the_buyer_is_made_whole_in_currency_but_not_in_compliance(self):
        s = TransferSchedule(THETA, rate=1.0)
        out = summarise([settle(s, "b|c", self.BREACHING)])
        assert out["transferred_total"] == pytest.approx(out["residual_overspend"])
        assert out["deals_breaching_rate"] == 1.0


class TestTheDisclosedClause:
    """The clause is the transfer's only channel, so its content is load-bearing."""

    def test_it_names_the_budget_the_contract_actually_enforces(self):
        s = TransferSchedule(THETA)
        assert "11.58" in s.clause()

    def test_it_names_the_cap_when_there_is_one(self):
        assert "0.50" in TransferSchedule(THETA, cap=0.50).clause()
        assert "capped" not in TransferSchedule(THETA).clause()

    def test_it_states_that_both_parties_are_already_bound(self):
        """Acceptance is assumed, which is the baseline's best case."""
        c = TransferSchedule(THETA).clause().lower()
        assert "accepted by both parties" in c
        assert "neither can opt" in c


class TestSummary:
    def test_an_empty_arm_reports_no_deals_rather_than_dividing_by_zero(self):
        assert summarise([]) == {"deals": 0.0}

    def test_compliant_deals_contribute_nothing_to_overspend(self):
        s = TransferSchedule(THETA)
        out = summarise([settle(s, "b|c", np.array([5.79, 2.0, 7.0]))])
        assert out["residual_overspend"] == 0.0
        assert out["deals_breaching"] == 0.0


class TestTheScenarioPreservesTheta:
    """The one-variable claim, pinned rather than checked once by hand.

    Arm F is only a comparison with arm B if both encode the *same* constraint.
    The generator appends a clause and touches nothing else, so
    ``Contract.from_scenario`` must read identical theta on every pair. If a
    future edit to the generator starts moving ``menu_features``, arm F stops
    being a mechanism comparison and becomes a scenario comparison, and every
    number in it would be measuring the wrong thing.

    Skips rather than fails where the scenarios have not been generated, since
    the suite must run with no data and no database.
    """

    SOURCE = Path("data/bargain_3_9")
    DEST = Path("data/transfer_3_9")

    def _registries(self):
        if not (self.SOURCE.exists() and self.DEST.exists()):
            pytest.skip("scenarios not generated; see make_transfer_scenario.py")
        from src.marketplace_integration.theta import ContractRegistry

        return (
            ContractRegistry.from_data_dir(str(self.SOURCE)),
            ContractRegistry.from_data_dir(str(self.DEST)),
        )

    def test_theta_is_identical_on_every_pair(self):
        a, b = self._registries()
        assert set(a.contracts) == set(b.contracts)
        for key in a.contracts:
            assert np.allclose(a.contracts[key].theta, b.contracts[key].theta), key

    def test_the_unsatisfiable_set_is_identical(self):
        """Four of nine pairs are unsatisfiable by construction; that must not move."""
        a, b = self._registries()

        def unsat(reg):
            return {k for k, c in reg.contracts.items() if not c.is_satisfiable()}

        assert unsat(a) == unsat(b)

    def test_the_clause_reaches_both_parties(self):
        """A transfer binds all N agents; a clause only the buyer sees is not one."""
        if not self.DEST.exists():
            pytest.skip("scenario not generated")
        import yaml

        buyer = yaml.safe_load(
            (self.DEST / "customers" / "customer_0001.yaml").read_text()
        )
        seller = yaml.safe_load(
            sorted((self.DEST / "businesses").glob("*.yaml"))[0].read_text()
        )
        assert "Binding side agreement" in buyer["request"]
        assert "Binding side agreement" in seller["description"]

    def test_the_budget_in_the_clause_is_the_budget_in_theta(self):
        """The number the agent reads and the B the contract enforces are one number."""
        a, _ = self._registries()
        if not self.DEST.exists():
            pytest.skip("scenario not generated")
        import yaml

        buyer = yaml.safe_load(
            (self.DEST / "customers" / "customer_0001.yaml").read_text()
        )
        budgets = {
            c.budget for k, c in a.contracts.items() if k.endswith("customer_0001")
        }
        assert len(budgets) == 1
        assert f"{budgets.pop():.2f}" in buyer["request"]
