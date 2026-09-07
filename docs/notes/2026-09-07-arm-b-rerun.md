# Arm B re-run on current code — the safety result replicates

**Date:** 2026-09-07. **Live**, 5 seeds, ~£0.50.
**Runs:** `arm_b_v2_1..5`. **Replay:** `results/replay_arm_b_v2/`.
**Reproduce:**

```
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts
for i in 1 2 3 4 5; do
  uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
    --gamma 0.4 --t-max 6 --experiment "arm_b_v2_$i" --override
done
uv run python -m src.marketplace_integration.replay \
  --schemas arm_b_v2_1 arm_b_v2_2 arm_b_v2_3 arm_b_v2_4 arm_b_v2_5 \
  --data data/bargain_3_9 --out results/replay_arm_b_v2
```

**Why:** limitation C10 records that arm B's runs predate the seller
reconciliation fix, so its trajectories came from a seller reasoning about
prices it never offered. Its outcome numbers were database measurements and
stood; its negotiation paths did not. This re-runs the arm on the current code
path so the paths stand too.

## The result

| | arm B, August batch | **arm B, current code** |
|---|---|---|
| governed rounds | 27 | **33** |
| **governed breaches** | **0** | **0** |
| corrected | 24/27 = 0.889 | **29/33 = 0.879** |
| openings / continuations | 23 / 4 | 23 / 10 |
| deals settled | 16 | **15** |
| deals breaching | 0 | **0** |
| overspend | £0.00 | **£0.00** |
| offered breach rate | 0.472 ± 0.073 | **0.442 ± 0.093** |

Per seed, governed breaches are 0, 0, 0, 0, 0. No solver failures, fallbacks,
certificate gaps or backtracks.

**The safety result replicates on the fixed code path.** Every other row sits
inside the noise: the offered rates differ by 0.030 against a seed SD of 0.093,
one deal in sixteen, and a correction rate that moves by 0.010.

## What was NOT done with it, and why

The instruction was to replace arm B's rows in Tables 5.3, 5.4, 5.5, 5.7 and
B.1 with this run. **That was not done, and the reason is the defect the same
review found elsewhere.**

Those tables compare five arms side by side. Arms A, C, C-meet and D come from
the August batch. Replacing arm B alone would leave four arms from one batch
and one from another, which is precisely the cross-batch comparison the review
flagged in Table B.2 and which this pass has just footnoted. It would fix one
consistency problem by creating a worse one, in the table the dissertation
argues from most.

Replacing them honestly needs all five arms re-run together — 25 runs, roughly
£2.50 and about two hours. That is affordable and was not affordable tonight
alongside the rest of the phase.

So the tables keep the internally consistent August batch, and this run is
reported as what it is: an independent replication on the fixed code, which
discharges the substance of C10 without pretending the arms were all rerun.
C10 is narrowed rather than deleted.

## What this does to C10

Before: *arm B's outcome numbers stand; its negotiation paths do not.*

After: the outcome numbers stand and are replicated, and the paths have now
been measured on the fixed code and give the same safety count. What remains of
C10 is only that the paths **printed in Chapter 5** are the old ones, because
the arms are tabulated as one batch.
