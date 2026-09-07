# Welfare per arm, and what enforcement actually restores

**Date:** 2026-09-06
**Data:** re-analysis of stored live runs. **No API calls, no cost.**
**Code:** `experiments/welfare_analysis.py`. Numbers in
`results/summary/welfare_analysis.json` (tracked).
**Depends on** `2026-09-06-potential-and-lyapunov.md` for Ψ = P·W.

## The gap this fills

The thesis reports breaches, overspend and closure. It reports **no welfare
measure at all**, so "the cost of the guarantee" (§5.12) could only be answered
as "zero detectable". Ψ = P·W is the potential of the concession field and is
expected joint surplus. Normalised by Ψ\* at the bargaining solution it makes
arms and scenarios comparable.

## Result 1 — enforcement raises expected joint surplus, live

`bargain_3_9`, 5 seeds, final governed state on satisfiable pairs:

| arm | mean Ψ/Ψ\* | seed SD |
|---|---|---|
| A ungoverned | 0.488 | 0.054 |
| D monitor | 0.453 | 0.172 |
| **B filter** | **0.827** | **0.014** |
| C negotiated | 0.648 | 0.107 |
| C-meet composed | 0.751 | 0.095 |
| F transfer | 0.645 | 0.124 |

Differences against the SD of a difference from per-arm seed SDs (§12):

| | Δ | SD | verdict |
|---|---|---|---|
| A → D | −0.034 | 0.180 | **−0.2 SD** — noise floor holds, as designed |
| **A → B** | **+0.339** | 0.056 | **+6.1 SD — claimed** |
| D → B | +0.374 | 0.173 | +2.2 SD — claimed |
| C → C-meet | +0.103 | 0.142 | +0.7 SD — **not claimed** |
| F → B | +0.182 | 0.125 | +1.5 SD — **not claimed** |
| D → F | +0.191 | 0.212 | +0.9 SD — **not claimed** |

Enforcement also **collapses the variance**: seed SD 0.054 → 0.014, and 0.172
for the monitor. The guarantee makes outcomes predictable as well as better.

On `undisclosed_3_9`, the centrepiece scenario: **A = 0.000 in every seed**,
B = 0.841, **+25.9 SD**.

## Result 2 — the filter restores the split, not the surplus

Ψ = 0.000 ungoverned is real, and decomposing it is the finding. At the final
ungoverned state on `undisclosed_3_9`, seed 1:

| pair | U_B | U_S | W | P | W at NBS |
|---|---|---|---|---|---|
| b0008\|c0003 | −1.32 | 1.90 | 0.58 | 1.1e−04 | **0.58** |
| b0004\|c0002 | −0.84 | 1.09 | 0.25 | 1.9e−06 | **0.25** |
| b0001\|c0001 | −1.85 | 2.45 | 0.60 | 4.5e−06 | **0.60** |
| b0005\|c0002 | −1.19 | 1.60 | 0.41 | 9.3e−06 | **0.41** |
| b0002\|c0001 | −2.10 | 2.40 | 0.30 | **5.3e−13** | **0.30** |

**W at the settled point equals W at the bargaining solution on every pair.**
Price is a pure transfer, so joint surplus is invariant to it. Ungoverned
trading destroys no surplus whatever — it moves the whole of it to the seller,
past the point where the buyer would rationally accept. Buyer utility is
negative on every pair and acceptance probability falls to between 1e−4 and
**5e−13**.

So the uninformed LLM buyer is not merely overspending by £21.70. **It settles
at terms its own payoff model would decline with probability indistinguishable
from one.** And what the filter buys is not a larger pie but a split both
parties would accept. That is the sharpest available statement of what a
contract-as-controller does, and the thesis does not currently make it.

## Result 3 — the gain is real and the margin is thin

The funnel sweep (2026-08-28) says the filter helps only where B/q_min > p\*
and hurts without bound below. Every satisfiable live pair:

| pair | B/q_min | p\* | margin |
|---|---|---|---|
| b0001\|c0001 | 5.790 | 5.680 | **+0.110** |
| b0002\|c0001 | 5.790 | 5.756 | **+0.034** |
| b0004\|c0002 | 7.450 | 7.343 | **+0.107** |
| b0005\|c0002 | 7.450 | 7.265 | **+0.185** |
| b0008\|c0003 | 10.460 | 10.423 | **+0.037** |

All five sit on the favourable side, by **0.034 to 0.185 scaled units**. The
entire live welfare result sits in a band a fifth of a scaled unit wide, on the
good side of a threshold nobody computed and the scenario author did not know
existed. This is the sharpest instance of §5.2's "an authored scenario changes
more than the variable it was authored to change".

## Limitations

- **Ψ is model-derived**, from the same per-pair calibration the drift analysis
  uses. It is not an observed payment; it is what the payoff model says the
  settled terms are worth. Assumption C5 carries it.
- **Final governed state**, not the replayed settled deal. Outcomes in §6–9 come
  from the database; these come from `certificates.jsonl`.
- **Contingent by construction.** Result 1 holds because of Result 3. It must
  never be written up as "enforcement improves welfare" without the margin table.
- Three of the six comparisons do not clear the noise floor and are not claimed.
