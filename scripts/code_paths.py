"""Which code path actually produced each governed round.

`solver_status` in the certificate reads `not_run` on the great majority of
rounds, and an earlier reading of that took it to mean the barrier programme
never ran. It does not. `project_into_safe_set` runs the same DCBF quadratic
program internally at gamma = 1, iterating to handle the bilinear budget row,
and only falls back to the closed form of limitation B7 when that fails. The
opening projection *is* a solved programme; it is simply recorded with
``result=None`` because it does not return through the filter's own result
object.

So the four paths have to be separated by replaying them. theta is recoverable
exactly from a stored record: h = (B - pq, p - c, q - q_min, q_max - q, ...) is
invertible given x, so the governing contract of every round can be
reconstructed and the projection re-run offline, deterministically and without
touching an API.

    uv run python scripts/code_paths.py
"""

from __future__ import annotations

import collections
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import DCBFFilter, _feasible_fallback  # noqa: E402
from src.contract import Contract  # noqa: E402


def theta_from_record(rec: dict, which: str = "h_prev") -> Contract | None:
    """Invert h to recover the governing theta of a recorded round."""
    h = rec.get(which) or {}
    x = rec["x_prev"] if which == "h_prev" else rec["x_applied"]
    if not h or x is None:
        return None
    p, q, d = (float(v) for v in x)
    try:
        budget = h["budget"] + p * q
        cost_floor = p - h["cost_floor"]
        q_min = q - h["q_min"]
        q_max = h["q_max"] + q
    except KeyError:
        return None
    if "d_min" in h and "d_max" in h:
        return Contract(budget=budget, cost_floor=cost_floor, q_min=q_min,
                        q_max=q_max, d_min=d - h["d_min"], d_max=h["d_max"] + d,
                        deadline_active=True)
    return Contract(budget=budget, cost_floor=cost_floor, q_min=q_min,
                    q_max=q_max, deadline_active=False)


def projection_path(x: np.ndarray, contract: Contract,
                    iterations: int = 6, tol: float = 1e-7) -> str:
    """Re-run the opening projection and report which branch returned."""
    current = np.asarray(x, dtype=float).copy()
    filt = DCBFFilter(gamma=1.0, rho=1e6, backtrack=False)
    for _ in range(iterations):
        if contract.is_safe(current, tol=tol):
            return "qp"
        result = filt.step([current], [np.zeros(3)], [contract])
        if not result.solved:
            break
        step = result.u[:3]
        if np.linalg.norm(step) < tol:
            break
        current = current + step
    if contract.is_safe(current, tol=tol):
        return "qp"
    _feasible_fallback(np.asarray(x, dtype=float), contract, tol)
    return "b7"


def classify(rec: dict) -> str:
    """One of five paths, decided from the record alone."""
    intervened = abs(float(rec["intervention"])) > 1e-9
    theta = theta_from_record(rec)
    if rec["solver_status"] == "solved":
        return "barrier QP"
    if intervened:
        if theta is None:
            return "opening projection (QP)"
        return ("opening projection (QP)" if
                projection_path(np.asarray(rec["x_proposed"], dtype=float), theta) == "qp"
                else "B7 closed-form clip")
    # Not intervened. Either the terms already complied, or nothing governed.
    if not rec["breach"]:
        return "already inside C(theta)"
    if theta is not None and not theta.is_satisfiable():
        return "unsatisfiable pass-through"
    return "pre-phase pass-through"


# Only run sets produced *after* the intervention-logging fix (integration
# defect 4) can be classified. The `arm_b_bargain_v*` set behind Table 5.8
# records 3 interventions where the same configuration on current code records
# 24, because opening projections were logged with zero intervention. Its
# certificates cannot support this table; the single-batch re-run can.
GROUPS = [
    ("arm B, bargain_3_9", "results/arm_b_batch2_v*"),
    ("arm B, bargain_adv_3_9", "results/arm_b_adv_*"),
    ("arm B, undisclosed_3_9", "results/arm_b_undis_v*"),
    ("arm C-meet, bargain_3_9", "results/arm_cm_batch2_v*"),
    ("arm C-meet-guarded", "results/arm_c_meet_guarded_*"),
]

ORDER = ["opening projection (QP)", "barrier QP", "B7 closed-form clip",
         "already inside C(theta)", "pre-phase pass-through",
         "unsatisfiable pass-through"]


def main() -> None:
    grand = collections.Counter()
    print(f"{'':28s}" + "".join(f"{k.split('(')[0][:11]:>13s}" for k in ORDER) + f"{'total':>8s}")
    for label, pattern in GROUPS:
        t = collections.Counter()
        for path in sorted(glob.glob(pattern + "/certificates.jsonl")):
            for line in open(path):
                t[classify(json.loads(line))] += 1
        grand.update(t)
        print(f"  {label:26s}" + "".join(f"{t[k]:13d}" for k in ORDER)
              + f"{sum(t.values()):8d}")
    print(f"  {'TOTAL':26s}" + "".join(f"{grand[k]:13d}" for k in ORDER)
          + f"{sum(grand.values()):8d}")
    qp = grand["opening projection (QP)"] + grand["barrier QP"]
    print(f"\n  rounds where a barrier programme was solved: "
          f"{qp} of {sum(grand.values())}")
    print(f"  of which recorded solver_status='solved': {grand['barrier QP']}")
    print(f"  B7 closed-form clips: {grand['B7 closed-form clip']}")


if __name__ == "__main__":
    main()
