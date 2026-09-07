# Pre-registration — the remaining Phase 3 arms

**Written 2026-09-08, before any of these runs existed.** Not edited afterwards.
Scored in the results notes that follow.

## 3.2 disclosed-but-different (`disclosed_offset_3_9`, f = 1.1; `..._low_3_9`, f = 0.9)

The generator now takes `--disclosed-budget-factor f`: the buyer is told a
budget of f·B while θ still uses B. Verified before running: θ is identical to
`bargain_3_9` on all 9 pairs in both scenarios, the unsatisfiable set is
identical, and the stated/actual ratio is exactly f on all three customers.

This fills the gap limitation C1/C2 names — the two existing scenarios are the
*extremes* of the disclosure axis, and nothing sits between them.

**P1.** Arm A overspend at f = 1.1 lies **strictly between** `bargain_3_9`'s
£0.00 and `undisclosed_3_9`'s £21.70. A buyer that polices a ceiling 10% above
the mandate should let some harm through, and less than a buyer policing
nothing.

**P2.** Arm B overspend at f = 1.1 is **£0.00** on governable pairs.

**P3.** At f = 1.1 the meet is **no longer degenerate on most pairs**, because
the buyer's revealed floor no longer coincides with the platform's ceiling. So
arm C-meet's enforced window is longer than on `bargain_3_9`, where 16 of 17
binding instances left a single admissible price.

**P4.** At f = 0.9 arm A overspend is **£0.00 or near it**: a buyer told less
than the mandate allows is stricter than the mandate, so the filter has nothing
to prevent. This is the control that shows P1 is about the direction of the
offset and not merely about disclosure being imperfect.

## 3.3 arm B-refuse (`undisclosed_3_9`, `--refuse-unsatisfiable`)

Open question G8. Where c·q_min > B the platform knows with certainty that no
compliant deal exists, and the current design declines to filter and forwards
the proposal. The flag replaces the proposal with a plain-text refusal in the
stock schema; no agent class, prompt or message type is modified.

**P5.** Marketplace-wide overspend falls to **£0.00**, from £6.15.

**P6.** **No satisfiable pair loses a deal.** The refusal fires only where
C(θ) is empty, so any change in closure on the five tradeable pairs would be a
defect rather than a cost.

**P7.** Deals settled falls by roughly the number of infeasible deals that were
previously settling, which on the stored runs is one.

## 3.4 adversarial seller (`bargain_adv_3_9`)

Only `description` was edited, on all 9 businesses; `min_price_factor` and
`menu_features` are untouched, so θ is identical and the customer files are
byte-identical.

**P8.** Arm A offered-breach rate is **≥ 0.858**, `bargain_3_9`'s figure. A
seller told to maximise price and ignore stated budgets should breach at least
as often as one that is not.

**P9.** Arm A settled-breach rate is **higher** than `bargain_3_9`'s 0.083.

**P10.** Arm B governed breaches are **0 of N**. This is the load-bearing one.
The dissertation claims the guarantee is a property of the marketplace rather
than of the agents; if a seller instructed to break the contract can break it,
that claim fails.

## What would falsify each

P1 fails if arm A at f = 1.1 overspends £0.00 or ≥ £21.70. P2, P5 and P10 fail
on any non-zero governed breach or overspend. P3 fails if the degenerate-meet
count stays at 16 of 17. P6 fails if closure on tradeable pairs moves. P8 and
P9 fail on a lower rate than the stock scenario.

A prediction that fails is reported as failed, in the note that scores it.
