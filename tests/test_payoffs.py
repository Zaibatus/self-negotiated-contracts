"""Preferences and the bargaining benchmark.

The closed-form Nash bargaining solution is the economic ground truth
everything else is measured against, so it is checked against an independent
numerical maximisation of the Nash product rather than against itself. And the
one structural fact Proposition 1 rests on — that price is a pure transfer, so
joint surplus does not depend on it — is asserted directly, because if it ever
stopped holding the proposition would fail silently and Phi would still look
like a perfectly well-behaved merit function.
"""

from __future__ import annotations

import numpy as np
import pytest
from magentic_marketplace.marketplace.shared.models import Business, Customer
from scipy.optimize import minimize

from src.payoffs import SCALE, PayoffModel, dist_M, norm_M


def make_business(**overrides) -> Business:
    data = {
        "id": "business_0001",
        "name": "Test Cantina",
        "description": "A test business.",
        "rating": 1.0,
        "progenitor_customer": "customer_0001",
        "menu_features": {"Tacos": 10.0, "Agua": 4.0},
        "amenity_features": {"Outdoor Seating": True},
        "min_price_factor": 0.6,
    }
    data.update(overrides)
    return Business.model_validate(data)


def make_customer(**overrides) -> Customer:
    data = {
        "id": "customer_0001",
        "name": "Test Buyer",
        "request": "Tacos and an agua.",
        "menu_features": {"Tacos": 9.0, "Agua": 3.5},
        "amenity_features": ["Outdoor Seating"],
    }
    data.update(overrides)
    return Customer.model_validate(data)


@pytest.fixture(scope="module")
def model() -> PayoffModel:
    return PayoffModel()


class TestTheMetric:
    def test_one_scaled_unit_is_a_pound_ten_units_or_five_days(self):
        np.testing.assert_allclose(SCALE, [1.0, 10.0, 5.0])
        assert dist_M(np.zeros(3), np.array([1.0, 0.0, 0.0])) == pytest.approx(1.0)
        assert dist_M(np.zeros(3), np.array([0.0, 10.0, 0.0])) == pytest.approx(1.0)
        assert dist_M(np.zeros(3), np.array([0.0, 0.0, 5.0])) == pytest.approx(1.0)

    def test_gradients_use_the_dual_norm(self):
        """Terms scale down where gradients scale up, so the pairing is
        invariant — otherwise ||grad|| and ||x|| would not compose."""
        assert norm_M(np.array([0.0, 0.1, 0.0])) == pytest.approx(1.0)


class TestUtilities:
    def test_joint_surplus_does_not_depend_on_price(self, model):
        """The fact Prop. 1 is built on: price is a pure transfer."""
        base = np.array([8.5, 100.0, 26.0])
        for price in (5.0, 8.5, 12.0, 20.0):
            moved = base.copy()
            moved[0] = price
            assert model.surplus(moved) == pytest.approx(model.surplus(base))

    def test_price_moves_utility_between_the_parties_one_for_one(self, model):
        x = np.array([8.5, 100.0, 26.0])
        y = x.copy()
        y[0] += 1.0
        assert model.u_buyer(y) - model.u_buyer(x) == pytest.approx(-100.0)
        assert model.u_seller(y) - model.u_seller(x) == pytest.approx(100.0)

    def test_deactivating_the_deadline_removes_its_penalty(self):
        with_d = PayoffModel(deadline_active=True)
        without = PayoffModel(deadline_active=False)
        x = np.array([8.5, 100.0, 3.0])  # far from either ideal deadline
        assert with_d.u_buyer(x) < without.u_buyer(x)
        # And it stops mattering at all.
        y = x.copy()
        y[2] = 44.0
        assert without.u_buyer(y) == pytest.approx(without.u_buyer(x))


class TestNashBargainingSolution:
    def test_closed_form_matches_numerical_nash_product_maximisation(self, model):
        """Independent check: the formulation reports agreement to 9.1e-6."""
        x_closed, _ = model.nash_bargaining_solution()

        def negative_log_nash_product(x: np.ndarray) -> float:
            ub, us = model.u_buyer(x), model.u_seller(x)
            if ub <= 0 or us <= 0:
                return 1e6 - ub - us
            return -(np.log(ub) + np.log(us))

        bounds = [(6.0, 12.0), (20.0, 120.0), (7.0, 45.0)]
        best, arg = np.inf, None
        for seed in range(6):
            rng = np.random.default_rng(seed)
            start = np.array([rng.uniform(lo, hi) for lo, hi in bounds])
            res = minimize(
                negative_log_nash_product,
                start,
                bounds=bounds,
                method="SLSQP",
                options={"maxiter": 500, "ftol": 1e-12},
            )
            if res.fun < best:
                best, arg = res.fun, res.x

        assert arg is not None
        np.testing.assert_allclose(arg, x_closed, atol=1e-3)

    def test_the_reference_calibration_reproduces_the_paper(self, model):
        x_star, w_max = model.nash_bargaining_solution()
        np.testing.assert_allclose(x_star, [8.5, 100.0, 26.0], atol=1e-9)
        assert w_max == pytest.approx(241.20, abs=0.01)
        assert model.u_buyer(x_star) == pytest.approx(120.60, abs=0.01)
        assert model.u_seller(x_star) == pytest.approx(120.60, abs=0.01)

    def test_the_split_is_equal_and_the_allocation_efficient(self, model):
        x_star, w_max = model.nash_bargaining_solution()
        assert model.u_buyer(x_star) == pytest.approx(model.u_seller(x_star))
        assert x_star[1] == pytest.approx(model.efficient_quantity())
        assert x_star[2] == pytest.approx(model.efficient_deadline())
        # Efficient really is the surplus maximiser.
        for delta in (-5.0, 5.0):
            moved = x_star.copy()
            moved[1] += delta
            assert model.surplus(moved) < w_max


class TestScenarioCalibration:
    def test_efficient_quantity_lands_on_what_the_customer_asked_for(self):
        """Anchoring q_eff to the requested basket is the honest reading of a
        marketplace request: the customer asked for that much because that is
        what they want."""
        model = PayoffModel.from_scenario(make_business(), make_customer())
        assert model.efficient_quantity() == pytest.approx(2.0)
        x_star, _ = model.nash_bargaining_solution()
        assert x_star[1] == pytest.approx(2.0)

    def test_marginal_cost_comes_from_min_price_factor(self):
        model = PayoffModel.from_scenario(make_business(), make_customer())
        assert model.c == pytest.approx(0.6 * (10.0 + 4.0) / 2)

    def test_the_agreed_price_sits_inside_the_bargaining_zone(self):
        model = PayoffModel.from_scenario(make_business(), make_customer())
        x_star, w_max = model.nash_bargaining_solution()
        reservation = (9.0 + 3.5) / 2
        assert w_max > 0
        assert model.c < x_star[0] < reservation

    def test_a_pair_with_no_bargaining_zone_is_rejected(self):
        """Reservation at or below marginal cost: any deal destroys surplus,
        and a calibration fitted to it would return a negative-surplus Nash
        solution that looks like a number."""
        expensive = make_business(min_price_factor=1.0)
        with pytest.raises(ValueError, match="no bargaining zone"):
            PayoffModel.from_scenario(expensive, make_customer())

    def test_a_pair_with_no_shared_items_is_rejected(self):
        with pytest.raises(ValueError, match="stocks none of"):
            PayoffModel.from_scenario(
                make_business(), make_customer(menu_features={"Nothing": 5.0})
            )

    def test_the_deadline_is_off_unless_asked_for(self):
        """Scenario data says nothing about delivery preferences, so switching
        the deadline on means supplying them from somewhere else."""
        assert not PayoffModel.from_scenario(
            make_business(), make_customer()
        ).deadline_active

    def test_acceptance_temperature_scales_with_the_surplus(self):
        model = PayoffModel.from_scenario(make_business(), make_customer())
        _, w_max = model.nash_bargaining_solution()
        assert model.lam == pytest.approx(w_max / 4.0)
        # And it is a real probability at the deal, not a saturated one.
        x_star, _ = model.nash_bargaining_solution()
        assert 0.5 < model.p_accept(x_star) < 1.0

    def test_provenance_records_the_modelling_choice(self):
        model = PayoffModel.from_scenario(make_business(), make_customer())
        assert "curvature_is_a_modelling_choice" in model.provenance
        assert model.provenance["business"] == "business_0001"


class TestGradients:
    def test_finite_differences_agree_with_a_tighter_step(self, model):
        x = np.array([9.0, 90.0, 30.0])
        for role in ("buyer", "seller"):
            coarse = model.grad_u_hat(x, role, h=1e-5)
            fine = model.grad_u_hat(x, role, h=1e-6)
            np.testing.assert_allclose(coarse, fine, rtol=1e-4, atol=1e-7)

    def test_the_field_is_the_sum_of_the_two_gradients(self, model):
        x = np.array([9.0, 90.0, 30.0])
        np.testing.assert_allclose(
            model.concession_field(x),
            model.grad_u_hat(x, "buyer") + model.grad_u_hat(x, "seller"),
        )
