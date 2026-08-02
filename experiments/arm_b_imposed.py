"""Arm B — externally imposed contract, enforced by the DCBF regulator.

theta comes from the scenario data (the buyer's reservation prices give B, the
seller's min_price_factor gives c) and is imposed on the marketplace: neither
agent agreed to it, and neither is told it exists. The regulator projects every
order proposal onto the safe set before it is delivered.

This is the live-LLM replication of F1 — breach rate to zero, convergence and
surplus preserved — with the scripted concession model replaced by whatever
the LLM actually does.

    uv run python experiments/arm_b_imposed.py --experiment arm_b_v1
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import main_for  # noqa: E402

main = main_for("filter", __doc__ or "")

if __name__ == "__main__":
    main()
