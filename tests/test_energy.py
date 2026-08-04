"""The two certificates, and the propositions they rest on.

These tests exist to pin the claims formulation.md v2 makes, so that a change
which quietly breaks one of them fails here rather than in a dissertation
chapter:

  * Prop. 1 — the zero of the concession field is the Nash bargaining
    solution, so Phi is a merit function for the *economic* equilibrium and
    not for an artefact of the update rule;
  * section 8 — under a binding constraint Phi does not vanish but Phi_proj
    does, which is what "anchor-free" has to mean once the agreement point has
    no closed form;
  * Prop. 2 — the termination threshold rises along an improving path, so no
    constant friction both permits progress and halts at the deal;
  * section 6.1 — the stability check is taken in the unit metric. Getting
    that wrong changes the headline number from -6.86 to -0.07 without
    changing any sign, which is exactly the kind of error that survives
    review.
"""

from __future__ import annotations

import numpy as np
import pytest

from src.certificates.energy import (
    _active_rows,
    contract_is_inside_monotone_region,
    contraction_transient,
    drift_outside_ball,
    friction_window,
    g_kappa,
    g_realised,
    g_realised_series,
    is_monotone,
    kappa_star,
    phi,
    phi_projected,
    project_onto_tangent_cone,
    stability_radius,
)
from src.contract import Contract, ControllerSpec
from src.payoffs import SCALE, PayoffModel

# The far start used throughout the formulation's experiments.
X0 = np.array([11.0, 40.0, 40.0])


@pytest.fixture(scope="module")
def model() -> PayoffModel:
    return PayoffModel()


@pytest.fixture(scope="module")
def x_star(model: PayoffModel) -> np.ndarray:
    return model.nash_bargaining_solution()[0]


class TestPhiIsAMeritFunctionForTheBargainingSolution:
    def test_phi_vanishes_at_the_nash_bargaining_solution(self, model, x_star):
        """Prop. 1. The formulation reports 6.4e-9."""
        assert phi(model, x_star) < 1e-7

    def test_phi_is_large_away_from_it(self, model):
        assert phi(model, X0) > 1.0

    def test_phi_tracks_distance_locally(self, model, x_star):
        """Locally Phi ~ L ||x - x*||, which is what a merit function needs.

        Not a distance, though: L is about 80 here, and Phi carries
        payoff-gradient units. Comparing Phi across differently calibrated
        negotiations would be meaningless.
        """
        previous = 0.0
        for radius in (0.05, 0.1, 0.2, 0.4):
            value = phi(model, x_star + radius * SCALE * np.array([1.0, 0.0, 0.0]))
            assert value > previous
            previous = value

    def test_the_field_is_a_sum_of_opposed_gradients(self, model, x_star):
        """At the deal each side still wants to move; only the sum vanishes.

        This is why one scalar cannot certify both convergence and
        termination, and therefore why there are two certificates.
        """
        from src.payoffs import norm_M

        assert norm_M(model.grad_u_hat(x_star, "buyer")) > 10.0
        assert norm_M(model.grad_u_hat(x_star, "seller")) > 10.0
        assert phi(model, x_star) < 1e-7


class TestProjectedCertificateUnderCoupling:
    """Section 8: the anchor-free claim, in the regime that motivates it."""

    @staticmethod
    def _binding_contract() -> Contract:
        # Unconstrained NBS spends 850, so a budget of 800 binds.
        return Contract(
            budget=800.0,
            cost_floor=6.0,
            q_min=20.0,
            q_max=120.0,
            d_min=7.0,
            d_max=45.0,
            deadline_active=True,
        )

    def test_projection_is_inert_when_nothing_is_active(self, model, x_star):
        loose = Contract(budget=1e6, cost_floor=0.0, q_min=0.0, q_max=1e6)
        assert phi_projected(model, x_star, loose) == pytest.approx(
            phi(model, x_star)
        )

    def test_on_the_boundary_the_projection_removes_the_absorbed_component(
        self, model
    ):
        """Phi stays large, Phi_proj drops: the field points into the budget."""
        contract = self._binding_contract()
        # A point exactly on the budget boundary, near the constrained deal.
        q = 94.249
        x = np.array([800.0 / q, q, 25.7])
        assert contract.h(x)[0] == pytest.approx(0.0, abs=1e-6)

        unprojected = phi(model, x)
        projected = phi_projected(model, x, contract)
        assert projected < unprojected
        assert projected < 2.0

    def test_a_constraint_the_field_points_away_from_is_left_alone(self, model):
        """Active but not binding on this motion — projecting it out would
        discard a real component of the field."""
        contract = Contract(
            budget=1e6, cost_floor=6.0, q_min=20.0, q_max=120.0
        )
        # Sit on q_min, where the field wants to increase q (into the set).
        x = np.array([8.5, 20.0, 26.0])
        assert contract.h(x)[2] == pytest.approx(0.0, abs=1e-9)
        assert model.concession_field(x)[1] > 0
        assert phi_projected(model, x, contract) == pytest.approx(phi(model, x))


class TestTerminationAndProposition2:
    def test_the_threshold_rises_along_an_improving_path(self, model, x_star):
        """kappa*(x_0) = 15.95 and kappa*(NBS) = 39.78 in the formulation."""
        rho = 0.5
        assert kappa_star(model, X0, rho) == pytest.approx(15.95, abs=0.05)
        assert kappa_star(model, x_star, rho) == pytest.approx(39.78, abs=0.05)

    def test_no_constant_friction_works(self, model):
        """Prop. 2, stated as a property of the measured window."""
        window = friction_window(model, X0, rho=0.5)
        assert not window.constant_friction_possible
        assert window.kappa_at_start < window.kappa_at_deal
        assert "escalating friction" in window.describe()

    def test_friction_below_the_start_threshold_permits_motion(self, model):
        window = friction_window(model, X0, rho=0.5)
        kappa = 0.5 * window.kappa_at_start
        assert g_kappa(model, X0, kappa, rho=0.5) > 0.0

    def test_friction_above_the_deal_threshold_freezes_the_start(self, model):
        window = friction_window(model, X0, rho=0.5)
        assert g_kappa(model, X0, window.kappa_at_deal, rho=0.5) == 0.0

    def test_the_escalating_schedule_drives_g_kappa_to_zero_by_t_max(
        self, model, x_star
    ):
        """Termination becomes a theorem rather than an assumption."""
        spec = ControllerSpec(t_max=12, kappa0=2.0, rho=0.5)
        values = [
            g_kappa(model, x_star, spec.kappa(k), spec.rho)
            for k in range(spec.t_max + 1)
        ]
        assert values[0] > 0.0, "friction must start low enough to permit motion"
        assert values[-1] == 0.0
        assert all(b <= a + 1e-9 for a, b in zip(values, values[1:]))

    def test_g_kappa_is_zero_only_when_both_sides_stall(self, model, x_star):
        rho = 0.5
        just_below = kappa_star(model, x_star, rho) * 0.99
        assert g_kappa(model, x_star, just_below, rho) > 0.0
        assert g_kappa(model, x_star, kappa_star(model, x_star, rho), rho) == 0.0


class TestStability:
    def test_lambda_max_is_taken_in_the_unit_metric(self, model, x_star):
        """The formulation reports -6.86; unscaled the same quantity is -0.07.

        Both are negative, so a sign check would pass either way — which is
        why this asserts the magnitude.
        """
        monotone, lam_max = is_monotone(model, x_star)
        assert monotone
        assert lam_max == pytest.approx(-6.86, abs=0.05)

    def test_the_game_is_locally_but_not_globally_stable(self, model):
        """Section 6.1: certified radius about 1 scaled unit, and the
        fractions fall away beyond it. That is a design instruction — confine
        C(theta) to the monotone region — not a caveat."""
        result = stability_radius(model, radii=(0.5, 1.0, 2.0, 3.0), samples=120)
        assert result["monotone_within_0.5"] == 1.0
        assert result["monotone_within_1.0"] == 1.0
        assert result["monotone_within_3.0"] < 0.6
        assert result["certified_radius"] == 1.0

    def test_a_wide_contract_does_not_fit_inside_the_stable_region(self, model):
        wide = Contract(budget=2000.0, cost_floor=6.0, q_min=20.0, q_max=120.0)
        fits, worst = contract_is_inside_monotone_region(model, wide, radius=1.0)
        assert not fits
        assert worst > 1.0

    def test_a_tight_contract_does(self, model, x_star):
        p, q, d = x_star
        tight = Contract(
            budget=float(p * q * 1.005),
            cost_floor=float(p * 0.995),
            q_min=float(q * 0.995),
            q_max=float(q * 1.005),
            d_min=float(d - 1.0),
            d_max=float(d + 1.0),
            deadline_active=True,
        )
        fits, worst = contract_is_inside_monotone_region(model, tight, radius=1.0)
        assert fits
        assert worst < 1.0

    def test_an_unbounded_deadline_cannot_be_certified(self, model, x_star):
        """C(theta) unbounded in a dimension the payoffs price: no ball holds it.

        Reporting a finite distance here would certify a contract that does not
        actually confine the negotiation.
        """
        p, q, _ = x_star
        no_deadline = Contract(
            budget=float(p * q * 1.005),
            cost_floor=float(p * 0.995),
            q_min=float(q * 0.995),
            q_max=float(q * 1.005),
            deadline_active=False,
        )
        assert model.deadline_active
        fits, worst = contract_is_inside_monotone_region(
            model, no_deadline, radius=1.0
        )
        assert not fits
        assert worst == float("inf")


class TestAssumptionFreeFallback:
    """The v1 realised-displacement energy, kept for transcripts the payoff
    model cannot be fitted to. Strictly weaker: it measures movement, so it
    cannot tell a negotiation that agreed from one that gave up."""

    def test_it_is_a_round_pair_displacement_in_scaled_units(self):
        traj = [
            np.array([1.0, 0.0, 0.0]),
            np.array([5.0, 0.0, 0.0]),
            np.array([4.0, 0.0, 0.0]),
        ]
        assert g_realised(traj, 0) == pytest.approx(9.0)

    def test_quantity_is_scaled_before_squaring(self):
        """10 units of quantity is one scaled unit, same as GBP 1 of price."""
        traj = [np.zeros(3), np.zeros(3), np.array([0.0, 10.0, 0.0])]
        assert g_realised(traj, 0) == pytest.approx(1.0)

    def test_an_incomplete_pair_raises_rather_than_shrinking_the_window(self):
        with pytest.raises(IndexError):
            g_realised([np.zeros(3), np.ones(3)], 0)

    def test_market_energy_is_the_sum_over_pairs(self):
        a = [np.zeros(3), np.zeros(3), np.array([2.0, 0.0, 0.0])]
        b = [np.zeros(3), np.zeros(3), np.array([0.0, 30.0, 0.0])]
        assert g_realised_series({"a": a, "b": b}) == [pytest.approx(13.0)]

    def test_a_settled_negotiation_has_zero_energy(self):
        traj = [np.array([3.0, 2.0, 1.0])] * 5
        assert g_realised_series({"pair": traj}) == [0.0, 0.0, 0.0]


class TestDecayEstimators:
    def test_transient_fit_recovers_a_known_rate(self):
        rate = 0.4
        assert contraction_transient(
            [100.0 * rate**k for k in range(12)]
        ) == pytest.approx(rate, rel=1e-6)

    def test_the_noise_floor_is_excluded_from_the_fit(self):
        """Fitting the plateau measures the noise, not the contraction — the
        error the audit caught."""
        rate = 0.4
        values = [100.0 * rate**k for k in range(8)] + [0.05] * 20
        assert contraction_transient(values) == pytest.approx(rate, rel=1e-3)

    def test_too_short_a_series_is_an_error(self):
        with pytest.raises(ValueError, match="at least 3"):
            contraction_transient([1.0, 0.5])

    def test_drift_recovers_alpha_and_beta(self):
        """Global decrease-in-expectation is false; drift outside a ball is
        what survives, and the ball radius is a reportable measure of how
        erratic the agents are."""
        alpha, beta = 0.3, 4.0
        values = [200.0]
        for _ in range(40):
            values.append((1 - alpha) * values[-1] + beta)
        fit = drift_outside_ball(values)
        assert fit["alpha"] == pytest.approx(alpha, rel=1e-6)
        assert fit["beta"] == pytest.approx(beta, rel=1e-6)
        assert fit["ball_radius"] == pytest.approx(beta / alpha, rel=1e-6)


class TestTangentConeProjectionIsExact:
    """Phi_proj at corners, not just on a single face.

    The sequential pass these replace is exact for one active row and wrong at
    a corner: projecting onto row 2 can push the result back out of row 1.
    Every test here fails against that implementation, which is the point —
    a test suite that passes on both versions would not have pinned anything.
    """

    @staticmethod
    def _sequential(field_s: np.ndarray, grads_s: np.ndarray) -> np.ndarray:
        """The old single-pass projection, kept so the tests can show it fails."""
        v = field_s.copy()
        for grad in grads_s:
            denom = float(grad @ grad)
            if denom <= 1e-9:
                continue
            overlap = float(grad @ v)
            if overlap >= 0:
                continue
            v = v - (overlap / denom) * grad
        return v

    # (a) ------------------------------------------------------------------

    def test_a_single_active_row_matches_the_sequential_result_exactly(self):
        """One row is the case the old code got right; it must not move."""
        rng = np.random.default_rng(0)
        for _ in range(200):
            field_s = rng.normal(size=3) * SCALE * 10
            grads_s = (rng.normal(size=(1, 3)) * SCALE)
            np.testing.assert_allclose(
                project_onto_tangent_cone(field_s, grads_s),
                self._sequential(field_s, grads_s),
                atol=1e-9,
            )

    def test_a_field_already_inside_the_cone_is_untouched(self):
        """"Points back into the set => not binding" survives the rewrite."""
        field_s = np.array([1.0, 2.0, 3.0])
        grads_s = np.array([[1.0, 0.0, 0.0], [0.0, 1.0, 0.0]])
        np.testing.assert_allclose(
            project_onto_tangent_cone(field_s, grads_s), field_s, atol=1e-12
        )

    def test_orthogonal_rows_still_agree_with_the_sequential_pass(self):
        """Why the realisable failure rate is only 6.3% and not 36%.

        cost_floor, q_min, q_max, d_min and d_max have axis-aligned, mutually
        orthogonal gradients, and sequential projection onto mutually
        orthogonal half-spaces is already exact. Only pairs involving the
        bilinear budget row can fail. If this ever stops holding, the
        explanation in the note is wrong.
        """
        rng = np.random.default_rng(1)
        axis_rows = np.array(
            [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
        ) * SCALE
        for _ in range(200):
            field_s = rng.normal(size=3) * SCALE * 10
            np.testing.assert_allclose(
                project_onto_tangent_cone(field_s, axis_rows),
                self._sequential(field_s, axis_rows),
                atol=1e-9,
            )

    # (b) ------------------------------------------------------------------

    def test_at_a_corner_the_result_lies_in_the_tangent_cone(self):
        """A budget x q_min corner where the sequential pass leaves the cone."""
        contract = Contract(
            budget=800.0, cost_floor=6.0, q_min=100.0, q_max=120.0,
            d_min=7.0, d_max=45.0, deadline_active=True,
        )
        x = np.array([8.0, 100.0, 26.0])  # spend 800 = B, and q = q_min
        assert contract.h(x)[0] == pytest.approx(0.0, abs=1e-9)
        assert contract.h(x)[2] == pytest.approx(0.0, abs=1e-9)

        jac = contract.grad_h(x)
        grads_s = np.array([jac[0], jac[2]]) * SCALE

        # Pick the field in the POLAR cone: F = -(g1 + g2). Every admissible
        # direction then makes the field worse, so the true projection is the
        # origin — and the sequential pass, projecting onto q_min after budget,
        # undoes the budget projection and lands outside.
        field_s = -(grads_s[0] + grads_s[1])

        sequential = self._sequential(field_s, grads_s)
        assert np.any(grads_s @ sequential < -1e-9), (
            "fixture no longer exercises the bug; pick another field"
        )

        exact = project_onto_tangent_cone(field_s, grads_s)
        assert np.all(grads_s @ exact >= -1e-9)

    def test_random_corners_always_land_in_the_cone(self):
        rng = np.random.default_rng(2)
        escapes = 0
        for _ in range(500):
            grads_s = rng.normal(size=(2, 3)) * SCALE
            field_s = rng.normal(size=3) * SCALE * 10
            exact = project_onto_tangent_cone(field_s, grads_s)
            assert np.all(grads_s @ exact >= -1e-7)
            if np.any(grads_s @ self._sequential(field_s, grads_s) < -1e-7):
                escapes += 1
        assert escapes > 0, "the sequential pass should fail on some of these"

    # (c) ------------------------------------------------------------------

    def test_a_converged_state_is_not_reported_as_unconverged(self):
        """The failure that matters: exact projection 0, sequential nonzero.

        At the same budget x q_min corner, with the field in the polar cone.
        No admissible direction improves anything, so the negotiation has
        converged and the certificate must read zero. The sequential pass
        reports a nonzero value and would call it still in motion.

        Note the rows have to be non-orthogonal for this to bite: with
        orthogonal rows the sequential projections commute and both agree.
        """
        contract = Contract(
            budget=800.0, cost_floor=6.0, q_min=100.0, q_max=120.0,
            deadline_active=False,
        )
        x = np.array([8.0, 100.0, 0.0])
        grads_s = _active_rows(contract, x, tol=1e-6) * SCALE
        assert len(grads_s) == 2
        assert abs(grads_s[0] @ grads_s[1]) > 1e-6, "rows must be non-orthogonal"

        field_s = -(grads_s[0] + grads_s[1])

        exact = project_onto_tangent_cone(field_s, grads_s)
        assert np.linalg.norm(exact) == pytest.approx(0.0, abs=1e-9)

        sequential = self._sequential(field_s, grads_s)
        assert np.linalg.norm(sequential) > 1.0
        assert np.any(grads_s @ sequential < -1e-9)

    def test_the_zero_case_arises_from_a_real_contract_too(self):
        """q_min = q_max pins quantity; a field pushing on q alone is absorbed."""
        contract = Contract(
            budget=1e6, cost_floor=0.0, q_min=50.0, q_max=50.0, deadline_active=False
        )
        x = np.array([10.0, 50.0, 0.0])
        rows = _active_rows(contract, x, tol=1e-6)
        assert len(rows) == 2  # q_min and q_max both active
        field_s = np.array([0.0, 40.0, 0.0])
        exact = project_onto_tangent_cone(field_s, rows * SCALE)
        assert np.linalg.norm(exact) == pytest.approx(0.0, abs=1e-9)

    # (d) ------------------------------------------------------------------

    def test_it_agrees_with_osqp_on_random_instances(self):
        """Cross-validation: enumeration is exact, so a QP must agree.

        This is what justifies choosing enumeration over a solver — the claim
        is checkable rather than asserted.
        """
        import osqp
        import scipy.sparse as sp

        rng = np.random.default_rng(3)
        for _ in range(150):
            n_rows = int(rng.integers(1, 5))
            grads_s = rng.normal(size=(n_rows, 3)) * SCALE
            field_s = rng.normal(size=3) * SCALE * 10

            problem = osqp.OSQP()
            problem.setup(
                P=sp.eye(3, format="csc") * 2.0,
                q=-2.0 * field_s,
                A=sp.csc_matrix(grads_s),
                l=np.zeros(n_rows),
                u=np.full(n_rows, np.inf),
                verbose=False,
                eps_abs=1e-10,
                eps_rel=1e-10,
                max_iter=40000,
                polishing=True,
            )
            solved = problem.solve(raise_error=False)
            if int(solved.info.status_val) not in (1, 2):
                continue  # solver trouble is not evidence about the enumeration

            exact = project_onto_tangent_cone(field_s, grads_s)
            assert np.linalg.norm(exact) == pytest.approx(
                float(np.linalg.norm(solved.x)), abs=1e-4
            )

    # integration ----------------------------------------------------------

    def test_phi_projected_uses_the_exact_projection_at_a_corner(self, model):
        contract = Contract(
            budget=800.0, cost_floor=6.0, q_min=100.0, q_max=120.0,
            d_min=7.0, d_max=45.0, deadline_active=True,
        )
        x = np.array([8.0, 100.0, 26.0])
        rows = _active_rows(contract, x, tol=1e-6)
        assert len(rows) == 2

        value = phi_projected(model, x, contract)
        field_s = model.concession_field(x) * SCALE
        expected = project_onto_tangent_cone(field_s, rows * SCALE)
        assert value == pytest.approx(float(np.linalg.norm(expected)))
        assert value <= phi(model, x) + 1e-9

    def test_an_interior_point_is_unaffected(self, model, x_star):
        """The regression gate for e13_dcbf and payoff_validation3.

        Their settled points are strictly interior, so no row is active and
        Phi_proj must still equal Phi exactly. If this moves, the projection
        changed behaviour where it should not have.
        """
        contract = Contract(
            budget=1e6, cost_floor=0.0, q_min=0.0, q_max=1e6, deadline_active=False
        )
        assert phi_projected(model, x_star, contract) == pytest.approx(
            phi(model, x_star)
        )
