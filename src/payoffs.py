"""Preferences, the bargaining benchmark, and the concession field.

This is formulation.md v2 sections 2-4, made estimable. The prototype
hard-codes one calibration; live negotiations need the same model fitted to
whatever the scenario says, so every parameter is a field and
``PayoffModel.from_scenario`` derives the ones the marketplace data determines.

    U_B(x) = a q - (b/2) q^2 - p q - (gamma_B/2)(d - d_B)^2
    U_S(x) =         p q - c q - (e/2) q^2 - (gamma_S/2)(d - d_S)^2

Price is a pure transfer, so the joint surplus W = U_B + U_S does not depend on
it: quantity and deadline are the efficiency-relevant terms and price is purely
distributive. That single fact is what makes Proposition 1 work — the rest
point of the concession dynamics is exactly the Nash bargaining solution, not
an artefact of whatever update rule the agents happen to run.

Terms have incommensurable units (pounds, units, days), so every norm is taken
in the metric M = diag(sigma)^-1 with sigma = (1, 10, 5): one scaled unit is
GBP 1 of price, 10 units of quantity, or 5 days. Reporting an unscaled norm
over these three would be adding pounds to days.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:  # pragma: no cover - typing only
    from magentic_marketplace.marketplace.shared.models import Business, Customer

# Unit-normalising scales for (p, q, d). One scaled unit = GBP 1, 10 units, 5 days.
SCALE = np.array([1.0, 10.0, 5.0])


def norm_M(v: np.ndarray) -> float:
    """Dual norm in the unit metric: gradients scale up where terms scale down."""
    return float(np.linalg.norm(np.asarray(v, dtype=float) * SCALE))


def dist_M(x: np.ndarray, y: np.ndarray) -> float:
    """Distance between term vectors in scaled units."""
    return float(np.linalg.norm((np.asarray(x, float) - np.asarray(y, float)) / SCALE))


@dataclass(frozen=True)
class PayoffModel:
    """Calibrated preferences for one bilateral negotiation.

    Defaults are the formulation's calibration, under which the Nash bargaining
    solution is x* = (8.5, 100, 26) with U_B = U_S = 120.60 and W_max = 241.20.
    """

    a: float = 12.0  # buyer marginal value intercept
    b: float = 0.04  # buyer value curvature
    c: float = 6.0  # seller marginal cost
    e: float = 0.02  # seller cost curvature
    gamma_b: float = 0.3  # buyer deadline curvature
    gamma_s: float = 0.3  # seller deadline curvature
    d_b: float = 40.0  # buyer's ideal deadline (late)
    d_s: float = 12.0  # seller's ideal deadline (early)
    lam: float = 60.0  # acceptance temperature
    deadline_active: bool = True

    provenance: dict[str, str | float] = field(default_factory=dict, compare=False)

    # ------------------------------------------------------------ utilities --

    def u_buyer(self, x: np.ndarray) -> float:
        p, q, d = float(x[0]), float(x[1]), float(x[2])
        value = self.a * q - 0.5 * self.b * q**2 - p * q
        return value - self._deadline_penalty(d, self.gamma_b, self.d_b)

    def u_seller(self, x: np.ndarray) -> float:
        p, q, d = float(x[0]), float(x[1]), float(x[2])
        value = p * q - self.c * q - 0.5 * self.e * q**2
        return value - self._deadline_penalty(d, self.gamma_s, self.d_s)

    def _deadline_penalty(self, d: float, curvature: float, ideal: float) -> float:
        if not self.deadline_active:
            return 0.0
        return 0.5 * curvature * (d - ideal) ** 2

    def surplus(self, x: np.ndarray) -> float:
        """W = U_B + U_S. Independent of price — the load-bearing fact."""
        return self.u_buyer(x) + self.u_seller(x)

    def utility(self, x: np.ndarray, role: str) -> float:
        return self.u_buyer(x) if role == "buyer" else self.u_seller(x)

    # ----------------------------------------------------------- acceptance --

    def p_accept(self, x: np.ndarray) -> float:
        """Both sides must find the draft acceptable for it to close.

        This is what creates the concession trade-off: demanding more raises
        your own utility and lowers the chance there is a deal at all.
        """
        return _sigma(self.u_buyer(x) / self.lam) * _sigma(self.u_seller(x) / self.lam)

    def u_hat(self, x: np.ndarray, role: str) -> float:
        """Expected value of the deal: P(x) * U_i(x)."""
        return self.p_accept(x) * self.utility(x, role)

    def grad_u_hat(self, x: np.ndarray, role: str, h: float = 1e-5) -> np.ndarray:
        """Central differences, stepped in scaled units so all three terms get
        a comparable perturbation."""
        x = np.asarray(x, dtype=float)
        grad = np.zeros(3)
        for i in range(3):
            step = np.zeros(3)
            step[i] = h * SCALE[i]
            grad[i] = (self.u_hat(x + step, role) - self.u_hat(x - step, role)) / (
                2 * step[i]
            )
        return grad

    def concession_field(self, x: np.ndarray) -> np.ndarray:
        """F(x) = grad Uhat_B + grad Uhat_S — the net force on the draft.

        Note that at the equilibrium the *individual* gradients are large and
        opposite (each side still wants to pull price its way); only the sum
        vanishes. That asymmetry is why convergence and termination need two
        different certificates rather than one.
        """
        return self.grad_u_hat(x, "buyer") + self.grad_u_hat(x, "seller")

    # -------------------------------------------------- bargaining benchmark --

    def efficient_quantity(self) -> float:
        return (self.a - self.c) / (self.b + self.e)

    def efficient_deadline(self) -> float:
        if not self.deadline_active:
            return 0.0
        total = self.gamma_b + self.gamma_s
        if total <= 0:
            return 0.0
        return (self.gamma_b * self.d_b + self.gamma_s * self.d_s) / total

    def nash_bargaining_solution(self) -> tuple[np.ndarray, float]:
        """Closed form: efficient (q, d) plus an equal split of the surplus.

        Symmetric, transferable utility via price. Returns (x*, W_max).
        """
        q = self.efficient_quantity()
        d = self.efficient_deadline()
        w = (
            (self.a - self.c) * q
            - 0.5 * (self.b + self.e) * q**2
            - self._deadline_penalty(d, self.gamma_b, self.d_b)
            - self._deadline_penalty(d, self.gamma_s, self.d_s)
        )
        # U_S = p q - C(q) - Phi_S = W/2  =>  p q = W/2 + C(q) + Phi_S
        transfer = (
            0.5 * w
            + self.c * q
            + 0.5 * self.e * q**2
            + self._deadline_penalty(d, self.gamma_s, self.d_s)
        )
        return np.array([transfer / q, q, d]), w

    # ------------------------------------------------------------- scenarios --

    @classmethod
    def from_scenario(
        cls,
        business: Business,
        customer: Customer,
        quantities: dict[str, int] | None = None,
        curvature: float = 0.04,
        deadline_active: bool = False,
        lam: float | None = None,
    ) -> PayoffModel:
        """Calibrate to one marketplace pair.

        Two numbers in the data determine the economics, and both are already
        used for theta:

          * the seller's marginal cost c = min_price_factor * list price;
          * the buyer's reservation price r per unit, from menu_features.

        Those pin the efficient quantity to the quantity the customer actually
        asked for. Requiring q_eff = q_requested and marginal value = r at that
        quantity gives, uniquely,

            e = (r - c) / q_requested,      a = r + b * q_requested,

        leaving only the buyer curvature b as a modelling choice. Anchoring
        q_eff to the requested basket is the honest reading of a marketplace
        request: the customer asked for that much because that is what they
        want, so the efficient quantity should be there and not somewhere the
        calibration happened to put it.

        The acceptance temperature defaults to W_max / 4, matching the scale
        the formulation calibrates by hand (lambda = 60 against W_max = 241).

        Deadline preferences have no counterpart in the scenario data, so they
        are off by default. Turning them on means supplying d_b, d_s and the
        curvatures from somewhere else, and saying where.

        Raises ValueError when the pair has no positive bargaining zone — a
        buyer whose reservation price is at or below the seller's cost has
        nothing to negotiate about, and a calibration fitted to that would
        return a Nash solution with negative surplus.
        """
        quantities = quantities or {}

        reservation_total = 0.0
        cost_total = 0.0
        total_qty = 0.0
        for item, reservation in customer.menu_features.items():
            list_price = business.menu_features.get(item)
            if list_price is None:
                continue
            qty = float(quantities.get(item, 1))
            total_qty += qty
            reservation_total += float(reservation) * qty
            cost_total += float(list_price) * business.min_price_factor * qty

        if total_qty <= 0:
            raise ValueError(
                f"business {business.id} stocks none of customer {customer.id}'s "
                "requested items; no payoff model is definable for this pair"
            )

        r = reservation_total / total_qty
        c = cost_total / total_qty
        if r <= c:
            raise ValueError(
                f"pair {business.id}|{customer.id} has no bargaining zone: the "
                f"buyer's reservation price {r:.2f} is at or below the seller's "
                f"marginal cost {c:.2f}, so any agreement destroys surplus"
            )

        e = (r - c) / total_qty
        a = r + curvature * total_qty

        model = cls(
            a=a,
            b=curvature,
            c=c,
            e=e,
            deadline_active=deadline_active,
            lam=1.0,  # placeholder, replaced below
            provenance={
                "business": business.id,
                "customer": customer.id,
                "reservation_per_unit": r,
                "marginal_cost": c,
                "requested_quantity": total_qty,
                "curvature_is_a_modelling_choice": curvature,
            },
        )
        _, w_max = model.nash_bargaining_solution()
        return replace(model, lam=lam if lam is not None else max(w_max / 4.0, 1e-6))


def _sigma(u: float | np.ndarray) -> float | np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(u, -50, 50)))
