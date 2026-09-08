# The guarded meet, measured — arm C-meet-guarded

**2026-09-08.** 20 live runs, ~£2. Scores the predictions registered in
`docs/notes/2026-09-08-PREREGISTRATION-guarded-meet.md`, which was written
before the arm had ever been run and has not been edited since.

γ = 0.4, T_max = 6, seeds v1–v5, `gemini-2.5-flash` minimal reasoning.
Scenarios `bargain_3_9` (f = 1.00), `offset_102_3_9`, `offset_105_3_9`,
`disclosed_offset_3_9` (f = 1.10). All outcomes below are recomputed by
`src.marketplace_integration.replay` against the Postgres database. Nothing
here is scored from `certificates.jsonl` except the per-round audit fields,
which exist only in the certificate and are labelled where used.

## A run set was discarded first

The first six runs were void. Four gates in `protocol.py` named the inference
arms by hand as `("inferred", "meet")` and none had been told about
`guarded_meet`, so the arm skipped the pre-phase, the envelope freeze and the
composition entirely: it was arm B under another name. It produced entirely
plausible numbers while doing so — the filter intervened, breaches fell, every
run exited clean. The only symptom was `pairs_meet_fallback = 0` at f = 1.02,
where arm C-meet has 24 unsatisfiable meets. Fixed by replacing the four gates
with one constant and pinning it against the declared type in the test suite
(`test_every_inference_arm_is_listed_in_INFERENCE_SOURCES`). The six runs were
dropped from the database and the arm re-run from scratch.

## Outcomes

Settled deals, deals breaching the mandate, and marketplace-wide overspend,
five seeds each, replayed from the database:

| f | C-meet settled / breached / overspend | **C-meet-guarded** |
|---|---|---|
| 1.00 | 15 / 0 / £0.00 | 15 / 2 / £0.47 |
| 1.02 | 15 / 13 / £3.45 | **15 / 2 / £0.30** |
| 1.05 | 16 / 15 / £13.41 | **15 / 8 / £8.20** |
| 1.10 | 14 / 14 / £16.51 | **15 / 7 / £7.02** |

And what each arm actually governed (per-round audit field
`extraction.meet_fallback`, plus the intervention magnitude):

| f | C-meet interventions | guarded interventions | guarded fallback rounds |
|---|---|---|---|
| 1.00 | 14 | 12 | **0** |
| 1.02 | **0** | 19 | 21 |
| 1.05 | **0** | 10 | 10 |
| 1.10 | **0** | 13 | 13 |

## The one clean result

Splitting every pair's rounds at the point its envelope freezes:

| f | rounds before the freeze | rounds after | **breaches after** | rounds on pairs that never froze |
|---|---|---|---|---|
| 1.00 | 12 | 12 | **0** | 47 |
| 1.02 | 24 | 21 | **0** | 30 |
| 1.05 | 10 | 10 | **0** | 43 |
| 1.10 | 13 | 13 | **0** | 44 |

**Not one round that the composed contract governed produced a breach, at any
f.** Every breaching round in all 20 runs is on a pair that never reached a
governed state. That is the guarantee the arm was built to recover, and it is
recovered: at f ≥ 1.02 arm C-meet governs *nothing* (0 interventions across 15
runs) and the guarded arm governs 44 rounds, all of them clean.

## Where the residual harm lives, and why it is not the composition's

The guarded arm still overspends £8.20 and £7.02 at f = 1.05 and 1.10. None of
it is on a governed round. It is on pairs whose envelope never froze, and there
are a lot of them:

| f | pair-instances | reached a governed round | rounds per pair |
|---|---|---|---|
| 1.00 | 36 | 12 | 9×1, 23×2, 4×4 |
| 1.02 | 40 | 21 | 9×1, 27×2, 4×3 |
| 1.05 | 42 | 10 | 21×1, 21×2 |
| 1.10 | 42 | 13 | 17×1, 23×2, 1×3, 1×4 |

Most pair-instances run for one or two rounds. A negotiated contract does not
exist until both sides have named a price, so a pair that settles in its first
round is ungoverned by construction — **limitation B6, not a filter failure and
not a composition failure.** Arm B has no pre-phase and governs from round zero,
which is exactly why arm B reaches £0.00 where this arm cannot.

So the composition's cost is the pre-phase, and it grows with f: the further
above the mandate the buyer's stated budget sits, the more a first-round
settlement overshoots by. At f = 1.00 that leak is £0.47 across five seeds; at
f = 1.05 it is £8.20.

## Scoring the predictions

**G1 — FAILS as written.** It predicted 0 breaches *and* £0.00 overspend at
every f, the same as arm B. Breaches on governed rounds are 0 of 12, 21, 10 and
13 — the load-bearing half holds exactly. Marketplace overspend is £0.47, £0.30,
£8.20 and £7.02, not £0.00. The prediction conflated "the composed contract is
never violated where it governs" with "the marketplace is clean", and only the
first is true. The second was never in the composition's reach, because B6 puts
the opening exchange outside it.

**G2 — FAILS.** Closure was predicted within seed noise of arm B (17 deals at
f = 1.1). It is 15 at every f, which is arm C-meet's closure, not arm B's. The
guarded arm neither gains nor loses trade relative to the arm it modifies; it
does not recover the two deals the pre-phase costs.

**G3 — CONFIRMED.** The fallback fired on **0 rounds** at f = 1.00, so the
guarded rule and the C-meet rule are literally the same computation there. This
is the control that matters: it shows G1's improvement at f ≥ 1.02 is the guard
firing and not the mandate quietly replacing composition everywhere. Worth
recording that the two run sets still differ by £0.47 and 2 breached deals under
an identical rule — that is pure seed nondeterminism, and it is a useful bound
on how much of any small difference in this chapter is noise.

**G4 — PARTIALLY CONFIRMED.** The fallback does fire at f ≥ 1.02 and not at
f = 1.00, as predicted. But it fires on a *minority* of pair-instances (21 of
40, 10 of 42, 13 of 42), not "most", because most pairs never leave the
pre-phase and so never present a meet to guard. The prediction was written as
though every pair reaches a composed contract; they do not.

## Two things to state rather than bury

**All corrections in this arm are closed-form clips, not QP projections.**
`solver_status` is `not_run` on every round of all 20 runs. On this scenario
family the composed safe set is degenerate — a single admissible price — which
routes every correction through limitation B7's feasibility fallback.
Minimality is therefore not claimed for any of the 54 corrections above; only
membership of C(θ) is.

**The guarded rule is strictly better than the meet at every f ≥ 1.02 and no
worse at f = 1.00**, on both overspend and breached deals, while settling the
same number of deals or one more. That is the claim this note supports. It does
not support "the guarantee is recovered marketplace-wide", and Chapter 8 must
say the conditional version.

## Reproduce

```
set -a; . ../multi-agent-marketplace/.env; set +a
for f in 100:bargain_3_9 102:offset_102_3_9 105:offset_105_3_9 110:disclosed_offset_3_9; do
  for n in 1 2 3 4 5; do
    uv run python experiments/arm_c_meet_guarded.py \
      --data "data/${f##*:}" --experiment "arm_c_meet_guarded_${f%%:*}_v${n}"
  done
done
uv run python -m src.marketplace_integration.replay \
  --schemas arm_c_meet_guarded_110_v1 ... arm_c_meet_guarded_110_v5 \
  --data data/disclosed_offset_3_9 --out /tmp/gm_replay_110
```
