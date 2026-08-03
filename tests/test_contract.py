"""Unit tests for the Contract schema (theta) and its safe set. No API calls."""

from __future__ import annotations

import numpy as np
import pytest
from magentic_marketplace.marketplace.shared.models import Business, Customer

from src.contract import N_ROWS, Contract, ContractSpec, ControllerSpec


def make_business(**overrides) -> Business:
    data = {
        "id": "business_0001",
        "name": "Test Cantina",
        "description": "A test business.",
        "rating": 1.0,
        "progenitor_customer": "customer_0001",
        "menu_features": {"Tacos": 10.0, "Agua": 4.0},
        "amenity_features": {"Outdoor Seating": True},
        "min_price_factor": 0.75,
    }
    data.update(overrides)
    return Business.model_validate(data)


def make_customer(**overrides) -> Customer:
    data = {
        "id": "customer_0001",
        "name": "Test Buyer",
        "request": "I would like tacos and an agua.",
        "menu_features": {"Tacos": 9.0, "Agua": 3.5},
        "amenity_features": ["Outdoor Seating"],
    }
    data.update(overrides)
    return Customer.model_validate(data)


class TestConstraints:
    def test_h_matches_the_template(self):
        contract = Contract(
            budget=1000.0,
            cost_floor=6.0,
            q_min=20.0,
            q_max=120.0,
            d_min=7.0,
            d_max=45.0,
            deadline_active=True,
        )
        h = contract.h(np.array([9.0, 90.0, 30.0]))
        assert h.shape == (N_ROWS,)
        np.testing.assert_allclose(h, [1000 - 810, 3.0, 70.0, 30.0, 23.0, 15.0])

    def test_budget_row_is_bilinear_not_linearised(self):
        contract = Contract(budget=100.0, cost_floor=1.0, q_min=1.0, q_max=100.0)
        # Doubling both price and quantity quadruples spend: only the exact
        # form gets this right.
        assert contract.h(np.array([2.0, 10.0, 0.0]))[0] == pytest.approx(80.0)
        assert contract.h(np.array([4.0, 20.0, 0.0]))[0] == pytest.approx(20.0)

    def test_grad_h_is_the_jacobian_at_x(self):
        contract = Contract(budget=100.0, cost_floor=1.0, q_min=1.0, q_max=100.0)
        x = np.array([3.0, 7.0, 2.0])
        jac = contract.grad_h(x)
        eps = 1e-6
        for dim in range(3):
            step = np.zeros(3)
            step[dim] = eps
            numeric = (contract.h(x + step) - contract.h(x - step)) / (2 * eps)
            np.testing.assert_allclose(jac[:, dim], numeric, atol=1e-6)

    def test_deadline_rows_deactivate(self):
        contract = Contract(
            budget=100.0, cost_floor=1.0, q_min=1.0, q_max=100.0, deadline_active=True
        )
        assert contract.active_labels() == [
            "budget",
            "cost_floor",
            "q_min",
            "q_max",
            "d_min",
            "d_max",
        ]
        assert contract.without_deadline().active_labels() == [
            "budget",
            "cost_floor",
            "q_min",
            "q_max",
        ]

    def test_inactive_rows_do_not_count_as_violations(self):
        contract = Contract(
            budget=100.0,
            cost_floor=1.0,
            q_min=1.0,
            q_max=100.0,
            d_min=5.0,
            d_max=9.0,
            deadline_active=True,
        )
        x = np.array([2.0, 3.0, 0.0])  # deadline 0 breaches d_min
        assert contract.violations(x) == ["d_min"]
        assert contract.without_deadline().violations(x) == []
        assert contract.without_deadline().is_safe(x)


class TestSatisfiability:
    def test_feasible_when_floor_fits_under_budget(self):
        assert Contract(
            budget=100.0, cost_floor=5.0, q_min=10.0, q_max=20.0
        ).is_satisfiable()

    def test_infeasible_when_floor_exceeds_budget(self):
        # c * q_min = 60 > B = 50: no price satisfies both rows at any quantity.
        assert not Contract(
            budget=50.0, cost_floor=6.0, q_min=10.0, q_max=20.0
        ).is_satisfiable()

    def test_infeasible_contract_has_no_safe_point(self):
        """The closed-form check agrees with brute force."""
        contract = Contract(budget=50.0, cost_floor=6.0, q_min=10.0, q_max=20.0)
        rng = np.random.default_rng(0)
        for _ in range(2000):
            x = np.array([rng.uniform(0.0, 20.0), rng.uniform(5.0, 25.0), 0.0])
            assert not contract.is_safe(x)

    def test_feasible_contract_has_a_safe_point(self):
        contract = Contract(budget=100.0, cost_floor=5.0, q_min=10.0, q_max=20.0)
        assert contract.is_safe(
            np.array([contract.budget / contract.q_min, contract.q_min, 0.0])
        )

    def test_inverted_quantity_band_is_infeasible(self):
        assert not Contract(
            budget=1e9, cost_floor=0.0, q_min=20.0, q_max=10.0
        ).is_satisfiable()


class TestFromScenario:
    def test_theta_comes_from_the_data(self):
        contract = Contract.from_scenario(make_business(), make_customer())
        # B is the customer's reservation total.
        assert contract.budget == pytest.approx(12.5)
        # c is the quantity-weighted mean of min_price_factor * list price —
        # min_price_factor is the field the marketplace itself never reads.
        assert contract.cost_floor == pytest.approx(0.75 * (10.0 + 4.0) / 2)
        assert contract.q_min == pytest.approx(2.0)
        assert contract.q_max == pytest.approx(4.0)

    def test_quantities_are_honoured(self):
        contract = Contract.from_scenario(
            make_business(), make_customer(), quantities={"Tacos": 3}
        )
        assert contract.q_min == pytest.approx(4.0)
        assert contract.budget == pytest.approx(9.0 * 3 + 3.5)

    def test_items_the_business_does_not_stock_are_skipped(self):
        customer = make_customer(
            menu_features={"Tacos": 9.0, "Something Else Entirely": 5.0}
        )
        contract = Contract.from_scenario(make_business(), customer)
        assert contract.q_min == pytest.approx(1.0)
        assert contract.notes["items_missing"] == "Something Else Entirely"

    def test_pair_with_no_shared_items_is_rejected_not_defaulted(self):
        customer = make_customer(menu_features={"Nothing In Common": 5.0})
        with pytest.raises(ValueError, match="stocks none of the items"):
            Contract.from_scenario(make_business(), customer)

    def test_spec_knobs_flow_through(self):
        spec = ContractSpec(
            q_max_factor=3.0,
            deadline_active=True,
            d_max=14.0,
            budget_slack=0.1,
        )
        contract = Contract.from_scenario(make_business(), make_customer(), spec)
        assert contract.q_max == pytest.approx(6.0)
        assert contract.d_max == pytest.approx(14.0)
        assert contract.budget == pytest.approx(12.5 * 1.1)
        assert contract.deadline_active

    def test_theta_is_six_dimensional_and_carries_no_controller_state(self):
        """theta is the agreement; gamma and tau are how it is enforced.

        Putting T_max in theta would make two contracts with the same safe set
        and different deadlines incomparable under the refinement order, which
        is a statement about sets of terms.
        """
        contract = Contract.from_scenario(make_business(), make_customer())
        assert contract.theta.shape == (6,)
        assert contract.h(np.array([5.0, 2.0, 0.0])).shape == (N_ROWS,)


class TestControllerSpec:
    """(gamma, tau) — the controller half of C = (theta, gamma, tau)."""

    def test_friction_escalates_without_bound_as_t_max_approaches(self):
        """Prop. 2: no constant friction works, so kappa must grow.

        This is what turns termination from an assumption into a theorem —
        whatever residual incentive remains, friction eventually exceeds it.
        """
        spec = ControllerSpec(t_max=10, kappa0=2.0)
        schedule = [spec.kappa(k) for k in range(11)]
        assert schedule[0] == pytest.approx(2.0)
        assert all(b >= a for a, b in zip(schedule, schedule[1:]))
        assert schedule[-1] > 100 * schedule[0]

    def test_a_zero_deadline_admits_no_motion_at_all(self):
        assert ControllerSpec(t_max=0).kappa(0) == float("inf")

    def test_refinement_order_is_subset_of_safe_sets(self):
        loose = Contract(budget=1000.0, cost_floor=5.0, q_min=10.0, q_max=100.0)
        strict = Contract(budget=900.0, cost_floor=6.0, q_min=20.0, q_max=90.0)
        assert strict.refines(loose)
        assert not loose.refines(strict)

    def test_refinement_agrees_with_set_containment(self):
        loose = Contract(budget=1000.0, cost_floor=5.0, q_min=10.0, q_max=100.0)
        strict = Contract(budget=900.0, cost_floor=6.0, q_min=20.0, q_max=90.0)
        rng = np.random.default_rng(1)
        for _ in range(2000):
            x = np.array([rng.uniform(0, 20), rng.uniform(5, 120), 0.0])
            if strict.is_safe(x):
                assert loose.is_safe(x)
