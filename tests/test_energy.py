"""The convergence layer: anchor-free energy, decay estimators, liveness.

The headline property under test is the one that motivates the whole
equilibrium-independent apparatus: G reaches zero at the constrained
equilibrium *without being told where that is*, including when a coupling
clause has moved the equilibrium to the generalised Nash point, where an
anchored certificate plateaus at its own squared anchor error.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.certificates.dcbf import DCBFFilter
from src.certificates.energy import (
    ConcessionModel,
    contraction_transient,
    drift_outside_ball,
    g_lookahead,
    g_realised,
    g_realised_series,
    roundpair_lookahead,
)
from src.certificates.metrics import time_to_contract
from src.contract import Contract

BUYER = ConcessionModel(rate=np.full(3, 0.25), target=np.array([6.5, 110.0, 40.0]))
SELLER = ConcessionModel(rate=np.full(3, 0.25), target=np.array([11.5, 60.0, 12.0]))


def contract(**overrides) -> Contract:
    data = {
        "budget": 100000.0,  # slack, so the barrier does not bind
        "cost_floor": 0.0,
        "q_min": 0.0,
        "q_max": 1e6,
        "deadline_active": False,
    }
    data.update(overrides)
    return Contract(**data)


class TestRealisedEnergy:
    def test_it_is_a_round_pair_displacement(self):
        traj = [np.array([1.0, 0.0, 0.0]), np.array([5.0, 0.0, 0.0]),
                np.array([4.0, 0.0, 0.0])]
        assert g_realised(traj, 0) == pytest.approx(9.0)

    def test_an_incomplete_pair_raises_rather_than_shrinking_the_window(self):
        """A short window would report a smaller energy, i.e. false progress."""
        traj = [np.array([1.0, 0.0, 0.0]), np.array([5.0, 0.0, 0.0])]
        with pytest.raises(IndexError):
            g_realised(traj, 0)

    def test_a_settled_negotiation_has_zero_energy(self):
        traj = [np.array([3.0, 2.0, 1.0])] * 5
        assert g_realised_series({"pair": traj}) == [0.0, 0.0, 0.0]

    def test_market_energy_is_the_sum_over_pairs(self):
        a = [np.zeros(3), np.zeros(3), np.array([2.0, 0.0, 0.0])]
        b = [np.zeros(3), np.zeros(3), np.array([0.0, 3.0, 0.0])]
        assert g_realised_series({"a": a, "b": b}) == [pytest.approx(13.0)]

    def test_pairs_of_unequal_length_contribute_while_they_last(self):
        short = [np.zeros(3), np.zeros(3), np.array([1.0, 0.0, 0.0])]
        long = [np.zeros(3)] * 5
        series = g_realised_series({"s": short, "l": long})
        assert len(series) == 3
        assert series[0] == pytest.approx(1.0)


class TestConcessionModel:
    def test_it_recovers_the_rate_and_target_it_generated(self):
        rate, target = 0.3, np.array([10.0, 50.0, 5.0])
        states = [np.array([2.0, 90.0, 30.0])]
        for _ in range(8):
            states.append(states[-1] + rate * (target - states[-1]))
        fitted = ConcessionModel.fit(states)
        np.testing.assert_allclose(fitted.rate, rate, atol=1e-6)
        np.testing.assert_allclose(fitted.target, target, atol=1e-5)

    def test_a_static_dimension_gets_a_zero_rate_not_an_extrapolation(self):
        states = [np.array([5.0, 10.0, 0.0]),
                  np.array([5.0, 12.0, 0.0]),
                  np.array([5.0, 13.6, 0.0]),
                  np.array([5.0, 14.88, 0.0])]
        fitted = ConcessionModel.fit(states)
        assert fitted.rate[0] == 0.0
        assert fitted.target[0] == pytest.approx(5.0)
        assert fitted.rate[1] > 0.0

    def test_too_few_observations_is_an_error_not_a_guess(self):
        with pytest.raises(ValueError, match="at least 3"):
            ConcessionModel.fit([np.zeros(3), np.ones(3)])


class TestLookaheadEnergy:
    def test_it_vanishes_exactly_at_the_fixed_point(self):
        con = contract()
        dcbf = DCBFFilter(gamma=1.0)
        xs = [np.array([9.0, 90.0, 30.0])]
        for _ in range(400):
            xs = roundpair_lookahead(xs, [con], (BUYER, SELLER), dcbf)
        assert g_lookahead(xs, [con], (BUYER, SELLER), dcbf) < 1e-9

    def test_it_decays_monotonically_towards_that_point(self):
        con = contract()
        dcbf = DCBFFilter(gamma=1.0)
        xs = [np.array([9.0, 90.0, 30.0])]
        energies = []
        for _ in range(30):
            energies.append(g_lookahead(xs, [con], (BUYER, SELLER), dcbf))
            xs = roundpair_lookahead(xs, [con], (BUYER, SELLER), dcbf)
        assert np.all(np.diff(energies) < 1e-9)

    def test_the_filter_inside_the_rollout_moves_the_zero_set(self):
        """With a binding constraint, G vanishes at the *constrained* point.

        This is the property that makes the energy anchor-free: nobody had to
        compute where the constrained equilibrium is, and it is not where the
        unconstrained one is.
        """
        dcbf = DCBFFilter(gamma=1.0)
        free, bound = contract(), contract(q_max=70.0)

        xs_free = [np.array([9.0, 90.0, 30.0])]
        xs_bound = [np.array([9.0, 90.0, 30.0])]
        for _ in range(400):
            xs_free = roundpair_lookahead(xs_free, [free], (BUYER, SELLER), dcbf)
            xs_bound = roundpair_lookahead(xs_bound, [bound], (BUYER, SELLER), dcbf)

        assert g_lookahead(xs_bound, [bound], (BUYER, SELLER), dcbf) < 1e-9
        # The constrained equilibrium is genuinely elsewhere...
        assert abs(xs_bound[0][1] - xs_free[0][1]) > 1.0
        # ...and it sits on the boundary the contract imposes.
        assert xs_bound[0][1] <= 70.0 + 1e-6
        # An energy anchored at the unconstrained point would read non-zero
        # here — that is the failure mode being avoided.
        assert np.sum((xs_bound[0] - xs_free[0]) ** 2) > 1.0


class TestDecayEstimators:
    def test_transient_fit_recovers_a_known_rate(self):
        rate = 0.4
        values = [100.0 * rate**k for k in range(12)]
        assert contraction_transient(values) == pytest.approx(rate, rel=1e-6)

    def test_the_noise_floor_is_excluded_from_the_fit(self):
        """A plateau must not be allowed to masquerade as slow contraction.

        Fitting the whole series, plateau included, is the error the audit
        caught; the transient-only estimator is the fix.
        """
        rate = 0.4
        values = [100.0 * rate**k for k in range(8)] + [0.05] * 20
        assert contraction_transient(values) == pytest.approx(rate, rel=1e-3)

    def test_too_short_a_series_is_an_error(self):
        with pytest.raises(ValueError, match="at least 3"):
            contraction_transient([1.0, 0.5])

    def test_drift_recovers_alpha_and_beta(self):
        alpha, beta = 0.3, 4.0
        values = [200.0]
        for _ in range(40):
            values.append((1 - alpha) * values[-1] + beta)
        fit = drift_outside_ball(values)
        assert fit["alpha"] == pytest.approx(alpha, rel=1e-6)
        assert fit["beta"] == pytest.approx(beta, rel=1e-6)
        assert fit["ball_radius"] == pytest.approx(beta / alpha, rel=1e-6)


class TestLiveness:
    def test_a_certified_bound_inside_t_max_is_honoured(self):
        cert = time_to_contract(g_initial=100.0, contraction=0.3, t_max=20)
        assert cert.certified_round_pairs == pytest.approx(
            np.log(100.0 / 1e-3) / np.log(1 / 0.3)
        )
        assert cert.certified_rounds == pytest.approx(2 * cert.certified_round_pairs)
        assert cert.honoured

    def test_a_bound_exceeding_t_max_is_not_honoured(self):
        cert = time_to_contract(g_initial=1e6, contraction=0.95, t_max=12)
        assert not cert.honoured
        assert cert.certified_rounds > 12

    def test_non_contracting_dynamics_yield_no_certificate(self):
        """The honest output is 'no bound', not a large number."""
        cert = time_to_contract(g_initial=100.0, contraction=1.02, t_max=12)
        assert cert.certified_rounds is None
        assert not cert.honoured
        assert "not in (0, 1)" in cert.reason

    def test_realised_length_is_compared_against_the_bound(self):
        cert = time_to_contract(
            g_initial=100.0, contraction=0.3, t_max=40, realised_rounds=6
        )
        assert cert.realised_within_bound is True
