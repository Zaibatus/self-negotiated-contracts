"""The §11 measurement layer: what the transcript can and cannot support.

The tests that matter here are the negative ones. An estimator that always
returns a number is worse than useless on five-round transcripts, so what is
asserted is that thin or one-sided data is *reported as such* rather than
silently producing a point estimate, and that a genuinely irrational agent
comes back marked inconsistent instead of being fitted anyway.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.marketplace_integration.payoff_estimation import (
    AcceptanceEvent,
    Round,
    assess_rationalizability,
    calibrate,
    fit_lambda,
    rounds_from_trajectory,
)
from src.payoffs import PayoffModel, norm_M


@pytest.fixture(scope="module")
def model() -> PayoffModel:
    return PayoffModel()


@pytest.fixture(scope="module")
def x_star(model: PayoffModel) -> np.ndarray:
    return model.nash_bargaining_solution()[0]


class TestLambdaFit:
    def test_it_recovers_a_lambda_it_generated(self, model, x_star):
        """Synthetic data from a known temperature, fitted back."""
        from dataclasses import replace

        truth = replace(model, lam=40.0)
        rng = np.random.default_rng(0)
        events = []
        for _ in range(400):
            x = x_star + rng.normal(0, 1, 3) * np.array([1.0, 10.0, 5.0])
            events.append(
                AcceptanceEvent(x=x, accepted=rng.random() < truth.p_accept(x))
            )
        fit = fit_lambda(model, events)
        assert fit.identified
        assert fit.lam == pytest.approx(40.0, rel=0.35)

    def test_one_sided_data_is_reported_as_unidentified(self, model, x_star):
        """Every event accepted: any lambda that makes acceptance likely fits."""
        events = [AcceptanceEvent(x=x_star, accepted=True) for _ in range(10)]
        fit = fit_lambda(model, events)
        assert not fit.identified
        assert "one-sided" in fit.reason
        assert fit.lam == model.lam  # falls back to the prior, not to the grid

    def test_no_events_keeps_the_prior(self, model):
        fit = fit_lambda(model, [])
        assert not fit.identified
        assert fit.lam == model.lam
        assert "no acceptance events" in fit.reason

    def test_calibrate_only_overrides_when_identified(self, model, x_star):
        thin = [AcceptanceEvent(x=x_star, accepted=True)]
        calibrated, fit = calibrate(model, thin)
        assert not fit.identified
        assert calibrated.lam == model.lam

    def test_the_profile_is_returned_so_flatness_is_visible(self, model, x_star):
        events = [AcceptanceEvent(x=x_star, accepted=True) for _ in range(5)]
        fit = fit_lambda(model, events)
        assert len(fit.profile) > 50


class TestRationalizability:
    def test_a_consistent_agent_yields_a_kappa_interval(self, model, x_star):
        """Stalls where the incentive is small, moves where it is large.

        Note which is which. The incentive is LARGER at the bargaining solution
        (79.56, the figure section 4 reports) than at a far start (16.63):
        gradients grow as the draft improves, because acceptance becomes likely
        and the deal becomes worth having. That is the mechanism behind
        Prop. 2, and it makes the naive fixture — "far from the deal means a
        big incentive" — exactly backwards.
        """
        far = np.array([11.0, 40.0, 40.0])
        rounds = [
            Round(  # moves, at the high-incentive point
                x_before=x_star, x_after=x_star + np.array([0.1, 0, 0]), role="buyer"
            ),
            Round(x_before=far, x_after=far, role="buyer"),  # stalls, low incentive
        ]
        assert norm_M(model.grad_u_hat(x_star, "buyer")) > norm_M(
            model.grad_u_hat(far, "buyer")
        )
        report = assess_rationalizability(model, rounds)
        assert report.consistent
        assert report.interval is not None
        lower, upper = report.interval
        assert lower < upper
        assert "consistent with cost-benefit" in report.describe()

    def test_an_inconsistent_agent_is_flagged_not_fitted(self, model, x_star):
        """Moves where the incentive is small, stalls where it is large.

        This is the outcome that would invalidate the transfer to LLM agents,
        so it must surface as a finding rather than as a fitted kappa.
        """
        far = np.array([11.0, 40.0, 40.0])
        rounds = [
            Round(  # stalls at the HIGH-incentive point
                x_before=x_star, x_after=x_star, role="buyer"
            ),
            Round(  # moves at the LOW-incentive point
                x_before=far, x_after=far + np.array([0.1, 0, 0]), role="buyer"
            ),
        ]
        report = assess_rationalizability(model, rounds)
        assert not report.consistent
        assert report.interval is None
        assert report.n_inconsistent_rounds > 0
        assert "NOT consistent" in report.describe()

    def test_all_moves_bounds_kappa_from_above_only(self, model, x_star):
        rounds = [
            Round(
                x_before=x_star, x_after=x_star + np.array([0.1, 0, 0]), role="buyer"
            )
        ]
        report = assess_rationalizability(model, rounds)
        assert report.consistent
        assert report.kappa_lower == 0.0
        assert np.isfinite(report.kappa_upper)

    def test_all_stalls_bounds_kappa_from_below_only(self, model):
        far = np.array([11.0, 40.0, 40.0])
        rounds = [Round(x_before=far, x_after=far, role="buyer")]
        report = assess_rationalizability(model, rounds)
        assert report.consistent
        assert report.kappa_upper == float("inf")
        assert report.kappa_lower > 0.0

    def test_no_rounds_is_reported_not_crashed(self, model):
        report = assess_rationalizability(model, [])
        assert report.n_rounds == 0
        assert "no rounds observed" in report.describe()

    def test_the_ordering_is_invariant_to_rho(self, model, x_star):
        far = np.array([11.0, 40.0, 40.0])
        rounds = [
            Round(
                x_before=x_star, x_after=x_star + np.array([0.1, 0, 0]), role="buyer"
            ),
            Round(x_before=far, x_after=far, role="buyer"),
        ]
        assert assess_rationalizability(model, rounds, rho=1.0).consistent
        assert assess_rationalizability(model, rounds, rho=0.5).consistent


class TestRoundsFromTrajectory:
    def test_roles_alternate_starting_with_the_seller(self):
        traj = [np.zeros(3), np.ones(3), 2 * np.ones(3), 3 * np.ones(3)]
        rounds = rounds_from_trajectory(traj)
        assert [r.role for r in rounds] == ["seller", "buyer", "seller"]

    def test_a_repeated_state_is_a_stall(self):
        x = np.array([8.5, 100.0, 26.0])
        rounds = rounds_from_trajectory([x, x.copy()])
        assert not rounds[0].moved
        assert rounds[0].displacement == pytest.approx(0.0)

    def test_displacement_is_in_scaled_units(self):
        a = np.array([8.5, 100.0, 26.0])
        b = a + np.array([0.0, 10.0, 0.0])
        assert rounds_from_trajectory([a, b])[0].displacement == pytest.approx(1.0)
