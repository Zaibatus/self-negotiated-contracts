# Chapter 7 — Conclusion

**State: DRAFT, 2026-08-10.** Sources: chapters 1 and 5, `50-limitations.md`,
and the gap list in `00-outline.md`.

---

## 7.1 What was established

**A contract's quantitative core can be enforced as a controller, on a live LLM
marketplace, without touching the agents.** Per-round exposure to the enforced
contract is zero on governed pairs in every configuration tried: 27 rounds
under an imposed contract, 100 rounds across three models, 126 rounds across
four values of γ, 136 rounds under a *negotiated* contract, and 22 rounds on
the undisclosed-budget scenario. No agent was forked, no prompt edited, and the
fallback tier never fired.

The invariance of that result is itself the evidence for the mechanism's
central property. The filter reads terms, solves a QP and rewrites; nothing in
that path can vary with the model, the prompt, or the provenance of θ. Where
the *problem* varies substantially — ungoverned offered-breach rates span
0.655 to 0.858 across models — the *solution* does not.

**Enforcement averts measurable harm exactly when the counterparty cannot.** On
a scenario withholding the budget from the buyer, ungoverned trading put £21.70
(7.9% of value) above a ceiling only the platform knew, in every seed, with all
15 settled deals breaching; under enforcement, on governable pairs, £0.00 and
0 of 13. On the scenario where the buyer *is* told its budget, the same
mechanism averts nothing measurable. The benefit of a safety layer is therefore
a function of how informed the counterparty is, and this work brackets that
axis with two extremes rather than asserting a single figure.

**Convergence and termination are separate obligations.** At the bargaining
solution the two agents' gradients are large and opposite — 79.56 each — and
only their sum vanishes, so no single scalar both certifies agreement and
detects that motion has stopped. Further, the friction threshold κ* rises along
an improving path (15.95 → 39.78), so no constant friction both permits
progress and halts at the deal; termination requires escalation. And the rest
point of the concession dynamics is the Nash bargaining solution, so the
convergence target is a property of preferences rather than of the update rule.

**A self-negotiated contract is enforced just as reliably as an imposed one,
and governs less.** Arm C infers θ from the agents' own opening positions and
holds them to it: zero breaches over 136 rounds. But the negotiated contract
**refines the platform's mandate in none of 29 cases** — it is looser on the
budget row by 1.21× on average, because a seller's opening ask sits above the
buyer's reservation — so enforcing it permits *more* realised harm than doing
nothing at all. This is the most substantive conceptual result in the
dissertation, and it converts §9's refinement order from a formal nicety into
the operationally important idea: what parties agree between themselves and
what a platform requires of them are different objects, and only their meet is
both legitimate and safe.

## 7.2 What was not established

Set out plainly, because the value of the safety result depends on not
overstating its neighbours.

**Convergence is not demonstrated on live agents.** It is proved on
gradient-ascent proxies. Live agents have no step schedule, enforced
negotiations run a median of one round, and Φ has a second zero far from the
deal that makes a low reading ambiguous precisely where live trajectories
begin. This asymmetry is stated in chapter 1 rather than left for an examiner
to find.

**Termination is measured, never enforced.** The escalating-friction schedule
from which G_κ is computed is one the agents never experience. The liveness
half of the framework has no live evidence, and this is the largest gap between
what the formalism claims and what the implementation does. Arm C is the only
place the bound binds at all — 14 of 29 agreed contracts run past T_max = 6 —
and even there it is observed rather than imposed.

**The economic half has never left simulation.** The shared-capacity clause,
the generalised Nash displacement and the shadow prices require a seller
serving two buyers concurrently, and the working scenario has none.

**Enforcement does not prevent violations from arising.** Measured per
continuation round it is the *highest* of the three arms. What it does is
correct almost everything it sees, concentrated at the opening, and thereby
shorten the negotiation. An earlier draft claimed prevention; that claim was an
artefact of a logging bug and is retracted.

**The mechanism is not a neutral referee.** It funnels settled terms onto the
constraint boundary — where the buyer spends its entire budget — not onto the
bargaining solution. That the two sit close together on the working scenario is
a coincidence of its calibration, not a property of the method.

**Everything rests on five seeds of three customers.** The safety and
harm-averted results are categorical and survive; the closure, surplus and
settled-breach differences do not clear the noise floor and are not claimed.

## 7.3 The remaining work, in order

Ordered by how much each would change the dissertation's claims, not by cost.

1. **Compose the negotiated contract with the mandate (G9).** Arm C shows the
   two contracts standing in the wrong refinement relation; the fix is to
   enforce their meet. The machinery exists — refinement is componentwise —
   and this is one arm's work. It converts arm C's negative result into a
   positive proposal, and it is the highest-value experiment not yet run.

2. **A scenario that sustains six to ten rounds.** Almost every unanswered
   question is downstream of negotiation length: convergence has no trajectory
   to test, the liveness bound barely binds, λ is unidentified, and "did not
   overshoot" cannot be distinguished from "ran out of rounds". One scenario
   fixes four gaps at once.

3. **Coupling on live agents (G2).** `mexican_33_99` has sellers serving
   multiple buyers, which would exercise the shared-capacity clause and make
   the shadow prices observable. Blocked on a scale-versus-depth decision
   rather than on anything technical.

4. **Enforce termination, or restate the claim (G3).** Either impose the
   friction schedule and accept a second intervention confounding the safety
   arm, or restate the termination result as conditional. The present position
   — claiming achievement while measuring a schedule nobody experiences — is
   the one option that should not survive.

5. **Refuse trades on unsatisfiable pairs (G8).** Where c·q_min > B the
   platform knows with certainty that no compliant deal exists, yet the current
   design merely declines to filter and lets the trade proceed. That is the
   whole of the residual £6.15 under enforcement on the undisclosed scenario.
   Refusing would take marketplace-wide overspend to zero and forbid nothing
   that should have been allowed.

6. **Cross-vendor models.** The model-dependence result compares three Gemini
   models and therefore tests capability, not vendor — and imperfectly even
   there, since the API retired every 2.x model but one. Blocked on API keys.

7. **More seeds.** Cheap, and would move the closure and surplus comparisons
   from "not claimed" to claimable. It would not touch any of the structural
   gaps above, which is why it is last.

## 7.4 Closing

The argument this dissertation makes is narrow and, within its scope, firm. LLM
agents negotiating on a marketplace routinely propose terms that violate the
contracts their own scenarios imply. Nothing about the agents prevents this;
what usually prevents the harm is a counterparty that happens to know the
constraint and refuses. That is a tendency, and a tendency is not a bound.

Treating the contract as a controller supplies the bound. A barrier-function
filter at the marketplace protocol takes per-round exposure to zero, does so
identically across models and across the provenance of the contract, and
averts 7.9% of transacted value on the scenario where the counterparty is
uninformed — all without forking a single agent.

What the work also shows, and what a shorter account would omit, is that this
is not the same as having governed the marketplace. The filter does not stop
violations arising, it is not neutral about where negotiations land, and a
contract the parties negotiate for themselves can be enforced perfectly while
permitting exactly what the platform forbids. Guarantees at the protocol are
real and worth having; the harder question — *whose* contract is being
guaranteed — turns out to be the one that decides whether the guarantee is
worth anything.
