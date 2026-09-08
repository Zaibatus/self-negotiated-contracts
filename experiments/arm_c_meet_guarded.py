"""Arm C-meet-guarded — composition with a fallback when the meet is empty.

Arm C-meet enforces ``theta_negotiated AND theta_mandate``. Section 5.10.1 of
the dissertation reports that this stops governing entirely at a two per cent
disclosure offset: the meet's floor times the minimum quantity exceeds the
meet's budget, the safe set is empty, and the protocol forwards the pair
unfiltered under limitation B4. Corrections go from 14 of 67 governed rounds at
f = 1.00 to **0 of 68** at f = 1.02 and never recover.

That is a design artefact rather than a fact about composition. B4's
pass-through is correct when *nothing* can comply. Here the mandate alone is
satisfiable on the same pair: the platform holds a valid contract and declines
to enforce it because a *different*, stricter contract turned out to be empty.

The guarded rule, stated in the lattice: enforce the greatest satisfiable lower
bound of {theta_neg, theta_man} that is at or below theta_man. When the meet is
non-empty that element is the meet. When the meet is empty it is theta_man
itself. Only when theta_man is *also* empty does B4's pass-through apply, which
is the case the four unsatisfiable pairs on bargain_3_9 are in.

This arm differs from ``arm_c_meet.py`` in exactly one line: the theta source.

PREDICTIONS, registered before any run of this arm existed and scored in
``docs/notes/2026-09-08-guarded-meet-results.md``. The pre-registration note is
``docs/notes/2026-09-08-PREREGISTRATION-guarded-meet.md``.

    G1  At every f in {1.00, 1.02, 1.05, 1.10} the guarded meet has 0 breaches
        on governed rounds and GBP 0.00 overspend -- the same as arm B at that
        f. This is the load-bearing one: if it fails, the guarded rule does not
        recover the guarantee and the condition Chapter 8 states must stand.

    G2  Closure at each f is within seed noise of arm B at that f (17 deals at
        f = 1.1). Falling back to the mandate should not cost trade, because the
        mandate is exactly what arm B enforces.

    G3  At f = 1.00 the guarded meet is identical to arm C-meet: the fallback
        never fires on a satisfiable meet, so the numbers reproduce the C-meet
        column of Table 5.8 up to seed noise.

    G4  At f >= 1.02 the fallback fires on most frozen instances, and the
        negotiated side still binds where the buyer countered at or below the
        mandate ceiling.

    uv run python experiments/arm_c_meet_guarded.py \
        --data data/offset_102_3_9 --experiment arm_c_meet_guarded_102_v1
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import build_parser, run_arm  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.set_defaults(theta_source="guarded_meet")
    args = parser.parse_args()
    if args.theta_source != "guarded_meet":
        parser.error("arm C-meet-guarded is theta_source='guarded_meet' by definition")
    run_arm(args, mode="filter")


if __name__ == "__main__":
    main()
