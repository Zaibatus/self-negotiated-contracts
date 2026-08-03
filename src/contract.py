"""Contract schema and validators for bilateral agent negotiation.

A contract is C = (theta, gamma, tau):

    theta = (B, c, q_min, q_max, d_min, d_max) in R^6   constraint parameters
    gamma in (0, 1]                                     enforcement rate
    tau   = (T_max, epsilon)                            liveness specification

over the term vector x = (p, q, d) — mean unit price, total quantity,
delivery deadline in days.  theta defines the safe set

    C(theta) = { x : h_i(x; theta) >= 0, i = 1..6 }

    h1 = B - p*q      buyer budget      (bilinear; linearised per round)
    h2 = p - c        seller cost floor
    h3 = q - q_min    quantity floor
    h4 = q_max - q    quantity ceiling
    h5 = d - d_min    deadline floor
    h6 = d_max - d    deadline ceiling

gamma and tau are controller parameters, not constraints on x: gamma sets how
fast the filter lets the draft approach the boundary, and tau is the liveness
obligation discharged by the termination certificate (``certificates.energy``,
formulation.md section 6). Making either a row of h would be a category error —
neither is a property a set of terms can satisfy or violate.

They live in ``ControllerSpec``. Keeping them out of theta also keeps the
refinement order meaningful: C' refines C iff C(theta') is a subset of
C(theta), which is a statement about sets of terms and says nothing about how
fast a filter enforces them.

Rows may be deactivated (``active_mask``) when the corresponding term is not
observable in a given testbed — in Magentic ``estimated_delivery`` is a free
text field that is frequently absent, and inventing a deadline to keep the row
alive would mean enforcing a contract nobody agreed to.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover - typing only
    from magentic_marketplace.marketplace.shared.models import Business, Customer

# Row order is fixed and load-bearing: dual variables are reported per row and
# compared across runs.
ROW_LABELS: tuple[str, ...] = (
    "budget",
    "cost_floor",
    "q_min",
    "q_max",
    "d_min",
    "d_max",
)

N_ROWS = len(ROW_LABELS)


@dataclass(frozen=True)
class ContractSpec:
    """Knobs for deriving theta from scenario data.

    These are modelling choices, not measurements — collected here so that
    every place a number is invented is visible in one object.
    """

    # Quantity band: q in [q_requested, ceil(q_requested * q_max_factor)].
    # The customer's basket sets the floor; the ceiling is the upsell room we
    # allow the seller.
    q_max_factor: float = 2.0
    # Deadline band in days. Only used when deadline_active is True.
    d_min: float = 0.0
    d_max: float = 7.0
    # Whether the deadline rows (h5, h6) participate at all.
    deadline_active: bool = False
    # Budget headroom: B = (1 + budget_slack) * sum(customer reservation prices).
    # 0.0 means the customer's stated reservation IS the hard budget.
    budget_slack: float = 0.0


@dataclass(frozen=True)
class ControllerSpec:
    """The (gamma, tau) half of the contract: how theta is enforced.

    Separated from theta because these are properties of the controller, not
    of the agreement. Two parties can agree the same safe set and be governed
    at different enforcement rates, and gamma is an economic policy parameter
    as much as a safety one — a cautious filter parks the negotiation short of
    the limits and inflates the shadow prices by a conservatism premium.
    """

    gamma: float = 0.4  # DCBF enforcement rate
    t_max: int = 12  # liveness: round-pairs allowed to reach agreement
    epsilon: float = 1e-3  # liveness: tolerance the certificate must reach
    # Friction schedule for the termination certificate. Constant friction is
    # provably insufficient (formulation.md Prop. 2), so kappa escalates.
    kappa0: float = 2.0
    rho: float = 0.5  # per-round step budget, in scaled units

    def kappa(self, k: int) -> float:
        """Escalating friction kappa_k = kappa_0 / (1 - k / T_max).

        Deadline pressure, modelled as friction that grows without bound as
        T_max approaches. This is what turns termination from an assumption
        into a theorem: whatever residual incentive remains, friction
        eventually exceeds it.
        """
        if self.t_max <= 0:
            return float("inf")
        fraction = min(k / self.t_max, 0.999)
        return self.kappa0 / (1.0 - fraction)


@dataclass(frozen=True)
class Contract:
    """theta = (B, c, q_min, q_max, d_min, d_max)."""

    budget: float
    cost_floor: float
    q_min: float
    q_max: float
    d_min: float = 0.0
    d_max: float = 7.0
    deadline_active: bool = True

    # Provenance, for audit trails. Not part of theta.
    pair_id: str | None = None
    notes: dict[str, float | str] = field(default_factory=dict, compare=False)

    # ---------------------------------------------------------------- theta --

    @property
    def theta(self) -> np.ndarray:
        """The contract as a vector. Composition is concatenation of these."""
        return np.array(
            [
                self.budget,
                self.cost_floor,
                self.q_min,
                self.q_max,
                self.d_min,
                self.d_max,
            ]
        )

    def refines(self, other: Contract, tol: float = 1e-9) -> bool:
        """C(self) is a subset of C(other): a stricter contract.

        The refinement order of formulation.md section 1. For this template it
        is componentwise: a tighter budget, a higher cost floor, and narrower
        bands all shrink the safe set.
        """
        checks = [
            self.budget <= other.budget + tol,
            self.cost_floor >= other.cost_floor - tol,
            self.q_min >= other.q_min - tol,
            self.q_max <= other.q_max + tol,
        ]
        if self.deadline_active and other.deadline_active:
            checks += [
                self.d_min >= other.d_min - tol,
                self.d_max <= other.d_max + tol,
            ]
        return all(checks)

    def active_mask(self) -> np.ndarray:
        """Boolean mask over ROW_LABELS of which rows are enforced."""
        mask = np.ones(N_ROWS, dtype=bool)
        if not self.deadline_active:
            mask[4] = False
            mask[5] = False
        return mask

    def active_labels(self) -> list[str]:
        """Labels of the enforced rows, in row order."""
        return [lbl for lbl, on in zip(ROW_LABELS, self.active_mask()) if on]

    def without_deadline(self) -> Contract:
        """Same theta with h5/h6 switched off (deadline unobservable)."""
        return replace(self, deadline_active=False)

    # ------------------------------------------------------------ constraint --

    def h(self, x: np.ndarray) -> np.ndarray:
        """True (non-linearised) constraint values at x = (p, q, d).

        Always returns all N_ROWS values; use ``active_mask`` to select. h1 is
        bilinear — this is the exact form, against which the filter's
        linearised step is verified post hoc.
        """
        p, q, d = float(x[0]), float(x[1]), float(x[2])
        return np.array(
            [
                self.budget - p * q,
                p - self.cost_floor,
                q - self.q_min,
                self.q_max - q,
                d - self.d_min,
                self.d_max - d,
            ]
        )

    def grad_h(self, x: np.ndarray) -> np.ndarray:
        """Jacobian of h at x, with h1 linearised around x.

        d(B - p*q)/d(p, q) = (-q, -p): valid for the small per-round
        adjustments typical of negotiation. Large single-round jumps are a
        stated attack surface (formulation.md section 7.4); the filter
        backtracks on the true h to close it.
        """
        p, q = float(x[0]), float(x[1])
        return np.array(
            [
                [-q, -p, 0.0],
                [1.0, 0.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, -1.0, 0.0],
                [0.0, 0.0, 1.0],
                [0.0, 0.0, -1.0],
            ]
        )

    def is_safe(self, x: np.ndarray, tol: float = 1e-6) -> bool:
        """Is x inside C(theta), counting only active rows?"""
        return bool(np.all(self.h(x)[self.active_mask()] >= -tol))

    def is_satisfiable(self, tol: float = 1e-9) -> bool:
        """Is C(theta) non-empty?

        For this template the answer is closed-form. Price is squeezed between
        the cost floor and B/q, and B/q is largest at the smallest admissible
        quantity, so a feasible point exists exactly when

            c * q_min <= B     and    q_min <= q_max    and    d_min <= d_max.

        This matters because a contract whose safe set is empty is not a strict
        contract, it is an impossible one: no proposal can ever satisfy it,
        every filtered step degrades onto slack, and the resulting metrics
        would read as a filter failing rather than as a deal that should never
        have been attempted. The right response to an unsatisfiable theta is no
        agreement, not a projection into nothing.
        """
        if self.q_min > self.q_max + tol:
            return False
        if self.deadline_active and self.d_min > self.d_max + tol:
            return False
        return self.cost_floor * self.q_min <= self.budget + tol

    def violations(self, x: np.ndarray, tol: float = 1e-6) -> list[str]:
        """Labels of active rows breached at x."""
        hv = self.h(x)
        return [
            lbl
            for lbl, on, v in zip(ROW_LABELS, self.active_mask(), hv)
            if on and v < -tol
        ]

    # ------------------------------------------------------------- scenarios --

    @classmethod
    def from_scenario(
        cls,
        business: Business,
        customer: Customer,
        spec: ContractSpec | None = None,
        quantities: dict[str, int] | None = None,
    ) -> Contract:
        """Derive theta for one (business, customer) pair from scenario YAML.

        Ground truth already in the data, previously unused by any code path:

          * ``Business.min_price_factor`` is the seller's cost floor as a
            fraction of list price -> c.
          * ``Customer.menu_features`` maps requested item -> the customer's
            reservation price -> B.

        Both are per-item; theta is over the aggregated order, so c is the
        quantity-weighted mean floor over the customer's requested basket and B
        is the reservation total. Aggregation matches ``terms.extract`` so that
        h1 = B - p*q is exactly B - total_price.

        Items the business does not stock are skipped: they cannot appear in
        one of its proposals, so they cannot constrain one.
        """
        spec = spec or ContractSpec()
        quantities = quantities or {}

        reservation_total = 0.0
        floor_total = 0.0
        total_qty = 0.0
        stocked: list[str] = []
        missing: list[str] = []

        for item, reservation_price in customer.menu_features.items():
            qty = float(quantities.get(item, 1))
            list_price = business.menu_features.get(item)
            if list_price is None:
                missing.append(item)
                continue
            stocked.append(item)
            total_qty += qty
            reservation_total += float(reservation_price) * qty
            floor_total += float(list_price) * business.min_price_factor * qty

        if total_qty <= 0:
            raise ValueError(
                f"business {business.id} stocks none of the items customer "
                f"{customer.id} requested ({sorted(customer.menu_features)}); "
                "no contract is definable for this pair"
            )

        budget = reservation_total * (1.0 + spec.budget_slack)
        cost_floor = floor_total / total_qty

        return cls(
            budget=budget,
            cost_floor=cost_floor,
            q_min=total_qty,
            q_max=float(math.ceil(total_qty * spec.q_max_factor)),
            d_min=spec.d_min,
            d_max=spec.d_max,
            deadline_active=spec.deadline_active,
            pair_id=f"{business.id}|{customer.id}",
            notes={
                "business": business.id,
                "customer": customer.id,
                "items_stocked": ",".join(sorted(stocked)),
                "items_missing": ",".join(sorted(missing)),
                "min_price_factor": business.min_price_factor,
                "reservation_total": reservation_total,
            },
        )
