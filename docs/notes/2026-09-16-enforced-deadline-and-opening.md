# The deadline enforced, and the opening at γ: one bound holds, one asymmetry is load-bearing

**Date:** 2026-09-16
**Companion to 2026-09-16-gamma-liveness-off09.md; both treatments run against
the same control** (arm B, `disclosed_offset_low_3_9`, γ = 0.4, T_max = 6,
`arm_b_off09_1..5`), gemini-2.5-flash, 5 seeds each. 10 new runs.

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts

for i in 1 2 3 4 5; do
  uv run python experiments/arm_b_imposed.py --data data/disclosed_offset_low_3_9 \
      --gamma 0.4 --t-max 6 --enforce-tmax \
      --experiment "arm_b_off09_tmax_v$i" --override
  uv run python experiments/arm_b_imposed.py --data data/disclosed_offset_low_3_9 \
      --gamma 0.4 --t-max 6 --open-with-gamma \
      --experiment "arm_b_off09_open04_v$i" --override
done
uv run python exploration/live_convergence/analyse_enforced_deadline.py
```

Numbers in `results/summary/enforced_deadline_off09.json` (tracked).

---

## Result

Satisfiable pairs only, as in the companion note.

| | baseline | `--enforce-tmax` | `--open-with-gamma` |
|---|---|---|---|
| governed rounds | 285 | 117 | 295 |
| breach rounds | 0 | **0** | **21** |
| median / max rounds per pair | 10.5 / 31 | 6.0 / **6** | 10.0 / 37 |
| proposals refused at the deadline | — | 16 (16 pairs) | — |
| median settled premium over cost floor | $0.0067 | **$0.0396** | $0.0067 |
| deals settled / settled in breach | 4 / 0 | 4 / **0** | 3 / **2** |
| total overspend | $0.00 | $0.00 | **$0.66** |

### The deadline holds, and its price is the predicted one

Until these runs, T_max was a certificate: arm C had 48% of its pairs sail
past it and nothing happened. With `--enforce-tmax` the protocol stops
delivering proposals once a pair has used its rounds — the limit of the
escalating friction schedule κ_k = κ₀/(1 − k/T_max), implemented with the
same refusal mechanism as G8, no agent touched. Measured:

* **The cap is hard.** Max trajectory length is exactly 6, against 31 in
  the control. 16 proposals across 16 pair-runs arrived after the deadline
  and were refused, so the agents genuinely ran into it.
* **Closure survives.** 4 deals settle, none in breach — the same as the
  control. Ending the negotiation at round 6 did not cost a deal here.
* **Liveness is bought at a price, and the price was predicted.** The
  companion note shows the filter releases the seller's concession toward
  the cost floor at ratio 1 − γ per round. Cut that decay at T_max and the
  buyer should be left paying about h₀(1 − γ)^(T_max − 1) ≈ 0.52 × 0.6⁵ ≈
  **$0.040** above the floor; the measured median premium is **$0.0396**,
  against $0.0067 uncut. The deadline turns the conservatism premium from
  cents into a real transfer, and its size follows from γ and T_max alone.
  Whoever sets the deadline, prices it.

### The opening projection is load-bearing: route 2 settles deals in breach

`--open-with-gamma` replaces the γ = 1 opening projection with a single
barrier step at the arm's γ — route 2 of the gamma-independence note, the
controlled experiment on the module docstring's third asymmetry. Two
findings:

* **The recovery bound is real but slack.** 19 of 24 openings were
  forwarded in breach and the DCBF permits violation to persist at ratio
  1 − γ per round; measured median recovery is **1 round**, because the
  seller's own next proposal usually re-enters C(θ). The barrier's
  geometric recovery is a worst-case bound the agents rarely test.
* **But 2 of 3 settled deals were struck in breach** ($0.66 overspend,
  both classified meaningful) — the only governed-arm breached deals in
  the entire project. The mechanism is not the barrier mathematics, which
  behaved exactly as specified. It is acceptance timing: a buyer can take
  the still-breaching opener before any recovery round happens. A knowing
  breach forwarded for even one round is an offer on the table, and offers
  on the table get accepted.

So the asymmetry the protocol docstring asserts — "the first proposal is
projected, not recovered" — is not a modelling convenience; it is the
difference between zero breached deals and a 67% breached-deal rate in this
cell. Route 2 should stay what it now is: an opt-in flag whose cost is
measured, not a default.

## Files

- `results/arm_b_off09_{tmax,open04}_v{1..5}/` — the 10 runs.
- `exploration/live_convergence/analyse_enforced_deadline.py` — the
  comparison (satisfiable pairs, deals replayed from Postgres).
- `results/summary/enforced_deadline_off09.json`.
