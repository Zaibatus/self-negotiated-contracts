"""Generate a bargaining scenario from a stock Magentic scenario. YAML only.

Why this exists. In the stock scenarios nobody haggles: a business quotes list
price, the customer pays, and the whole negotiation is two or three messages
long. That is fine for studying selection bias, but a contraction rate and an
energy decay need a *trajectory* — six to twelve alternating rounds of terms
moving. Without one, only the invariance half of the thesis can be measured on
live agents.

The fix is data, not code. ``Business.description`` and ``Customer.request``
flow verbatim into the agent prompts, so a bargaining scenario needs no change
to the marketplace, the agents, or the prompt templates. The testbed stays
stock; only the scenario is ours.

Two edits, both auditable, both applied identically to every arm:

  1. Sellers are told the discount authority they already have in the data.
     ``min_price_factor`` sits in every business YAML and, before this work,
     was read by no code path and no prompt — the seller was never told it
     could discount, so it never did. Telling it is a disclosure, not an
     invention.

  2. Buyers are given a budget below the cheapest available basket, and told
     to counter-offer before paying. The budget is written into
     ``menu_features`` as well as the request text, so the number in the prompt
     and the B of theta are the same number. A scenario where the agent is
     told one budget and the contract enforces another would measure the gap
     between them rather than the mechanism.

The budget is placed *inside the bargaining zone*: at ``zone_position`` of the
way from the seller's cost floor up to its list price, for the cheapest
business that can serve the basket. So it binds by construction — at list
price no deal fits and the seller must concede — while remaining feasible by
construction, for any dataset. A flat fraction of list price does not have
that property: min_price_factor reaches 0.93 in mexican_3_9, so a flat 0.92
budget is below one seller's floor and the contract it induces is
unsatisfiable rather than merely tight. The script still checks feasibility
and refuses, as a backstop.

Lower ``zone_position`` means a harder bargain and a longer negotiation.

Usage:
    uv run python scripts/make_bargain_scenario.py \\
        --source ../multi-agent-marketplace/data/mexican_3_9 \\
        --dest data/bargain_3_9
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
    out["description"] = f"{business['description'].strip()} {clause}"
    return out


def rewrite_customer(
    customer: dict[str, Any],
    businesses: list[dict[str, Any]],
    zone_position: float,
) -> tuple[dict[str, Any], dict[str, float]]:
    """Give the buyer a binding budget, consistent between prompt and theta."""
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
    out["request"] = (
        f"{customer['request'].strip()} {BUYER_CLAUSE.format(budget=budget)}"
    )

    return out, {
        "budget": budget,
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
    parser.add_argument("--dest", default="data/bargain_3_9")
    parser.add_argument(
        "--zone-position",
        type=float,
        default=0.35,
        help="where in the (cost floor, list price) bargaining zone to place the "
        "buyer's budget; lower means a harder bargain",
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
        rewritten, info = rewrite_customer(customer, businesses, args.zone_position)
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


if __name__ == "__main__":
    main()
