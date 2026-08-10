"""Arm C — the self-negotiated contract, inferred and then enforced.

The central treatment of the original design, and the one the repository is
named after: theta is not imposed by the platform but agreed between the
agents, and only then enforced against them.

It is *inferred* rather than exchanged, which is the design decision that keeps
the rest of the thesis intact. Adding a "propose terms of engagement" message
would fork the agent classes and kill the agent-agnostic claim that arms B and
D rest on. Instead the two opening positions the agents already state -- the
seller's opening ask and the buyer's first counter -- are read as the envelope
they have jointly committed to, and the DCBF-QP holds the negotiation inside
it. See ``src/marketplace_integration/inference.py`` for why those two numbers
are the right object.

Everything else is arm B: same filter, same gamma, same scenario, same code
path. The arms differ in exactly one thing, which is where theta comes from.

    uv run python experiments/arm_c_negotiated.py --experiment arm_c_v1

The pre-phase is counted against T_max by default; pass
``--no-prephase-counts-against-tmax`` to measure the enforced window alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import build_parser, run_arm  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.set_defaults(theta_source="inferred")
    args = parser.parse_args()
    if args.theta_source != "inferred":
        parser.error("arm C is theta_source='inferred' by definition")
    run_arm(args, mode="filter")


if __name__ == "__main__":
    main()
