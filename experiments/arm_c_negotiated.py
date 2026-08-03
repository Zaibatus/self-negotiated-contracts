"""Arm C — bilaterally negotiated contract. The central treatment arm.

SCAFFOLD, and it says so rather than running. The regulator, the theta
representation and the enforcement path this arm needs are all built and
tested; the theta-negotiation pre-phase is not. Falling back to arm B's imposed
theta would produce a full report that looked like a result and would not be
one, so this exits instead.

Design, for the record.

Arms B and D impose theta from scenario data. Arm C makes theta the *outcome*
of a negotiation: before haggling over terms, the two agents agree the rulebook
they will haggle inside. Because theta is a vector, that agreement is an
ordinary negotiation over R^6 and the same two-layer machinery applies one
level up. A signed agreement is then the pair (x*, theta) — what was agreed,
under which invariant rules.

Already here:
  * theta as a vector, so "agreeing a contract" is agreeing six numbers, and
    "renegotiating" is moving in theta-space (src/contract.py);
  * the refinement order C' <= C iff C(theta') is a subset of C(theta), which
    is what makes "a stricter contract" a well-defined notion for agents to
    converge on (Contract.refines);
  * enforcement of an arbitrary theta at the protocol layer, whatever its
    provenance (src/marketplace_integration/protocol.py);
  * a satisfiability check, so an agreed theta with an empty safe set is
    detectable rather than merely unproductive (Contract.is_satisfiable).

Missing, and this is the actual research content of the arm:

  1. A message type for proposing and accepting theta. The stock marketplace
     has TextMessage, OrderProposal and Payment, and none carries a rulebook.
     Either encode theta in a structured TextMessage payload — keeps the
     testbed stock, costs extraction reliability — or add a ContractProposal
     message, which is clean but forks the protocol's action set.
  2. A fallback when the agents fail to agree. No-deal is the honest default;
     the alternative, quietly imposing theta, makes the arm a mixture of B and
     C and must not be silent.
  3. Whether the pre-phase counts against T_max. It is negotiation time, so it
     probably should, and that decision changes the liveness certificate.
  4. What the marketplace does when the agreed theta is unsatisfiable. Two
     agents can agree an impossible contract; is_satisfiable detects it, but
     the response is a design decision rather than a bug.

Open question for supervision: should agents negotiate theta directly, or
negotiate x and have theta *inferred* from the envelope of their positions?
The second needs no new message type and may be closer to how commitments
actually form — a party discovers its own red line by approaching it.
"""

from __future__ import annotations


def main() -> None:
    print(__doc__)
    print(
        "Not run: the theta-negotiation pre-phase is unimplemented.\n"
        "Arm B (imposed theta) and arm D (monitor only) are runnable today."
    )
    raise SystemExit(2)


if __name__ == "__main__":
    main()
