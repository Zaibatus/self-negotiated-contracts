"""Discrete-time control barrier function filter — the safety layer.

Condition (Agrawal & Sreenath, discrete-time exponential CBF), rate
gamma in (0, 1]:

    h_i(x_{k+1}) >= (1 - gamma) h_i(x_k)

Inside C(theta) this is forward invariance (no breach, ever); from outside it
forces geometric recovery of the violation at rate (1 - gamma).

The filter is the minimally-invasive QP over the joint state of n concurrent
negotiations, with slack for graceful degradation:

    min_{u, delta}  ||u - u_prop||^2 + rho ||delta||^2
    s.t.            grad_h_i . u + gamma h_i(x) + delta_i >= 0,   delta >= 0

Three things here that the synthetic prototype in experiments/certificates/
does not do, each closing a gap the audit found or the formulation flagged:

  1. OSQP with an explicit status check and a tiered fallback, replacing
     SLSQP's measured 6.7% silent status-failure rate. A solver that returns
     an unreported non-convergence is not acceptable in a safety component.
  2. Exact dual variables straight from the solver, replacing NNLS
     reconstruction. The duals are the shadow prices of section 6, so this is
     what makes those numbers solver-grade rather than indicative.
  3. Backtracking on the TRUE bilinear h. The QP works on the per-round
     linearisation of the budget row; a large single-round jump can therefore
     satisfy the linearised condition and still breach the real one. That is
     formulation.md section 7.4's stated attack surface. We close it by
     halving the step until the true h honours what the QP promised, which
     makes "zero violations of the true h" hold by construction rather than
     by luck.

"Minimally invasive" is measured in the unit metric M = diag(sigma)^-1 with
sigma = (1, 10, 5), not in raw Euclidean norm. The three terms are priced in
pounds, units and days, so a raw norm would silently declare that shifting the
deadline by one day is as intrusive as moving the price by one pound. The
objective is therefore ||(u - u_prop) / sigma||^2, which is the same metric
the certificates and every reported distance use.

Sign convention for duals: OSQP's y is negative on active lower bounds
(l <= Az), so shadow prices are reported as lambda = max(-y, 0).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import osqp
import scipy.sparse as sp

from ..contract import N_ROWS, ROW_LABELS, Contract
from ..payoffs import SCALE

# OSQP status codes we are willing to act on.
_OK_STATUS = {1, 2}  # OSQP_SOLVED, OSQP_SOLVED_INACCURATE

SHARED_CAPACITY_LABEL = "shared:capacity"


@dataclass
class FilterResult:
    """Everything one filter step produced, including how it went wrong."""

    u: np.ndarray  # (3n,) applied joint adjustment
    u_prop: np.ndarray  # (3n,) what the agents proposed
    slack: np.ndarray  # (m,) per-row slack actually used
    duals: np.ndarray  # (m,) shadow prices, >= 0
    row_labels: list[str]
    status: str  # solver status string
    solved: bool  # status in {solved, solved_inaccurate}
    fallback: str | None = None  # which fallback tier fired, if any
    backtracks: int = 0  # halvings needed to satisfy the true h
    certificate_gap: bool = False  # step taken WITHOUT a verified guarantee
    notes: dict[str, float] = field(default_factory=dict)

    @property
    def interventions(self) -> np.ndarray:
        """Per-pair ||u_safe - u_prop||_M, in scaled units."""
        n = self.u.size // 3
        delta = (self.u - self.u_prop).reshape(n, 3) / SCALE
        return np.linalg.norm(delta, axis=1)

    @property
    def intervention(self) -> float:
        """Joint ||u_safe - u_prop||_M, in scaled units."""
        return float(np.linalg.norm(self.interventions))

    def dual(self, label: str) -> float:
        """Shadow price of a named row, 0.0 if the row was not present."""
        try:
            return float(self.duals[self.row_labels.index(label)])
        except ValueError:
            return 0.0


def build_rows(
    xs: list[np.ndarray],
    contracts: list[Contract],
    shared_capacity: float | None = None,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Stack every active constraint of every pair into one system.

    Composition is concatenation: pair i's rows occupy columns 3i..3i+2, and a
    coupling clause (shared capacity) is one extra row touching all pairs.

    Returns (G, h0, labels) with G of shape (m, 3n).
    """
    n = len(xs)
    grads: list[np.ndarray] = []
    h0: list[float] = []
    labels: list[str] = []

    for i, (x, contract) in enumerate(zip(xs, contracts)):
        hv = contract.h(x)
        jac = contract.grad_h(x)
        mask = contract.active_mask()
        for j in range(N_ROWS):
            if not mask[j]:
                continue
            g = np.zeros(3 * n)
            g[3 * i : 3 * i + 3] = jac[j]
            grads.append(g)
            h0.append(float(hv[j]))
            labels.append(f"{i}:{ROW_LABELS[j]}")

    if shared_capacity is not None:
        g = np.zeros(3 * n)
        for i in range(n):
            g[3 * i + 1] = -1.0
        grads.append(g)
        h0.append(float(shared_capacity - sum(float(x[1]) for x in xs)))
        labels.append(SHARED_CAPACITY_LABEL)

    if not grads:
        raise ValueError("no active constraint rows; the contract enforces nothing")

    return np.array(grads), np.array(h0), labels


def project_into_safe_set(
    x: np.ndarray,
    contract: Contract,
    iterations: int = 6,
    tol: float = 1e-7,
) -> np.ndarray:
    """Nearest point in C(theta) to x, by iterated linearised projection.

    The DCBF condition governs *transitions*, so it needs a previous state. The
    first proposal of a negotiation has none. Seeding the state with the
    proposal itself and letting the barrier recover geometrically would mean
    knowingly forwarding a breaching first offer for several rounds, so instead
    the opening state is projected into C once, and the barrier governs
    everything after it.

    Iteration handles the bilinear budget row: each pass linearises around the
    current iterate, and the loop stops as soon as the true h is satisfied.
    """
    current = np.asarray(x, dtype=float).copy()
    filt = DCBFFilter(gamma=1.0, rho=1e6, backtrack=False)
    for _ in range(iterations):
        if contract.is_safe(current, tol=tol):
            return current
        result = filt.step([current], [np.zeros(3)], [contract])
        if not result.solved:
            break
        step = result.u[:3]
        if np.linalg.norm(step) < tol:
            break
        current = current + step
    return current


class DCBFFilter:
    """Minimally-invasive DCBF-QP filter over n concurrent negotiations."""

    def __init__(
        self,
        gamma: float = 0.4,
        rho: float = 1e4,
        solver: str = "osqp",
        backtrack: bool = True,
        max_backtracks: int = 12,
        tol: float = 1e-7,
    ):
        """Configure the filter.

        Args:
            gamma: DCBF rate. gamma -> 1 permits approaching the boundary in
                one step; small gamma is cautious and, per section 6, inflates
                the shadow price by a conservatism premium. It is an economic
                policy parameter, not only a safety one.
            rho: slack penalty. Large rho means the filter fights hard before
                degrading.
            solver: "osqp" (the implementation standard) or "slsqp" (kept only
                to reproduce the v1 tables and for the audit's A/B).
            backtrack: verify each step against the true bilinear h and halve
                until it holds.
            max_backtracks: give up after this many halvings and flag a gap.
            tol: feasibility tolerance.
        """
        if not 0.0 < gamma <= 1.0:
            raise ValueError(f"gamma must be in (0, 1], got {gamma}")
        if solver not in {"osqp", "slsqp"}:
            raise ValueError(f"unknown solver {solver!r}")
        self.gamma = gamma
        self.rho = rho
        self.solver = solver
        self.backtrack = backtrack
        self.max_backtracks = max_backtracks
        self.tol = tol

        # Reliability counters — reported, never swallowed.
        self.n_calls = 0
        self.n_solver_failures = 0
        self.n_fallbacks = 0
        self.n_certificate_gaps = 0
        self.n_backtracked = 0
        # Per tier, because they are not interchangeable: a stiffened retry is
        # a solved QP, holding is a refusal to move, and an unverified hold is
        # a step taken with no guarantee at all. One aggregate rate hides which.
        self.fallback_tiers: dict[str, int] = {}

    # ----------------------------------------------------------------- API --

    def step(
        self,
        xs: list[np.ndarray],
        u_props: list[np.ndarray],
        contracts: list[Contract],
        shared_capacity: float | None = None,
    ) -> FilterResult:
        """Filter one joint proposal.

        Args:
            xs: current term vectors, one per pair.
            u_props: proposed adjustments, one per pair.
            contracts: theta, one per pair.
            shared_capacity: Q of the coupling clause h = Q - sum_j q_j, or
                None for independent pairs.

        Returns:
            FilterResult. Always returns a step: the filter never locks up.
        """
        self.n_calls += 1
        n = len(xs)
        if not (len(u_props) == len(contracts) == n):
            raise ValueError("xs, u_props and contracts must have equal length")

        gmat, h0, labels = build_rows(xs, contracts, shared_capacity)
        u_prop_flat = np.concatenate([np.asarray(u, dtype=float) for u in u_props])

        result = self._solve(gmat, h0, labels, u_prop_flat)

        if self.backtrack:
            self._backtrack_on_true_h(result, xs, contracts, h0, shared_capacity)

        if result.fallback is not None:
            self.n_fallbacks += 1
            self.fallback_tiers[result.fallback] = (
                self.fallback_tiers.get(result.fallback, 0) + 1
            )
        if result.certificate_gap:
            self.n_certificate_gaps += 1
        if result.backtracks:
            self.n_backtracked += 1
        return result

    def reliability(self) -> dict[str, float]:
        """Solver reliability profile — reported alongside every experiment."""
        calls = max(self.n_calls, 1)
        out = {
            "calls": float(self.n_calls),
            "solver_failure_rate": self.n_solver_failures / calls,
            "fallback_rate": self.n_fallbacks / calls,
            "certificate_gap_rate": self.n_certificate_gaps / calls,
            "backtrack_rate": self.n_backtracked / calls,
        }
        for tier, count in sorted(self.fallback_tiers.items()):
            out[f"fallback_{tier}_rate"] = count / calls
        return out

    # ------------------------------------------------------------ internals --

    def _solve(
        self,
        gmat: np.ndarray,
        h0: np.ndarray,
        labels: list[str],
        u_prop: np.ndarray,
    ) -> FilterResult:
        """Tiered solve: nominal -> stiffened -> hold -> conservative recovery."""
        attempt = self._solve_once(gmat, h0, labels, u_prop, self.rho)
        if attempt.solved:
            return attempt

        self.n_solver_failures += 1

        # Tier (a): stiffen the slack penalty and retry once.
        retry = self._solve_once(gmat, h0, labels, u_prop, self.rho * 10.0)
        if retry.solved:
            retry.fallback = "retry_stiff_rho"
            return retry

        n_u = gmat.shape[1]
        m = gmat.shape[0]
        inside = bool(np.all(h0 >= -self.tol))

        if inside:
            # Tier (b): hold state. u = 0 satisfies the DCBF condition exactly
            # when h >= 0, since the row reduces to gamma * h >= 0.
            return FilterResult(
                u=np.zeros(n_u),
                u_prop=u_prop,
                slack=np.zeros(m),
                duals=np.zeros(m),
                row_labels=labels,
                status=attempt.status,
                solved=False,
                fallback="hold",
            )

        # Tier (c): outside C, so holding does not recover. Ask for the
        # smallest step that satisfies the barrier rows, i.e. the same QP with
        # a zero target.
        recovery = self._solve_once(gmat, h0, labels, np.zeros(n_u), self.rho * 10.0)
        if recovery.solved:
            recovery.fallback = "conservative_recovery"
            recovery.u_prop = u_prop
            return recovery

        # Nothing worked. Hold, and say so loudly: this step carries no
        # guarantee and must show up in the reported metrics.
        return FilterResult(
            u=np.zeros(n_u),
            u_prop=u_prop,
            slack=np.zeros(m),
            duals=np.zeros(m),
            row_labels=labels,
            status=attempt.status,
            solved=False,
            fallback="hold_outside_unverified",
            certificate_gap=True,
        )

    def _solve_once(
        self,
        gmat: np.ndarray,
        h0: np.ndarray,
        labels: list[str],
        u_prop: np.ndarray,
        rho: float,
    ) -> FilterResult:
        if self.solver == "osqp":
            return self._solve_osqp(gmat, h0, labels, u_prop, rho)
        return self._solve_slsqp(gmat, h0, labels, u_prop, rho)

    @staticmethod
    def _row_scales(gmat: np.ndarray) -> np.ndarray:
        """s_i = ||grad h_i||_M, the natural scale of each constraint row.

        Used to precondition the QP by the change of variables
        delta_i = s_i * delta_bar_i. The rows carry very different magnitudes —
        the budget row's gradient is (-q, -p, 0), two to three orders larger
        than the unit-coefficient rows — and that spread costs OSQP its
        convergence at the default slack penalty (measured: the same QP hits
        max-iter at rho = 1e4 unpreconditioned and solves in 4850 iterations
        with it).

        This is preconditioning ONLY. The objective weight on the substituted
        variable is rho * s_i^2, so the optimisation problem is bit-for-bit the
        one that was there before, and the filter's behaviour is unchanged.
        Dropping the s_i^2 and penalising delta_bar directly would look like a
        tidier "relative violation" weighting and would in fact be a different
        filter: slack on the budget row would become ~10^6 times cheaper, and
        the trajectory drifts out of C(theta) through it.

        Rows with a vanishing gradient are left alone: dividing by ~0 would
        manufacture the conditioning problem this removes.
        """
        n_u = gmat.shape[1]
        scales = np.linalg.norm(gmat * np.tile(SCALE, n_u // 3), axis=1)
        return np.where(scales > 1e-12, scales, 1.0)

    def _solve_osqp(
        self,
        gmat: np.ndarray,
        h0: np.ndarray,
        labels: list[str],
        u_prop: np.ndarray,
        rho: float,
    ) -> FilterResult:
        m, n_u = gmat.shape

        # Precondition by delta = s * delta_bar. The objective weight becomes
        # rho * s^2, so this is a change of variables and not a re-weighting.
        scales = self._row_scales(gmat)
        gmat_n = gmat / scales[:, None]
        h0_n = h0 / scales

        # z = [u (n_u); delta_bar (m)]
        # Objective ||(u - u_prop)/sigma||^2 + rho ||delta||^2, so the u block
        # of P is 2/sigma^2 rather than 2. Without the metric the QP would
        # trade a day of deadline against a pound of price one for one.
        inv_var = 1.0 / np.tile(SCALE, n_u // 3) ** 2
        p_diag = np.concatenate([2.0 * inv_var, 2.0 * rho * scales**2])
        pmat = sp.diags(p_diag, format="csc")
        qvec = np.concatenate([-2.0 * inv_var * u_prop, np.zeros(m)])

        # DCBF rows:  G_n u + delta_bar >= -gamma h0_n
        # slack rows:       delta_bar >= 0
        amat = sp.bmat(
            [
                [sp.csc_matrix(gmat_n), sp.eye(m, format="csc")],
                [None, sp.eye(m, format="csc")],
            ],
            format="csc",
        )
        lvec = np.concatenate([-self.gamma * h0_n, np.zeros(m)])
        uvec = np.full(2 * m, np.inf)

        prob = osqp.OSQP()
        prob.setup(
            P=pmat,
            q=qvec,
            A=amat,
            l=lvec,
            u=uvec,
            verbose=False,
            eps_abs=1e-9,
            eps_rel=1e-9,
            max_iter=20000,
            polishing=True,
        )
        # Explicit: OSQP is deprecating raise_error=False as the default. We
        # need the status returned, not raised — the whole tiered fallback
        # below is built on inspecting it.
        res = prob.solve(raise_error=False)

        status_val = int(res.info.status_val)
        solved = status_val in _OK_STATUS
        if not solved or res.x is None or not np.all(np.isfinite(res.x)):
            return FilterResult(
                u=np.zeros(n_u),
                u_prop=u_prop,
                slack=np.zeros(m),
                duals=np.zeros(m),
                row_labels=labels,
                status=str(res.info.status),
                solved=False,
            )

        u = np.asarray(res.x[:n_u], dtype=float)
        # Undo the substitution so slack and duals are reported in the original
        # constraint units: delta = s * delta_bar, and the multiplier on the raw
        # row is y_bar / s (since y_bar * (a/s) = (y_bar/s) * a).
        slack = np.maximum(np.asarray(res.x[n_u:], dtype=float), 0.0) * scales
        # OSQP's y is negative on active lower bounds; the shadow price is -y.
        duals = np.maximum(-np.asarray(res.y[:m], dtype=float), 0.0) / scales

        return FilterResult(
            u=u,
            u_prop=u_prop,
            slack=slack,
            duals=duals,
            row_labels=labels,
            status=str(res.info.status),
            solved=True,
            notes={"osqp_iter": float(res.info.iter)},
        )

    def _solve_slsqp(
        self,
        gmat: np.ndarray,
        h0: np.ndarray,
        labels: list[str],
        u_prop: np.ndarray,
        rho: float,
    ) -> FilterResult:
        """Legacy path. Kept only to reproduce the v1 tables and A/B the audit.

        Duals are not available from SLSQP, so they come back as zeros rather
        than as a reconstruction that would look like a measurement.
        """
        from scipy.optimize import minimize

        m, n_u = gmat.shape

        inv_var = 1.0 / np.tile(SCALE, n_u // 3) ** 2
        # Same preconditioning as the OSQP path, so the two solvers optimise
        # the same problem and the audit's A/B compares like with like.
        scales = self._row_scales(gmat)
        gmat_n = gmat / scales[:, None]
        h0_n = h0 / scales
        slack_weight = rho * scales**2

        def obj(z: np.ndarray) -> float:
            u, delta = z[:n_u], z[n_u:]
            return float(
                np.sum(inv_var * (u - u_prop) ** 2)
                + np.sum(slack_weight * delta**2)
            )

        def obj_grad(z: np.ndarray) -> np.ndarray:
            u, delta = z[:n_u], z[n_u:]
            return np.concatenate(
                [2 * inv_var * (u - u_prop), 2 * slack_weight * delta]
            )

        eye = np.eye(m)
        cons = []
        for i in range(m):
            cons.append(
                {
                    "type": "ineq",
                    "fun": (
                        lambda z, i=i: gmat_n[i] @ z[:n_u]
                        + self.gamma * h0_n[i]
                        + z[n_u + i]
                    ),
                    "jac": (lambda z, i=i: np.concatenate([gmat_n[i], eye[i]])),
                }
            )
            cons.append(
                {
                    "type": "ineq",
                    "fun": (lambda z, i=i: z[n_u + i]),
                    "jac": (lambda z, i=i: np.concatenate([np.zeros(n_u), eye[i]])),
                }
            )

        z0 = np.concatenate([u_prop, np.zeros(m)])
        res = minimize(
            obj,
            z0,
            jac=obj_grad,
            constraints=cons,
            method="SLSQP",
            options={"maxiter": 300, "ftol": 1e-10},
        )
        return FilterResult(
            u=np.asarray(res.x[:n_u], dtype=float),
            u_prop=u_prop,
            slack=np.maximum(np.asarray(res.x[n_u:], dtype=float), 0.0) * scales,
            duals=np.zeros(m),
            row_labels=labels,
            status=str(res.message),
            solved=bool(res.success),
        )

    def _backtrack_on_true_h(
        self,
        result: FilterResult,
        xs: list[np.ndarray],
        contracts: list[Contract],
        h0: np.ndarray,
        shared_capacity: float | None,
    ) -> None:
        """Halve the step until the TRUE h honours what the linearised QP promised.

        The QP guarantees h_i(x) + grad_h_i . u >= (1 - gamma) h_i(x) - delta_i
        on the linearisation. We require the same inequality on the exact h,
        which for the bilinear budget row is a strictly stronger demand. Only
        meaningful from inside C: from outside, u -> 0 does not recover, so we
        leave the recovery step alone.
        """
        if not result.solved:
            return
        if not all(c.is_safe(x, tol=self.tol) for x, c in zip(xs, contracts)):
            return

        target = (1.0 - self.gamma) * h0 - result.slack - self.tol
        u = result.u.copy()

        for attempt in range(self.max_backtracks + 1):
            realised = self._true_h_after(xs, contracts, u, shared_capacity)
            if np.all(realised >= target):
                result.u = u
                result.backtracks = attempt
                return
            u = 0.5 * u

        # Exhausted: fall back to holding, which is safe inside C.
        result.u = np.zeros_like(result.u)
        result.backtracks = self.max_backtracks
        result.fallback = "backtrack_exhausted_hold"

    @staticmethod
    def _true_h_after(
        xs: list[np.ndarray],
        contracts: list[Contract],
        u: np.ndarray,
        shared_capacity: float | None,
    ) -> np.ndarray:
        """Exact constraint values at x + u, in the same row order as build_rows."""
        vals: list[float] = []
        new_xs = []
        for i, (x, contract) in enumerate(zip(xs, contracts)):
            x_next = np.asarray(x, dtype=float) + u[3 * i : 3 * i + 3]
            new_xs.append(x_next)
            hv = contract.h(x_next)
            mask = contract.active_mask()
            vals.extend(float(hv[j]) for j in range(N_ROWS) if mask[j])
        if shared_capacity is not None:
            vals.append(float(shared_capacity - sum(float(x[1]) for x in new_xs)))
        return np.array(vals)
