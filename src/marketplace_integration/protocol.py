"""The contract as a controller of the marketplace itself.

``GovernedMarketplaceProtocol`` subclasses Magentic's
``SimpleMarketplaceProtocol`` and intercepts ``SendMessage`` — the single
funnel every agent-to-agent message passes through.

Why here and not in the agents. The protocol is the only place with a view of
*all* concurrent negotiations at once, which is what the joint filter needs:
a coupling clause such as a shared supplier capacity touches several pairs in
one constraint row, and its dual is a market-wide shadow price. It also means
no agent class is forked, so the guarantee holds for whatever LLM is dropped
in — which is the whole content of "we certify the game, not the agents".

Three asymmetries are deliberate and are results, not shortcuts:

  * **Only seller moves are projected.** An ``OrderProposal`` is a structured,
    binding artefact, so it can be minimally adjusted and re-sent. A buyer's
    counter-offer is prose; rewriting it would mean putting words in an
    agent's mouth, and the thesis restricts itself to quantitative terms.
  * **Two trajectories per pair.** ``binding`` holds only proposal terms and
    is what the barrier constrains — the state of the contract is what is
    actually on the table. ``observed`` interleaves the buyer's extracted
    counter-offers and is what the round-pair energy consumes.
  * **The first proposal is projected, not recovered.** A DCBF governs
    transitions and needs a previous state; an opening offer has none.
    Forwarding a breaching opener while the barrier recovers geometrically
    would be a knowing breach, so the opening state is projected into C once.

Modes:
    "filter"  project proposals and rewrite the outgoing message
    "monitor" detect and record, forward the message untouched (arm D)
    "off"     record the trajectory only, no contract enforcement (arm A)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np
from magentic_marketplace.marketplace.actions import (
    ActionAdapter,
    OrderProposal,
    SendMessage,
    TextMessage,
)
from magentic_marketplace.marketplace.protocol.protocol import SimpleMarketplaceProtocol
from magentic_marketplace.platform.database.base import BaseDatabaseController
from magentic_marketplace.platform.shared.models import (
    ActionExecutionRequest,
    ActionExecutionResult,
    AgentProfile,
)

from ..certificates.dcbf import DCBFFilter, project_into_safe_set
from ..certificates.metrics import RoundRecord, make_round_record, summarise
from .terms import Terms, from_order_proposal, from_text, rewrite_proposal
from .theta import ContractRegistry, pair_key

Mode = Literal["filter", "monitor", "off"]


@dataclass
class PairState:
    """Everything the regulator remembers about one negotiation."""

    key: str
    business_id: str
    customer_id: str
    binding: list[np.ndarray] = field(default_factory=list)
    observed: list[np.ndarray] = field(default_factory=list)
    rounds: int = 0
    settled: bool = False
    opened_outside: bool | None = None
    unsatisfiable: bool = False

    @property
    def last_binding(self) -> np.ndarray | None:
        return self.binding[-1] if self.binding else None


class GovernedMarketplaceProtocol(SimpleMarketplaceProtocol):
    """Marketplace protocol with a DCBF contract layer under every message."""

    def __init__(
        self,
        registry: ContractRegistry,
        mode: Mode = "filter",
        gamma: float = 0.4,
        rho: float = 1e4,
        couple: bool = True,
        solver: str = "osqp",
    ):
        """Configure the regulator.

        Args:
            registry: theta for every definable pair.
            mode: "filter", "monitor" or "off" (see module docstring).
            gamma: DCBF rate. Also an economic policy parameter — a cautious
                filter parks negotiations short of the limits and inflates the
                shadow prices by a conservatism premium.
            rho: slack penalty in the QP.
            couple: enforce each business's shared-capacity clause across its
                concurrently open negotiations. Requires the registry to carry
                capacities; without them this has no effect.
            solver: "osqp" (standard) or "slsqp" (legacy, for A/B only).
        """
        super().__init__()
        self.registry = registry
        self.mode: Mode = mode
        self.couple = couple
        self.filter = DCBFFilter(gamma=gamma, rho=rho, solver=solver)
        self.states: dict[str, PairState] = {}
        self.records: list[RoundRecord] = []
        # Messages we could not govern, and why. Reported, never dropped.
        self.ungoverned: list[dict[str, str]] = []

    # ----------------------------------------------------------- interception --

    async def execute_action(
        self,
        *,
        agent: AgentProfile,
        action: ActionExecutionRequest,
        database: BaseDatabaseController,
    ) -> ActionExecutionResult:
        """Govern the message, then hand it to the stock protocol.

        The rewrite is an **in-place mutation of the caller's request**, and it
        has to be. The server route persists the request object it was handed
        (``platform/server/routes/actions.py``: ``ActionRowData(request=request,
        ...)``) and the recipient reads the message back out of the database, so
        anything the regulator does to a *copy* is computed, logged and then
        discarded — the counterparty still receives the original terms.

        That is not hypothetical. The first arm B run on bargain_3_9 used
        ``action.model_copy(...)`` here, and every filtered proposal reached the
        customer unfiltered: the certificate log recorded corrections to 11.58
        and 11.40 while the database, the buyer and the seller's confirmation
        all showed 13.76 and 11.12. The arm measured nothing. Worse, the
        integration tests passed throughout, because they asserted on
        ``result.content`` — which does carry the rewrite — rather than on what
        the caller was left holding.

        Mutating in place is therefore the enforcement point, not a shortcut
        around one. ``tests/test_marketplace_integration.py`` now asserts on the
        request object after the call for exactly this reason.
        """
        parsed = ActionAdapter.validate_python(action.parameters)

        if isinstance(parsed, SendMessage):
            replacement = self._govern(parsed)
            if replacement is not None:
                action.parameters = replacement.model_dump(mode="json")

        return await super().execute_action(
            agent=agent, action=action, database=database
        )

    def _govern(self, message: SendMessage) -> SendMessage | None:
        """Apply the contract layer. Returns a replacement message, or None."""
        if isinstance(message.message, OrderProposal):
            return self._on_proposal(message, message.message)
        if isinstance(message.message, TextMessage):
            self._on_text(message, message.message)
        return None

    # ------------------------------------------------------------ seller move --

    def _on_proposal(
        self, envelope: SendMessage, proposal: OrderProposal
    ) -> SendMessage | None:
        business_id, customer_id = envelope.from_agent_id, envelope.to_agent_id
        key = pair_key(business_id, customer_id)
        contract = self.registry.get(business_id, customer_id)

        if contract is None:
            self.ungoverned.append(
                {
                    "pair": key,
                    "proposal": proposal.id,
                    "reason": "no definable contract for this pair",
                }
            )
            return None

        try:
            terms = from_order_proposal(proposal)
        except ValueError as exc:
            self.ungoverned.append(
                {"pair": key, "proposal": proposal.id, "reason": str(exc)}
            )
            return None

        # The deadline rows only participate when a deadline was actually
        # stated; otherwise we would be enforcing terms nobody agreed to.
        effective = contract if terms.deadline_observed else contract.without_deadline()

        state = self.states.setdefault(
            key,
            PairState(key=key, business_id=business_id, customer_id=customer_id),
        )
        x_proposed = terms.vector

        if not effective.is_satisfiable():
            # C(theta) is empty: this seller's cost floor is above this buyer's
            # budget, so no terms could ever satisfy the contract. Projecting
            # into an empty set is not a safety operation, and every step would
            # degrade onto slack and read in aggregate as a filter that cannot
            # hold its constraints. The honest outcome here is "no deal", so we
            # record the breach and forward the message untouched.
            state.unsatisfiable = True
            self._record(state, effective, state.last_binding
                         if state.last_binding is not None else x_proposed,
                         x_proposed, x_proposed, None, terms)
            state.binding.append(x_proposed)
            state.observed.append(x_proposed)
            return None

        if state.last_binding is None:
            return self._open_negotiation(
                envelope, proposal, state, effective, terms, x_proposed
            )
        return self._continue_negotiation(
            envelope, proposal, state, effective, terms, x_proposed
        )

    def _open_negotiation(self, envelope, proposal, state, contract, terms, x_proposed):
        """First proposal of a pair: project into C rather than recover into it."""
        state.opened_outside = not contract.is_safe(x_proposed)

        if self.mode == "filter" and state.opened_outside:
            x_applied = project_into_safe_set(x_proposed, contract)
        else:
            x_applied = x_proposed.copy()

        replacement = None
        if self.mode == "filter" and not np.allclose(x_applied, x_proposed):
            new_proposal = rewrite_proposal(proposal, x_applied, contract)
            # Re-read the terms actually sent: rounding to cents means the
            # recorded trajectory must come from the message, not the intent.
            x_applied = from_order_proposal(new_proposal).vector
            replacement = envelope.model_copy(update={"message": new_proposal})

        self._record(
            state, contract, x_proposed, x_proposed, x_applied, None, terms
        )
        state.binding.append(x_applied)
        state.observed.append(x_applied)
        return replacement

    def _continue_negotiation(
        self, envelope, proposal, state, contract, terms, x_proposed
    ):
        """Subsequent proposals: the barrier governs the transition."""
        x_prev = state.last_binding
        assert x_prev is not None

        # The joint filter sees every live negotiation of this business, so the
        # coupling clause and its shadow price are computed against the true
        # market state. But only the message currently in flight can be
        # changed: a proposal already sent to another customer cannot be
        # retracted. So the peers enter with a zero proposed adjustment and
        # whatever adjustment the QP would like to make to them is discarded.
        # In effect the clause becomes a residual-capacity constraint on
        # whoever is moving now, which is also how a real regulator works — it
        # can only act on the transaction in front of it.
        peers = self._peers(state)
        xs = [x_prev] + [p.last_binding for p in peers]
        contracts = [contract] + [
            self.registry.get(p.business_id, p.customer_id) or contract for p in peers
        ]
        u_props = [x_proposed - x_prev] + [np.zeros(3) for _ in peers]
        capacity = (
            self.registry.capacity_for(state.business_id)
            if (self.couple and peers)
            else None
        )

        result = self.filter.step(xs, u_props, contracts, shared_capacity=capacity)

        x_applied = x_proposed.copy()
        replacement = None
        if self.mode == "filter":
            x_filtered = x_prev + result.u[:3]
            if not np.allclose(x_filtered, x_proposed):
                new_proposal = rewrite_proposal(proposal, x_filtered, contract)
                x_applied = from_order_proposal(new_proposal).vector
                replacement = envelope.model_copy(update={"message": new_proposal})
            else:
                x_applied = x_filtered

        self._record(state, contract, x_prev, x_proposed, x_applied, result, terms)
        state.binding.append(x_applied)
        state.observed.append(x_applied)
        return replacement

    # ------------------------------------------------------------- buyer move --

    def _on_text(self, envelope: SendMessage, message: TextMessage) -> None:
        """Record the buyer's counter-offer, if it states one. Never rewritten.

        This is the only extraction in the trusted computing base, and it is
        best-effort by design: a message that names no terms is not a move in
        term space, and inventing one would feed noise into the energy that
        would read as revealed remaining gain.
        """
        customer_id, business_id = envelope.from_agent_id, envelope.to_agent_id
        key = pair_key(business_id, customer_id)
        state = self.states.get(key)
        if state is None or state.last_binding is None:
            return

        terms = from_text(message, fallback_quantity=float(state.last_binding[1]))
        if terms is None:
            return
        state.observed.append(terms.vector)

    # ------------------------------------------------------------- internals --

    def _peers(self, state: PairState) -> list[PairState]:
        """The business's other negotiations that are live and have a state."""
        if not self.couple:
            return []
        if self.registry.capacity_for(state.business_id) is None:
            return []
        return [
            other
            for other in self.states.values()
            if other.business_id == state.business_id
            and other.key != state.key
            and other.last_binding is not None
            and not other.settled
        ]

    def _record(
        self,
        state: PairState,
        contract,
        x_prev: np.ndarray,
        x_proposed: np.ndarray,
        x_applied: np.ndarray,
        result,
        terms: Terms,
    ) -> None:
        record = make_round_record(
            pair_id=state.key,
            round_index=state.rounds,
            mode=self.mode,
            contract=contract,
            x_prev=x_prev,
            x_proposed=x_proposed,
            x_applied=x_applied,
            result=result,
            pair_slot=0,
            business_id=state.business_id,
            customer_id=state.customer_id,
            extraction={
                "source": terms.source,
                "exact": str(terms.exact),
                "deadline_observed": str(terms.deadline_observed),
            },
        )
        self.records.append(record)
        state.rounds += 1

    # -------------------------------------------------------------- reporting --

    def report(self) -> dict[str, float]:
        """Headline safety numbers plus the solver's reliability profile."""
        out = summarise(self.records)
        out.update({f"solver_{k}": v for k, v in self.filter.reliability().items()})
        out["pairs_opened_outside_C"] = float(
            sum(1 for s in self.states.values() if s.opened_outside)
        )
        out["pairs_unsatisfiable"] = float(
            sum(1 for s in self.states.values() if s.unsatisfiable)
        )
        out["ungoverned_messages"] = float(len(self.ungoverned))
        return out

    def trajectories(self, binding: bool = False) -> dict[str, list[np.ndarray]]:
        """Per-pair term trajectories, for the energy layer."""
        return {
            key: (state.binding if binding else state.observed)
            for key, state in self.states.items()
        }
