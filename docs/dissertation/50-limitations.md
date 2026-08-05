# Chapter 6 — Limitations

Deduplicated from six sources: `formulation.md` §10 (items 1–8), the addendum
§A.5 (items 9–17), and the limitation sections of the four arm notes. Where the
same limitation appears in several places the strongest statement wins; where
two sources disagree, the disagreement is noted rather than resolved silently.

**State: DONE.** This is the single list; the sources should point here rather
than restating.

---

## A. Scope of the formalism

**A1 — Quantitative terms only.** Clauses with no numeric template ("delivery
in good faith") have no h(x). The thesis restricts to structured terms, which
are the economically binding core of a marketplace transaction but not all of a
contract. *(§10.1)*

**A2 — Utilities are quadratic/quasi-linear with symmetric logistic
acceptance.** Proposition 1 depends on transferable utility, symmetry and
interiority. *(§10.2)*

**A3 — Convergence is local.** The induced game is monotone within ≈1 scaled
unit of the agreement, not globally (18% over the whole box). This is a design
instruction — confine C(θ) to the stable region — but the sufficient condition
on θ is open. *(§10.3, OPEN-3)*

**A4 — Φ_proj = 0 is a weaker statement at a corner than in the interior.**
Prop. 1 identifies the field zero with the bargaining solution under
interiority; the separation is 0.029 units with one binding constraint and
unmeasured at a corner. *(addendum 15)*

## B. Guarantees that are conditional or unenforced

**B1 — Termination is measured, not enforced.** §6.3 says termination is
*achieved* by escalating friction; the integration computes G_κ from a schedule
the agents never experience. The liveness half of §5 has no live evidence at
all. **This is the largest gap between what the formulation claims and what the
implementation does.** *(addendum A.5.1; every arm note)*

**B2 — Invariance holds from inside C(θ).** From outside, the DCBF gives
geometric recovery, not instant compliance. Opening proposals are projected
once rather than recovered, which is a design decision, not a theorem. *(§10.6)*

**B3 — The budget row is linearised per round.** Large single-round jumps are
an attack surface; closed by backtracking on the true bilinear h, which makes
"zero violations of the true h" hold by construction rather than by luck.
*(§10.6, and the filter's own docstring)*

**B4 — Contracts with an empty safe set are detected and deliberately not
filtered.** Where c·q_min > B no proposal can comply. Projecting into an empty
set is not a safety operation, so those pairs run in monitor mode and their
breaches are reported separately. Four of nine definable pairs on
`bargain_3_9`. *(addendum 11)*

**B5 — Money is quantised and the safe set is not.** Any "zero breaches" claim
must state whether it survives writing the terms back at currency precision.
Ours does, because the rewrite quantises *into* C(θ); it did not before.
*(addendum 17)*

## C. What the evidence can and cannot carry

**C1 — n = 5 seeds × 3 customers, throughout.** Every empirical claim is five
draws of three situations. The reported ± is seed variance under one fixed
scenario, not sampling error over pairs, and says nothing about generalisation
to other baskets or price levels. The safety result clears the A/D noise floor
by ~12× and survives; the closure, surplus and settled-breach differences do
not. *(all four arm notes)*

**C2 — The benefit side is untested, because of how the scenario was built.**
`bargain_3_9` discloses the budget to the buyer, which makes it bind *and*
makes the buyer enforce it. So the filter is shown to provide a bound, not to
avert harm. A scenario that withholds the constraint from the buyer would
settle this. *(arm A bargain note; outline G1)*

**C3 — The bargaining scenario is authored.** YAML only — the marketplace, the
agents and the prompts are unmodified — but the negotiation is *designed*
rather than naturally occurring. The stock scenario is retained as the control.
*(addendum 10)*

**C4 — Coupling has never run on live agents.** `mexican_3_9` has no business
serving two customers, so the shared-capacity clause, the GNE displacement and
the shadow prices of §8 exist only in simulation. *(addendum 9; outline G2)*

**C5 — Cost-benefit rationalizability is the bridge and is barely tested.**
§3 assumes only that agents move iff ρ‖∇Û_i‖ > κ. The test exists, but λ is
unidentified at 5–15 rounds, so the payoff model falls back to the scenario
prior on every run. *(§10.8, §11; outline G6)*

**C6 — Φ trajectories are collected but not claimed.** §5's 96%-decrease is
under a tuned diminishing step; live agents have no step schedule, so a
decrease fraction on live data would test something never claimed. *(arm B and
D notes)*

**C7 — §6.4's T_max/surplus curve does not transfer.** Measured on proxies at
T_max = 10…320 round-pairs against live lengths of 3–5. The shape is a
contribution; the numbers are not predictions. *(arm B note)*

**C8 — T_max barely binds.** At observed lengths of median 3, p90 5, even the
calibrated T_max = 6 leaves the liveness column with almost no signal.
*(arm B and D notes)*

**C9 — Contraction estimates need a genuine transient.** Noise-ball fits are
not evidence; the transient-only estimator is the corrected one. *(§10.7)*

**C10 — Arm B's trajectories predate the reconciliation fix.** Its outcome
numbers are database measurements and stand; its negotiation paths were
produced by a seller reasoning from prices it never offered. *(arm B, arm D
notes)*

## D. Implementation and reproducibility

**D1 — Extraction risk is asymmetric, and smaller than §10.6 assumed.**
`OrderProposal` is structured, so the seller's terms are read rather than
inferred and the budget row is exact. Only the buyer's free-text counter-offers
are extracted. A test deliberately pins a phrasing the regex misses, so the
surface stays visible. *(addendum 12, correcting §10.6)*

**D2 — Enforcement requires mutating the request the server persists.** A
regulator that rewrites a copy computes corrections and delivers the originals.
Five seeds of arm B did exactly that while passing a full test suite. *(addendum
16)*

**D3 — The environment is not pinned, so "bit-reproducible" is currently false
as stated.** The prototype files are byte-identical with fixed seeds, yet
`audit.py`'s SLSQP probe reports 7/60 status failures where §7 quotes 6.7%
(4/60). scipy changed, not the code. This strengthens the case for OSQP but the
claim needs rewording. *(addendum 13)*

**D4 — Agents in the theory are gradient-ascent proxies.** The transfer to LLM
negotiators rests entirely on C5. *(§10.8)*

## Superseded — do not restate

- *"E13 used a crude boundary projection; rerun with the filter"* (§10.5) —
  **discharged**, addendum A.1. The residual was neither the clip nor step
  decay.
- *"CBF-LLM: flexibility without guarantees"* (§10.1) — **corrected**, see
  `60-related-work.md`. CBF-LLM does prove forward invariance; what fails is
  the antecedent, not the theorem.
- *"the seller desync is cosmetic"* (arm B note, first version) — **corrected**
  and fixed. The stale history is fed to the seller's next prompt.
