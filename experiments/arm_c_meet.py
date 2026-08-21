"""Arm C-meet — the negotiated contract composed with the platform mandate.

Arm C established that a self-negotiated theta is enforced exactly as reliably
as an imposed one (0 breaches over 136 enforced rounds) and yet does *not*
deliver the mandate: the negotiated theta refined the platform's contract on
**none of the 9 pairs**, its budget row looser on every one by 1.05-1.52x and
identically in every seed, because both opening positions are deterministic
given the scenario. (Corrected 2026-08-21: this said "0 of 29 envelopes", the
pooled form retracted in SCIENCE.md section 9 -- the 29 are 9 pairs observed
across 1-5 seeds each and are not independent.)

The fix is composition. The enforced contract here is

    theta_enforced = theta_negotiated  AND  theta_mandate

the meet in the refinement lattice (``Contract.meet``): componentwise min on
the upper bounds, max on the lower bounds, with
C(a AND b) = C(a) intersect C(b) exactly -- see ``tests/test_contract_algebra.py``,
which is the first thing in this project to check that algebra rather than
assert it, and which found ``Contract.refines`` wrong on the deadline case.

The pre-phase is identical to arm C: agents state positions, the envelope is
frozen once both have spoken. Only the contract handed to the filter differs,
so arms C and C-meet differ in exactly one thing.

    uv run python experiments/arm_c_meet.py --experiment arm_c_meet_v1

The pre-phase counts against T_max by default; see
``--no-prephase-counts-against-tmax``.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import build_parser, run_arm  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.set_defaults(theta_source="meet")
    args = parser.parse_args()
    if args.theta_source != "meet":
        parser.error("arm C-meet is theta_source='meet' by definition")
    run_arm(args, mode="filter")


if __name__ == "__main__":
    main()
