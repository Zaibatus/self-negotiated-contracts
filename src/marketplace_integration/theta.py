"""Scenario YAML -> theta, for every (business, customer) pair.

Agent ids are the scenario ids (``BusinessAgentProfile.from_business`` sets
``id=business.id``), so a pair key is simply the two agent ids that appear on
a ``SendMessage``. No name resolution is needed anywhere.

Nothing here invents a number that the data already contains. In particular
``Business.min_price_factor`` — present in every business YAML in the
Magentic datasets and, before this, read by no code path and no prompt — is
the seller's cost floor as a fraction of list price, which is exactly the c of
theta. See ``Contract.from_scenario``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from magentic_marketplace.experiments.utils import (
    load_businesses_from_yaml,
    load_customers_from_yaml,
)
from magentic_marketplace.marketplace.shared.models import Business, Customer

from ..contract import Contract, ContractSpec


def pair_key(business_id: str, customer_id: str) -> str:
    """Canonical pair identifier, used as the key of every per-pair record."""
    return f"{business_id}|{customer_id}"


@dataclass
class ContractRegistry:
    """theta for every definable pair in a scenario, plus the coupling clause.

    Pairs where the business stocks none of the customer's requested items
    have no definable contract; they are recorded in ``undefinable`` rather
    than given a default, because a contract over items that cannot be sold
    would constrain nothing while looking like governance.
    """

    spec: ContractSpec
    contracts: dict[str, Contract] = field(default_factory=dict)
    businesses: dict[str, Business] = field(default_factory=dict)
    customers: dict[str, Customer] = field(default_factory=dict)
    undefinable: list[str] = field(default_factory=list)
    # Pairs with a definable but *unsatisfiable* theta: the business's cost
    # floor sits above the customer's budget, so C(theta) is empty and no deal
    # is possible. Kept separate from `contracts` consumers via
    # `satisfiable_pairs`, because enforcing an impossible contract and
    # enforcing a strict one look identical in aggregate metrics and are not
    # the same thing.
    unsatisfiable: list[str] = field(default_factory=list)
    # Shared per-business capacity Q of h_shared = Q - sum_j q_j over that
    # business's concurrently open negotiations. None means uncoupled.
    capacity: dict[str, float] = field(default_factory=dict)

    # ------------------------------------------------------------- loading --

    @classmethod
    def from_data_dir(
        cls,
        data_dir: str | Path,
        spec: ContractSpec | None = None,
        capacity_factor: float | None = None,
    ) -> ContractRegistry:
        """Build the registry from a Magentic data directory.

        Args:
            data_dir: a scenario folder containing businesses/ and customers/.
            spec: the modelling knobs (quantity band, deadline band, T_max).
            capacity_factor: if set, each business gets a shared capacity
                Q = capacity_factor * (total quantity its customers could
                request). Below 1.0 the clause binds and the coupled
                equilibrium moves to the generalised Nash point — which is the
                regime where anchored certificates fail and the shadow prices
                become observable.
        """
        spec = spec or ContractSpec()
        data_path = Path(data_dir)
        businesses = load_businesses_from_yaml(data_path / "businesses")
        customers = load_customers_from_yaml(data_path / "customers")
        return cls.from_participants(
            businesses, customers, spec=spec, capacity_factor=capacity_factor
        )

    @classmethod
    def from_participants(
        cls,
        businesses: list[Business],
        customers: list[Customer],
        spec: ContractSpec | None = None,
        capacity_factor: float | None = None,
    ) -> ContractRegistry:
        """Build the registry from already-loaded profiles."""
        spec = spec or ContractSpec()
        registry = cls(
            spec=spec,
            businesses={b.id: b for b in businesses},
            customers={c.id: c for c in customers},
        )

        for business in businesses:
            for customer in customers:
                key = pair_key(business.id, customer.id)
                try:
                    contract = Contract.from_scenario(business, customer, spec)
                except ValueError:
                    registry.undefinable.append(key)
                    continue
                registry.contracts[key] = contract
                if not contract.is_satisfiable():
                    registry.unsatisfiable.append(key)

        if capacity_factor is not None:
            for business in businesses:
                demand = sum(
                    contract.q_min
                    for key, contract in registry.contracts.items()
                    if key.startswith(f"{business.id}|")
                )
                registry.capacity[business.id] = capacity_factor * demand

        return registry

    # ------------------------------------------------------------- lookups --

    def get(self, business_id: str, customer_id: str) -> Contract | None:
        """theta for a pair, or None when no contract is definable."""
        return self.contracts.get(pair_key(business_id, customer_id))

    def is_satisfiable(self, business_id: str, customer_id: str) -> bool:
        """Does this pair have a non-empty safe set?"""
        contract = self.get(business_id, customer_id)
        return contract is not None and contract.is_satisfiable()

    def capacity_for(self, business_id: str) -> float | None:
        """Q of the coupling clause for a business, or None when uncoupled."""
        return self.capacity.get(business_id)

    def pairs_of_business(self, business_id: str) -> list[str]:
        """Every definable pair this business participates in."""
        prefix = f"{business_id}|"
        return sorted(k for k in self.contracts if k.startswith(prefix))

    def summary(self) -> dict[str, float]:
        """Coverage numbers, reported so that silent gaps cannot pass as care."""
        total = len(self.contracts) + len(self.undefinable)
        return {
            "businesses": float(len(self.businesses)),
            "customers": float(len(self.customers)),
            "pairs_total": float(total),
            "pairs_defined": float(len(self.contracts)),
            "pairs_undefinable": float(len(self.undefinable)),
            "pairs_unsatisfiable": float(len(self.unsatisfiable)),
            "pairs_tradeable": float(len(self.contracts) - len(self.unsatisfiable)),
            "coupled_businesses": float(len(self.capacity)),
        }
