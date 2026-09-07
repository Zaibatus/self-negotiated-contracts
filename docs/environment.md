# The pinned environment

**Recorded 2026-09-07.** Limitation D3 said the environment was not pinned and
that the claim of bit-level reproducibility was therefore false as stated. This
file, `uv.lock` and `requirements-lock.txt` are the repair.

## What is pinned

`uv.lock` resolves 135 packages and was verified against `pyproject.toml`
with `uv lock --check` on 2026-09-07: it is current, and the versions it names
are the versions installed. `requirements-lock.txt` is the same resolution
exported with SHA-256 hashes for every artefact, so an install can be verified
rather than merely repeated:

```
uv sync --extra dev          # from uv.lock
pip install --require-hashes -r requirements-lock.txt   # the hash-checked path
```

## The versions every number in the dissertation was produced under

```
Python 3.13.9
numpy 2.4.6
scipy 1.18.0
osqp 1.1.3
asyncpg 0.31.0
pydantic 2.13.4
matplotlib 3.11.1
```

Platform: macOS (darwin), arm64.

## The solver-status probe

`experiments/certificates/audit.py` runs 60 quadratic programs along a live
trajectory with SciPy's SLSQP and counts the ones that return a non-success
status. It is the probe that motivated choosing an operator-splitting solver
instead, and it is the measurement limitation D3 was about.

| environment | failures | worst linearised residual |
|---|---|---|
| original, at the time of the 2026-08 runs | 4 / 60 | not recorded |
| **pinned, 2026-09-07** | **7 / 60** | \(-2.43 \times 10^{-6}\) |

Reproduce with:

```
uv run python experiments/certificates/audit.py
```

**The 4/60 cannot be recovered.** It was measured under an earlier SciPy, and
that environment was not captured before it was replaced. What is fixed from
here is forward reproducibility: the probe returns 7/60 under the versions
above, and will keep doing so. The historical figure is reported as historical,
not reconciled.

The direction of the change is worth keeping, because it is the argument for
the solver actually used. A probe that moves from 4 to 7 failures out of 60
because a numerical library changed underneath it is exactly the fragility that
made an unreported non-convergence unacceptable in a safety component.
