# RL-AR Focus Module — Notes for Arm E

**Source:** Tian, Hamedmoghadam, Shorten, Ferraro. *Reinforcement Learning with Adaptive Regularization for Safe Control of Critical Systems.* NeurIPS 2024. arXiv:2404.15199  
**Read:** 2026-06-07

---

## 1. What the focus module is

The focus module learns a **state-dependent scalar weight β(s): S → [0, 1]**, parameterised as a small neural network β_ψ(s) with a shifted tanh output so β_ψ(s) ∈ (0, 1).

The combined action at state s is:

```
a_β(s) = β(s) · a_reg(s) + (1 − β(s)) · a_rl(s)
```

where:
- **a_reg(s)** = action from the *safe base policy* π_reg (in the paper, a constrained MPC controller)
- **a_rl(s)** = action sampled from the *learned RL policy* π_rl (SAC)

Lemma 1 shows this is equivalent to solving a regularised optimisation problem at each state, where the regularisation strength λ(s) = β(s) / (1 − β(s)) is adaptive and state-dependent.

---

## 2. How β(s) is trained

β_ψ is updated by gradient ascent on the expected Q-value of the blended action:

```
∇_ψ  (1/|B|) Σ_{(s, a_reg) ∈ B}  min_i Q_φᵢ(s, β_ψ(s)·a_reg + (1−β_ψ(s))·a_rl(s))
```

- Uses the minimum of two clipped Q-networks (standard SAC anti-overestimation trick)
- Sampled from the replay buffer, so **frequently-visited states dominate updates**
- Initialised so β_ψ(s) ≥ 0.999 (pure safe policy at the start of training)

---

## 3. When β(s) is high vs low

| β(s) ≈ 1 | β(s) ≈ 0 |
|-----------|-----------|
| State poorly visited → noisy Q estimates | State well-visited → accurate Q estimates |
| Early training | Late training |
| Rely on safe base policy | Rely on learned RL policy |
| Strong regularisation (λ → ∞) | Weak regularisation (λ → 0) |

Key theoretical result: as π_rl → π* (optimal), β*(s) → 0 (Lemma 2). The combined policy converges to π* with zero total variation distance (Theorem 3).

---

## 4. Experimental results (§4)

- **Zero training failures** across all environments vs 19–99 failures for SAC, 3–74 for safe-RL baselines (Table 1)
- **Competitive final performance** with unconstrained SAC — RL-AR does not sacrifice return for safety
- **Robust to 60% parameter mismatch** between estimated and actual model; β(s) adapts quickly when model is wrong

---

## 5. Mapping to Arm E

The paper's setting: continuous-action safe control with a model-based safe controller as π_reg.  
Arm E setting: LLM negotiation agents; "safety" = contract compliance.

Proposed mapping:

| RL-AR concept | Arm E concept |
|---------------|--------------|
| π_reg (safe base policy) | Contract-compliant policy π_contract — a policy that always proposes/accepts terms within the negotiated contract bounds |
| π_rl (learned policy) | Learned negotiation policy π_θ — fine-tuned via RL on welfare reward |
| β(s) (focus weight) | Contract adherence weight α(s) — how strongly to enforce contract terms at negotiation state s |
| State s | Negotiation state (conversation history, current proposal, round number) |
| Safety constraint | Contract constraint (price ≤ agreed bound, quality ≥ agreed bound, etc.) |
| Replay buffer Q-update | RLHF / RL policy gradient update on negotiation trajectories |

The blended negotiation action would be:

```
a_α(s) = α(s) · a_contract(s) + (1 − α(s)) · a_θ(s)
```

where a_contract is the greedy contract-compliant action (e.g. propose exactly the agreed price) and a_θ is sampled from the learned negotiation policy.

---

## 6. Open questions for supervisor

1. **How to define π_contract for an LLM agent?**  
   In the paper, π_reg is a deterministic MPC controller. For an LLM agent, the "contract-compliant policy" could be a constrained generation: only tokens/actions that satisfy the contract terms (e.g. proposed price ≤ contract bound). Is this a hard constraint (rejection sampling) or a soft prompt?

2. **What is the "state" for the focus module?**  
   In the paper, s is a physical state vector. For negotiation, s is the conversation history (variable-length). The focus module network β_ψ must encode this — a transformer encoder over the history, or just a summary (round number, gap to contract bounds, proposal history)?

3. **Is the Q-value signal well-defined during LLM negotiation training?**  
   SAC has a clear scalar reward per timestep. In negotiation, the reward may only be observable at transaction end (sparse). Does this break the gradient update for β_ψ?

4. **Does the convergence theory (Lemma 2, Theorem 3) hold under LLM approximation error?**  
   The paper assumes π_rl converges to π*. LLM fine-tuning with PPO/DPO is unlikely to achieve this exactly. Is the practical takeaway just the inductive bias (start safe, relax as learning proceeds) rather than the formal guarantee?

5. **Fallback: if PPO is infeasible, use DPO.**  
   The TRL library supports DPO, which optimises a preference objective without a separate value function. α(s) could still be used as a curriculum-style mixing coefficient during DPO training rather than an inference-time blend. Is this a valid approximation?

---

## 7. Literature to check before implementing

- Cheng et al. 2019b (cited as prior work the focus module improves on — state-*independent* β)
- Constitutional AI (Bai et al. 2022) — closest to arm E fallback if PPO proves infeasible
- DPO (Rafailov et al. NeurIPS 2023) — TRL implementation for the DPO fallback path
