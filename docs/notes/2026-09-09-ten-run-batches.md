# Forty runs that were never reported, and what they say

**Date:** 2026-09-09 (runs made 2026-09-07). **Cost:** £0.00 to analyse — the
runs already existed; this is replay only.

## What they are

Four run families of ten seeds each sit in `results/` and are referenced by no
note and no section of the dissertation:

| family | arm | scenario | mode |
|---|---|---|---|
| `arm_a_bg2_1..10` | A | `bargain_3_9` | `off` |
| `arm_b_bg2_1..10` | B | `bargain_3_9` | `filter` |
| `arm_a_un2_1..10` | A | `undisclosed_3_9` | `off` |
| `arm_b_un2_1..10` | B | `undisclosed_3_9` | `filter` |

All at γ = 0.4, OSQP, on the current code path (same day as `arm_b_v2`, after
the seller-reconciliation fix). They were found while auditing run-family sizes
against the dissertation's "five runs throughout", and are recorded here so
that the count in the repository matches the count in the text.

## What they say

Replayed against Postgres:

| | deals | breaching | overspend | governed rounds breaching |
|---|---|---|---|---|
| `bargain_3_9` arm A | 26 | 4 | £0.82 | 69/100 |
| `bargain_3_9` arm B | 31 | 1 | **£0.00** | **0/69** |
| `undisclosed_3_9` arm A | 30 | **30** | £54.55 | **48/48** |
| `undisclosed_3_9` arm B | 29 | 1 | £6.15 | **0/44** |

Every categorical claim reproduces:

- **Zero governed breaches under enforcement**, on 69 + 44 = **113 further
  governed rounds**. The safety result is the one that gains from these runs.
- **Ungoverned undisclosed trading is still categorical**: 30 of 30 settled
  deals breach, 48 of 48 governed rounds breach.
- Arm B's one breaching deal on `undisclosed_3_9` is the unsatisfiable pair at
  £6.15 — the same single pair limitation B4(a) records, unchanged across ten
  further runs.
- Arm A on `bargain_3_9` settles 4 breaching deals in 26 at £0.82, which is the
  same instability the batch-consistency note reports: the disclosed-scenario
  overspend is not a reproducible constant.

Nothing here changes an outcome comparison. Closure and surplus still rest on
five runs, because these families cover arms A and B only.

## Why they were not reported before

No reason that survives inspection. They were run, they succeeded, and they
were not written up. Recording them now removes the only place where the
repository holds evidence the document does not, and the evidence happens to
point the same way.

## Reproduce

```bash
uv run python - <<'PY'
import asyncio
from src.marketplace_integration.replay import replay_schema, _dsn_from_env
from src.marketplace_integration.theta import ContractRegistry
from src.contract import ContractSpec

async def go():
    dsn = _dsn_from_env()
    for lab, d, pre in (("bargain A", "data/bargain_3_9", "arm_a_bg2_"),
                        ("bargain B", "data/bargain_3_9", "arm_b_bg2_"),
                        ("undis A", "data/undisclosed_3_9", "arm_a_un2_"),
                        ("undis B", "data/undisclosed_3_9", "arm_b_un2_")):
        reg = ContractRegistry.from_data_dir(d, spec=ContractSpec())
        deals = br = gr = grb = 0; over = 0.0
        for i in range(1, 11):
            r = await replay_schema(f"{pre}{i}", reg, dsn)
            deals += len(r.deals); br += sum(1 for x in r.deals if x.breached)
            over += sum(x.overspend for x in r.deals)
            for rec in r.records:
                if reg.is_satisfiable(rec.business_id, rec.customer_id):
                    gr += 1; grb += bool(rec.breach)
        print(lab, deals, br, round(over, 2), f"{grb}/{gr}")

asyncio.run(go())
PY
```

Expected: `bargain A 26 4 0.82 69/100`, `bargain B 31 1 0.0 0/69`,
`undis A 30 30 54.55 48/48`, `undis B 29 1 6.15 0/44`.
