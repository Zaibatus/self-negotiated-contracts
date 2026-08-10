"""Arm C — theta inferred from the agents' own opening positions.

Arms B and D impose theta: it is derived from the scenario data by
``Contract.from_scenario`` and neither agent agreed to it, or is even told it
exists. That is a *regulator*. The repository is called self-negotiated
contracts because the design's central treatment is the other one — a contract
the two parties settle between themselves, which is then enforced against them.

The obvious way to build that is a new message type ("propose terms of
engagement"), and it is the wrong way: it forks the agents, and the
agent-agnostic claim in the module docstring of ``protocol.py`` dies with it.
So the contract is *inferred* from what the agents already say.

## The envelope, and why it is the right object

Two positions are stated before any deal is struck:

* the seller's **opening ask** ``p_s`` — the price it is asking for
* the buyer's **first counter** ``p_b`` — the price it says it will pay

Each is a self-binding commitment in the only direction it can be. A seller
that opened at ``p_s`` cannot coherently demand *more* later; a buyer that
offered ``p_b`` cannot coherently offer *less*. The zone of possible agreement
they have jointly staked out is ``[p_b, p_s]``, and the contract that enforces
it is exactly theta's two price rows:

    h1 = B - p*q >= 0    with  B = p_s * q   ->  p <= p_s   (seller's own ask)
    h2 = p - c   >= 0    with  c = p_b       ->  p >= p_b   (buyer's own offer)

So both rows come from the agents' own words, and neither party can be pushed
outside the range it itself opened. Note the safe set is non-empty **by
construction** whenever ``p_b < p_s``, which is what makes this different from
the imposed contract: the imposed theta is unsatisfiable on four of nine pairs
because a cost floor and a budget set by two unrelated bits of scenario data
need not overlap. An envelope of two live positions always does.

## What this does not do, and it matters

The inferred contract enforces **what the agents agreed**, which is not the
same as what an external mandate requires. ``B = p_s * q`` is the *seller's
opening ask*, and on this scenario that sits above the customer's true
reservation, so a pair can honour its self-negotiated contract perfectly while
breaching the scenario theta that arm B enforces. That is not a bug in the
inference — it is the substantive difference between a contract and a
regulation, and arm C is reported against **both** thetas for that reason.

## Structural terms are not inferred

Only the price rows are negotiated. ``q_min``/``q_max`` are the customer's
requested basket and ``d_min``/``d_max`` the deadline band: those are the
*subject* of the negotiation, not positions taken in it, and a quantity band
inferred from one observation would be a band of width zero. They carry over
from the scenario contract unchanged, and the note records this as the one
place arm C is not purely self-negotiated.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..contract import Contract


@dataclass
class Positions:
    """The two opening positions of one pair, and the contract they imply.

    ``frozen`` is the point of the class. The envelope is fixed the moment both
    sides have spoken and is never revised afterwards, because a contract that
    tracked the latest positions would be renegotiated every round and would
    constrain nothing — each concession would simply move the boundary to wherever
    the conceding party had just arrived.
    """

    seller_ask: float | None = None
    buyer_offer: float | None = None
    quantity: float | None = None
    contract: Contract | None = None
    frozen_at_round: int | None = None
    # Why no contract was inferred, when none was. Reported, never silent.
    failure: str | None = None

    @property
    def is_frozen(self) -> bool:
        return self.contract is not None

    def note_seller(self, price: float, quantity: float) -> None:
        """Record the seller's opening ask. Later asks are ignored."""
        if self.seller_ask is None:
            self.seller_ask = float(price)
            self.quantity = float(quantity)

    def note_buyer(self, price: float) -> None:
        """Record the buyer's first counter. Later counters are ignored."""
        if self.buyer_offer is None:
            self.buyer_offer = float(price)

    def try_freeze(self, base: Contract, round_index: int) -> Contract | None:
        """Build the envelope once both sides have stated a price.

        Args:
            base: the scenario contract, for the structural terms only
                (quantity band, deadline band). Its price rows are discarded.
            round_index: the round at which the freeze happened, recorded so
                the pre-phase length is measurable rather than assumed.

        Returns:
            The inferred contract, or None while the pre-phase is still open.
        """
        if self.is_frozen:
            return self.contract
        if self.seller_ask is None or self.buyer_offer is None:
            return None

        quantity = self.quantity or base.q_min
        if self.buyer_offer >= self.seller_ask:
            # The buyer offered at or above the ask. There is no zone to
            # enforce -- the negotiation is already over on price -- and an
            # envelope with c >= B/q is empty, so we would be filtering into an
            # impossible set. Left ungoverned and counted.
            self.failure = (
                f"buyer offer {self.buyer_offer:.2f} >= seller ask "
                f"{self.seller_ask:.2f}: no zone to enforce"
            )
            return None

        self.contract = Contract(
            budget=self.seller_ask * quantity,
            cost_floor=self.buyer_offer,
            q_min=base.q_min,
            q_max=base.q_max,
            d_min=base.d_min,
            d_max=base.d_max,
        )
        self.frozen_at_round = round_index
        return self.contract


@dataclass
class InferenceReport:
    """How the pre-phase went, across every pair. Printed with the arm."""

    pairs: dict[str, Positions] = field(default_factory=dict)

    def summary(self) -> dict[str, float]:
        total = len(self.pairs)
        frozen = [p for p in self.pairs.values() if p.is_frozen]
        never = [p for p in self.pairs.values() if not p.is_frozen]
        out: dict[str, float] = {
            "pairs_seen": float(total),
            "pairs_frozen": float(len(frozen)),
            "pairs_never_frozen": float(len(never)),
            "freeze_rate": float(len(frozen) / total) if total else 0.0,
        }
        if frozen:
            rounds = [p.frozen_at_round or 0 for p in frozen]
            out["mean_prephase_rounds"] = float(sum(rounds) / len(rounds))
            out["max_prephase_rounds"] = float(max(rounds))
            widths = [
                (p.seller_ask or 0.0) - (p.buyer_offer or 0.0) for p in frozen
            ]
            out["mean_zone_width"] = float(sum(widths) / len(widths))
        return out

    def failures(self) -> list[dict[str, str]]:
        """Pairs that ran ungoverned, and why. An honest outcome, not an error."""
        return [
            {
                "pair": key,
                "reason": p.failure
                or (
                    "buyer never stated a price: no counter-offer to infer a "
                    "budget row from"
                ),
            }
            for key, p in sorted(self.pairs.items())
            if not p.is_frozen
        ]
