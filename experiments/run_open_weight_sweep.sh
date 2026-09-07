#!/usr/bin/env bash
# Replicate the model axis on a hosted open-weight model.
#
# Mirrors the 2026-08-07 model sweep exactly: arms A and B, 5 seeds,
# bargain_3_9, gamma 0.4, T_max 6. The ONLY thing varying is the model.
#
# Needs GROQ_API_KEY in the environment. Do not commit it.
#
#   export GROQ_API_KEY=...        # or put it in ~/.groq_key (chmod 600)
#   bash experiments/run_open_weight_sweep.sh
set -euo pipefail

MODEL="${LLM_MODEL_OVERRIDE:-llama-3.3-70b-versatile}"
TAG="$(echo "$MODEL" | tr '.-' '__')"
HERE="$(cd "$(dirname "$0")/.." && pwd)"
MARKET="$HERE/../multi-agent-marketplace"

# Postgres settings come from the marketplace .env; the LLM settings are then
# overridden so nothing from that file selects the model.
cd "$MARKET" && source .env
cd "$HERE"

if [ -z "${GROQ_API_KEY:-}" ] && [ -f "$HOME/.groq_key" ]; then
  GROQ_API_KEY="$(tr -d '[:space:]' < "$HOME/.groq_key")"
fi
if [ -z "${GROQ_API_KEY:-}" ]; then
  echo "GROQ_API_KEY is not set and ~/.groq_key does not exist." >&2
  exit 2
fi

export LLM_PROVIDER=openai
export OPENAI_BASE_URL=https://api.groq.com/openai/v1
export OPENAI_API_KEY="$GROQ_API_KEY"
export LLM_MODEL="$MODEL"
unset LLM_REASONING_EFFORT   # Llama has no reasoning-effort parameter

echo "== preflight: can $MODEL emit an OrderProposal? =="
uv run python experiments/preflight_model.py --trials 10
echo
read -r -p "Preflight done. Continue to the arms? [y/N] " reply
[ "$reply" = "y" ] || { echo "stopped"; exit 0; }

echo "== pilot: one seed of arm B, to check it TRANSACTS and not just chats =="
uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
    --gamma 0.4 --t-max 6 --experiment "arm_b_${TAG}_pilot" --override

echo
echo "== message mix on the pilot: order_proposal and payment must be non-zero =="
docker exec multi-agent-marketplace-postgres-1 psql \
  -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-marketplace}" -tc \
  "select data->'request'->'parameters'->'message'->>'type', count(*)
     from arm_b_${TAG}_pilot.actions
    where data->'request'->>'name'='SendMessage' group by 1;"
echo "  (Gemini reference for one seed: text 58, order_proposal 9, payment 3)"
echo
read -r -p "Mix healthy? Continue to the full 5 seeds x 2 arms? [y/N] " reply
[ "$reply" = "y" ] || { echo "stopped"; exit 0; }

for i in 1 2 3 4 5; do
  uv run python experiments/arm_a_no_contract.py --live --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_a_${TAG}_v$i" --override
  uv run python experiments/arm_b_imposed.py --data data/bargain_3_9 \
      --gamma 0.4 --t-max 6 --experiment "arm_b_${TAG}_v$i" --override
done

echo "== replay from the database, never from the regulator's own log =="
uv run python -m src.marketplace_integration.replay \
    --schemas "arm_b_${TAG}_v1" "arm_b_${TAG}_v2" "arm_b_${TAG}_v3" \
              "arm_b_${TAG}_v4" "arm_b_${TAG}_v5" \
    --data data/bargain_3_9 --out "results/replay_${TAG}"
echo "done: results/replay_${TAG}"
