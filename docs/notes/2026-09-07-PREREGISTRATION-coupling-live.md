# PRE-REGISTRATION — the coupling clause, tested live

**Written 2026-09-07, BEFORE any run on `data/coupled_3_9` exists.**
Scenario by `scripts/make_coupled_scenario.py --force`. Not to be edited after
the first run.

## Why

C4: *"Coupling has never run on live agents. No business serves two customers,
so the shared-capacity clause, the equilibrium displacement and the shadow
prices exist only in simulation."* The first clause is a fact about the **data**.
`protocol.py` already has `couple`, `capacity_for` and peer detection, and both
arm scripts already expose `--capacity-factor`. Every shipped scenario is
partitioned one-customer-per-business, so the wiring has never fired.

## The scenario

`business_0001` gains `Jalapeno Infused Tequila Sunrise` at list **8.66**, the
median of the three businesses already stocking it (8.31, 8.66, 11.30). Floor
6.75 against customer_0002's reservation 7.45, so the new pair is tradeable —
checked by the generator, which refuses otherwise. Registry: **10 defined pairs**
(was 9); `business_0001` serves customer_0001 and customer_0002. With
`--capacity-factor 0.67`, **Q = 2.01** against a demand of 3 units, so the clause
binds by construction.

## Registered predictions

**C1 — activation.** The capacity row fires only when both of business_0001's
pairs are concurrently live, because `capacity` is `None` unless `_peers` is
non-empty. I predict it fires on **some but not all** seeds, because customer_0001
may settle with business_0002 or 0003 before customer_0002 engages
business_0001 at all. **If it never fires, the experiment is void** and says
nothing about coupling — that outcome is to be reported as void, not as a null.

**C2 — safety, the load-bearing one.** On seeds where it fires, settled
quantities on business_0001 satisfy **q₁ + q₂ ≤ 2.01**, and governed rounds show
**zero breaches of the capacity row**. This is the coupling counterpart of the
per-pair safety result and is the claim most likely to transfer.

**C3 — a positive dual.** Where the row binds, the filter's multiplier on
`shared:capacity` is **> 0**. §22 shows it equals 2·η·λ_econ at a converged rest
point; live negotiations do not converge, so I predict only the sign, not the
value.

**C4 — the theory test, and I expect it to fail.** §22's variational-GNE result
needs a sustained concurrent negotiation. Live negotiations run a median of
**2 rounds** (measured on the hardbargain pilot today) and both pairs must be
live simultaneously. I therefore predict the allocation will **not** be close to
the equalised-marginal-potential solution, and that this experiment will
establish coupling *safety* live while leaving the *economics* in simulation.

## What would falsify each

- C1 fails if the row fires on every seed, or on none.
- C2 fails if any settled pair breaches Q, or any governed round shows a
  capacity breach.
- C3 fails if the dual is zero while the row is active.
- C4 fails if the allocation matches the equalised-marginal solution.

## Stated confound

Adding an item to a menu adds a **competitor** to customer_0002's choice set as
well as creating coupling. Any comparison against `bargain_3_9` therefore
confounds coupling with competition. §5.2's lesson — an authored scenario
changes more than intended — applies and is not dodged here.

## Protocol

Arm B, 5 seeds, `--capacity-factor 0.67`, γ = 0.4, T_max = 6,
`gemini-2.5-flash` at minimal reasoning effort. Roughly £0.50.
