"""Client-side reconciliation: the sender learns what the server accepted.

The regulator rewrites proposals in flight, and the marketplace's stock agents
do not notice. ``BusinessAgent`` stores the proposal it *intends* to send and
appends it to the conversation history before the send completes, then ignores
``result.content`` on success. So under a filter the seller's books and the
seller's memory both hold terms that never reached anyone.

That is not cosmetic, and calling it cosmetic — as the first version of the arm
B note did — understates it in a way that matters. The stale history is fed
straight back into the prompt that generates the seller's next response
(``business/agent.py``: ``generate_response_to_inquiry(customer_id,
self.customer_histories[customer_id])``), so the seller concedes from a price it
never actually offered. It believed it had offered 13.76 when the buyer saw
11.58. The welfare accounting is computed from database payments and is
therefore unaffected, but the *behaviour* is not.

**This does not weaken the agent-agnostic claim, and the distinction is worth
being precise about.** The guarantee lives at the protocol: a seller that
ignores the response still cannot breach, because enforcement happens before
the message is persisted and delivered. What this mixin fixes is the seller's
own bookkeeping, which is a client concern, not a safety mechanism. Recording
what the server accepted rather than what you asked for is what any correct API
client does — a payment processor that returned an adjusted amount would be
handled the same way. No decision-making code is touched.

In deployment the consequence of not doing this is concrete: the seller would
invoice the pre-filter amount.
"""

from __future__ import annotations

from typing import Any

from magentic_marketplace.marketplace.actions import (
    Message,
    OrderProposal,
    SendMessage,
)


class ReconcilingAgentMixin:
    """Sync local state from the server's response after every send.

    Mixed in *before* the agent class so this ``send_message`` runs first:

        class GovernedBusinessAgent(ReconcilingAgentMixin, BusinessAgent): ...
    """

    async def send_message(self, to_agent_id: str, message: Message) -> Any:
        """Send, then reconcile if the server accepted something else."""
        result = await super().send_message(to_agent_id, message)  # type: ignore[misc]

        if getattr(result, "is_error", False):
            return result

        accepted = _accepted_message(result)
        if accepted is None or accepted == message:
            return result

        self._reconcile_sent_message(to_agent_id, message, accepted)
        return result

    # ------------------------------------------------------------------ --

    def _reconcile_sent_message(
        self, to_agent_id: str, sent: Message, accepted: Message
    ) -> None:
        """Replace the optimistic local record with what actually went out."""
        if isinstance(accepted, OrderProposal):
            self._reconcile_proposal_storage(to_agent_id, accepted)
        self._reconcile_history(to_agent_id, sent, accepted)

        logger = getattr(self, "logger", None)
        if logger is not None:
            logger.info(
                "Terms adjusted in flight by the marketplace; local records "
                "reconciled to the accepted message.",
                data={"to_agent_id": to_agent_id},
            )

    def _reconcile_proposal_storage(
        self, to_agent_id: str, accepted: OrderProposal
    ) -> None:
        """Point the stored proposal at the accepted terms.

        Matched by id, which the rewrite preserves precisely so that payment
        matching keeps working. Without this the payment confirmation quotes —
        and an invoice would charge — the pre-filter total.
        """
        storage = getattr(self, "proposal_storage", None)
        if storage is None:
            return
        stored = storage.get_proposal(accepted.id)
        if stored is not None:
            stored.proposal = accepted
            return
        # Never stored (a customer-side agent, or an unusual ordering): record
        # the accepted version rather than nothing.
        agent_id = getattr(self, "id", "")
        storage.add_proposal(accepted, agent_id, to_agent_id)

    def _reconcile_history(
        self, to_agent_id: str, sent: Message, accepted: Message
    ) -> None:
        """Rewrite the trailing history line, which the next prompt will read.

        The agent appends its own message to the history *after* the send
        returns, so at this point the entry does not exist yet and there is
        nothing to rewrite. Recording the correction here instead would be
        overwritten a moment later. So the accepted message is stashed and
        ``add_to_history`` substitutes it — see ``add_to_history`` below.
        """
        pending = getattr(self, "_accepted_messages", None)
        if pending is None:
            pending = {}
            self._accepted_messages = pending  # type: ignore[attr-defined]
        pending[(to_agent_id, id(sent))] = accepted

    def add_to_history(self, customer_id: str, message: Any, role: str) -> None:
        """Record what the server accepted, not what was proposed.

        Overridden rather than post-editing the history list because the agent
        formats entries itself and the formatting is not reversible from the
        string.
        """
        pending = getattr(self, "_accepted_messages", None)
        if pending:
            accepted = pending.pop((customer_id, id(message)), None)
            if accepted is not None:
                message = accepted
        super().add_to_history(customer_id, message, role)  # type: ignore[misc]


def _accepted_message(result: Any) -> Message | None:
    """Pull the message the server actually accepted out of the action result.

    Returns None rather than raising when the result is not a SendMessage echo:
    a reconciliation failure must not take down a negotiation.
    """
    content = getattr(result, "content", None)
    if not isinstance(content, dict):
        return None
    try:
        return SendMessage.model_validate(content).message
    except Exception:  # noqa: BLE001 - server responses are not ours to trust
        return None
