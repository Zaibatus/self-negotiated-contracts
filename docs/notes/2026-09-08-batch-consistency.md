# The five-arm comparison, re-run in a single batch

**2026-09-08.** 30 live runs, ~£3. All on `data/bargain_3_9`, γ = 0.4,
T_max = 6, seeds v1–v5, `gemini-2.5-flash` minimal reasoning. Experiment names
`arm_{a,b,c,cm,d}_batch2_v{1..5}`. Every outcome below is recomputed by
`src.marketplace_integration.replay` against the Postgres database.

## Why

Table 5.8 assembles five arms that were run at different times. The same review
that flagged the cross-batch defect in Table B.2 applies to it: if the model,
the scenario file or the harness moved between arms, a difference between
columns is not necessarily a difference between arms. Substituting one re-run
arm into the existing table would have made that worse, not better. The only
clean answer is to run all five together and see whether the same conclusions
come out.

## Result

| `bargain_3_9` | arm A | arm D | **arm B** | arm C | **arm C-meet** |
|---|---|---|---|---|---|
| Proposals offered | 77 | 85 | 49 | 121 | 76 |
| Breaching the scenario θ | 0.779 | 0.812 | 0.449 | 0.876 | 0.711 |
| Deals settled | 12 | 13 | **15** | 12 | **15** |
| Settled breaching | 0.083 | 0.077 | **0.000** | 0.083 | **0.000** |
| Overspend | **£1.93** | £0.00 | **£0.00** | £0.01 | **£0.00** |
| Settled per seed, SD | 0.49 | 0.49 | **0.00** | 0.49 | **0.00** |

Against Table 5.8 (A 95 / 0.858 / 12 / 0.083 / £0.00; D 80 / 0.822 / 12 /
0.083 / £0.00; B 51 / 0.472 / 16 / 0.000 / £0.00; C 219 / 0.922 / 14 / 0.143 /
£0.48; C-meet 67 / 0.664 / 15 / 0.000 / £0.00):

**Every categorical claim reproduces.** Arms B and C-meet settle zero breaching
deals and overspend £0.00. Arm C is still the only governed arm that overspends
at all. The closure ordering is unchanged: B and C-meet at 15, ahead of D at 13
and A and C at 12. And arms B and C-meet settled 3 of 3 pairs on *every* seed,
SD zero — the two arms the safety claim rests on are the two that do not vary.

## One thing does not reproduce, and it is arm A's overspend

Table 5.8 reports **£0.00** for arm A on `bargain_3_9`. This batch reports
**£1.93**, carried entirely by seed v2 (per-seed £0.00, £1.93, £0.00, £0.00,
£0.00). Re-replaying the original runs confirms they are not misreported: they
give £0.00 across all five seeds, and 95 proposals.

The two batches agree on everything around it. Both settle **12 deals** of
which **exactly 1 breaches**. They differ only in *which row* that one deal
breaches. In the Table 5.8 batch the settled breach is on the cost floor and
`q_min` — the exception §5.1 already records — and costs nothing. In this batch
it is a budget breach worth £1.93.

So arm A's £0.00 on the disclosed scenario is **not a reproducible constant.**
It is one seed in ten either settling a budget-breaching deal or not. Budget
breaches are plentiful in the offered proposals of both batches (29, 13, 15, 7,
17 rounds and 10, 12, 12, 15, 11 rounds); what varies is whether the buyer
accepts one.

The claim the chapter draws from that number survives, and should be stated as
the comparison it is rather than as a zero: an informed buyer leaves *little*
for enforcement to prevent — £1.93 across five seeds here, against £21.70 on
the undisclosed scenario — not *nothing*. The enforcement result is unaffected:
arms B and C-meet are £0.00 in both batches.

## Arm C's £0.48 was one seed, as suspected

Arm C overspends £0.48 in Table 5.8 and £0.01 here. §5.9 already notes that the
comparable undisclosed-scenario figure is carried by a single seed at £17.58
against an SD of £5.94. This batch is consistent with that: arm C's overspend on
`bargain_3_9` is a small, unstable, seed-carried quantity, and the defensible
statement is the ordinal one — arm C is the only governed arm that overspends at
all — not the cardinal one.

## What is not comparable across batches, by construction

Proposal counts. Arm A 95 → 77 and arm C 219 → 121. The caption of Table 5.8
already says proposal totals are not comparable across arms because the
inference arms emit a pre-phase; they are no more comparable across batches,
since the number of rounds an LLM negotiation runs is not fixed. Breach *rates*
are the comparable quantity and they move by 0.03–0.08, within the spread the
per-seed numbers show.

## Reproduce

```
set -a; . ../multi-agent-marketplace/.env; set +a
for n in 1 2 3 4 5; do
  uv run python experiments/arm_a_no_contract.py --live --data data/bargain_3_9 --experiment arm_a_batch2_v$n
  uv run python experiments/arm_b_imposed.py      --data data/bargain_3_9 --experiment arm_b_batch2_v$n
  uv run python experiments/arm_c_negotiated.py   --data data/bargain_3_9 --experiment arm_c_batch2_v$n
  uv run python experiments/arm_c_meet.py         --data data/bargain_3_9 --experiment arm_cm_batch2_v$n
  uv run python experiments/arm_d_monitored.py    --data data/bargain_3_9 --experiment arm_d_batch2_v$n
done
uv run python -m src.marketplace_integration.replay \
  --schemas arm_a_batch2_v1 ... arm_a_batch2_v5 --data data/bargain_3_9 --out /tmp/b2_replay_a
```

**Note on arm A.** `arm_a_no_contract.py` defaults to *replaying* the recorded
`mexican_3_9` baselines and does not run anything. `--live` is required for it
to run on `bargain_3_9`, and without it the arm silently reports the wrong
scenario's numbers. That happened once here and was caught by the replay
returning zero proposals for the batch schemas.
