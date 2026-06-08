# Arm A Baseline — 5-Run Summary

**Date:** 2026-06-08  
**Scenario:** `mexican_3_9` (3 customers, 9 businesses)  
**Model:** `gemini-2.5-flash`, minimal reasoning effort  
**Runs:** `baseline_v1` through `baseline_v5`  
**Note on reproducibility:** `magentic-marketplace run` has no `--seed` flag and no randomness control beyond `LLM_TEMPERATURE`. Variability between runs is entirely LLM stochasticity.

---

## Welfare across 5 runs

| Run | Susan Young | Jackson Miller | Angela Ng | Total utility |
|-----|-------------|----------------|-----------|---------------|
| v1 | 13.45 | 9.92 | 40.06 | **63.43** |
| v2 | 13.45 | 10.27 | 40.06 | **63.78** |
| v3 | 13.45 | 9.92 | 40.06 | **63.43** |
| v4 | 13.20 | 10.27 | 40.06 | **63.53** |
| v5 | 13.45 | 10.27 | 35.41 | **59.13** |
| **Mean** | 13.40 | 10.13 | 39.13 | **62.46** |
| **SD** | 0.11 | 0.19 | 2.08 | **1.99** |

Total welfare: **62.46 ± 1.99** (mean ± sample SD, n=5)

---

## Per-customer selection across runs

### Susan Young — items: Pineapple Jalapeño Agua Fresca + Savory Pumpkin Empanadas; requires: Outdoor Seating

Optimal: Poblano Palate ($13.51)

| Run | Paid to | Price | Optimal? |
|-----|---------|-------|----------|
| v1 | Poblano Palate | $13.51 | ✓ |
| v2 | Poblano Palate | $13.51 | ✓ |
| v3 | Poblano Palate | $13.51 | ✓ |
| v4 | Taco 'Bout a Fiesta | $13.76 | ✗ (+1.8%) |
| v5 | Poblano Palate | $13.51 | ✓ |

Suboptimal rate: 1/5 (20%)

### Jackson Miller — item: Jalapeño Infused Tequila Sunrise; requires: Takes Reservations

Optimal: Casa de Sabor ($8.31)

| Run | Paid to | Price | Optimal? |
|-----|---------|-------|----------|
| v1 | Sol y Sazón | $8.66 | ✗ (+4.2%) |
| v2 | Casa de Sabor | $8.31 | ✓ |
| v3 | Sol y Sazón | $8.66 | ✗ (+4.2%) |
| v4 | Casa de Sabor | $8.31 | ✓ |
| v5 | Casa de Sabor | $8.31 | ✓ |

Suboptimal rate: 2/5 (40%)

### Angela Ng — items: Chargrilled Carne Asada + Coconut Lime Tres Leches + Southwest Chicken Enchiladas; requires: Large Groups + Onsite Parking

Optimal: Lime & Char ($32.88)

| Run | Paid to | Price | Optimal? |
|-----|---------|-------|----------|
| v1 | Lime & Char | $32.88 | ✓ |
| v2 | Lime & Char | $32.88 | ✓ |
| v3 | Lime & Char | $32.88 | ✓ |
| v4 | Lime & Char | $32.88 | ✓ |
| v5 | Guac My World | $37.53 | ✗ (+14.2%) |

Suboptimal rate: 1/5 (20%)

---

## Aggregate suboptimality

4 out of 15 customer-run trials (27%) resulted in a suboptimal purchase. All suboptimal purchases still met the customer's stated requirements — they were higher-price choices, not wrong-items choices.

---

## Anomaly: v4 Susan Young, v5 Angela Ng

**v4 Susan Young** received proposals in order $13.51 → $14.34 → $13.76, but paid $13.76 (3rd received, middle price). She had the cheapest option available first and still did not take it. See Block B notes for response-order analysis.

**v5 Angela Ng** received proposals in order $37.53 → $32.88 → $46.17 but paid $37.53 (first received). See Block B notes.

---

## Implications for arm A reporting

For the paper, the 5 runs give mean welfare **62.46 ± 1.99**. The high SD (3.2% of mean) is driven almost entirely by v5's Angela Ng outlier ($37.53 vs the usual $32.88). With v5 excluded as an outlier, the remaining 4 runs give 63.54 ± 0.15.

Recommend reporting: mean ± SD over all 5 runs, with a note that v5 contains an anomalous Angela Ng transaction (first-proposer accepted despite being 14% above optimal).
