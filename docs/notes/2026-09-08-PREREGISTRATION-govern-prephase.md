# Pre-registration — governing the pre-phase (arm C-meet-guarded, `--govern-prephase`)

**Written 2026-09-08, before the option had ever been run.** Not edited
afterwards. Scored in `docs/notes/2026-09-08-govern-prephase-results.md`.

## What it changes

One branch in `protocol.py`. Where the negotiated envelope does not yet exist,
the arm currently forwards the round unfiltered (limitation B6). With
`--govern-prephase` it enforces the platform's mandate instead:

```
envelope is None  ->  governing = theta_mandate      (was: pass through)
envelope exists   ->  governing = guarded_meet(envelope, mandate)
```

No Magentic agent, prompt or message schema is touched. The flag is off by
default, so every number already in the thesis is unaffected.

## Why

`docs/notes/2026-09-08-guarded-meet-results.md` found that **no round the
composed contract governed produced a breach at any offset**, and that the
entire residual — £0.47, £0.30, £8.20, £7.02 at f = 1.00, 1.02, 1.05, 1.10 —
sits on pairs that never froze an envelope. Most pairs settle in one or two
rounds and the first round is the pre-phase, so the composition never gets to
act on them.

B6 says a *negotiated* contract cannot govern the exchange that creates it.
That is true, and it does not follow that the exchange must be ungoverned: the
platform's mandate exists from the first message. Governing the pre-phase by
the mandate leaves the parties free to agree anything the mandate permits,
which is exactly the freedom arm C-meet was built to protect.

## Predictions

**P1 (load-bearing).** Marketplace-wide overspend is **£0.00 at every f** in
{1.00, 1.02, 1.05, 1.10}. The residual identified above is entirely pre-phase,
so governing the pre-phase should remove all of it. If P1 fails, the residual
is not what the guarded-meet note says it is, and that note needs correcting.

**P2.** Closure is within run-to-run variation of arm B at the same f (arm B
settles 17 deals at f = 1.1, 15 on `bargain_3_9`). Governing the pre-phase by
the mandate makes the opening exchange behave as arm B's does, so it should
cost no trade relative to arm B.

**P3.** The envelope is inferred from **corrected** openings, so the inferred
budget row should be **tighter** than in the ungoverned-pre-phase arm, and the
meet should be unsatisfiable on **fewer** instances. `pairs_meet_fallback`
should fall relative to the 0, 21, 10, 13 rounds recorded without the flag.

**P4.** Deals settled during the pre-phase — which the plain guarded arm cannot
touch — now comply. Concretely: **no settled deal breaches the mandate on a
pair whose envelope never froze.**

## What would falsify the section

- P1 fails at any f → report it and correct the guarded-meet note's attribution
  of the residual.
- P2 fails (closure materially below arm B) → governing the pre-phase costs
  trade, and the trade-off has to be stated rather than the win claimed.
- P3 fails (fallback rate unchanged or higher) → correcting the opening does
  not tighten the envelope, and the mechanism in this note is wrong.

## Runs

γ = 0.4, T_max = 6, five runs each, `gemini-2.5-flash` minimal reasoning.
Scenarios `bargain_3_9`, `offset_102_3_9`, `offset_105_3_9`,
`disclosed_offset_3_9`. 20 runs, ≈ £2.

```
uv run python experiments/arm_c_meet_guarded.py --govern-prephase \
    --data data/<scenario> --experiment arm_gp_<f>_v<n>
```

Outcomes are recomputed by `src.marketplace_integration.replay` against the
Postgres database.

## One thing this note cannot claim

There is no seed control in the runner. `v1`..`v5` are five independent runs at
an identical configuration, and the variation between them is language-model
sampling nondeterminism, not seed variance. Nothing here is a controlled
seed comparison, and the word "seed" is avoided for that reason.
