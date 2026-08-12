# Chapter 5 — Results: five arms on a live LLM marketplace

**Sources:** the arm notes in `docs/notes/`. This file is the *argument* the
arms make together, which none of the individual notes states; the numbers and
their reproduction stay in the notes.

**State: DRAFT COMPLETE.** Arms A, B, C, C-meet and D, on both `bargain_3_9`
and `undisclosed_3_9`. Arm E is deferred and is named as such in chapter 7.

**Retracted claims, stated here so no reader meets them as live:** an earlier
draft led §4 with *"enforcement is prevention"* — that the filter changes the
trajectory so violations stop arising. It was an artefact of the intervention
logging bug (chapter 4, bug 4) and is **withdrawn**. The surviving claim is
narrower and is what §4 now says: *correct the opening and the negotiation
ends.* An earlier draft also reported the funnel effect as a multiple of the
A/D noise floor, dividing by a single realisation; that arithmetic is withdrawn
in favour of the categorical statement.

---

## The narrative

The chapter should be read as one argument in six steps, not as a list of
experiments. Steps 1–2 establish the problem and demolish the first attempt to
measure it; step 2b is the **empirical centre of the dissertation**, the only
place a benefit is measured in currency; steps 3–4 characterise what enforcement
actually does; steps 5–6 are the culmination, where the contract stops being
imposed and starts being negotiated.

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
more than the variable it was authored to change.

### 2b. The centrepiece: withhold the budget and the benefit appears, in currency

`undisclosed_3_9` drops the buyer clause and changes nothing else — same θ, same
seller mandate, same basket. The buyer is no longer told its ceiling; the
platform still knows it. That single variable decides the whole benefit side.

| governable pairs, 5 seeds | arm A (off) | arm B (filter) |
|---|---|---|
| offered breaching θ | 1.000 | 0.294 *(infeasible pairs only)* |
| deals settled | 15 | 13 |
| deals breaching | **15/15** | **0/13** |
| governed rounds breaching | 25/25 | **0/22** |
| **transacted above the ceiling** | **£21.70 (7.93%)** | **£0.00** |

Every ungoverned deal breaches in every seed; no governed deal breaches in any.
**Unlike every other contrast in this chapter, this one is categorical and needs
no noise floor** — there is nothing to average, because the per-seed table is
3/3 breaching against 0/3 in all five seeds. This is the single result that
justifies the machinery: everything else in the dissertation bounds a risk,
and this measures a harm.

The mechanism is **buyer passivity, not seller aggression**: with no budget to
defend, the buyer accepts the seller's opening list price, so every proposal is
an opening and every opening exceeds B. What the filter substitutes for is
therefore *an informed counterparty*. Where one exists, it adds a bound and
little else; where one does not, it is the only thing between the marketplace
and a 7.9% overspend. Those two scenarios bracket the range, and real
deployments sit between them.

Two corrections this forced on earlier sections, both propagated:

- **Zero settled dispersion is not diagnostic of enforcement.** On this scenario
  *both* arms have per-pair settled-price SD = 0.000 — arm B at B/q_min, arm A
  at list price. The funnel result survives as "the contract picks *which* point",
  but not as "the contract collapses the spread".
- **£6.15 of harm survives under arm B**, all of it on a pair whose safe set is
  empty (c·q_min > B), which the filter detects and deliberately does not act on.
  Marketplace-wide the reduction is £21.70 → £6.15, a 72% cut; on governable
  pairs it is total. That gap is a design decision (G8), not a limit of the
  theorem.

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

### 5. A self-negotiated contract is enforced just as well — and governs less

Arm C is the treatment the design was named for: θ agreed between the agents
and only then enforced. It is *inferred* rather than exchanged — the envelope of
the seller's opening ask and the buyer's first counter — so no message type is
added and the agent-agnostic claim survives.

| | arm A | arm D | arm B | **arm C** |
|---|---|---|---|---|
| proposals offered | 95 | 80 | 51 | **219** |
| breaching the **scenario** θ | 0.858 | 0.822 | 0.472 | **0.922** |
| settled breaching the scenario θ | 0.083 | 0.083 | **0.000** | **0.143** |
| overspend | £0.00 | £0.00 | £0.00 | **£0.48** |
| **breaches of the θ it enforced** | — | — | **0/27** | **0/136** |

Both halves matter and they point opposite ways.

**The guarantee transfers intact.** Zero breaches of the negotiated contract
over 136 enforced rounds. The filter never inspects where θ came from — arms B
and C share every line of that path and differ only in which `Contract` object
is handed to it — so this is confirmation that the mechanism is indifferent to
the contract's provenance, which is what "we certify the game, not the agents"
should also mean for the contract.

**Enforcing it is not governance.** The negotiated θ **refines the imposed one
on none of the 9 pairs** — its budget row is looser on every one, by 1.05–1.52×,
identically in every seed, because both opening positions are deterministic
given the scenario and a seller's opening ask sits above the customer's
reservation. The direction is categorical, not an estimate with a spread. So arm C settles a
*higher* fraction of breaching deals than doing nothing (0.143 against 0.083)
and is the only arm on `bargain_3_9` that overspends.

This makes §9's refinement order the load-bearing idea rather than a formal
nicety, and names the composition step 6 then runs: enforce
**θ_negotiated ∧ θ_mandate**, the meet — parties may agree their own terms, but
only inside the platform's rules.

Two further contrasts. Arm C **does not compress** the negotiation — 167
governed rounds against arm B's 27, because the envelope leaves a zone to haggle
inside — and **14 of its 29 agreed contracts run past T_max = 6**, which is the
only place in this project where the liveness bound binds at all (C8). A
negotiated contract preserves the negotiation and pays for it in termination.

### 6. Composition recovers the guarantee — the culmination

Arm C-meet enforces the meet of the negotiated envelope and the platform's
mandate. The pre-phase is identical to arm C; only the contract handed to the
filter differs. §9.5's Proposition 3 is what licenses it:
C(θ₁ ∧ θ₂) = C(θ₁) ∩ C(θ₂), exactly.

| | arm A | arm D | arm B | arm C | **arm C-meet** |
|---|---|---|---|---|---|
| proposals offered | 95 | 80 | 51 | 219 | 67 |
| breaching the scenario θ | 0.858 | 0.822 | 0.472 | 0.922 | 0.664 |
| deals settled | 12 | 12 | 16 | 14 | **15** |
| settled breaching the scenario θ | 0.083 | 0.083 | **0.000** | 0.143 | **0.000** |
| overspend | £0.00 | £0.00 | £0.00 | £0.48 | **£0.00** |

**The guarantee is recovered, and closure is not the price.** Zero of fifteen
settled deals breach the mandate; overspend returns to £0.00 from arm C's
£0.48; and fifteen deals close, against arm B's sixteen and arm A's twelve. The
structural half holds by construction and was verified rather than assumed: the
enforced contract refines the mandate in **27 of 27** frozen instances, and
refines the negotiated envelope in 27 of 27 as well — so what the parties agreed
survives inside what is enforced.

That is the thesis's answer to its own title. A self-negotiated contract is safe
to *permit* precisely when it is not enforced alone.

**The negotiated side genuinely binds** — on 17 of 27 frozen instances across 4
distinct pairs — so the composition is not a formality that collapses back to
the mandate. But the bite is one-sided and scenario-specific: it is always on
the cost floor and never on the budget, because the seller's opening ask sits
above the mandate's ceiling on every pair, and 16 of the 17 leave a **degenerate**
safe set — a single admissible price — because `bargain_3_9` tells the buyer its
budget, so the buyer's revealed floor coincides with the platform's ceiling.

**Two things this arm did not deliver, and both belong here rather than in a
footnote.** The intervention rate was predicted to rise and instead fell — 0.82
against arm B's 0.89 — because the pre-phase absorbs the opening exchange where
arm B does most of its correcting, so a tighter contract governs a shorter
window. And composition can *destroy* feasibility: on one seed a buyer
counter-offered above its own stated budget, the meet had no common ground, and
the pair ran unfiltered. That is the arm's only breaching enforced round. On
satisfiable meets it is 16 enforced rounds, 0 breaching.

## The claim this supports, and the claim it does not

**Supported:** the filter converts a *tendency* into a *bound*. Per-round
exposure goes to zero, on governed pairs, on live agents, with no agent forked
and no fallback tier ever firing. That is the live replication of F1
(9.9% → 0% in simulation).

**Supported, as of arm C-meet:** that a contract the parties negotiate for
themselves can be permitted without giving up the platform's guarantee, provided
it is composed with the mandate rather than enforced in its place. 0/15 settled
breaches with closure preserved.

**Also supported, as of the undisclosed scenario:** that the filter averts
*realised* harm where the counterparty cannot police the constraint itself —
£21.70 → £0.00 on governable pairs, 15/15 breaching deals → 0/13, in every seed.

**Not supported:** that this magnitude transfers. The benefit is a function of
how informed the counterparty is, and the two scenarios are the extremes of that
axis rather than samples from it. On `bargain_3_9` the buyer accepted one bad
deal in twelve and the filter averted nothing measurable; on `undisclosed_3_9`
it averted everything. Neither number is a prediction for a marketplace in
between.

## The cost of the guarantee

Zero detectable, and the caveat is the sample size. No pair closed ungoverned
and stopped closing under the filter. Arm B settled *more* deals (16 vs 12),
but almost all of that is one pair, and arm B's runs predate the reconciliation
fix, so its trajectories came from a seller reasoning about prices it never
offered.

## Method material belonging in chapter 4

Seven bugs are worth a page, because each is a general lesson about testing a
safety layer and each passed a full suite. They are set out in chapter 4 §4.5;
what belongs here is only which results they touched:

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

4. **The intervention logging gap.** Opening projections were recorded with
   `intervention = 0`, hiding almost every correction the filter made and
   producing the false "enforcement is prevention" finding retracted in §4.
5. **The buyer's counter-offer was the seller's own quote.** Buyers restate the
   price on the table before naming their own — "The current quote of $13.76 is
   above my budget of $11.58" — and `_MONEY.search` returns the *first* figure.
   The extractor recorded a counter-offer at the seller's own ask and discarded
   the buyer's real position. **110 of 125 extracted buyer moves (88%) were
   echoes.** It corrupted only the *observed* trajectory, so the drift,
   funnelling and safety results — computed on binding trajectories or database
   outcomes — survive; the section 11 report did not.

6. **The negotiated arms raised on every governed round.** Arms C and C-meet
   threw on every proposal after θ was agreed. The exception escaped before the
   action was persisted, so messages vanished silently and five seeds produced a
   clean, interpretable, entirely false result — 0 enforced rounds out of 35 —
   that was nearly written up as "the pre-phase consumes everything". An A/B
   control on an untouched code path is what caught it.
7. **The projection returned the breach on a degenerate safe set.** Composition
   makes C(θ) a single point on this scenario, and the QP cannot land on one; the
   routine handed back the unsafe input while reporting success. Arm C-meet
   breached 2 of 6 enforced rounds before this was closed.

The common thread: all seven were invisible to tests that asserted on a
plausible-looking surface rather than the one that decides what the counterparty
sees. Three later lessons compound it — a value nothing depends on is a value
nothing checks (bug 5); a safety layer fails *quietly*, returning well-formed
output from a function whose whole job was to return a safe one (bugs 6 and 7);
and when a result looks like a finding, control for the diff before believing it
(bug 6).

## Figures

1. Three-arm bar chart: offered / settled / governed-per-round, with the A–D
   noise floor as an error band. *(have data)*
2. Flagged-vs-corrected, with the different-trajectories caveat in the caption.
   *(have data)*
3. Per-pair closure table across arms, with infeasible pairs marked. *(have)*
4. The `mexican_3_9` → `bargain_3_9` inversion — offers worse, deals cleaner.
   *(have)*
5. **The harm-averted bar**: value transacted above the ceiling, arm A vs arm B
   on `undisclosed_3_9`, per seed. The centrepiece figure. *(have)*
6. **The refinement lattice**: θ_negotiated, θ_mandate and their meet on one
   pair, with C(θ) drawn in (p, q), showing the envelope sitting *above* the
   mandate and the meet below both. *(have data; schematic)*
7. Five-arm settled-breach and overspend summary. *(have)*
