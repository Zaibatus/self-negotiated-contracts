"""Contracts as reward transfers — the Christoffersen et al. baseline, ported.

This is the comparator the thesis argues against, implemented on the same
testbed so the two mechanisms can be measured against the same scenario and the
same theta. Chapter 2 differentiates them in one line: *reward transfers make
the good outcome an equilibrium; this work bounds every intermediate step.*
Until now that contrast was conceptual. This module makes it measurable.

Reference: Christoffersen, Haupt & Hadfield-Menell, "Get It in Writing: Formal
Contracts Mitigate Social Dilemmas in Multi-Agent RL", AAMAS 2023
(arXiv:2208.10469v3). Their code is MIT-licensed at
github.com/Algorithmic-Alignment-Lab/contracts, built on RLlib.

**A notation collision, stated once.** They write a contract ``theta``; so do
we, and they are different objects. Theirs is a *transfer function*
``theta: (S x A) u {acc} -> R^N`` whose range is zero-sum. Ours is the
*constraint vector* ``theta = (B, c, q_min, q_max, d_min, d_max)`` defining a
safe set. Throughout this module, ``theta`` alone means ours, and the transfer
function is always named ``transfer`` or ``schedule``.

What is ported, and what could not be
-------------------------------------

Ported faithfully:

  * **The transfer is zero-sum.** Their Definition 2.2 requires
    ``sum_i theta_i = 0``, so a contract redistributes and never creates or
    destroys value. ``TransferSchedule.transfer`` returns a vector that sums to
    zero exactly, and a test pins it.
  * **The transfer is state-dependent.** It is a function of the proposed terms
    ``x = (p, q, d)``, which is this testbed's state-action pair.
  * **It is bounded.** Their Theorem 3.1 quantifies richness as transfers
    bounded by ``R_max / (1 - gamma)``. ``cap`` is that bound.
  * **It is pre-specified and binding.** Both parties are told the schedule
    before negotiating, and it settles automatically on the deal that closes.

Not ported, because the substrate will not carry it:

  * **The learning loop.** Their agents are RL policies that maximise expected
    discounted reward, and Theorem 3.1 is a statement about the subgame-perfect
    equilibria such agents converge to. A language model has no reward channel
    and no training loop here. There is nothing for a transfer to act *on*
    except the agent's reading of its own instructions.
  * **Unanimous acceptance as a game stage.** Their augmented game has a
    proposer stage and an ``acc`` action, and rejection returns the null
    contract. Modelling that faithfully would need agents that can compute
    whether accepting improves their continuation value. Instead the schedule
    is disclosed and acceptance is *assumed*, which is the most favourable
    possible reading of the baseline: it is handed the agreement its mechanism
    would have had to earn.

Both omissions favour the baseline, and that is deliberate. If it still fails
to bound anything, the failure is not an artefact of a weak implementation.

The only channel a transfer has
-------------------------------

Because there is no reward signal, the schedule reaches the agents the one way
anything reaches a language model: as text in its context, via the scenario
YAML. That is the same mechanism ``make_bargain_scenario.py`` uses for the
budget, so the marketplace, the agent classes and the prompt templates stay
stock and only the scenario differs.

It is worth being explicit that this costs the baseline the property this
thesis's filter has. Enforcement at the protocol never touches an agent; a
transfer must be *told* to one. Chapter 2 evaluates instruction-in-the-prompt
and measures what it delivers: 86% of proposals still breach. The prediction
registered in the arm F note is that a transfer clause lands in the same place,
because a payment that changes the value of a breach does not make the breach
undeliverable.

Which rows the transfer covers
------------------------------

Only the budget row. That is not a simplification of convenience: across every
arm and both scenarios, *every observed breach is on the budget row* — sellers
never violate the cost floor or the quantity bounds. Extending the transfer to
the other rows would need a unit convention converting days and units into
currency, which no result here would exercise. ``violation`` therefore returns
the budget overshoot in currency, and ``full_violation`` is offered for the
generalisation with its unit caveat attached rather than hidden.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..contract import Contract

# Index convention for the zero-sum vector, fixed once.
BUYER, SELLER = 0, 1
N_PARTIES = 2


@dataclass(frozen=True)
class TransferSchedule:
    """A zero-sum, state-dependent, bounded transfer derived from ``theta``.

    The schedule is built from the *same* contract the DCBF filter would
    enforce, so arms B and F encode the same commercial constraint and differ
    only in what the marketplace does about it.

    Args:
        contract: the theta this schedule is derived from.
        rate: multiple of the breach paid across. ``rate=1.0`` makes a breach
            exactly break-even for the seller, which is the weakest schedule
            that removes the gain from breaching. Above 1.0 it is a penalty.
        cap: the bound of Theorem 3.1's richness condition, in currency.
            ``None`` means unbounded, which is richer than their theorem needs
            and again favours the baseline.
    """

    contract: Contract
    rate: float = 1.0
    cap: float | None = None

    def __post_init__(self) -> None:
        if self.rate < 0:
            raise ValueError("rate must be non-negative; a negative transfer "
                             "would pay the seller for breaching")
        if self.cap is not None and self.cap < 0:
            raise ValueError("cap must be non-negative")

    # ------------------------------------------------------------ violation --

    def violation(self, x: np.ndarray) -> float:
        """Budget overshoot at terms ``x``, in currency. Zero inside C(theta).

        This is ``max(0, p*q - B)`` — the amount by which the deal exceeds what
        the buyer may spend. It is the true bilinear quantity, not a linearised
        one: a transfer settles on a concrete deal, so there is no round-to-round
        approximation to make.
        """
        x = np.asarray(x, dtype=float)
        return float(max(0.0, x[0] * x[1] - self.contract.budget))

    def full_violation(self, x: np.ndarray) -> np.ndarray:
        """Per-row violation amounts, for the generalisation.

        **Units are not commensurable across rows** — the budget row is in
        currency, the quantity rows in units, the deadline rows in days — so
        these must not be summed without a stated conversion. No result in this
        work exercises a non-budget breach, so no conversion is defined here.
        """
        return np.maximum(0.0, -self.contract.h(np.asarray(x, dtype=float)))

    # ------------------------------------------------------------- transfer --

    def amount(self, x: np.ndarray) -> float:
        """The size of the transfer at ``x``, after rate and cap."""
        t = self.rate * self.violation(x)
        if self.cap is not None:
            t = min(t, self.cap)
        return float(t)

    def transfer(self, x: np.ndarray) -> np.ndarray:
        """The zero-sum transfer vector at ``x``, indexed [BUYER, SELLER].

        The seller pays and the buyer receives, because it is the seller that
        proposes terms above the budget. Sums to zero exactly, which is
        Definition 2.2's constraint and is pinned by a test rather than assumed.
        """
        t = self.amount(x)
        out = np.zeros(N_PARTIES, dtype=float)
        out[BUYER] = +t
        out[SELLER] = -t
        return out

    def is_null(self, x: np.ndarray, tol: float = 1e-9) -> bool:
        """True where the schedule does nothing, i.e. terms comply."""
        return self.amount(x) <= tol

    # ---------------------------------------------------------------- text --

    def clause(self) -> str:
        """The clause disclosed to both agents in the scenario YAML.

        This is the only channel the transfer has. It states the schedule in
        the terms an agent can act on: what triggers it, who pays, how much.
        """
        cap = ""
        if self.cap is not None:
            cap = f" The transfer is capped at ${self.cap:.2f}."
        multiple = (
            "the full amount of the excess"
            if abs(self.rate - 1.0) < 1e-9
            else f"{self.rate:.2f} times the excess"
        )
        return (
            "Binding side agreement, already accepted by both parties: if the "
            f"total agreed price exceeds ${self.contract.budget:.2f}, the seller "
            f"pays the buyer {multiple} on settlement, automatically and without "
            f"dispute.{cap} Both parties are bound by this and neither can opt "
            "out. Take it into account when deciding what to propose or accept."
        )


# ---------------------------------------------------------------- settlement --


@dataclass(frozen=True)
class Settlement:
    """What a schedule actually moved on one settled deal."""

    pair_id: str
    terms_total: float
    violation: float
    transfer_buyer: float
    transfer_seller: float

    @property
    def zero_sum_residual(self) -> float:
        """How far this settlement is from zero-sum. Should be exactly 0.0."""
        return abs(self.transfer_buyer + self.transfer_seller)


def settle(schedule: TransferSchedule, pair_id: str, x: np.ndarray) -> Settlement:
    """Settle a schedule against the terms a deal actually closed at."""
    x = np.asarray(x, dtype=float)
    tr = schedule.transfer(x)
    return Settlement(
        pair_id=pair_id,
        terms_total=float(x[0] * x[1]),
        violation=schedule.violation(x),
        transfer_buyer=float(tr[BUYER]),
        transfer_seller=float(tr[SELLER]),
    )


def summarise(settlements: list[Settlement]) -> dict[str, float]:
    """Arm-level numbers for the transfer baseline.

    ``residual_overspend`` is the point of comparison with arm B. A transfer
    redistributes the overspend; it does not remove it. The buyer is made whole
    in currency, and the deal still closed outside C(theta) — so if the question
    is whether the marketplace can promise that no deal breaches, a transfer
    does not answer it. Both numbers are reported so the distinction is visible
    rather than argued.
    """
    if not settlements:
        return {"deals": 0.0}
    breaching = [s for s in settlements if s.violation > 1e-9]
    return {
        "deals": float(len(settlements)),
        "deals_breaching": float(len(breaching)),
        "deals_breaching_rate": len(breaching) / len(settlements),
        "residual_overspend": float(sum(s.violation for s in settlements)),
        "transferred_total": float(sum(s.transfer_buyer for s in settlements)),
        "value_transacted": float(sum(s.terms_total for s in settlements)),
        "max_zero_sum_residual": float(
            max(s.zero_sum_residual for s in settlements)
        ),
    }
