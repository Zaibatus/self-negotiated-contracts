# The introduction's worked exchange delivered the wrong number

**Date:** 2026-09-09
**Cost:** £0.00 (replay and offline projection only)

## What was wrong

Section 1.2 sets up a worked exchange — a customer wanting two items on a
£11.58 budget, a seller opening at £6.755 a unit or £13.51 for the pair — and
Section 1.4, Figure 1.1 and Section 7.6 all said the filter delivered it to the
buyer as **£11.58 → £11.57**, "a penny below the boundary", with the gloss
"prices must land on whole pence, and the layer rounds *into* the permitted
region rather than onto its edge".

The filter delivers **£11.58**, exactly the budget. Both the number and the
gloss were wrong.

The £11.57 appears to have been copied from
`2026-08-05-arm-a-bargain-scenario.md`, where it is a real *settled* price on
`business_0002|customer_0001` in an ungoverned run. That is a different
quantity from the filter's output on a different pair, and that note is correct
as it stands.

## What is actually true

`business_0001|customer_0001` on `bargain_3_9` has
θ = (B=11.58, c=5.2689, q_min=2, q_max=4, d_min=0, d_max=7).
The live record for that pair in `arm_b_batch2_v1` reads

    x_proposed  [6.755, 2.0, 0.0]   total 13.51
    x_applied   [5.79,  2.0, 0.0]   total 11.58

and the offline projection agrees, returning h = (0.0, 0.5211, 0.0, 2, 0, 7) —
the budget row and the q_min row both **active**, so the corrected terms sit on
the boundary of C(θ).

That is not a rounding artefact, it is what "nearest" means. The closest
compliant point to a proposal that breaches always lies on the boundary of the
safe set, and the boundary belongs to the set because h ≥ 0 admits equality.
`_repair_quantisation` only nudges a whole cent when h < −tol, so it does not
fire here and there is no inward rounding to describe.

## Fixed

- `chapters/01-introduction.tex` — prose and the Figure 1.1 caption; the
  "penny below the boundary / rounds into the region" sentence replaced with
  the correct account of why nearest lands on the boundary.
- `chapters/07-lsep.tex` — the offer-and-acceptance discussion.
- `figures/render_intro.py` — the arrow label and the docstring; figure
  regenerated and copied into the thesis.

## Reproduce

```bash
uv run python - <<'PY'
import numpy as np
from src.certificates.dcbf import project_into_safe_set
from src.marketplace_integration.theta import ContractRegistry
from src.contract import ContractSpec

reg = ContractRegistry.from_data_dir("data/bargain_3_9", spec=ContractSpec())
c = reg.get("business_0001", "customer_0001")
x = np.array([6.755, 2.0, 0.0])
y = project_into_safe_set(x, c)
print(y, "total %.2f" % (y[0] * y[1]), "h =", np.round(c.h(y), 4))
PY
```

Expected: `[5.79 2. 0.]  total 11.58  h = [0. 0.5211 -0. 2. 0. 7.]`.

And against the live record:

```bash
uv run python - <<'PY'
import json
for ln in open("results/arm_b_batch2_v1/certificates.jsonl"):
    r = json.loads(ln)
    xp = r.get("x_proposed")
    if xp and abs(xp[0] * xp[1] - 13.51) < 0.02:
        print(r["business_id"], r["customer_id"], xp, "->", r["x_applied"])
        break
PY
```

Expected: `business_0001 customer_0001 [6.755, 2.0, 0.0] -> [5.79, 2.0, 0.0]`.
