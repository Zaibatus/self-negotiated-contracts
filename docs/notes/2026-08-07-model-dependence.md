# Is the result LLM-dependent?

**Date:** 2026-08-07
**Answers supervision ask (3) of 2026-08-06.**
**Data:** arms A and B on `bargain_3_9`, γ = 0.4, T_max = 6, 5 seeds per cell,
three models. 20 new runs.

## Reproduce

```bash
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts

for M in gemini-3.5-flash gemini-3.1-flash-lite; do
  TAG=$(echo $M | tr '.-' '__'); export LLM_MODEL=$M
  for i in 1 2 3 4 5; do
    uv run python experiments/arm_a_no_contract.py --live --data data/bargain_3_9 \
        --gamma 0.4 --t-max 6 --experiment "arm_a_${TAG}_v$i" --override
    uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
        --gamma 0.4 --t-max 6 --experiment "arm_b_${TAG}_v$i" --override
  done
done
```

Numbers are in `results/summary/models.json` (tracked).

---

## The hypothesis, and it holds

**The safety result should be model-independent by construction** — enforcement
happens at the protocol, so the filter does not care what produced the
proposal — while the **behavioural** results should vary, because how often an
agent proposes something inadmissible is entirely a property of the agent.

Both halves confirmed.

| model | arm | offered breach | settled breach | governed breaches | deals | corrected | mean ‖u‖_M |
|---|---|---|---|---|---|---|---|
| gemini-2.5-flash | A | 0.858 | 0.083 | 46/58 | 12 | — | — |
| | **B** | 0.472 | **0.000** | **0/27** | 16 | 24/27 | 0.874 |
| gemini-3.5-flash | A | 0.667 | 0.067 | 28/49 | 15 | — | — |
| | **B** | 0.299 | **0.000** | **0/52** | 15 | 52/52 | 0.564 |
| gemini-3.1-flash-lite | A | 0.655 | 0.000 | 17/35 | 15 | — | — |
| | **B** | 0.377 | **0.000** | **0/21** | 15 | 19/21 | 0.887 |

### Safety: identical across all three

**Zero governed-pair breaches under arm B, in every model, across 100 governed
rounds.** This was pre-registered as falsifiable: a non-zero result for any
model would have been an enforcement bug rather than a finding. It did not
occur.

That is what "model-independent by construction" should look like when it is
true. The filter never inspects the model, the proposal, or the prompt — it
reads the terms, solves a QP, and rewrites. Nothing in that path can vary with
the generator.

### Behaviour: varies substantially

The ungoverned numbers move by a lot:

- offered breach rate spans **0.655 → 0.858**, a 0.20 range against a
  within-model seed SD of ~0.03–0.05;
- governed per-round breaching spans **49% (17/35) → 79% (46/58)**;
- settled breaches: gemini-3.1-flash-lite settled **zero** bad deals in 15,
  where gemini-2.5-flash settled 1 in 12.

So the *problem* the safety layer addresses is strongly model-dependent, and
the *solution* is not. That is a good shape for the thesis: the guarantee does
not inherit the variance of the thing it governs.

### One counter-intuitive detail worth keeping

The **weakest** model tested (`gemini-3.1-flash-lite`) produced the **fewest**
breaches and settled no bad deals. Capability and contract compliance are not
aligned here — the smaller model proposes less aggressively rather than more.
With n = 5 seeds and one scenario I would not build on it, but it argues
against the intuition that better models are safer negotiators.

## A reporting bug this found, and it corrects a published number

`intervention` was recorded as `0.0` for the **opening projection** — the
correction applied to the first proposal of a negotiation, which does not go
through the barrier QP and so arrived with `result=None`. It is unambiguously
an intervention: the terms the buyer receives differ from the terms the seller
sent.

The consequence is large. For the baseline model:

| | arm B, governed rounds |
|---|---|
| previously reported "filter bound at all" | 11.1% |
| **actual, counting opening projections** | **88.9% (24/27)** |
| of which opening projections | **21** |

**The arm B note's filter-behaviour table is wrong** and is corrected there.
The filter is not a light touch that occasionally nudges — it rewrites almost
every proposal it sees, and the great majority of that work happens on the
opening offer.

That also re-frames the "enforcement is prevention" finding from the arm D
note: the mechanism is now visible rather than inferred. The filter corrects
the opening, and the corrected opening is why so little correction is needed
afterwards.

A second inconsistency surfaced with it: recorded interventions were computed
in **raw** Euclidean norm while `FilterResult.intervention` used the scaled
metric, so the arm B note's "mean 0.795" was in mixed units. Both are fixed,
and the table above is in scaled units throughout. All figures here were
recomputed from the stored records rather than by re-running, since
`u − u_prop = x_applied − x_proposed` is exact and both are recorded.

## Limitations — and this one is substantial

**This tests capability, not vendor.** Only `GEMINI_API_KEY` is available;
OpenAI and Anthropic clients need keys that are not set. The cross-vendor
comparison supervision actually asked for remains **not done**.

**And it does not cleanly test capability either.** Every 2.x model except
`gemini-2.5-flash` has been retired by the API — `gemini-2.5-pro`,
`gemini-2.5-flash-lite`, `gemini-2.0-flash` and `gemini-2.0-flash-lite` all
return 404 "no longer available", despite `gemini-2.5-pro` still being listed
by the models endpoint. So a within-generation ladder was impossible and the
comparison crosses generations, mixing capability with whatever else changed
between 2.5 and 3.x.

**Reasoning effort is held constant at `minimal`, which excluded the pro-class
models.** `gemini-3.1-pro-preview` and `gemini-3.6-flash` both fail with
"Budget 0 is invalid. This model only works in thinking mode." Running them at
a higher effort would have confounded capability with reasoning budget, so they
were dropped rather than run under different settings. The strongest model
tested is therefore a flash-class one.

**n = 5 seeds × 3 customers per cell**, as everywhere else. The safety result
is 0/100 and needs no interval; the behavioural spreads are three points and
should be read as suggestive.

**Deals settled is flat at 15 for both new models** against 12 for the
baseline, and I have not investigated why. It may be that the newer models
close more reliably, or a scenario interaction. Not claimed either way.
