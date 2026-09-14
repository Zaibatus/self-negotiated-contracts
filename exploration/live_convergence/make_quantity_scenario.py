"""Generate a bargaining scenario in which QUANTITY is also negotiable.

Side exploration, not thesis material. A copy of
``scripts/make_bargain_scenario.py`` with one addition, kept separate rather
than edited in place so the thesis generator stays byte-identical.

**Why.** Across 3,865 stored rounds quantity moved in 11 (0.3%), always by an
item being dropped, and deadline never. Every live trajectory in the
dissertation is therefore one-dimensional in price. A convergence rate measured
on such a path cannot distinguish "the filter changed the dynamics" from "the
filter moved the single free scalar", and the constrained rest point sits on a
face rather than in the interior of any axis.

**The addition.** Two clauses, VOLUME_SELLER_CLAUSE and VOLUME_BUYER_CLAUSE,
appended after the price clauses this script already writes. The seller is told
it may win volume by quoting a lower unit price for a larger order; the buyer is
told it will take more units if the unit price falls, subject to the same total
cap. Both are disclosures of room that theta already contains — ``q_max`` is
``ceil(q_min * q_max_factor)`` and has always been 2x the basket — not new
authority.

**Why quantity is then forced to bind.** B is the reservation total for one unit
of each item and is placed inside the bargaining zone, so B is only slightly
above ``c * q_min``. If the seller upsells to q > q_min then ``c * q > B``
necessarily: the budget row cannot be satisfied by cutting price alone, because
price is floored at c. The QP must cut quantity. That is a corner of C(theta)
where two rows are active at once, and it is what makes the trajectory
two-dimensional.

Everything else — source scenario, zone position, budget split, disclosure
flags — is inherited unchanged, so a run of this against
``--disclosed-budget-factor 0.90`` differs from ``disclosed_offset_low_3_9`` in
the volume clauses and nothing else.

Usage:
    uv run python exploration/live_convergence/make_quantity_scenario.py \
        --source ../multi-agent-marketplace/data/mexican_3_9 \
        --dest exploration/live_convergence/data/quantity_off09_3_9 \
        --disclosed-budget-factor 0.90
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from typing import Any

import yaml

SELLER_CLAUSE = (
    "Pricing policy: the listed prices are opening prices, not final ones. "
    "You are authorised to negotiate and may go as low as {floor_pct:.0f}% of any "
    "listed price — for example {example_item} lists at ${example_list:.2f} and you "
    "may go to ${example_floor:.2f}. You must never quote below that floor, because "
    "below it the order loses money. Open at or near list price, concede gradually "
    "when a customer pushes back, and put every revised price in a new order "
    "proposal so the customer has something concrete to accept."
)

BUYER_CLAUSE = (
    "Budget: I can spend at most ${budget:.2f} in total, and I must not exceed it. "
    "The first quote I receive will probably be above that, so do not accept it. "
    "Ask the business for a better price, and keep negotiating — several rounds if "
    "necessary — until the total is within my budget. Only pay once a proposal is "
    "at or under ${budget:.2f}."
)


VOLUME_SELLER_CLAUSE = (
    " Volume: you may also win the order on size rather than on price alone. "
    "If the customer will take more than one unit of an item, you may quote a "
    "lower unit price for the whole order — never below your floor — and you "
    "should prefer a larger order at a reduced unit price to a single unit at "
    "list. State the quantity of every item explicitly in the order proposal."
)

VOLUME_BUYER_CLAUSE = (
    " Quantity: I will take more than one unit of an item if that brings the "
    "unit price down, and you should ask whether it does. My total spend is "
    "still capped at the figure above, so a larger order only helps me if the "
    "unit price falls enough to keep the total within it. Say how many units I "
    "would take at the unit price being offered."
)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def dump_yaml(data: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(data, handle, sort_keys=False, allow_unicode=True, width=88)


def cheapest_basket(
    businesses: list[dict[str, Any]], items: list[str]
) -> tuple[float, float, str | None]:
    """Cheapest total, and that business's floor total, over businesses that
    stock every requested item.

    Returns (list_total, floor_total, business_id). A customer no business can
    serve gets (inf, inf, None) and is left untouched — inventing demand for
    an item nobody sells is not a bargaining scenario, it is a broken one.
    """
    best = (float("inf"), float("inf"), None)
    for business in businesses:
        menu = business.get("menu_features", {})
        if not all(item in menu for item in items):
            continue
        list_total = sum(float(menu[item]) for item in items)
        floor_total = list_total * float(business["min_price_factor"])
        if list_total < best[0]:
            best = (list_total, floor_total, business["id"])
    return best


def rewrite_business(business: dict[str, Any]) -> dict[str, Any]:
    """Disclose the discount authority already present in the data."""
    menu = business.get("menu_features", {})
    if not menu:
        return business
    factor = float(business["min_price_factor"])
    example_item, example_list = max(menu.items(), key=lambda kv: float(kv[1]))
    clause = SELLER_CLAUSE.format(
        floor_pct=factor * 100.0,
        example_item=example_item,
        example_list=float(example_list),
        example_floor=float(example_list) * factor,
    )
    out = dict(business)
    out["description"] = (
        f"{business['description'].strip()} {clause}{VOLUME_SELLER_CLAUSE}"
    )
    return out


def rewrite_customer(
    customer: dict[str, Any],
    businesses: list[dict[str, Any]],
    zone_position: float,
    disclose_budget: bool = True,
    disclosed_budget_factor: float = 1.0,
) -> tuple[dict[str, Any], dict[str, float]]:
    """Give the buyer a binding budget, consistent between prompt and theta.

    With ``disclose_budget=False`` the budget still lands in ``menu_features``
    — so theta, and the platform, are unchanged — but the request text says
    nothing about it and does not instruct the buyer to refuse. The buyer then
    has a genuine willingness-to-pay ceiling it has not been told about, which
    is what makes harm possible and therefore what makes harm-averted
    measurable.
    """
    items = list(customer.get("menu_features", {}))
    list_total, floor_total, source = cheapest_basket(businesses, items)
    if source is None:
        return customer, {}

    budget = round(floor_total + zone_position * (list_total - floor_total), 2)
    if not floor_total < budget < list_total:
        raise ValueError(
            f"customer {customer['id']}: budget {budget:.2f} is not strictly "
            f"inside the bargaining zone ({floor_total:.2f}, {list_total:.2f}) "
            "— the contract would be unsatisfiable or non-binding. Choose a "
            "--zone-position strictly inside (0, 1)."
        )

    # Split the budget across items in proportion to their cheapest list price,
    # so that sum(menu_features.values()) == budget exactly and theta's B is
    # the number the prompt states.
    shares = _split(budget, [_cheapest_item(businesses, item) for item in items])
    out = dict(customer)
    out["menu_features"] = {item: share for item, share in zip(items, shares)}
    stated = round(budget * disclosed_budget_factor, 2)
    if disclose_budget:
        out["request"] = (
            f"{customer['request'].strip()} "
            f"{BUYER_CLAUSE.format(budget=stated)}{VOLUME_BUYER_CLAUSE}"
        )
    # Undisclosed: the request is left exactly as the stock scenario wrote it.
    # Nothing is added and nothing is removed, so the only difference from the
    # disclosed variant is the absence of the budget clause.

    return out, {
        "budget": budget,
        "stated_budget": stated,
        "disclosed_budget_factor": disclosed_budget_factor,
        "cheapest_list_total": list_total,
        "cheapest_floor_total": floor_total,
        "headroom_over_floor": budget - floor_total,
        "discount_needed_pct": 100.0 * (list_total - budget) / list_total,
    }


def _cheapest_item(businesses: list[dict[str, Any]], item: str) -> float:
    prices = [
        float(b["menu_features"][item])
        for b in businesses
        if item in b.get("menu_features", {})
    ]
    return min(prices) if prices else 1.0


def _split(total: float, weights: list[float]) -> list[float]:
    """Split total across weights, rounded to cents, summing exactly to total."""
    weight_sum = sum(weights) or len(weights)
    shares = [round(total * w / weight_sum, 2) for w in weights]
    shares[-1] = round(total - sum(shares[:-1]), 2)
    return shares


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source", default="../multi-agent-marketplace/data/mexican_3_9"
    )
    parser.add_argument(
        "--dest",
        default="exploration/live_convergence/data/quantity_off09_3_9",
    )
    parser.add_argument(
        "--zone-position",
        type=float,
        default=0.35,
        help="where in the (cost floor, list price) bargaining zone to place the "
        "buyer's budget; lower means a harder bargain",
    )
    parser.add_argument(
        "--no-disclose-budget",
        dest="disclose_budget",
        action="store_false",
        help="derive theta from the budget but do NOT tell the buyer about it "
        "(the G1 experiment: makes harm possible, so harm-averted is "
        "measurable)",
    )
    parser.add_argument(
        "--disclosed-budget-factor",
        type=float,
        default=1.0,
        help="tell the buyer a budget of f times the real one, while theta "
        "still uses the real one. f = 1.0 is the disclosed scenario and f "
        "below 1 makes the buyer more cautious than the mandate requires; "
        "f above 1 is the interesting case, a buyer that believes it may "
        "spend more than the platform will permit",
    )
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source, dest = Path(args.source), Path(args.dest)
    if dest.exists():
        if not args.force:
            raise SystemExit(f"{dest} already exists; pass --force to overwrite")
        shutil.rmtree(dest)

    businesses = [load_yaml(p) for p in sorted((source / "businesses").glob("*.yaml"))]
    customers = [load_yaml(p) for p in sorted((source / "customers").glob("*.yaml"))]

    for business in businesses:
        dump_yaml(
            rewrite_business(business), dest / "businesses" / f"{business['id']}.yaml"
        )

    header = (
        f"{'customer':<16}{'budget':>10}{'cheapest list':>16}"
        f"{'cost floor':>13}{'discount needed':>18}"
    )
    print(header)
    print("-" * len(header))
    for customer in customers:
        rewritten, info = rewrite_customer(
            customer, businesses, args.zone_position, args.disclose_budget,
            args.disclosed_budget_factor,
        )
        dump_yaml(rewritten, dest / "customers" / f"{customer['id']}.yaml")
        if info:
            print(
                f"{customer['id']:<16}{info['budget']:>10.2f}"
                f"{info['cheapest_list_total']:>16.2f}"
                f"{info['cheapest_floor_total']:>13.2f}"
                f"{info['discount_needed_pct']:>17.1f}%"
            )
        else:
            print(f"{customer['id']:<16}{'unservable — left unchanged':>39}")

    # Carry over anything else the scenario ships (e.g. baseline_utilities.json),
    # flagged rather than silently reused: those baselines were computed at list
    # prices and do not describe this scenario.
    for extra in source.glob("*.json"):
        shutil.copy(extra, dest / extra.name)
        print(
            f"\nCopied {extra.name} — NOTE: computed at list prices for the source "
            "scenario, so it is not a valid welfare baseline here."
        )

    print(f"\nWrote {dest}")
    if not args.disclose_budget:
        print(
            "  Budget NOT disclosed to the buyer: theta is identical to the "
            "disclosed\n  variant, and the request text is the only difference."
        )


if __name__ == "__main__":
    main()
