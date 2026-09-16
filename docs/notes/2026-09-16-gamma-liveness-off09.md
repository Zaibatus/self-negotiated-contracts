# γ bites: the sweep re-run where the negotiation is long enough to see it

**Date:** 2026-09-16
**Executes route (1) of 2026-08-07-gamma-independence.md §"What would make γ bite".**
**Data:** arm B on `disclosed_offset_low_3_9` (f = 0.90), γ ∈ {0.2, 0.4, 0.7, 1.0},
5 seeds each, gemini-2.5-flash, T_max = 6. 15 new runs (γ = 0.4 reuses
`arm_b_off09_1..5`).

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts

for SPEC in g02:0.2 g07:0.7 g10:1.0; do
  TAG=${SPEC%%:*}; G=${SPEC#*:}
  for i in 1 2 3 4 5; do
    uv run python experiments/arm_b_imposed.py \
        --data data/disclosed_offset_low_3_9 \
        --gamma $G --t-max 6 --experiment "arm_b_off09_${TAG}_v$i" --override
  done
done
uv run python exploration/live_convergence/analyse_gamma_off09.py
```

Numbers are in `results/summary/gamma_liveness_off09.json` (tracked).

---

## Result

Satisfiable pairs only (the 4 no-bargaining-zone pairs per run are forwarded
by design and split out; their rounds account for every breach flag in the
raw logs). Margin is min h over the economic rows (budget, cost_floor) —
the q box rows are structurally zero on this scenario and would read 0.000
at every γ, which is exactly the mistake the old sweep's margin column made.

| γ | governed rounds | breaches | median rounds/pair | median margin | per-step ρ to rest point (n) | 1 − γ |
|---|---|---|---|---|---|---|
| 0.2 | 500 | **0** | 15.0 | 0.0361 | **0.778** (318) | 0.8 |
| 0.4 | 285 | **0** | 10.5 | 0.0172 | **0.571** (170) | 0.6 |
| 0.7 | 285 | **0** | 7.0 | 0.0022 | **0.281** (84) | 0.3 |
| 1.0 | 187 | **0** | 3.0 | 0.0022 | **0.000** (20) | 0.0 |

Three claims, each of which the 2026-08-07 sweep could not make:

**1. γ is live.** Median negotiation length is monotone in γ: 15 rounds at
γ = 0.2 down to 3 at γ = 1.0. On `bargain_3_9` every cell sat at 1.2–1.4
rounds and 73–86% of governed rounds were the γ-blind opening projection;
here the opening is < 5% of rounds and the continuation dominates.

**2. The observed contraction rate is the filter's rate constant.** Per-step
distance to the trajectory's own rest point contracts at a median ratio that
matches 1 − γ in all four cells (0.778 vs 0.8, 0.571 vs 0.6, 0.281 vs 0.3,
0.000 vs 0.0). The mechanism is visible in any single trajectory
(`arm_b_off09_g02_v1`, business_0001|customer_0001): the opening is projected
onto the budget boundary, the buyer then demands a price at the seller's cost
floor, and the filter clips each concession so h_cost_floor decays
0.521 → 0.416 → 0.331 → 0.266 — ratios 0.799, 0.796, 0.803. The DCBF
inequality h_{k+1} ≥ (1 − γ) h_k is met with equality: the agents push hard
enough that the constraint, not their concession schedule, sets the speed.
This bounds the arm C finding ("ρ ≈ 0.62 governed and ungoverned — that's
the agents, not my filter"): it is true where the filter is slack, and false
where it binds. Under a binding contract, convergence speed belongs to γ.

**3. The boundary layer exists and widens as γ falls.** Median continuation
margin 0.036 at γ = 0.2 vs 0.002 at γ ≥ 0.7, and the mean-margin-by-round
profile decays geometrically at ≈ 1 − γ per cell (γ = 0.2:
0.217 → 0.209 → 0.171 → 0.138 → 0.111 → 0.089; γ = 0.4:
0.147 → 0.088 → 0.053 → 0.034; γ = 0.7: 0.039 → 0.014 → 0.005). The
conservatism premium reaches the settled price with the predicted sign —
the buyer pays a median 1.1 cents above the cost floor at γ = 0.2 against
0.2 cents at γ ≥ 0.7 — but it is economically negligible here, because even
at ratio 0.8 per round a 15-round negotiation decays a $0.52 gap to cents.
A deadline that cuts negotiations short is what would make the premium
material; see the enforced-T_max work.

**Safety is intact in the long regime.** Zero breaches on satisfiable pairs
across 1,257 governed rounds — an order of magnitude more exposure than the
126 rounds the original sweep certified on.

## What did not match

The shadow-price prediction. §6 reads a small γ as inflating the duals by a
conservatism premium; measured mean cost_floor duals *rise* with γ (0.20,
0.18, 0.32, 0.41 for γ = 0.2 → 1.0). The confounder is mechanical: the QP's
DCBF row lower bound is −γ h₀, so the dual is priced against a γ-scaled
constraint and the two effects are not separated by this design. Reported,
not resolved.

## Files

- `exploration/live_convergence/analyse_gamma_off09.py` — the analysis
  (explicit per-cell globs; a prefix glob would fold the later off09
  families into the γ = 0.4 cell).
- `results/arm_b_off09_g{02,07,10}_v{1..5}/` — the 15 new runs.
- `results/summary/gamma_liveness_off09.json`.
