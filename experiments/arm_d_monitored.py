"""Arm D — same contract, detection only. The runtime-monitor baseline.

Identical theta and identical bookkeeping to arm B, with one difference: the
regulator never rewrites a proposal. It sees the breach, records it, and lets
it through.

The comparison B vs D is the one that isolates *projecting* from *flagging*.
An AgentSpec-style runtime monitor can tell you a contract was broken; the
question this arm answers is how much of the safety result comes from
detection and how much from the minimally-invasive correction. Any welfare
difference between B and D is the price of the correction, not of the
contract, since both arms carry the same contract.

    uv run python experiments/arm_d_monitored.py --experiment arm_d_v1
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from experiments._common import main_for  # noqa: E402

main = main_for("monitor", __doc__ or "")

if __name__ == "__main__":
    main()
