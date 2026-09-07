"""Generate a scenario in which one business serves two customers. YAML only.

Limitation C4 says "coupling has never run on live agents. No business serves
two customers, so the shared-capacity clause, the equilibrium displacement and
the shadow prices exist only in simulation." That is true of the DATA, not of
the code: `protocol.py` already carries a `couple` flag, `registry.capacity_for`
and peer detection, and both arm scripts already expose `--capacity-factor`.
Nothing has ever set them because every shipped scenario is partitioned --
businesses 1-3 serve customer_0001, 4-6 serve customer_0002, 7-9 serve
customer_0003, one customer each by construction.

THE EDIT, and it is one line of data. `business_0001` gains
"Jalapeno Infused Tequila Sunrise", the single item `customer_0002` requests, so
it can serve both customer_0001 and customer_0002. Nothing else changes: no
description text, no min_price_factor, no reservation price, no other menu
entry, and no code.

THE PRICE is the median list price of the three businesses that already stock
that item (8.31, 8.66, 11.30 -> 8.66). A median rather than a minimum or a
choice of my own, because the number decides whether the new pair is
satisfiable and should not be tuned to the answer. With business_0001's shipped
min_price_factor of 0.78 the floor is 6.75, below customer_0002's reservation of
7.45, so the pair is tradeable -- checked, not assumed, and the script refuses
if it is not.

CAPACITY is supplied at registry construction, not in the YAML:
`ContractRegistry.from_data_dir(..., capacity_factor=f)` sets
Q = f * (total quantity the business's customers could demand). business_0001
then faces demand of 3 units (2 from customer_0001, 1 from customer_0002), so
f = 0.67 gives Q = 2 and the clause binds. Pass `--capacity-factor` to the arm.

WHAT THIS DOES NOT FIX. The scenario is still authored, and section 5.2's
lesson applies with full force: an authored scenario changes more than the
variable it was authored to change. Adding an item to a menu adds a business to
customer_0002's choice set, which changes competition as well as coupling. Any
result must be read against `bargain_3_9` with that confound stated.

Run:
    uv run python scripts/make_coupled_scenario.py --force
    uv run python experiments/arm_b_imposed.py --data data/coupled_3_9 \
        --capacity-factor 0.67 --experiment coupled_b_v1 --override
"""

from __future__ import annotations

import argparse
import shutil
import statistics
import sys
from pathlib import Path

import yaml

COUPLED_ITEM = "Jalapeno Infused Tequila Sunrise"
HOST_BUSINESS = "business_0001"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="data/bargain_3_9")
    parser.add_argument("--dest", default="data/coupled_3_9")
    parser.add_argument("--item", default=COUPLED_ITEM)
    parser.add_argument("--host", default=HOST_BUSINESS)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    source, dest = Path(args.source), Path(args.dest)
    if dest.exists():
        if not args.force:
            raise SystemExit(f"{dest} already exists; pass --force to overwrite")
        shutil.rmtree(dest)
    shutil.copytree(source, dest)

    bdir = dest / "businesses"
    prices = []
    for path in sorted(bdir.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        if args.item in (data.get("menu_features") or {}):
            prices.append(float(data["menu_features"][args.item]))
    if not prices:
        raise SystemExit(f"no business stocks {args.item!r}; nothing to copy a price from")
    list_price = round(statistics.median(prices), 2)

    host_path = bdir / f"{args.host}.yaml"
    host = yaml.safe_load(host_path.read_text())
    if args.item in host["menu_features"]:
        raise SystemExit(f"{args.host} already stocks {args.item!r}")
    floor = list_price * float(host["min_price_factor"])

    reservations = []
    for path in sorted((dest / "customers").glob("*.yaml")):
        cust = yaml.safe_load(path.read_text())
        if args.item in (cust.get("menu_features") or {}):
            reservations.append(float(cust["menu_features"][args.item]))
    if not reservations:
        raise SystemExit(f"no customer requests {args.item!r}")
    reservation = max(reservations)
    if reservation <= floor:
        raise SystemExit(
            f"refusing: floor {floor:.2f} is at or above the buyer's reservation "
            f"{reservation:.2f}, so the new pair would have no bargaining zone"
        )

    host["menu_features"][args.item] = list_price
    host_path.write_text(yaml.safe_dump(host, sort_keys=False, allow_unicode=True))

    print(f"source {source} -> {dest}")
    print(f"  {args.host} gains {args.item!r} at list {list_price:.2f} "
          f"(median of {len(prices)} stockists: {prices})")
    print(f"  min_price_factor {host['min_price_factor']} -> floor {floor:.2f}")
    print(f"  buyer reservation {reservation:.2f} -> bargaining zone "
          f"{reservation - floor:+.2f} per unit")
    print("  nothing else changed.")


if __name__ == "__main__":
    main()
