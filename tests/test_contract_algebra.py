"""The refinement order and the meet, as properties rather than assertions.

`formulation.md` §1 states that contracts carry a refinement order
``C' ⊑ C iff C(θ') ⊆ C(θ)`` and that composition is well behaved. Until this
file, nothing checked either claim — and the first thing these tests found was
that `Contract.refines` was **wrong** on the deadline case (see
`TestRefinesIsTheSubsetOrder.test_an_unbounded_deadline_does_not_refine_a_bounded_one`).

The tests assert on the surface that matters: not that `meet` returns something
plausible, but that ``C(a ∧ b)`` is *exactly* the intersection of the two safe
sets, sampled over a box that exercises every row in both directions.
"""

from __future__ import annotations

import itertools

import numpy as np
import pytest

from src.contract import Contract

A = Contract(budget=100.0, cost_floor=5.0, q_min=8.0, q_max=20.0,
             d_min=1.0, d_max=6.0)
B = Contract(budget=80.0, cost_floor=6.0, q_min=10.0, q_max=25.0,
             d_min=0.0, d_max=4.0)
C = Contract(budget=120.0, cost_floor=4.0, q_min=5.0, q_max=30.0,
             d_min=2.0, d_max=9.0)

CONTRACTS = [A, B, C, A.without_deadline(), B.without_deadline()]

# A box that straddles every bound of every contract above, so a sampled point
# can be inside one safe set and outside the other on any row.
GRID = [
    np.array([p, q, d])
    for p, q, d in itertools.product(
        [3.0, 4.5, 5.5, 6.5, 9.0], [4.0, 9.0, 12.0, 22.0, 28.0], [0.0, 1.5, 5.0, 8.0]
    )
]


def theta_eq(a: Contract, b: Contract) -> bool:
    """Equality on θ *and* on which rows are active."""
    return bool(
        np.allclose(a.theta, b.theta) and a.deadline_active == b.deadline_active
    )


class TestRefinesIsTheSubsetOrder:
    """`refines` must agree with actual set inclusion on the sample grid."""

    @pytest.mark.parametrize("a", CONTRACTS)
    @pytest.mark.parametrize("b", CONTRACTS)
    def test_refines_implies_containment(self, a: Contract, b: Contract):
        if not a.refines(b):
            return
        outside = [x for x in GRID if a.is_safe(x) and not b.is_safe(x)]
        assert not outside, (
            f"refines() claims C(a) ⊆ C(b) but {outside[0]} is in C(a) only"
        )

    def test_an_unbounded_deadline_does_not_refine_a_bounded_one(self):
        """The bug these tests were written to catch.

        `a.without_deadline()` imposes no constraint on d, so its safe set is
        unbounded in a direction where `a`'s is not. It cannot refine `a`. The
        original implementation skipped the deadline comparison whenever either
        side had the rows off, and returned True.
        """
        loose = A.without_deadline()
        assert not loose.refines(A)

        witness = np.array([6.0, 10.0, 99.0])
        assert loose.is_safe(witness)
        assert not A.is_safe(witness)

    def test_a_bounded_deadline_does_refine_an_unbounded_one(self):
        """The other direction, which is a refinement and must stay one."""
        assert A.refines(A.without_deadline())

    def test_the_order_is_reflexive_and_antisymmetric(self):
        for a in CONTRACTS:
            assert a.refines(a)
        for a, b in itertools.combinations(CONTRACTS, 2):
            if a.refines(b) and b.refines(a):
                assert theta_eq(a, b)


class TestMeetIsAGreatestLowerBound:
    @pytest.mark.parametrize("a", CONTRACTS)
    @pytest.mark.parametrize("b", CONTRACTS)
    def test_the_meet_refines_both_inputs(self, a: Contract, b: Contract):
        m = a.meet(b)
        assert m.refines(a)
        assert m.refines(b)

    @pytest.mark.parametrize("a", CONTRACTS)
    @pytest.mark.parametrize("b", CONTRACTS)
    def test_the_meet_is_the_greatest_such_bound(self, a: Contract, b: Contract):
        """Anything refining both inputs also refines the meet."""
        m = a.meet(b)
        for c in CONTRACTS:
            if c.refines(a) and c.refines(b):
                assert c.refines(m)

    def test_meet_with_something_you_already_refine_changes_nothing(self):
        assert theta_eq(B.meet(A), B) or B.refines(A) is False
        tight = Contract(budget=50.0, cost_floor=7.0, q_min=12.0, q_max=15.0,
                         d_min=2.0, d_max=3.0)
        assert tight.refines(A)
        assert theta_eq(tight.meet(A), tight)


class TestMeetIsASemilatticeOperation:
    @pytest.mark.parametrize("a", CONTRACTS)
    def test_idempotent(self, a: Contract):
        assert theta_eq(a.meet(a), a)

    @pytest.mark.parametrize("a", CONTRACTS)
    @pytest.mark.parametrize("b", CONTRACTS)
    def test_commutative(self, a: Contract, b: Contract):
        assert theta_eq(a.meet(b), b.meet(a))

    @pytest.mark.parametrize("a", CONTRACTS)
    @pytest.mark.parametrize("b", CONTRACTS)
    @pytest.mark.parametrize("c", CONTRACTS)
    def test_associative(self, a: Contract, b: Contract, c: Contract):
        assert theta_eq(a.meet(b).meet(c), a.meet(b.meet(c)))


class TestTheSafeSetOfTheMeetIsTheIntersection:
    """The claim the whole algebra rests on, and the one arm C-meet uses.

    Exactness matters: an inner approximation would still refine both inputs
    and pass every test above while quietly forbidding admissible terms.
    """

    @pytest.mark.parametrize("a", CONTRACTS)
    @pytest.mark.parametrize("b", CONTRACTS)
    def test_c_of_meet_equals_intersection_on_the_grid(
        self, a: Contract, b: Contract
    ):
        m = a.meet(b)
        for x in GRID:
            assert m.is_safe(x) == (a.is_safe(x) and b.is_safe(x)), (
                f"disagreement at {x}: meet={m.is_safe(x)}, "
                f"a={a.is_safe(x)}, b={b.is_safe(x)}"
            )

    def test_the_budget_row_intersects_exactly_despite_being_bilinear(self):
        """h1 = B - p*q is bilinear in x but *linear in B*, which is why the
        componentwise min is the exact intersection rather than a conservative
        inner bound."""
        a = Contract(budget=100.0, cost_floor=0.0, q_min=0.0, q_max=1e6,
                     deadline_active=False)
        b = Contract(budget=60.0, cost_floor=0.0, q_min=0.0, q_max=1e6,
                     deadline_active=False)
        m = a.meet(b)
        assert m.budget == pytest.approx(60.0)
        # The binding point of the tighter budget is on the meet's boundary,
        # so nothing admissible under both has been given away.
        assert m.is_safe(np.array([6.0, 10.0, 0.0]))       # p*q = 60
        assert not m.is_safe(np.array([6.01, 10.0, 0.0]))  # p*q = 60.1


class TestTheMeetCanBeUnsatisfiable:
    def test_two_satisfiable_contracts_can_have_no_common_ground(self):
        """Not a defect — it is the composition reporting that the parties
        agreed something the mandate forbids entirely. Handled as any other
        unsatisfiable theta (limitation B4)."""
        cheap = Contract(budget=50.0, cost_floor=1.0, q_min=10.0, q_max=20.0,
                         deadline_active=False)
        dear = Contract(budget=500.0, cost_floor=9.0, q_min=10.0, q_max=20.0,
                        deadline_active=False)
        assert cheap.is_satisfiable() and dear.is_satisfiable()
        m = cheap.meet(dear)          # B = 50, c = 9, q_min = 10 -> 90 > 50
        assert not m.is_satisfiable()

    def test_a_zero_margin_meet_is_satisfiable_not_a_rounding_casualty(self):
        """The `bargain_3_9` case: the buyer states its budget verbatim, so
        c_negotiated = B_mandate / q_min *exactly* and the meet's safe set is a
        single price. It must not be classed unsatisfiable by float noise."""
        m = Contract(budget=31.38, cost_floor=10.46, q_min=3.0, q_max=6.0,
                     deadline_active=False)
        assert m.cost_floor * m.q_min == pytest.approx(m.budget)
        assert m.is_satisfiable()
        assert m.is_safe(np.array([10.46, 3.0, 0.0]))


class TestTheMeetNeedsAnOpeningProjection:
    """Why arm C-meet re-projects when theta is agreed, and arm C need not.

    A DCBF governs *transitions*: from inside C it gives forward invariance,
    from outside only geometric recovery (limitation B2). A negotiated contract
    comes into existence part-way through a negotiation, so whether the state
    is inside it at that moment decides whether the guarantee holds.
    """

    ASK, QTY = 6.755, 2.0
    OFFER = 5.79
    MANDATE = Contract(budget=11.58, cost_floor=5.27, q_min=2.0, q_max=4.0,
                       deadline_active=False)

    def envelope(self) -> Contract:
        return Contract(budget=self.ASK * self.QTY, cost_floor=self.OFFER,
                        q_min=self.MANDATE.q_min, q_max=self.MANDATE.q_max,
                        deadline_active=False)

    def test_the_envelope_contains_the_opening_ask_by_construction(self):
        """So for arm C the freeze-time projection is a provable no-op, and
        arm C's published 0/136 is unaffected by adding it."""
        x_ask = np.array([self.ASK, self.QTY, 0.0])
        env = self.envelope()
        assert env.h(x_ask)[0] == pytest.approx(0.0)   # exactly on the budget row
        assert env.is_safe(x_ask)

    def test_the_meet_does_not_contain_the_opening_ask(self):
        """Which is why arm C-meet must project: the contract is born with the
        state already outside it."""
        m = self.envelope().meet(self.MANDATE)
        assert not m.is_safe(np.array([self.ASK, self.QTY, 0.0]))
        assert m.budget == pytest.approx(11.58)
        assert m.cost_floor == pytest.approx(5.79)

    def test_recovery_from_outside_still_breaches(self):
        """The measured failure, as arithmetic: the DCBF condition is met and
        the terms are still inadmissible."""
        m = self.envelope().meet(self.MANDATE)
        gamma = 0.4
        h_prev = m.h(np.array([self.ASK, self.QTY, 0.0]))[0]
        h_applied = m.h(np.array([6.165, self.QTY, 0.0]))[0]
        assert h_prev == pytest.approx(-1.93)
        assert h_applied == pytest.approx(-0.75)
        assert h_applied >= (1 - gamma) * h_prev      # DCBF satisfied
        assert h_applied < 0                          # and still in breach

    def test_the_meets_safe_set_is_a_single_price_on_this_scenario(self):
        """The buyer states its budget verbatim, so c_meet * q_min = B_meet to
        the cent and only one price is admissible — arm B's funnel point."""
        m = self.envelope().meet(self.MANDATE)
        assert m.cost_floor * m.q_min == pytest.approx(m.budget)
        assert m.is_satisfiable()
        assert m.is_safe(np.array([5.79, 2.0, 0.0]))
        assert not m.is_safe(np.array([5.80, 2.0, 0.0]))
