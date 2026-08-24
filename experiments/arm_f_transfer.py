"""Arm F — the contract as a reward transfer (the Christoffersen et al. baseline).

The comparator Chapter 2 differentiates against, now measured on the same
testbed rather than argued about. Reference: Christoffersen, Haupt &
Hadfield-Menell, AAMAS 2023 (arXiv:2208.10469v3); mechanism and porting notes in
``src/marketplace_integration/transfers.py``.

**What differs from arm B, and it is one thing.** Both encode the *same* theta —
the transfer scenario is generated from ``bargain_3_9`` without touching
``menu_features``, and ``ContractRegistry`` reads the same B on all 9 pairs
(verified, not assumed). Arm B enforces that constraint at the message path.
Arm F prices it: a binding, zero-sum transfer obliges the seller to pay the
buyer the excess on settlement, and both parties are told so.

**The regulator runs in ``monitor`` mode, and that is not a shortcut.** A
transfer does not touch the message path — that is what makes it a different
mechanism rather than a differently-tuned filter. Monitor mode records the
trajectory and the breaches and rewrites nothing, which is exactly the
observational stance a transfer regime needs. Arms D and F therefore share a
code path and differ only in the scenario, so any difference between them is
attributable to the clause and nothing else.

**Registered before the run**, so it cannot be retrofitted:

  1. Offered breach rate stays in arm A/D territory (0.82-0.86), not arm B's
     0.472. A transfer changes the payoff of a breach; it does not make the
     breach undeliverable, and nothing in the message path is altered.
  2. Settled breaches stay above zero. This is the load-bearing prediction: arm
     B settles 0.000 and the whole thesis claim is that a per-round bound is
     what buys that.
  3. Residual overspend stays above zero even though the buyer is made whole in
     currency. A transfer redistributes; it does not prevent. If overspend
     reaches zero here, the thesis's central contrast is weaker than claimed
     and Chapter 5 has to say so.
  4. Some effect is plausible on *settled* terms even so, because the buyer is
     told the seller must repay any excess, which gives an informed buyer one
     more reason to hold out. If arm F beats arm D on settled breaches, that is
     the baseline working through the only channel it has — instruction — and
     it should be reported as such rather than as enforcement.

Prediction 4 is the one worth watching. It is the honest version of "does the
baseline do anything at all", and the answer being *yes, a little* would not
threaten the thesis: Chapter 2 already measures what instruction delivers.

    uv run python scripts/make_transfer_scenario.py --dest data/transfer_3_9
    uv run python experiments/arm_f_transfer.py --data data/transfer_3_9 \
        --t-max 6 --experiment arm_f_v1
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import main_for  # noqa: E402

# Monitor, deliberately: a transfer prices a breach, it does not intercept one.
main = main_for("monitor", __doc__ or "")

if __name__ == "__main__":
    main()
