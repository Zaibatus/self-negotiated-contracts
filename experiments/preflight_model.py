"""Can the configured model actually drive the marketplace? Ask before paying.

The four safety axes vary model, gamma, scenario and contract provenance, but
every model is a Gemini. A reviewer's obvious question is whether the result is
a property of the mechanism or of one vendor's instruction-following, and the
sharpest answer is an open-weight model with different failure modes.

Switching is pure configuration -- `LLM_PROVIDER`, `LLM_MODEL` and, for anything
OpenAI-compatible, `OPENAI_BASE_URL` (dcbf: openai.py defines it as
`EnvField("OPENAI_BASE_URL")`). So Llama via Ollama, Groq, Together or
Fireworks needs no code change.

What does NOT transfer for free is **structured output**. Every seller move in
this testbed is an `OrderProposal` with a typed item list, and the whole
enforcement path reads `total_price` and per-item quantities. A model that
emits prose where a schema was demanded produces no proposal, no contract row,
and therefore no governed round -- which would look exactly like "the filter
had nothing to do" rather than "the model could not be driven". That
misreading is expensive and silent, which is the same failure shape as the five
integration bugs.

So this asks the question first, for a few pennies, before any arm is run:
given the current environment, does the model return a valid OrderProposal, how
often, and how fast?

**What this does NOT establish, learned the hard way on 2026-08-28.** A model
can pass here 5/5 and still be unable to drive the marketplace, because this
tests *capability in isolation* and the arms need *choice under a long agent
loop*. Llama 3.1 8B returned a valid OrderProposal on every trial of this
script and then, in a real arm, sent 90 text messages, 2 order proposals and
**zero payments** across a whole seed -- it chatted instead of transacting and
closed no deal. Gemini on the same scenario sends 58 text, 9 proposals, 3
payments.

A USABLE verdict here is therefore necessary and not sufficient. The cheap
confirmation is a single-seed pilot arm followed by:

    select data->'request'->'parameters'->'message'->>'type', count(*)
      from <schema>.actions
     where data->'request'->>'name' = 'SendMessage' group by 1;

If `order_proposal` is not a healthy fraction and `payment` is zero, the model
cannot drive the testbed however well it scores here.

Reproduce (Ollama, local, free):

    export LLM_PROVIDER=openai OPENAI_BASE_URL=http://localhost:11434/v1 \
           OPENAI_API_KEY=ollama LLM_MODEL=llama3.1:8b
    uv run python experiments/preflight_model.py --trials 10

Reproduce (a hosted open-weight endpoint):

    export LLM_PROVIDER=openai OPENAI_BASE_URL=https://api.groq.com/openai/v1 \
           OPENAI_API_KEY=... LLM_MODEL=llama-3.3-70b-versatile
    uv run python experiments/preflight_model.py --trials 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from magentic_marketplace.marketplace.actions.messaging import (  # noqa: E402
    OrderProposal,
)
from magentic_marketplace.marketplace.llm import generate  # noqa: E402

PROMPT = (
    "You are a seller on a marketplace. The customer wants 3 units of "
    "'widget A' and 2 units of 'widget B'. Your cost floor is 4.00 per unit. "
    "Respond with an order proposal priced at 5.50 per unit for both items, "
    "delivered in 3 days. Use the id 'preflight-1'."
)


async def one_trial(model: str | None, provider: str | None) -> dict[str, Any]:
    started = time.monotonic()
    # Pass provider/model only when explicitly given. Handing `generate` an
    # explicit None makes the discriminated config union fail to extract its
    # tag instead of falling back to the environment.
    kwargs: dict[str, Any] = {}
    provider = provider or os.environ.get("LLM_PROVIDER")
    model = model or os.environ.get("LLM_MODEL")
    if provider:
        kwargs["provider"] = provider
    if model:
        kwargs["model"] = model
    if os.environ.get("LLM_REASONING_EFFORT"):
        kwargs["reasoning_effort"] = os.environ["LLM_REASONING_EFFORT"]
    try:
        result, usage = await generate(
            PROMPT,
            response_format=OrderProposal,
            **kwargs,
        )
    except Exception as exc:
        return {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "seconds": time.monotonic() - started,
        }

    # A schema-valid object is necessary but not sufficient: the enforcement
    # path needs total_price to agree with the line items, because that is the
    # number the budget row is computed from.
    line_total = sum(i.unit_price * i.quantity for i in result.items)
    consistent = abs(line_total - result.total_price) < 0.011
    return {
        "ok": True,
        "consistent_total": bool(consistent),
        "n_items": len(result.items),
        "total_price": float(result.total_price),
        "line_total": float(line_total),
        "delivery": result.estimated_delivery,
        "seconds": time.monotonic() - started,
        "tokens_in": getattr(usage, "prompt_tokens", None),
        "tokens_out": getattr(usage, "completion_tokens", None),
    }


async def run(trials: int, model: str | None, provider: str | None) -> dict[str, Any]:
    results = []
    for i in range(trials):
        outcome = await one_trial(model, provider)
        results.append(outcome)
        flag = "ok " if outcome["ok"] else "FAIL"
        extra = (
            f"items={outcome['n_items']} total={outcome['total_price']:.2f} "
            f"consistent={outcome['consistent_total']}"
            if outcome["ok"]
            else outcome["error"][:120]
        )
        print(f"  trial {i + 1:>2}  {flag}  {outcome['seconds']:>6.2f}s  {extra}")
    return {"trials": results}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=10)
    parser.add_argument("--model", default=None, help="overrides LLM_MODEL")
    parser.add_argument("--provider", default=None, help="overrides LLM_PROVIDER")
    parser.add_argument("--out", default="results/summary/preflight_model.json")
    args = parser.parse_args()

    provider = args.provider or os.environ.get("LLM_PROVIDER")
    model = args.model or os.environ.get("LLM_MODEL")
    base_url = os.environ.get("OPENAI_BASE_URL")
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")

    print("resolved configuration")
    print(f"  provider   {provider}")
    print(f"  model      {model}")
    print(f"  base_url   {base_url or '(provider default)'}")
    print(f"  api key    {'set' if key else 'MISSING'}")
    print(f"  effort     {os.environ.get('LLM_REASONING_EFFORT') or '(default)'}\n")

    if not key:
        print("! no API key in the environment. For Ollama any placeholder works:")
        print("    export OPENAI_API_KEY=ollama")
        sys.exit(2)

    report = asyncio.run(run(args.trials, model, provider))
    trials = report["trials"]
    ok = [t for t in trials if t["ok"]]
    consistent = [t for t in ok if t["consistent_total"]]
    n = max(len(trials), 1)

    print(f"\n  schema valid      {len(ok)}/{len(trials)} ({len(ok) / n:.0%})")
    print(f"  totals consistent {len(consistent)}/{len(trials)} "
          f"({len(consistent) / n:.0%})")
    if ok:
        mean_s = sum(t["seconds"] for t in ok) / len(ok)
        print(f"  mean latency      {mean_s:.2f}s")

    # The two failure modes are NOT equally serious, and an earlier version of
    # this script conflated them.
    #
    # Schema failure is fatal: no OrderProposal means no contract row and no
    # governed round, which in the summary tables is indistinguishable from
    # "the filter had nothing to correct".
    #
    # An inconsistent total is NOT fatal. Magentic classifies it as an
    # `invalid_total_price` analytics finding (run_analytics.py:515) rather
    # than rejecting the message, `total_price` is what the customer actually
    # pays (run_audit.py:453), and it is the same field the budget row is
    # computed from. So the enforcement measurement stays coherent -- the
    # filter clamps the number that becomes the payment. It is an agent
    # pathology to report, not a blocker.
    schema_rate = len(ok) / n
    verdict = (
        "USABLE" if schema_rate == 1.0
        else "MARGINAL" if schema_rate >= 0.9
        else "NOT USABLE"
    )
    print(f"\n  verdict: {verdict}")
    if verdict != "USABLE":
        print("  A model that cannot reliably emit OrderProposal produces zero")
        print("  governed rounds, which reads as 'nothing to enforce' rather")
        print("  than 'the model could not be driven'. Do not run arms until")
        print("  schema validity is 100%, or record the rate as a result.")
    if len(consistent) < len(ok):
        rate = 1.0 - len(consistent) / max(len(ok), 1)
        print(f"\n  NOTE: {rate:.0%} of valid proposals have total_price out of")
        print("  step with their line items. Not a blocker -- Magentic scores")
        print("  this as `invalid_total_price` and total_price is both what is")
        print("  paid and what the budget row reads -- but it is an agent")
        print("  pathology this model has and Gemini does not, and it belongs")
        print("  in the write-up rather than in a footnote.")

    report["config"] = {
        "provider": provider,
        "model": model,
        "base_url": base_url,
    }
    report["verdict"] = verdict
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
