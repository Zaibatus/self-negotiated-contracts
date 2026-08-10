"""Term extraction: Magentic messages -> the term vector x = (p, q, d).

This is the layer that replaces the scripted ``proposal`` of the synthetic
prototype, and it is deliberately asymmetric — which is itself a result worth
stating rather than a wart to hide.

**Seller moves are exact.** ``OrderProposal`` is a structured message carrying
``items[].unit_price``, ``items[].quantity``, ``total_price`` and
``estimated_delivery``. Nothing is inferred; the term vector is read off. So
the "term extraction is in the trusted computing base" risk
(formulation.md section 7.2) does *not* apply to the side that emits the
binding numbers.

**Buyer moves are noisy.** Counter-offers arrive as free-text
``TextMessage``. Regex first, and an injectable LLM extractor only when the
regex finds nothing. This is the entire residual extraction surface, and
isolating it here is what makes the planned extraction-noise robustness
experiment a measurement rather than a hand-wave.

Aggregation to R^3, for orders with several line items:

    q = sum_i quantity_i
    p = total_price / q          (quantity-weighted mean unit price)
    d = parse_days(estimated_delivery)

chosen so that h1 = B - p*q is *exactly* B - total_price, preserving the
bilinear structure the formulation analyses. Per-item stacking (x in R^{3m})
is the natural generalisation and is not implemented here.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from magentic_marketplace.marketplace.actions.messaging import (
    OrderItem,
    OrderProposal,
    TextMessage,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..contract import Contract

# --------------------------------------------------------------------------
# Deadline parsing
# --------------------------------------------------------------------------

_UNIT_DAYS: dict[str, float] = {
    "minute": 1.0 / 1440.0,
    "min": 1.0 / 1440.0,
    "hour": 1.0 / 24.0,
    "hr": 1.0 / 24.0,
    "day": 1.0,
    "business day": 1.0,
    "week": 7.0,
    "month": 30.0,
}

# "2-3 business days", "45 minutes", "about 1 week", "24 hrs"
_DURATION = re.compile(
    r"(?P<lo>\d+(?:\.\d+)?)\s*(?:-|to|–)?\s*(?P<hi>\d+(?:\.\d+)?)?\s*"
    r"(?P<unit>minutes?|mins?|hours?|hrs?|business\s+days?|days?|weeks?|months?)",
    re.IGNORECASE,
)

_MONEY = re.compile(r"(?:[$£€]\s*(\d+(?:,\d{3})*(?:\.\d+)?))|"
                    r"(?:(\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:dollars|usd|pounds|eur))",
                    re.IGNORECASE)

_QUANTITY = re.compile(
    r"(?:(\d+)\s*(?:x|units?|items?|pieces?|servings?|portions?))|"
    r"(?:(?:quantity|qty)\s*(?:of|:|=)?\s*(\d+))|"
    r"(?:(\d+)\s+of\s+(?:them|these|those))",
    re.IGNORECASE,
)


def parse_days(text: str | None) -> float | None:
    """Best-effort duration -> days. None when nothing parses.

    Returning None is the point: ``estimated_delivery`` is optional and free
    text, and the caller deactivates the deadline rows rather than inventing a
    value. Enforcing a deadline nobody stated would be enforcing the wrong
    contract.

    Ranges take the upper end — the deadline the customer would actually be
    held to.
    """
    if not text:
        return None
    match = _DURATION.search(text)
    if not match:
        return None
    unit = re.sub(r"\s+", " ", match.group("unit").strip().lower())
    unit = unit.rstrip("s")
    if unit.startswith("business day"):
        unit = "business day"
    days_per = _UNIT_DAYS.get(unit)
    if days_per is None:
        # Singularisation left something odd, e.g. "hrs" -> "hr"
        days_per = _UNIT_DAYS.get(unit.rstrip("."), None)
    if days_per is None:
        return None
    hi = match.group("hi")
    value = float(hi) if hi is not None else float(match.group("lo"))
    return value * days_per


# --------------------------------------------------------------------------
# Extraction results
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Terms:
    """x = (p, q, d) plus the provenance needed to audit the extraction."""

    price: float
    quantity: float
    deadline: float | None
    source: str  # "order_proposal" | "text_regex" | "text_llm"
    exact: bool  # True only when read from structured fields
    fields: dict[str, float | str] = field(default_factory=dict)

    @property
    def vector(self) -> np.ndarray:
        """x in R^3. A missing deadline becomes 0.0 and is masked off, never
        silently treated as 'immediately'."""
        return np.array(
            [self.price, self.quantity, 0.0 if self.deadline is None else self.deadline]
        )

    @property
    def deadline_observed(self) -> bool:
        return self.deadline is not None


def from_order_proposal(proposal: OrderProposal) -> Terms:
    """Exact terms from a structured seller proposal.

    ``total_price`` is taken as authoritative for p*q — the marketplace
    already validates it against sum(unit_price * quantity), and using it
    directly is what makes the budget row exact rather than nearly exact.
    """
    quantity = float(sum(item.quantity for item in proposal.items))
    if quantity <= 0:
        raise ValueError(f"proposal {proposal.id} has non-positive total quantity")
    total = float(proposal.total_price)
    return Terms(
        price=total / quantity,
        quantity=quantity,
        deadline=parse_days(proposal.estimated_delivery),
        source="order_proposal",
        exact=True,
        fields={
            "proposal_id": proposal.id,
            "total_price": total,
            "n_items": float(len(proposal.items)),
            "estimated_delivery": proposal.estimated_delivery or "",
        },
    )


LLMExtractor = Callable[[str], "Terms | None"]


def from_text(
    message: TextMessage | str,
    fallback_quantity: float,
    llm_extractor: LLMExtractor | None = None,
    current_price: float | None = None,
) -> Terms | None:
    """Best-effort terms from a free-text buyer counter-offer.

    Regex first; the injectable ``llm_extractor`` is consulted only when the
    regex finds no price, so the expensive and less predictable path runs as
    rarely as possible. Returns None when neither finds anything — a message
    that states no terms is not a move in term space, and fabricating one
    would put noise into the trajectory that the energy would then read as
    revealed gain.

    ``fallback_quantity`` is the quantity currently on the table, used when the
    buyer names a price but no quantity (the common case: "can you do $12?").

    ``current_price`` is the unit price already on the table, and supplying it
    closes a real extraction defect that ran for the whole project. Buyers
    habitually restate the seller's quote before naming their own number:

        "The current quote of $13.76 is above my budget of $11.58."

    ``_MONEY.search`` returns the *first* figure, so the extractor recorded the
    buyer as counter-offering at $13.76 — the price the seller had just asked
    for — and silently discarded $11.58, which is the only number in the
    sentence the buyer actually owns. Both halves are wrong: a fabricated move
    to the seller's own ask, and the real position dropped.

    So every figure is considered, those equal to the price on the table are
    discarded as echoes, and the first survivor is the buyer's position. When
    every figure is an echo the message states no position and returns None,
    which is correct whether the buyer was accepting or rejecting: in neither
    case is it a *new* point in term space.

    Measured over the 25 stored arm A/B/D runs, **110 of 125 extracted buyer
    "moves" (88%) were echoes**. The published drift, funnelling and safety
    results are unaffected because they are computed on the *binding*
    trajectory (seller proposals, exact structured terms) or on database
    outcomes; the corrupted surface is the *observed* trajectory, which is what
    arm C's inference reads — which is why arm C is where this surfaced.
    """
    content = message.content if isinstance(message, TextMessage) else message

    matches = list(_MONEY.finditer(content))
    quantity_match = _QUANTITY.search(content)

    if not matches:
        if llm_extractor is not None:
            return llm_extractor(content)
        return None

    quantity = fallback_quantity
    if quantity_match is not None:
        qty_raw = next(g for g in quantity_match.groups() if g is not None)
        quantity = float(qty_raw)

    # A buyer quoting a bare figure is usually quoting the *total*, not a unit
    # price. Disambiguate only when the text says so explicitly.
    per_unit = bool(re.search(r"\b(each|per\s+(?:unit|item|piece))\b", content, re.I))

    def unit(match: re.Match[str]) -> float:
        raw = next(g for g in match.groups() if g is not None)
        value = float(raw.replace(",", ""))
        return value / quantity if not per_unit and quantity > 0 else value

    # Every money figure in the message, not just the first. Buyers habitually
    # restate the seller's quote before naming their own number -- "The current
    # quote of $13.76 is above my budget of $11.58" -- and taking `.search()`
    # returned the seller's figure while discarding the buyer's. Dropping the
    # echoes leaves the buyer's own position, which is the move we are after.
    chosen = next(
        (
            m
            for m in matches
            if current_price is None or abs(unit(m) - current_price) >= 0.005
        ),
        None,
    )
    if chosen is None:
        # Every figure in the message was the price already on the table, so
        # the buyer stated no position of its own. Not a move in term space.
        return None

    return Terms(
        price=unit(chosen),
        quantity=quantity,
        deadline=parse_days(content),
        source="text_regex",
        exact=False,
        fields={"matched": chosen.group(0), "per_unit": str(per_unit)},
    )


# --------------------------------------------------------------------------
# Writing filtered terms back onto a proposal
# --------------------------------------------------------------------------


def rewrite_proposal(
    proposal: OrderProposal,
    x: np.ndarray,
    contract: Contract | None = None,
    max_cent_steps: int = 40,
) -> OrderProposal:
    """Project a proposal onto filtered terms, keeping it internally consistent.

    The marketplace validates ``total_price == sum(unit_price * quantity)``
    when the business generates a proposal, and matches payments against
    stored proposals by id. So a rewrite that only edited ``total_price``
    would produce a message the marketplace itself rejects.

    Quantity is distributed over line items in proportion to the original mix,
    with at least 1 unit per surviving item, and unit prices are scaled by the
    common factor that makes the line items sum to the filtered total. The
    proposal id is preserved: this is the same proposal, adjusted, and
    breaking the id would break payment matching.

    **Quantisation is repaired toward the interior when a contract is given.**
    Prices are money, so they round to the cent, and the QP's exact solution
    does not generally land on a cent boundary. Rounding to nearest then puts
    the realised total marginally outside C(theta) about half the time it
    matters. Measured before this repair existed: every governed round on one
    bargain_3_9 pair breached the budget row by exactly one penny, ten rounds
    out of ten — not noise but a systematic bias, and enough to make "zero
    breaches" false as stated. A safety filter that must quantise should
    quantise *into* the safe set, so the cents are nudged until the true h is
    satisfied.

    Only price-adjustable rows can be repaired this way. A quantity or deadline
    breach survives, and is left visible rather than papered over.
    """
    price, quantity = float(x[0]), float(x[1])
    target_total = price * quantity

    original_qty = sum(item.quantity for item in proposal.items)
    if original_qty <= 0:
        raise ValueError(f"proposal {proposal.id} has non-positive total quantity")

    target_qty = max(1, int(round(quantity)))
    quantities = _distribute(target_qty, [item.quantity for item in proposal.items])

    base_total = sum(
        item.unit_price * qty for item, qty in zip(proposal.items, quantities)
    )
    scale = (target_total / base_total) if base_total > 0 else 1.0

    items: list[OrderItem] = []
    for item, qty in zip(proposal.items, quantities):
        items.append(
            item.model_copy(
                update={
                    "quantity": qty,
                    "unit_price": round(item.unit_price * scale, 2),
                }
            )
        )

    total = round(sum(i.unit_price * i.quantity for i in items), 2)
    rebuilt = proposal.model_copy(update={"items": items, "total_price": total})
    if contract is None:
        return rebuilt
    return _repair_quantisation(rebuilt, contract, max_cent_steps)


def _repair_quantisation(
    proposal: OrderProposal, contract: Contract, max_cent_steps: int
) -> OrderProposal:
    """Nudge unit prices by whole cents until the true h is satisfied.

    Moves the *largest* line item, so the fewest cents shift the total the
    furthest, and gives up rather than looping if the breach is on a row price
    cannot fix.
    """
    mask = contract.active_mask()
    for _ in range(max_cent_steps):
        values = contract.h(from_order_proposal(proposal).vector)
        if bool(np.all(values[mask] >= 0.0)):
            return proposal
        if mask[0] and values[0] < 0:
            step = -0.01  # over budget: come down
        elif mask[1] and values[1] < 0:
            step = 0.01  # under the cost floor: come up
        else:
            return proposal  # quantity or deadline: not a price problem

        items = list(proposal.items)
        target = max(range(len(items)), key=lambda i: items[i].unit_price)
        new_price = round(items[target].unit_price + step, 2)
        if new_price <= 0:
            return proposal
        items[target] = items[target].model_copy(update={"unit_price": new_price})
        proposal = proposal.model_copy(
            update={
                "items": items,
                "total_price": round(
                    sum(i.unit_price * i.quantity for i in items), 2
                ),
            }
        )
    return proposal


def _distribute(target: int, weights: list[int]) -> list[int]:
    """Split ``target`` units across line items in proportion to ``weights``.

    Every item keeps at least one unit — dropping a line item is a change of
    what is being bought, not an adjustment of terms, and the filter has no
    mandate for that.
    """
    n = len(weights)
    if n == 0:
        return []
    target = max(target, n)
    total_weight = sum(weights) or n
    raw = [max(1.0, target * w / total_weight) for w in weights]
    out = [max(1, int(v)) for v in raw]

    # Hand out (or claw back) the rounding remainder, largest fractional part
    # first, never taking an item below 1.
    diff = target - sum(out)
    order = sorted(range(n), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    idx = 0
    while diff != 0 and idx < 10 * n:
        i = order[idx % n]
        if diff > 0:
            out[i] += 1
            diff -= 1
        elif out[i] > 1:
            out[i] -= 1
            diff += 1
        idx += 1
    return out
