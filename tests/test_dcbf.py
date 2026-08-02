"""The safety layer's guarantee, asserted on the TRUE constraint.

The point of these tests is that they check the property the thesis claims —
forward invariance of C(theta) under the exact bilinear h — rather than the
property the QP happens to enforce, which is the same condition on a
per-round linearisation. Those two come apart precisely on the large jumps
that formulation.md section 7.4 names as the attack surface, so testing the
linearised version would test around the interesting case.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.certificates.dcbf import (
    SHARED_CAPACITY_LABEL,
    DCBFFilter,
    build_rows,
    project_into_safe_set,
)
from src.contract import Contract

GAMMA = 0.4


def contract(**overrides) -> Contract:
    data = {
        "budget": 1000.0,
        "cost_floor": 6.0,
        "q_min": 20.0,
        "q_max": 120.0,
        "d_min": 7.0,
        "d_max": 45.0,
        "deadline_active": True,
    }
    data.update(overrides)
    return Contract(**data)


class TestInvariance:
    def test_no_breach_of_the_true_h_under_aggressive_proposals(self):
        """500 random steps, 20% of them wild overshoots: zero breaches."""
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        rng = np.random.default_rng(7)
        x = np.array([9.0, 90.0, 30.0])
        assert con.is_safe(x)

        for _ in range(500):
            u_prop = rng.normal(0.0, 3.0, 3)
            if rng.random() < 0.2:
                u_prop *= rng.uniform(5.0, 15.0)
            result = filt.step([x], [u_prop], [con])
            x = x + result.u
            assert con.is_safe(x), f"breached at {x} on rows {con.violations(x)}"

    def test_dcbf_inequality_holds_on_the_true_h(self):
        """h_i(x_{k+1}) >= (1 - gamma) h_i(x_k) - slack, exactly."""
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        rng = np.random.default_rng(11)
        x = np.array([9.0, 90.0, 30.0])

        for _ in range(200):
            u_prop = rng.normal(0.0, 4.0, 3)
            h_before = con.h(x)[con.active_mask()]
            result = filt.step([x], [u_prop], [con])
            x = x + result.u
            h_after = con.h(x)[con.active_mask()]
            assert np.all(h_after >= (1 - GAMMA) * h_before - result.slack - 1e-6)

    def test_the_linearisation_gap_is_real_and_is_caught(self):
        """A step that satisfies the linearised row and breaks the true one.

        The gap opens when price and quantity both rise: the second-order term
        of B - p*q is -dp*dq, so the linearisation *overestimates* remaining
        budget in exactly that quadrant. Here

            h1 = 190, linearised h1 after = 190 - 90(1) - 9(11) = 1 >= 0,
            true      h1 after = 1000 - 10 * 101              = -10 < 0,

        so the QP passes the proposal through untouched and the contract is
        breached. Without backtracking that breach lands; with it, it does not.
        If this ever stops failing on the unbacktracked filter, the
        backtracking has become dead code and should be deleted rather than
        kept as decoration.
        """
        con = contract(budget=1000.0)
        x = np.array([9.0, 90.0, 30.0])  # spend 810, headroom 190
        u_prop = np.array([1.0, 11.0, 0.0])

        naive = DCBFFilter(gamma=1.0, backtrack=False).step([x], [u_prop], [con])
        careful = DCBFFilter(gamma=1.0, backtrack=True).step([x], [u_prop], [con])

        # The linearised filter finds nothing to correct.
        np.testing.assert_allclose(naive.u, u_prop, atol=1e-5)
        assert not con.is_safe(x + naive.u), "linearisation gap did not appear"
        assert con.h(x + naive.u)[0] == pytest.approx(-10.0, abs=1e-3)

        assert con.is_safe(x + careful.u)
        assert careful.backtracks > 0

    def test_minimally_invasive_on_compliant_proposals(self):
        """A safe proposal is passed through untouched."""
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        x = np.array([9.0, 90.0, 30.0])
        u_prop = np.array([-0.1, -1.0, 0.5])
        result = filt.step([x], [u_prop], [con])
        np.testing.assert_allclose(result.u, u_prop, atol=1e-6)
        assert result.intervention < 1e-6


class TestRecovery:
    def test_geometric_recovery_from_outside_the_set(self):
        """From outside C the violation shrinks by (1 - gamma) per round.

        The bound is slack-aware: with a finite slack penalty the QP will buy a
        little degradation rather than lock up, and asserting the slack-free
        rate would be asserting a guarantee the design deliberately does not
        make.
        """
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        x = np.array([4.0, 90.0, 30.0])  # price below the cost floor
        assert not con.is_safe(x)

        cost_floor_row = con.active_labels().index("cost_floor")
        violation = initial = -con.h(x)[1]
        # 40 rounds at rate 0.6 takes a violation of 2.0 to ~2.6e-9, well
        # under the 1e-6 safety tolerance. 20 rounds would leave 7.3e-5 and
        # the set membership assertion below would fail for the right reason.
        for _ in range(40):
            result = filt.step([x], [np.zeros(3)], [con])
            slack = float(result.slack[cost_floor_row])
            x = x + result.u
            new_violation = max(-con.h(x)[1], 0.0)
            assert new_violation <= (1 - GAMMA) * violation + slack + 1e-6
            violation = new_violation
        assert violation <= (1 - GAMMA) ** 40 * initial + 1e-9
        assert con.is_safe(x)

    def test_projection_puts_an_opening_offer_inside_C(self):
        con = contract()
        for start in (
            np.array([4.0, 90.0, 30.0]),  # under the cost floor
            np.array([20.0, 110.0, 30.0]),  # way over budget (bilinear row)
            np.array([9.0, 5.0, 60.0]),  # under q_min and over d_max
        ):
            projected = project_into_safe_set(start, con)
            assert con.is_safe(projected), f"{start} -> {projected}"

    def test_projection_leaves_a_safe_point_alone(self):
        con = contract()
        x = np.array([9.0, 90.0, 30.0])
        np.testing.assert_allclose(project_into_safe_set(x, con), x)


class TestSolverHygiene:
    def test_every_call_reports_a_checked_status(self):
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        rng = np.random.default_rng(3)
        x = np.array([9.0, 90.0, 30.0])
        for _ in range(100):
            result = filt.step([x], [rng.normal(0, 5, 3)], [con])
            assert result.status, "a solver status must always be reported"
            x = x + result.u
        assert filt.reliability()["solver_failure_rate"] == 0.0

    def test_duals_are_nonnegative_shadow_prices(self):
        """OSQP's y is negative on active lower bounds; we report -y."""
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        x = np.array([6.05, 90.0, 30.0])  # hard against the cost floor
        result = filt.step([x], [np.array([-5.0, 0.0, 0.0])], [con])
        assert np.all(result.duals >= 0.0)
        # Pushing into the cost floor prices that row and nothing else.
        assert result.dual("0:cost_floor") > 0.0
        assert result.dual("0:q_max") == pytest.approx(0.0, abs=1e-6)

    def test_slack_keeps_the_filter_from_locking_up(self):
        """An unsatisfiable contract degrades gracefully instead of failing."""
        con = Contract(budget=50.0, cost_floor=6.0, q_min=10.0, q_max=20.0)
        assert not con.is_satisfiable()
        filt = DCBFFilter(gamma=GAMMA)
        result = filt.step([np.array([6.0, 10.0, 0.0])], [np.zeros(3)], [con])
        assert result.solved
        assert result.slack.sum() > 0.0

    def test_slsqp_path_still_runs_for_the_v1_comparison(self):
        con = contract()
        result = DCBFFilter(gamma=GAMMA, solver="slsqp").step(
            [np.array([9.0, 90.0, 30.0])], [np.array([1.0, 5.0, 0.0])], [con]
        )
        assert result.u.shape == (3,)
        # SLSQP gives no duals; we return zeros rather than a reconstruction
        # that would look like a measurement.
        assert np.all(result.duals == 0.0)

    def test_gamma_must_be_a_rate(self):
        with pytest.raises(ValueError, match="gamma"):
            DCBFFilter(gamma=0.0)
        with pytest.raises(ValueError, match="gamma"):
            DCBFFilter(gamma=1.5)


class TestComposition:
    def test_rows_stack_by_concatenation(self):
        con = contract()
        xs = [np.array([9.0, 90.0, 30.0]), np.array([8.0, 70.0, 25.0])]
        gmat, h0, labels = build_rows(xs, [con, con])
        assert gmat.shape == (12, 6)
        assert labels[0] == "0:budget" and labels[6] == "1:budget"
        # Pair 0's rows touch only pair 0's columns.
        assert np.all(gmat[:6, 3:] == 0.0)
        assert np.all(gmat[6:, :3] == 0.0)
        np.testing.assert_allclose(h0[:6], con.h(xs[0]))

    def test_coupling_clause_is_one_extra_row_touching_every_pair(self):
        con = contract()
        xs = [np.array([9.0, 90.0, 30.0]), np.array([8.0, 70.0, 25.0])]
        gmat, h0, labels = build_rows(xs, [con, con], shared_capacity=140.0)
        assert labels[-1] == SHARED_CAPACITY_LABEL
        np.testing.assert_allclose(gmat[-1], [0, -1, 0, 0, -1, 0])
        assert h0[-1] == pytest.approx(140.0 - 160.0)

    def test_binding_capacity_is_enforced_and_priced(self):
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        xs = [np.array([9.0, 60.0, 30.0]), np.array([8.0, 70.0, 25.0])]
        # Both pairs want more quantity; together they cannot have it.
        u_props = [np.array([0.0, 20.0, 0.0]), np.array([0.0, 20.0, 0.0])]
        result = filt.step(xs, u_props, [con, con], shared_capacity=140.0)

        new_total = sum(
            x[1] + result.u[3 * i + 1] for i, x in enumerate(xs)
        )
        assert new_total <= 140.0 + 1e-6
        assert result.dual(SHARED_CAPACITY_LABEL) > 0.0

    def test_slack_capacity_is_not_priced(self):
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        xs = [np.array([9.0, 60.0, 30.0]), np.array([8.0, 70.0, 25.0])]
        result = filt.step(
            xs, [np.zeros(3), np.zeros(3)], [con, con], shared_capacity=400.0
        )
        assert result.dual(SHARED_CAPACITY_LABEL) == pytest.approx(0.0, abs=1e-6)

    def test_scarcity_raises_the_shadow_price(self):
        """The dual of the coupling clause rises as capacity tightens."""
        con = contract()
        filt = DCBFFilter(gamma=GAMMA)
        xs = [np.array([9.0, 60.0, 30.0]), np.array([8.0, 70.0, 25.0])]
        u_props = [np.array([0.0, 20.0, 0.0]), np.array([0.0, 20.0, 0.0])]

        prices = [
            filt.step(xs, u_props, [con, con], shared_capacity=cap).dual(
                SHARED_CAPACITY_LABEL
            )
            for cap in (170.0, 150.0, 135.0)
        ]
        assert prices[0] < prices[1] < prices[2]
