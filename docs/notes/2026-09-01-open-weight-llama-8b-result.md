# Llama 3.1 8B cannot drive the testbed — and the preflight did not predict it

**Date:** 2026-09-01 (runs executed 2026-08-28)
**Status:** RUN, one seed, arm B, `bargain_3_9`, γ = 0.4, T_max = 6.
**Cost: £0.00** — local Ollama on the M4, no hosted API.
**Scores** prediction 4 of `2026-08-28-open-weight-model-preregistration.md`.
Predictions 1–3 are **not** scored: the run produced zero governed rounds, so
there is nothing to compare against arm B's 0/27.

## Reproduce

```bash
brew install ollama
OLLAMA_FLASH_ATTENTION=1 OLLAMA_CONTEXT_LENGTH=16384 ollama serve &
ollama pull llama3.1:8b

cd ../multi-agent-marketplace && docker compose up -d && source .env
export LLM_PROVIDER=openai OPENAI_BASE_URL=http://localhost:11434/v1
export OPENAI_API_KEY=ollama LLM_MODEL=llama3.1:8b
unset LLM_REASONING_EFFORT
cd ../self-negotiated-contracts
uv run python experiments/preflight_model.py --trials 5
uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
    --gamma 0.4 --t-max 6 --experiment arm_b_llama_pilot --override
```

The message mix, which is the diagnostic that matters:

```sql
select data->'request'->'parameters'->'message'->>'type', count(*)
  from arm_b_llama_pilot.actions
 where data->'request'->>'name' = 'SendMessage' group by 1;
```

`OLLAMA_CONTEXT_LENGTH=16384` is not optional. The default is 4096 and the
agent prompts exceed it; every request in this run logged `truncated = 0` only
because the context was raised first.

## The result

One seed of arm B, against the same seed of the Gemini run:

| | Llama 3.1 8B | Gemini 2.5 Flash |
|---|---|---|
| text messages | 90 | 58 |
| **order proposals** | **2** | 9 |
| **payments** | **0** | 3 |
| Search calls | 3 | 3 |
| FetchMessages | **6619** | 99 |
| pairs engaged | 2 of 27 | — |
| **governed rounds** | **0** | 5–7 |
| wall clock, one seed | **32 min** | ~1 min |

The registry is identical on both runs — 9 businesses, 3 customers, 27 pairs,
9 definable, 18 undefinable, 4 unsatisfiable, 5 tradeable — so the scenario is
not what differs.

**Llama converses and does not transact.** It sends *more* text than Gemini and
almost no structured proposals, and it never completes a payment, so no deal
closes. It polls `FetchMessages` 67× more, which is where the 32 minutes went.

**The filter never executed.** `solver_calls = 0`. Both pairs Llama engaged
were among the 4 whose safe sets are empty and which run unfiltered by design.

**It cannot address counterparties reliably.** 14 of its 17 errors are
`to_agent_id biz_0003 not found` — it invents `biz_0003` for `business_0003`.
That is part of why only 2 of 27 pairs were engaged at all.

## The methodological finding, which is the reusable part

`preflight_model.py` scored this model **5/5 schema valid, verdict USABLE**
minutes before the arm produced nothing. The preflight was not wrong; it was
answering a different question.

- The preflight measures **capability in isolation**: asked directly for an
  `OrderProposal`, can the model emit one?
- The arm requires **choice under a long agent loop**: given a conversation, a
  menu, a counterparty and a tool set, does the model *elect* to emit one?

These come apart, and they came apart completely here. Any model-swap claim
resting on one-shot schema compliance is unsupported.

This is the same shape as the seven integration bugs: a plausible surface that
nobody had asserted on, standing in for the surface that decides the outcome.
It is the eighth instance and belongs in chapter 4 with the others. The
mitigation is now built in — `preflight_model.py` documents the limit, and
`run_open_weight_sweep.sh` gates the full sweep behind a one-seed pilot and the
message-mix query above.

## A second pathology, smaller but real

Across preflight trials Llama produced line items summing to £27.50 and
reported `total_price` of 33.00, 32.10, 31.50 — **100% inconsistent**, roughly
20% high. Magentic scores this as `invalid_total_price`
(`run_analytics.py:515`) rather than rejecting the message, and `total_price`
is both what the customer pays (`run_audit.py:453`) and what the budget row
reads, so the enforcement measurement would stay coherent. It is not a blocker.
It is a failure mode Gemini does not have, and had the arms run it would have
given the filter *more* to catch, not less.

## What is NOT established

- **Nothing about open-weight models in general.** This is one model at one
  size, locally quantised. The obvious confounds — 8B scale, Q4 quantisation,
  Ollama's OpenAI-compatibility shim — are not separated.
- **A qwen2.5:14b comparison was attempted and is void.** Every one of its 300
  LLM calls returned `404 model not found`: the download had been killed
  mid-flight by a server restart and `ollama pull` reported exit 0 regardless.
  No conclusion of any kind should be drawn from that run, and its schema
  `arm_b_qwen_pilot` should be dropped rather than replayed.
- **The vendor-independence question remains open.** `SCIENCE.md` §8's model
  row still reads three Gemini models. The next attempt is a hosted
  open-weight model at 70B (`llama-3.3-70b-versatile` via Groq), which is
  wired and gated in `experiments/run_open_weight_sweep.sh` and needs only a
  key.

## Honest note on how this was reported

The first pass at this called the arithmetic inconsistency fatal and marked the
model NOT USABLE, which was wrong — the marketplace tolerates it by design. The
second pass then called the model USABLE, which was also wrong, for the
opposite reason. Only the pilot settled it. Recorded because the write-up
should not present a verdict that took two corrections as though it were read
off cleanly the first time.
