# Chapter 7 — Conclusion

**State: DRAFT COMPLETE, 2026-08-11.** Sources: chapters 1 and 5, `50-limitations.md`,
and the gap list in `00-outline.md`.

---

## 7.1 What was established

**A contract's quantitative core can be enforced as a controller, on a live LLM
marketplace, without touching the agents.** Per-round exposure to the enforced
contract is zero on governed pairs in every configuration tried: 27 rounds
under an imposed contract, 100 rounds across three models, 126 rounds across
four values of γ, 136 rounds under a *negotiated* contract, 16 under a
*composed* one, and 22 rounds on the undisclosed-budget scenario. No agent was forked, no prompt edited, and the
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

**Composition is what makes a self-negotiated contract safe to permit.** This
is the dissertation's answer to its own title, and it arrives in two steps.
First the negative one:

**A self-negotiated contract is enforced just as reliably as an imposed one,
and governs less.** Arm C infers θ from the agents' own opening positions and
holds them to it: zero breaches over 136 rounds. But the negotiated contract
**refines the platform's mandate on none of the 9 pairs** — its budget row is
looser on every one, by 1.05–1.52×, identically in every seed because both
opening positions are deterministic given the scenario, because a seller's
opening ask sits above the buyer's reservation — so enforcing it permits *more* realised harm than doing
nothing at all. This is the most substantive conceptual result in the
dissertation, and it converts §9's refinement order from a formal nicety into
the operationally important idea.

Then the positive one. **Enforcing θ_negotiated ∧ θ_mandate recovers the
guarantee without buying it with closure.** Arm C-meet settles 0 of 15 deals in
breach of the mandate and overspends £0.00 — against arm C's 2 of 14 and £0.48 —
while closing fifteen deals, against arm B's sixteen and the ungoverned twelve.
The enforced contract refines the mandate in 27 of 27 instances and the
negotiated envelope in 27 of 27, so what the parties agreed survives inside what
is enforced: the platform removes only what the mandate already forbade.

This rests on Proposition 3, and the exactness matters. The meet is the true
intersection of the safe sets rather than an inner approximation — each row of h
is monotone in its own θ component and the bilinear budget row is *linear in B* —
so composing contracts forbids nothing that both parties had agreed was
admissible. An inner approximation would have passed every structural check
while quietly narrowing the deal space.

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

1. **A scenario that sustains six to ten rounds.** Almost every unanswered
   question is downstream of negotiation length: convergence has no trajectory
   to test, the liveness bound barely binds, λ is unidentified, and "did not
   overshoot" cannot be distinguished from "ran out of rounds". One scenario
   fixes four gaps at once.

2. **Coupling on live agents (G2).** `mexican_33_99` has sellers serving
   multiple buyers, which would exercise the shared-capacity clause and make
   the shadow prices observable. Blocked on a scale-versus-depth decision
   rather than on anything technical.

3. **Enforce termination, or restate the claim (G3).** Either impose the
   friction schedule and accept a second intervention confounding the safety
   arm, or restate the termination result as conditional. The present position
   — claiming achievement while measuring a schedule nobody experiences — is
   the one option that should not survive.

4. **Refuse trades on unsatisfiable pairs (G8).** Where c·q_min > B the
   platform knows with certainty that no compliant deal exists, yet the current
   design merely declines to filter and lets the trade proceed. That is the
   whole of the residual £6.15 under enforcement on the undisclosed scenario.
   Refusing would take marketplace-wide overspend to zero and forbid nothing
   that should have been allowed.

5. **Cross-vendor models.** The model-dependence result compares three Gemini
   models and therefore tests capability, not vendor — and imperfectly even
   there, since the API retired every 2.x model but one. Blocked on API keys.

6. **More seeds.** Cheap, and would move the closure and surplus comparisons
   from "not claimed" to claimable. It would not touch any of the structural
   gaps above, which is why it is last.

## 7.4 The three deliberate gaps

Three things this dissertation does not do are worth separating from the
ordered list above, because each is a *gap* — a known question left open for a
stated reason — rather than a failure to notice something.

**Coupling and shadow prices.** The shared-capacity clause, the generalised
Nash displacement and the KKT shadow prices are derived, simulated and never
run live. This is not an oversight: it needs a scenario in which one seller
serves two buyers concurrently, and the working scenario has none. `mexican_33_99`
does. The gap is a scale-versus-depth choice made in favour of depth — five arms
on one nine-pair scenario rather than two arms on a ninety-nine-pair one — and
the economic half of the formalism is the price paid for it.

**Cross-vendor models.** The model-dependence result compares three Gemini
models, so it tests capability rather than vendor, and imperfectly even there,
since the API retired every 2.x model but one and the strongest models tested
refused to run at the fixed reasoning budget. What would close it is API keys
for a second and third vendor, and nothing else. The claim in the meantime is
correspondingly narrow: the safety result is *architecturally* model-independent
— the filter never inspects the generator — and *empirically* verified across
three models of one family.

**Live convergence.** Safety is demonstrated live; convergence is not. The
reason is not that the experiment was skipped but that this regime cannot carry
it: enforced negotiations run a median of one round, live agents have no step
schedule to which the theorem applies, and Φ's second zero makes a low reading
ambiguous exactly where live trajectories start. Closing it needs a
sustained-negotiation regime, not more seeds of this one — and arm C is
evidence such a regime is reachable, since a contract loose enough to leave a
bargaining zone produced 219 proposals where the imposed contract produced 51.

The honest summary is that this dissertation demonstrates safety broadly and
convergence not at all, and that the boundary between them is a property of how
short LLM negotiations are rather than of the theory.

## 7.5 Closing

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
