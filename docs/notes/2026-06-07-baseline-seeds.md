# Arm A Baseline — 3-Seed Summary

**Date:** 2026-06-07  
**Scenario:** `mexican_3_9` (3 customers, 9 businesses)  
**Model:** `gemini-2.5-flash`, minimal reasoning effort  
**Seeds:** `baseline_v1`, `baseline_v2`, `baseline_v3`

---

## Per-seed results

| Seed | Susan Young | Jackson Miller | Angela Ng | Total utility |
|------|-------------|----------------|-----------|---------------|
| v1 | $13.51 optimal ✓ | $8.66 **suboptimal** (opt $8.31, +4.2%) | $32.88 optimal ✓ | 63.43 |
| v2 | $13.51 optimal ✓ | $8.31 optimal ✓ | $32.88 optimal ✓ | 63.78 |
| v3 | $13.51 optimal ✓ | $8.66 **suboptimal** (opt $8.31, +4.2%) | $32.88 optimal ✓ | 63.43 |

**Mean total utility:** 63.55  
**Std dev:** 0.20

---

## First-proposal bias observation

Jackson Miller exhibits suboptimal choice in **2/3 seeds**. The mechanism is transparent from the logs:

- The customer broadcasts to all 9 businesses simultaneously.
- Businesses that propose first (without waiting to assess competition) win, even at a worse price.
- In v1 and v3: Sol y Sazón ($8.66) sent its proposal before Casa de Sabor ($8.31). Jackson accepted the first valid proposal received.
- In v2: The search returned Casa de Sabor first in the results list, and Casa de Sabor proposed first, so Jackson paid the optimum.

**Root cause:** first-proposal bias here is driven by proposal *timing* (which business replies faster), not search ranking. The search always returns all 9 businesses; the ordering within the results list varies by seed and influences which business the customer contacts first, which in turn influences which business replies first.

This is a weaker form of the 10–30× bias described in Bansal et al. (2025) — here the bias is 4.2% price overpay rather than a 10–30× speed/quality trade-off — but the structural mechanism (accept first acceptable proposal without waiting) is identical.

---

## LLM call counts

| Seed | LLM calls | Failed |
|------|-----------|--------|
| v1 | 46 | 0 |
| v2 | 54 | 0 |
| v3 | 49 | 0 |

Mean: 49.7 calls per run. At gemini-2.5-flash pricing, ~$0.05–0.15 per run.

---

## Implications for arm B / arm C

- An externally-imposed contract (arm B) that requires businesses to include a "best-price guarantee" clause would push Jackson Miller to the optimal price regardless of proposal order.
- A negotiated contract (arm C) where Jackson Miller explicitly negotiates on price before accepting should also eliminate the suboptimal outcome — the negotiation creates a commitment device that delays acceptance until proposals converge.
- This makes Jackson Miller's transaction the **primary within-seed indicator** to track across arms.
