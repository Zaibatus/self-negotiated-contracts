# Chapter 5 — Results: three arms on a live LLM marketplace

**Sources:** the four arm notes in `docs/notes/`. This file is the *argument*
the arms make together, which none of the individual notes states; the numbers
and their reproduction stay in the notes.

**State: DONE for arms A, B and D.** Arm C does not exist (G7); arm E is
deferred.

---

## The narrative

The chapter should be read as one argument in four steps, not as four
experiments.

### 1. Ungoverned marketplaces breach the contracts their own scenarios imply

Two scenarios, five seeds each. Every breach is on the budget row; the cost
floor and quantity bounds are never violated by the sellers.

| | `mexican_3_9` (stock) | `bargain_3_9` (authored) |
|---|---|---|
| proposals offered breaching θ | 0.593 ± 0.029 | 0.858 ± 0.050 |
| deals settled breaching θ | 0.400 (6/15) | 0.083 (1/12) |
| overspend / value transacted | 0.52% | 0.00% |

### 2. But the buyer already declines most of it — and the scenario that was supposed to prove otherwise proved this instead

`bargain_3_9` was built to make the budget bind so the safety result would be
visible. It made offers much worse and deals much *cleaner*. Every settled deal
lands exactly on the budget, because the edit that makes the budget bind also
tells the customer what it is, and the customer then polices it.

**This is the most important negative result in the dissertation** and it
should be presented as such rather than buried: an authored scenario changes
more than the variable it was authored to change. It is also why the benefit
side remains untested (G1).

### 3. Detection alone shows how much the marketplace is straining

Arm D — same detection, no correction:

| | arm A (off) | arm D (monitor) | arm B (filter) |
|---|---|---|---|
| offered breaching θ | 0.858 | 0.822 | **0.472** |
| settled breaching θ | 0.083 | 0.083 | **0.000** |
| governed rounds breaching | 46/58 | 37/51 | **0/27** |
| deals settled | 12 | 12 | 16 |

Arms A and D are behaviourally identical by construction, so **every A/D
difference is the noise floor**:

| | A vs D (noise) | A vs B (treatment) | contrast |
|---|---|---|---|
| offered breach rate | 0.036 | 0.386 | **4.4 SD** |
| governed per-round rate | 0.068 | 0.793 | — |

Expressed against the SD of a difference, √(0.050² + 0.073²) = 0.089 from the
per-arm seed SDs — **not** as a ratio to the single observed A/D gap, which is
one realisation and not an estimate of spread. The safety effect clears it
comfortably; the closure and surplus differences do not, and are not claimed.

### 4. Enforcement corrects; it shortens; it does not prevent

An earlier draft of this chapter claimed the filter worked mainly by
*prevention* — that it changed the trajectory so violations stopped arising.
That rested on a count of 3/27 corrections under arm B, which was wrong:
opening projections were logged with `intervention = 0`, hiding almost every
correction the filter made. Recomputed:

| | governed rounds | openings | continuations | flag rate | correction rate |
|---|---|---|---|---|---|
| arm A | 58 | 22 | 36 | 0.79 | — |
| arm D | 51 | 25 | 26 | 0.73 | — |
| **arm B** | **27** | **23** | **4** | **0.89** | **0.89** |

On continuation rounds alone — 0.72 (A), 0.54 (D), **0.75 (B)** — arm B is the
highest of the three. The filter does not lower the per-round rate at which
violations arise.

What survives is mechanical and worth stating plainly: **enforcement shortens
the negotiation** (27 governed rounds against 51 and 58, median length 1 against
2), **corrects nearly everything it sees** (89%), and **concentrates its work at
the opening** (23 of 27 governed rounds are openings). The story is "correct the
opening and the negotiation ends".

Arm B has four continuation rounds in total, so even that comparison is
underpowered and should be presented as such.

**Corollary that still holds:** a monitor cannot be costed as "the filter minus
the rewriting". It sits on a path a filter would never have produced — though
the reason is that the negotiation ends sooner, not that violations stop
arising. Any figure putting the two side by side needs that caption.

## The claim this supports, and the claim it does not

**Supported:** the filter converts a *tendency* into a *bound*. Per-round
exposure goes to zero, on governed pairs, on live agents, with no agent forked
and no fallback tier ever firing. That is the live replication of F1
(9.9% → 0% in simulation).

**Not supported:** that the filter prevents harm the buyer would otherwise have
accepted. On `bargain_3_9` the buyer accepted one bad deal in twelve, and one
event cannot carry a rate claim. Saying so is not a hedge — it is the honest
reading, and G1 names the experiment that would settle it.

## The cost of the guarantee

Zero detectable, and the caveat is the sample size. No pair closed ungoverned
and stopped closing under the filter. Arm B settled *more* deals (16 vs 12),
but almost all of that is one pair, and arm B's runs predate the reconciliation
fix, so its trajectories came from a seller reasoning about prices it never
offered.

## Method material belonging in chapter 4

Three bugs are worth a page, because each is a general lesson about testing a
safety layer and each passed a full suite:

1. **The wire copy.** The regulator rewrote a copy of the request; the server
   persists the original. Five seeds of arm B enforced nothing while the
   certificate log recorded corrections. The tests asserted on the value the
   protocol *returned* rather than what the caller was left holding.
2. **Currency quantisation.** Prices round to the cent, the safe set does not.
   Ten of ten governed rounds on one pair breached by exactly −0.01. A "zero
   breaches" claim has to say whether it survives writing the terms back in the
   currency's own precision.
3. **The sender's stale books.** The seller's history is fed into the prompt
   that generates its next offer, so under a filter it conceded from a price it
   never made. Fixed by client-side reconciliation; the guarantee never
   depended on it, but the trajectories did.

The common thread: all three were invisible to tests that asserted on a
plausible-looking surface rather than the one that decides what the counterparty
sees.

## Figures

1. Three-arm bar chart: offered / settled / governed-per-round, with the A–D
   noise floor as an error band. *(have data)*
2. Flagged-vs-corrected, with the different-trajectories caveat in the caption.
   *(have data)*
3. Per-pair closure table across arms, with infeasible pairs marked. *(have)*
4. The `mexican_3_9` → `bargain_3_9` inversion — offers worse, deals cleaner.
   *(have)*
