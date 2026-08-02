# negotiation-certificates

Formal safety and convergence guarantees for LLM-agent negotiation: contracts as controllers.
MSc thesis prototype (Imperial College London). Supervisor: Dr Pietro Ferraro; co-supervisor: Haozhe Tian.

**Status:** formulation complete and verified (`docs/formulation.md` v2); simulation may proceed.

**Idea in one line:** a negotiated contract is a controller for the negotiation itself — a discrete-time control barrier function (DCBF) layer guarantees no contract breach at any round, and an anchor-free "net-gain" Lyapunov energy (Zusai, arXiv:1805.04898) certifies convergence to the (generalised) Nash agreement point without knowing where it is.

## Repository layout

```
docs/         formulation.md   — the formal model v2, DEFINITIVE (dissertation theory chapter)
              formulation_v1.md — archived first version (heuristic-based, superseded)
              pietro_meeting_brief.md, thesis_handover_recap.md — supervision docs
experiments/  numbered below; verbatim files kept bit-reproducible (fixed seeds)
figures/      figure_anchorfree_energy.png — the three-curve headline figure
results/      (scratch, not tracked)
```

## Experiments → findings

| file | finding |
|---|---|
| `dcbf_negotiation.py` | **F1** DCBF-QP filter: breaches 9.9% → 0%, convergence & surplus preserved. **F2** invariance ≠ convergence counterexample. |
| `lyapunov_layer.py` | **F3** Lyapunov contraction exact vs theory (0.3164 = (1−r)⁴). **F4** CBF–Lyapunov tension ≈ 9.6% of round-pairs (seller-round sampling — see audit). **F5** naive composed certificate fails under coupling. |
| `gne_shadow_price.py` | **F5** GNE re-anchoring; **F6** shadow prices from KKT multipliers, scarcity + conservatism-premium decomposition (indicative until OSQP). |
| `netgain_energy.py` | Anchor-free net-gain energy G: ties GNE-anchored performance with zero equilibrium knowledge; noise-free G → 0 exactly. |
| `farstart_experiment.py` | Far-start repair of the binding-case comparison + the headline figure. Naive anchor plateaus at its squared anchor error (510.3 ≈ 509.9 predicted); G contracts at 0.37 and → 0 unaided. |
| `payoff_model.py` | Utilities, Nash bargaining closed form (verified vs numerical Nash-product max to 9e-6), acceptance model, energies. |
| `payoff_dynamics.py` | **E1** concession-field zero = Nash bargaining solution exactly (Prop. 1). E2 escalating friction terminates. E4 global stability check. |
| `payoff_validation2.py` | **E8** T_max vs surplus-loss trade-off curve. **E9** certified stability radius (~1 scaled unit; lambda_max = -6.86 at NBS). E6/E7 superseded by round 3. |
| `payoff_validation3.py` | **E11** Phi merit function (decreases 96%, 99.98% of max surplus). **E12** Prop. 2: no constant friction works. **E13** projected certificate: Phi_proj = 0.00000 at the constrained field-zero. |
| `audit.py` | Reliability probes: transient-only contraction estimator, SLSQP status-failure rate (6.7%), decrease-in-expectation check (drift positive mid-range → drift-outside-a-ball formulation). |

Full corrected claims and scope: `docs/formulation.md` §7 (assumptions & limitations).

## Reproduce

```bash
pip install -r requirements.txt
cd experiments
python dcbf_negotiation.py      # F1/F2
python lyapunov_layer.py        # F3/F4/F5
python gne_shadow_price.py      # F5/F6 (slow: many QPs)
python netgain_energy.py        # G validation
python farstart_experiment.py   # headline figure -> ../figures/
python audit.py                 # reliability probes
```

Seeds are fixed at module level; runs are deterministic per file.

## Roadmap (week 2)

1. OSQP swap with solver-status checks and safe fallback (exact duals for the price results).
2. Magentic Marketplace integration: term-extraction layer replaces scripted `proposal`.
3. Report operational energies (realised displacement + model-based lookahead) on live LLM negotiations; T_max certificate vs realised lengths.
4. Extraction-noise robustness experiment; Fabraix safety-filter-exploitation spec.
5. Refactor shared code out of `experiments/` into `src/` once bit-reproducibility of the quoted tables no longer needs preserving.
