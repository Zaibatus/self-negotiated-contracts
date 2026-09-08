# Pre-registration — the guarded meet (arm C-meet-guarded)

**Written 2026-09-08, before the arm had ever been run.** Not edited afterwards.
Scored in `docs/notes/2026-09-08-guarded-meet-results.md`.

## What the arm changes

One rule, in `src/contract.py`:

```
guarded_meet(envelope, mandate) =
    (envelope ∧ mandate, False)   if that meet is satisfiable, or if the mandate is not
    (mandate,            True)    otherwise
```

Nothing else moves. The Magentic agents, their prompts and the message schema
are untouched; the arm's launcher differs from `arm_c_meet.py` in exactly one
line (`--theta-source guarded_meet`). The rule is the greatest satisfiable
lower bound of {θ_neg, θ_man} that is still at or below θ_man.

## Why it exists

Phase 3.5 measured where composition breaks. On the offset scenarios the meet
of the self-negotiated envelope with the platform's mandate is **empty on most
frozen pair-instances**, and limitation B4 then forwards the pair unfiltered:

| scenario | governed rounds | corrected under C-meet |
|---|---|---|
| f = 1.00 (`bargain_3_9`) | 67 | 14/67 |
| f = 1.02 | 68 | **0/68** |
| f = 1.05 | 75 | **0/75** |
| f = 1.10 | 64 | **0/64** |

B4's pass-through is the right answer when *nothing* can comply. It is the
wrong answer here: the platform holds a satisfiable mandate of its own and
declines to enforce it because the parties agreed something incompatible with
it. Composition should never let the platform govern *less* than it would have
governed alone.

## Predictions

**G1 (load-bearing).** At every f ∈ {1.00, 1.02, 1.05, 1.10} the guarded meet
records **0 breaches on governed rounds and £0.00 overspend** — the same as arm
B at that f. If G1 fails the rule does not recover the guarantee, the claim
comes out of the thesis, and the negative result is reported instead.

**G2.** Closure at each f is within seed noise of arm B at that f (arm B settles
17 deals at f = 1.1). Falling back to the mandate should not cost trade,
because the mandate is exactly what arm B enforces.

**G3.** At f = 1.00 the guarded meet is **identical to arm C-meet** up to seed
noise: the fallback cannot fire where the meet is satisfiable, and it is
satisfiable on 56 of 67 governed rounds there. This is the control that shows
G1 is not bought by simply replacing composition with the mandate everywhere.

**G4.** At f ≥ 1.02 the fallback fires on **most** governed instances (the
counterpart of the 0/68, 0/75, 0/64 above), and the negotiated side still binds
on the minority where the buyer countered at or below the mandate ceiling —
i.e. `pairs_meet_fallback` is large but not total.

## What would falsify the section

- G1 fails at any f → no claim; report the failure.
- G3 fails (f = 1.00 differs materially from C-meet) → the rule is doing
  something other than what it says on satisfiable meets.
- G4 total (fallback on 100% of instances at every f including 1.00) → the arm
  has collapsed into arm B and composition contributes nothing.

## Runs

γ = 0.4, T_max = 6, seeds v1–v5, `gemini-2.5-flash` minimal reasoning.
Scenarios `bargain_3_9`, `offset_102_3_9`, `offset_105_3_9`,
`disclosed_offset_3_9` (f = 1.1). 20 runs, ≈ £2.

```
uv run python experiments/arm_c_meet_guarded.py \
    --data data/<scenario> --experiment arm_c_meet_guarded_<f>_v<n>
```

Outcomes are recomputed by `src.marketplace_integration.replay` against the
Postgres database. Nothing in this note is scored from `certificates.jsonl`.
