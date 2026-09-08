# Phase 3 scored against its pre-registration

**Date:** 2026-09-08. **Live**, 90 runs, **£9.00** against a £10 cap.
**Pre-registration:** `docs/notes/2026-09-08-PREREGISTRATION-phase3.md`,
written before any of these scenarios or runs existed.
**Adversarial arm scored separately in** `2026-09-08-adversarial-seller.md`.

**Seven of ten predictions hold. P3 fails, and its failure is the most
interesting result in the phase.**

| | prediction | verdict |
|---|---|---|
| P1 | arm A overspend at f=1.1 strictly between £0.00 and £21.70 | **holds** — £12.77 |
| P2 | arm B overspend at f=1.1 is £0.00 | **holds** |
| P3 | at f=1.1 the meet is less degenerate, enforced window longer | **FAILS — the opposite** |
| P4 | at f=0.9 arm A overspend is £0.00 or near it | **holds, weakly** — £1.21 |
| P5 | refusal takes marketplace overspend to £0.00 | **holds** |
| P6 | no satisfiable pair loses a deal under refusal | **holds** |
| P7 | deals fall by roughly the infeasible deals previously settling | **holds** |
| P8 | adversarial arm A offered-breach ≥ 0.858 | **holds** — 0.992 |
| P9 | adversarial arm A settled-breach higher than 0.083 | **holds** — 0.600 |
| P10 | adversarial arm B governed breaches 0 of N | **holds** — 0 of 32 |

## 3.2 — between the extremes

`--disclosed-budget-factor f` tells the buyer f·B while θ still reads B out of
`menu_features`. Verified before running: θ identical to `bargain_3_9` on all 9
pairs at both f, unsatisfiable set identical, stated/actual ratio exactly f.

| | overspend | deals | settled breaching |
|---|---|---|---|
| `bargain_3_9`, f = 1.0, arm A | £0.00 | 12 | 1 |
| **offset f = 1.1, arm A** | **£12.77** | 15 | 14 |
| `undisclosed_3_9`, arm A | £21.70 | 15 | 15 |
| **offset f = 1.1, arm B** | **£0.00** | 17 | **0** |
| offset f = 0.9, arm A | £1.21 | 11 | 8 |
| offset f = 0.9, arm B | **£0.00** | 4 | **0** |

**P1 holds and fills the gap limitation C2 named.** The disclosure axis is no
longer two extremes with nothing between them: a buyer told 10% more than the
mandate allows lets £12.77 through, between the £0.00 of a correctly informed
buyer and the £21.70 of an uninformed one. The benefit of enforcement is
monotone in how wrong the counterparty's belief is, and now has an interior
point rather than an interpolation.

**P2 holds.** Zero governed breaches on 28 rounds, £0.00 overspend.

**P4 holds weakly.** £1.21 rather than £0.00, on a buyer told *less* than it may
spend. The residual sits on pairs the mandate cannot satisfy anyway. The
direction is right: an over-cautious buyer is nearly as safe as a correctly
informed one, so P1's effect is about the *direction* of the offset and not
about disclosure merely being imperfect.

One unregistered observation, reported because it is large. At f = 0.9 arm B
runs **285 governed rounds and settles 4 deals**, against 28 rounds and 17
deals at f = 1.1. A buyer told it may spend less than it can haggles far longer
and closes far less. The filter is not the cause — it breaches nothing in
either case — but a mandate looser than the buyer's belief is expensive in
liveness, which is a cost the dissertation has not priced anywhere else.

## P3 fails, and composition is what fails

**Predicted:** at f = 1.1 the buyer's revealed floor no longer coincides with
the platform's ceiling, so the meet is less often degenerate and arm C-meet's
enforced window is longer.

**Measured:** the meet is not less degenerate. It is **empty**.

Effective unsatisfiable pair-instances for C-meet, across five seeds:

| scenario | per seed | total |
|---|---|---|
| `bargain_3_9`, f = 1.0 | 4, 1, 3, 1, 2 | 11 |
| **offset f = 1.1** | 6, 4, 7, 1, 2 | **20** |

The mandate alone is unsatisfiable on 4 pairs. Everything above that is
composition destroying feasibility the mandate did not.

The arithmetic on `business_0005|customer_0002` is the whole story:

```
mandate B            7.45      theta reads menu_features, unchanged
buyer is told        8.20      = 1.1 x 7.45
seller opening ask   8.66
meet B  = min(7.45, 8.66 x 1)            = 7.45
meet c  = max(mandate floor, buyer counter ~8.20) = ~8.20
meet c x q_min = 8.20  >  7.45 = meet B  ->  C(meet) is EMPTY
```

A buyer told it may spend more than the mandate allows *counters above the
mandate's ceiling*. The meet takes the maximum of the two floors and the
minimum of the two budgets, so the parties' own agreed zone lies entirely
outside what the platform permits, and their intersection is empty. C-meet then
has nothing to enforce, runs unfiltered by design, and every round breaches:
64 of 64 governed rounds, **0 corrections**, £16.51 overspend — worse than
ungoverned.

**This sharpens §5.9.1 from an edge case into a regime.** That section records
that composition destroyed feasibility on *one seed* of `bargain_3_9`, where a
buyer counter-offered above its own stated budget. At f = 1.1 that is not an
accident; it is what the scenario guarantees. Composition is safe to permit only
while the parties' beliefs are no looser than the mandate. Tell the buyer a
number above the ceiling and the meet — the dissertation's answer to its own
title — governs nothing at all.

It is not a safety failure of the filter. Every one of those rounds is on a
pair whose effective safe set is empty, which the design detects and
deliberately declines to filter (limitation B4). It is a failure of the
*composition* to be useful, and it is the first regime found where enforcing
the meet is worse than enforcing the mandate.

## 3.3 — G8 answered

`--refuse-unsatisfiable` replaces the proposal on an empty-safe-set pair with a
plain `TextMessage` in the stock schema explaining that no terms could comply.
No agent class, prompt or message type was modified.

| | `undisclosed_3_9`, arm B | **arm B-refuse** |
|---|---|---|
| governed rounds | 22 | 25 |
| governed breaches | 0 | **0** |
| offered breach rate | 0.294 | **0.000** |
| deals settled | 13 | 15 |
| deals breaching | 0 | **0** |
| marketplace-wide overspend | £6.15 | **£0.00** |

**P5 holds.** Marketplace-wide overspend goes to zero. The £6.15 residual that
Chapter 5 and Chapter 7 both describe as the whole of arm B's remaining harm is
the single deal on an unsatisfiable pair, and refusing it removes it.

**P6 holds.** No satisfiable pair lost a deal; closure rose from 13 to 15.

**P7 holds.** The offered-breach rate falls to 0.000 because a refused proposal
never reaches the counterparty to be counted.

So the answer to open question G8 is that refusing costs nothing measurable
here and removes all residual harm. What it does assert is a power the platform
does not currently claim: refusing to let two willing parties transact on the
basis of a constraint neither of them stated. Chapter 7 already frames that as
the question, and this measures the price of answering it one way — which on
this scenario is zero.

## Cost

90 runs, ~£9.00, against a £10 cap. No run exceeded its budget and the guard
never fired.

---

# Addendum: where composition breaks (added 2026-09-08, +10 runs, ~£1.00)

P3's failure at f = 1.1 invited an obvious question: how far above the mandate
can the buyer's belief sit before composition stops working? Arm C-meet was run
at f = 1.02 and f = 1.05, five seeds each. Runs `arm_cm_o102_1..5`,
`arm_cm_o105_1..5`.

| f | unsatisfiable meet-instances | governed rounds | **corrections** |
|---|---|---|---|
| **1.00** | 11 | 67 | **14 / 67** |
| **1.02** | 24 | 68 | **0 / 68** |
| 1.05 | 20 | 75 | **0 / 75** |
| 1.10 | 20 | 64 | **0 / 64** |

**Composition does not degrade gradually. It stops entirely between f = 1.00
and f = 1.02** — a two per cent overstatement of the budget — and never
recovers.

The algebra says why, and it recasts an observation the dissertation already
records as harmless.

```
meet B = min(mandate B, seller ask x q_req)
meet c = max(mandate floor, buyer's first counter)
satisfiable  <=>  meet_c x q_min <= meet_B
```

At f = 1.00 the buyer counters at exactly its stated budget, so
`meet_c x q_min = B = meet_B`. Satisfiable — but **with equality**. That is
precisely §5.9.1's finding that 16 of 17 binding instances left a *degenerate*
safe set, a single admissible price.

§5.9.1 treats that degeneracy as a curiosity of the scenario. It is not. **A
degenerate safe set is the boundary of feasibility, not a narrow margin on the
right side of it.** The composition result works on `bargain_3_9` because the
buyer is told exactly the number the mandate uses, and it is sitting exactly on
the edge the whole time. Any positive offset tips it over.

So the dissertation's answer to its own title needs a condition attached:
**enforcing the meet recovers the guarantee only while the parties' stated
positions are no looser than the mandate.** On this scenario family that
tolerance is zero. Whether it is zero in general or an artefact of
`q_min = q_requested` is not established here, and the algebra above suggests
the latter is worth checking: a contract with slack between `q_min` and the
requested basket would not sit on the boundary.
