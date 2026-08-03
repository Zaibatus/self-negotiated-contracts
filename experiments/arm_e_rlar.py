"""Arm E — RL-AR: adaptive regularisation between the filter and the LLM.

SCAFFOLD, deliberately. Deferred until arms A-D produce live numbers.

The payoff-based framing changes what this arm *is*, and the change is worth
recording before anyone implements the older plan.

Under RL-AR (Tian, Hamedmoghadam, Shorten, Ferraro, NeurIPS 2024,
arXiv:2404.15199) a focus module learns a state-dependent weight beta(s) that
blends a safe base policy with a learned one:

    a_beta(s) = beta(s) a_reg(s) + (1 - beta(s)) a_rl(s)

The earlier arm-E note mapped pi_reg to "a contract-compliant policy", left
undefined for an LLM agent, and that was the arm's main open question.

It is now defined, and it already exists: **pi_reg is the DCBF filter's
output**. The filter takes any proposal and returns the nearest one satisfying
the barrier, which is exactly a safe base policy — model-free, always
available, and with a guarantee attached. The blend becomes

    x_applied = beta(s) x_filtered + (1 - beta(s)) x_proposed

with beta near 1 a cautious regulator and beta near 0 an agent let through
untouched. That is the same dial as gamma, made state-dependent: gamma is a
fixed conservatism, beta(s) a learned one. And section 8 already shows gamma is
not only a safety parameter — it displaces where the negotiation settles and
moves the shadow prices — so a *learned* gamma is a learned economic policy,
which deserves saying out loud before it is trained.

So arm E stops being a mechanism bolted beside the safety layer and becomes a
continuation of it. Worth raising with Haozhe, whose paper it is.

Three obstacles remain, unchanged by the reframing:
  1. Reward is sparse — observable at transaction end, not per round — which is
     what the focus module's Q-value update needs.
  2. The state s is a conversation, not a vector. A summary (round index,
     distance to each barrier, intervention history) is the obvious encoding,
     and is exactly what RoundRecord already logs.
  3. The convergence theory assumes pi_rl converges to pi*. Under LLM
     fine-tuning it will not, so the practical claim is the inductive bias —
     start safe, relax as evidence accumulates — not the formal guarantee.

Prerequisite before any of this: arms A-D on live agents. A learned relaxation
of a safety layer whose cost has not been measured is a solution without a
problem.
"""

from __future__ import annotations


def main() -> None:
    print(__doc__)
    print("Not run: deferred until arms A-D have live numbers.")
    raise SystemExit(2)


if __name__ == "__main__":
    main()
