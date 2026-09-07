# Replicating the safety axes on an open-weight model

**Date:** 2026-08-28
**Status: PREFLIGHT BUILT AND VALIDATED, ARMS NOT RUN.** No open-weight model
has been contacted and no money has been spent on one. Everything below
"Registered predictions" is a prediction, not a measurement, and must not be
cited as a result.
**Blocked on:** an endpoint. See "What is needed".

## Why this axis, and why it is the weakest one

`SCIENCE.md` §8 replicates safety along four axes, and the model axis is the
soft one: three Gemini models, one vendor, one instruction-following lineage,
one structured-output implementation. "0/100 governed rounds across three
Gemini models" answers *does this survive a model swap* only in the narrowest
sense.

The mechanism argument says it should not matter at all. The filter is
policy-agnostic — it projects whatever arrives, and never reads the model that
produced it. If that argument is right, an open-weight model with entirely
different failure modes changes nothing. **A vendor-independent replication is
therefore the cheapest available strengthening of the strongest claim in the
thesis**, and the only version of the model axis that answers the obvious
reviewer question.

## Why the preflight exists

Switching model is pure configuration: `LLM_PROVIDER`, `LLM_MODEL`, and for
anything OpenAI-compatible `OPENAI_BASE_URL`, which
`clients/openai.py` already exposes as `EnvField("OPENAI_BASE_URL")`. No code
change. Llama through Ollama, Groq, Together or Fireworks all reach the
marketplace unmodified.

What does not transfer for free is **structured output**. Every seller move is
an `OrderProposal` with a typed item list, and the enforcement path reads
`total_price` and per-item quantities to build the budget row. A model that
emits prose where a schema was demanded produces no proposal, no contract row,
and therefore **no governed round** — which in the summary tables is
indistinguishable from "the filter had nothing to correct".

That is the sixth instance of the pattern behind all five integration bugs: a
plausible-looking value on a surface nobody asserted on. So the schema question
is asked first, for pennies, by `experiments/preflight_model.py`.

**The preflight is validated.** Run against the current Gemini configuration it
returns 3/3 schema-valid, 3/3 with `total_price` consistent with the line items
(5.50 × 5 = 27.50), mean latency 1.09 s, verdict USABLE. So a failure against
an open-weight model is a fact about that model, not about the harness.

## What is needed

One of:

1. **Ollama, local, free.** `brew install ollama && ollama pull llama3.1:8b`.
   No API cost; slow on this machine and its OpenAI-compatibility layer has
   historically been the weakest at strict JSON schema, so the preflight may
   well return NOT USABLE.
2. **A hosted open-weight endpoint** — Groq, Together or Fireworks. Costs
   roughly the same as arm F (~£0.50 for 5 seeds × 2 arms) and has materially
   better structured-output support. This is the one to prefer.

## Reproduce

```bash
# 1. preflight — pennies, and refuses to proceed if the model cannot be driven
export LLM_PROVIDER=openai
export OPENAI_BASE_URL=https://api.groq.com/openai/v1   # or the Ollama URL
export OPENAI_API_KEY=...                               # 'ollama' for Ollama
export LLM_MODEL=llama-3.3-70b-versatile
uv run python experiments/preflight_model.py --trials 10

# 2. only if the verdict is USABLE — the arms, mirroring the 2026-08-07 sweep
cd ../multi-agent-marketplace && docker compose up -d && source .env
cd ../self-negotiated-contracts
TAG=llama_3_3_70b
for i in 1 2 3 4 5; do
  uv run python experiments/arm_a_no_contract.py --live --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_a_${TAG}_v$i" --override
  uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_b_${TAG}_v$i" --override
done

# 3. outcomes from the database, never from the regulator's own log
uv run python -m src.marketplace_integration.replay \
    --schemas arm_b_${TAG}_v1 arm_b_${TAG}_v2 arm_b_${TAG}_v3 \
              arm_b_${TAG}_v4 arm_b_${TAG}_v5 \
    --data data/bargain_3_9 --out results/replay_${TAG}
```

Everything else is held at the standard configuration: γ = 0.4, T_max = 6,
5 seeds, `bargain_3_9`, so the only thing varying against the 2026-08-07 sweep
is the model.

## Registered predictions

Written before any run, scored as written afterwards, in the arm F style.

1. **Arm B governed breaches: 0 / all rounds.** The strong prediction. The
   filter never reads the model, so a non-zero count would mean the safety
   result was an artefact of Gemini's behaviour, which would be the most
   important negative result in the thesis.
2. **Arm A offered-breach rate is *not* predicted to match Gemini's 0.858.**
   A different model bargains differently and the ungoverned rate is a fact
   about the agent. Any value is consistent with the thesis; only a rate near
   zero would be awkward, because it would mean this model has nothing for the
   filter to correct and the arm is uninformative rather than confirmatory.
3. **Intervention rate falls in arm B's recorded 0.60–0.83 band**, weakly. It
   depends on how far outside C(θ) the openings land, which is model-dependent.
4. **Structured-output failures, if any, appear in the preflight and not
   silently in the arms.** If the preflight is USABLE and arms still produce
   zero governed rounds, that is a bug, not a result — the same shape as
   integration bug 6, which produced a clean, interpretable and entirely false
   five-seed result.

## How to report it

If prediction 1 holds, `SCIENCE.md` §8's model row becomes *"3 Gemini models
plus one open-weight model, 0 / N governed rounds"* and the vendor-independence
question closes. If it fails, that is the headline finding of the thesis and
everything else is subordinate to it.

Either way the **n stays 5 seeds × 3 customers**, and the categorical framing
in §12 applies unchanged.
