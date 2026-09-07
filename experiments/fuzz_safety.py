"""Monte Carlo safety fuzzing of the enforcement path.

Every safety number in the thesis is `0 breaches out of N observed rounds` on
one scenario family, three customers, five seeds. That is evidence about the
situations the agents happened to produce. It is not evidence about the
*mechanism*, because the agents never proposed a large single-round jump, never
drove a near-degenerate safe set, and never asked for a fractional quantity.

This fuzzes the shipped code — `DCBFFilter`, `project_into_safe_set` and
`rewrite_proposal`, imported, not reimplemented — over randomly sampled
contracts, states and proposed moves, including the regimes the live runs never
reached. A failure here is a finding about the filter, not about an LLM.

What it can and cannot show. This is a property test, not a proof: it samples
the input space, so it can only ever report "no counterexample in N draws".
It is deliberately adversarial about *where* it samples — the bilinear budget
row under large jumps, and safe sets that are a single point — because those
are the two places `formulation.md` section 7.4 and the `_repair_quantisation`
docstring already flag as thin.

Properties, each checked against the TRUE (non-linearised) h:

  P1  projection      x0 outside C, theta satisfiable  ->  result inside C
  P2  invariance      x inside C, any proposed u       ->  x + u_applied inside C
  P3  dcbf            the true h honours h(x+u) >= (1-gamma) h(x) - slack
  P4  wire            the rewritten *message* satisfies the contract as sent
  P5  observability   when a step leaves C, SOMETHING in FilterResult says so

P2 is the one the thesis claims. P5 is deliberately stricter than anything the
filter promises: `certificate_gap` is set only when the *solver* fails
(dcbf.py:400), so it was never meant to flag a step that satisfied the QP and
still left C(theta). P5 failing is therefore not a broken promise — it is the
absence of a signal the safety claim needs, which is the same shape as bug 7,
where OSQP reported success while the routine handed back the unsafe input.

Read P2 and P3 together. They answer different questions and they disagree:
P3 asks whether the barrier inequality held *including the slack the QP was
allowed to use*, and P2 asks whether the state is still in the safe set. A
filter that degrades gracefully onto slack passes P3 and fails P2, which is
precisely what graceful degradation means and precisely what the headline
"zero breaches" does not distinguish.

Reproduce:

    uv run python experiments/fuzz_safety.py --draws 20000 --seed 20260828
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.dcbf import DCBFFilter, project_into_safe_set  # noqa: E402
from src.contract import ROW_LABELS, Contract  # noqa: E402

TOL = 1e-6
# Below this a violation is floating-point noise, not something a counterparty
# could ever be charged for. One cent on a single unit is 0.01, so 1e-3 is an
# order of magnitude inside the smallest breach that can exist on the wire.
MATERIAL_TOL = 1e-3

# Wire-path fuzzing needs the marketplace message schema. It is optional so the
# core DCBF properties still run in an environment without magentic installed.
try:
    from magentic_marketplace.marketplace.actions.messaging import (  # noqa: E402
        OrderItem,
        OrderProposal,
    )

    from src.marketplace_integration.terms import (  # noqa: E402
        from_order_proposal,
        rewrite_proposal,
    )

    WIRE = True
except Exception as exc:  # pragma: no cover - environment dependent
    WIRE = False
    WIRE_ERROR = repr(exc)


@dataclass
class Failure:
    """One counterexample, with everything needed to replay it."""

    prop: str
    regime: str
    draw: int
    detail: dict[str, Any]


# ---------------------------------------------------------------- sampling --


def sample_contract(rng: np.random.Generator, regime: str) -> Contract:
    """Draw a theta. `tight` deliberately crowds the satisfiability boundary."""
    cost_floor = float(rng.uniform(0.5, 40.0))
    q_min = float(rng.integers(1, 200))
    q_max = float(int(q_min * float(rng.uniform(1.0, 3.0))))

    # c * q_min <= B is the satisfiability condition. `tight` samples the ratio
    # just below 1 so the safe set is a sliver, and sometimes exactly 1 so it is
    # a single point -- a legitimate contract the meet actually produces.
    floor = cost_floor * q_min
    if regime == "tight":
        ratio = float(rng.choice([1.0, 1.0 + 1e-9, *rng.uniform(1.0, 1.02, 3)]))
    elif regime == "degenerate":
        ratio = 1.0
    else:
        ratio = float(rng.uniform(1.05, 4.0))
    budget = floor * ratio

    deadline_active = bool(rng.random() < 0.7)
    d_min = float(rng.uniform(0.0, 3.0))
    d_max = d_min + float(rng.uniform(0.0, 10.0))
    return Contract(
        budget=budget,
        cost_floor=cost_floor,
        q_min=q_min,
        q_max=q_max,
        d_min=d_min,
        d_max=d_max,
        deadline_active=deadline_active,
    )


def sample_inside(rng: np.random.Generator, c: Contract) -> np.ndarray | None:
    """Uniform-ish point in C(theta), or None if the sliver eludes rejection."""
    for _ in range(200):
        q = float(rng.integers(int(c.q_min), int(c.q_max) + 1))
        hi = c.budget / q
        if hi < c.cost_floor:
            continue
        p = float(rng.uniform(c.cost_floor, hi))
        d = float(rng.uniform(c.d_min, c.d_max)) if c.deadline_active else 0.0
        x = np.array([p, q, d])
        if c.is_safe(x, tol=TOL):
            return x
    # Fall back to the analytic corner: the only point when C is a single point.
    x = np.array(
        [c.budget / c.q_min, c.q_min, c.d_min if c.deadline_active else 0.0]
    )
    return x if c.is_safe(x, tol=TOL) else None


def sample_outside(rng: np.random.Generator, c: Contract) -> np.ndarray:
    """A breaching draft, of the kind an ungoverned agent actually sends."""
    q = float(rng.uniform(c.q_min * 0.5, c.q_max * 1.5))
    p = (c.budget / max(q, 1e-9)) * float(rng.uniform(1.01, 3.0))
    d = float(rng.uniform(c.d_min - 3.0, c.d_max + 6.0))
    return np.array([p, max(q, 1e-6), d])


def sample_u(rng: np.random.Generator, x: np.ndarray, regime: str) -> np.ndarray:
    """Proposed adjustment. `jump` is the stated attack surface on h1."""
    if regime == "jump":
        scale = np.array([x[0] * 2.0, x[1] * 2.0, 10.0])
    else:
        scale = np.array([x[0] * 0.15, x[1] * 0.15, 2.0])
    return rng.normal(0.0, 1.0, 3) * scale


# -------------------------------------------------------------- properties --


def active_true_h(c: Contract, x: np.ndarray) -> np.ndarray:
    return c.h(x)[c.active_mask()]


def make_proposal(x: np.ndarray, n_items: int, rng: np.random.Generator):
    """A structurally valid OrderProposal carrying terms x."""
    qty = max(n_items, int(round(x[1])))
    weights = rng.integers(1, 5, n_items)
    quantities = np.maximum(1, (weights / weights.sum() * qty).astype(int))
    unit = float(x[0])
    items = [
        OrderItem(
            id=f"menu_{i}",
            item_name=f"item_{i}",
            quantity=int(q),
            unit_price=round(unit, 2),
        )
        for i, q in enumerate(quantities)
    ]
    total = round(sum(i.unit_price * i.quantity for i in items), 2)
    return OrderProposal(
        id=f"fuzz_{rng.integers(1 << 30)}",
        items=items,
        total_price=total,
        estimated_delivery=f"{max(0, int(round(x[2])))} days",
    )


def run(draws: int, seed: int, gammas: list[float]) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    regimes = ["wide", "tight", "degenerate", "jump"]
    tested: dict[str, int] = defaultdict(int)
    failed: dict[str, int] = defaultdict(int)
    material: dict[str, int] = defaultdict(int)
    worst: dict[str, float] = defaultdict(float)
    rows: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_regime: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    failures: list[Failure] = []
    solver_stats: dict[str, int] = defaultdict(int)
    slack_on_exit: list[float] = []
    slack_on_stay: list[float] = []

    def record(
        prop: str,
        regime: str,
        ok: bool,
        draw: int,
        detail: dict,
        margin: float | None = None,
        broken: list[str] | None = None,
    ) -> None:
        """Log one check. ``margin`` is min(h) after the step: how far outside.

        A violation of 1e-9 is representation error and a violation of a penny
        is a breach that reaches the counterparty. Counting them together would
        make this fuzzer cry wolf, so MATERIAL_TOL separates them and both are
        reported.
        """
        tested[prop] += 1
        by_regime[regime][prop + "_n"] += 1
        if margin is not None and margin < worst[prop]:
            worst[prop] = float(margin)
        if not ok:
            failed[prop] += 1
            by_regime[regime][prop + "_fail"] += 1
            if margin is not None and margin < -MATERIAL_TOL:
                material[prop] += 1
                by_regime[regime][prop + "_material"] += 1
                for label in broken or []:
                    rows[prop][label] += 1
            if len(failures) < 40:
                detail = dict(detail, margin=margin)
                failures.append(Failure(prop, regime, draw, detail))

    for draw in range(draws):
        regime = regimes[draw % len(regimes)]
        gamma = float(rng.choice(gammas))
        contract = sample_contract(rng, regime)
        if not contract.is_satisfiable():
            continue
        filt = DCBFFilter(gamma=gamma)

        # ---- P1: projection of a breaching opening lands inside C ----------
        x_out = sample_outside(rng, contract)
        x_proj = project_into_safe_set(x_out, contract)
        record(
            "P1_projection",
            regime,
            contract.is_safe(x_proj, tol=TOL),
            draw,
            {
                "theta": contract.theta.tolist(),
                "x_outside": x_out.tolist(),
                "x_projected": x_proj.tolist(),
                "h": active_true_h(contract, x_proj).tolist(),
                "gamma": gamma,
            },
            margin=float(np.min(active_true_h(contract, x_proj))),
            broken=contract.violations(x_proj, tol=MATERIAL_TOL),
        )

        # ---- P2/P3/P5: a barrier step from inside C ------------------------
        x_in = sample_inside(rng, contract)
        if x_in is None:
            continue
        u_prop = sample_u(rng, x_in, regime)
        result = filt.step([x_in], [u_prop], [contract])
        solver_stats[result.status] += 1
        if result.fallback:
            solver_stats["fallback:" + result.fallback] += 1
        x_next = x_in + result.u[:3]

        h_now = active_true_h(contract, x_in)
        h_next = active_true_h(contract, x_next)
        invariant = bool(np.all(h_next >= -TOL))
        record(
            "P2_invariance",
            regime,
            invariant,
            draw,
            {
                "theta": contract.theta.tolist(),
                "gamma": gamma,
                "x": x_in.tolist(),
                "u_proposed": u_prop.tolist(),
                "u_applied": result.u[:3].tolist(),
                "h_next": h_next.tolist(),
                "status": result.status,
                "fallback": result.fallback,
                "certificate_gap": bool(result.certificate_gap),
            },
            margin=float(np.min(h_next)),
            broken=contract.violations(x_next, tol=MATERIAL_TOL),
        )

        slack = result.slack if result.slack.size == h_now.size else np.zeros_like(h_now)
        (slack_on_exit if not invariant else slack_on_stay).append(
            float(np.max(np.abs(slack))) if slack.size else 0.0
        )
        dcbf_ok = bool(np.all(h_next >= (1.0 - gamma) * h_now - slack - 1e-6))
        record(
            "P3_dcbf",
            regime,
            dcbf_ok,
            draw,
            {
                "theta": contract.theta.tolist(),
                "gamma": gamma,
                "x": x_in.tolist(),
                "u_applied": result.u[:3].tolist(),
                "h_now": h_now.tolist(),
                "h_next": h_next.tolist(),
                "slack": slack.tolist(),
                "backtracks": result.backtracks,
            },
            margin=float(np.min(h_next - ((1.0 - gamma) * h_now - slack))),
            broken=[
                ROW_LABELS[i]
                for i, on in enumerate(contract.active_mask())
                if on
            ][: 0],
        )

        # P5: the filter must not stay silent about a step it cannot certify.
        record(
            "P5_observability",
            regime,
            invariant or bool(result.certificate_gap) or bool(result.fallback),
            draw,
            {
                "theta": contract.theta.tolist(),
                "gamma": gamma,
                "certificate_gap": bool(result.certificate_gap),
                "fallback": result.fallback,
                "status": result.status,
                "h_next": h_next.tolist(),
            },
            margin=float(np.min(h_next)),
            broken=contract.violations(x_next, tol=MATERIAL_TOL),
        )

        # ---- P4: the message as actually sent ------------------------------
        if WIRE:
            try:
                proposal = make_proposal(x_in, int(rng.integers(1, 4)), rng)
                rewritten = rewrite_proposal(proposal, x_next, contract)
                x_wire = from_order_proposal(rewritten).vector
                q_rounded = abs(x_wire[1] - x_next[1]) > 1e-9
                if q_rounded:
                    by_regime[regime]["P4_q_rounded"] += 1
                record(
                    "P4_wire" if not q_rounded else "P4_wire_qround",
                    regime,
                    contract.is_safe(x_wire, tol=TOL),
                    draw,
                    {
                        "theta": contract.theta.tolist(),
                        "x_filtered": x_next.tolist(),
                        "x_as_sent": x_wire.tolist(),
                        "h_as_sent": active_true_h(contract, x_wire).tolist(),
                        "violations": contract.violations(x_wire, tol=TOL),
                    },
                    margin=float(np.min(active_true_h(contract, x_wire))),
                    broken=contract.violations(x_wire, tol=MATERIAL_TOL),
                )
            except Exception as exc:
                record(
                    "P4_wire",
                    regime,
                    False,
                    draw,
                    {"exception": repr(exc), "theta": contract.theta.tolist()},
                )

    return {
        "draws": draws,
        "seed": seed,
        "gammas": gammas,
        "tested": dict(tested),
        "failed": dict(failed),
        "material": dict(material),
        "worst_margin": dict(worst),
        "broken_rows": {k: dict(v) for k, v in rows.items()},
        "by_regime": {k: dict(v) for k, v in by_regime.items()},
        "solver_status": dict(solver_stats),
        "slack_when_left_C": {
            "n": len(slack_on_exit),
            "mean_max_slack": float(np.mean(slack_on_exit)) if slack_on_exit else 0.0,
            "frac_with_slack": (
                float(np.mean([v > 1e-9 for v in slack_on_exit]))
                if slack_on_exit
                else 0.0
            ),
        },
        "slack_when_stayed_in_C": {
            "n": len(slack_on_stay),
            "mean_max_slack": float(np.mean(slack_on_stay)) if slack_on_stay else 0.0,
            "frac_with_slack": (
                float(np.mean([v > 1e-9 for v in slack_on_stay]))
                if slack_on_stay
                else 0.0
            ),
        },
        "failures": [f.__dict__ for f in failures],
        "wire_enabled": WIRE,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--draws", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=20260828)
    parser.add_argument(
        "--gammas", type=float, nargs="+", default=[0.2, 0.4, 0.7, 1.0]
    )
    parser.add_argument("--out", default="results/summary/fuzz_safety.json")
    args = parser.parse_args()

    if not WIRE:
        print(f"! wire path disabled: {WIRE_ERROR}\n")

    report = run(args.draws, args.seed, args.gammas)

    names = [
        "P1_projection",
        "P2_invariance",
        "P3_dcbf",
        "P4_wire",
        "P4_wire_qround",
        "P5_observability",
    ]
    print(f"draws {report['draws']}  seed {report['seed']}  "
          f"gamma in {report['gammas']}\n")
    print(f"{'property':<16}{'tested':>9}{'failed':>9}{'material':>10}"
          f"{'rate':>10}{'worst h':>14}")
    for name in names:
        n = report["tested"].get(name, 0)
        f = report["failed"].get(name, 0)
        m = report["material"].get(name, 0)
        w = report["worst_margin"].get(name, 0.0)
        if n:
            print(f"{name:<16}{n:>9}{f:>9}{m:>10}{m / n:>10.2e}{w:>14.2e}")
    print("\n  P4_wire        = quantity survived the rewrite unrounded")
    print("  P4_wire_qround = the wire rounded quantity; live baskets are")
    print("                   already integers, so this regime is synthetic")
    print("\n  failed  = any violation beyond is_safe tolerance (1e-6)")
    print(f"  material = violation beyond {MATERIAL_TOL:g}, i.e. not "
          "representation error")

    print("\nby regime (failures / tested)")
    hdr = f"{'regime':<12}" + "".join(f"{n.split('_')[0]:>12}" for n in names)
    print(hdr)
    for regime, cells in report["by_regime"].items():
        row = f"{regime:<12}"
        for name in names:
            n = cells.get(name + "_n", 0)
            f = cells.get(name + "_fail", 0)
            row += f"{f'{f}/{n}':>12}" if n else f"{'-':>12}"
        print(row)

    ex, st = report["slack_when_left_C"], report["slack_when_stayed_in_C"]
    print(f"\nslack use  left C: {ex['frac_with_slack']:.3f} of {ex['n']} steps "
          f"(mean max slack {ex['mean_max_slack']:.3e})")
    print(f"           stayed: {st['frac_with_slack']:.3f} of {st['n']} steps "
          f"(mean max slack {st['mean_max_slack']:.3e})")

    if report["broken_rows"]:
        print("\nwhich row breaks, among material failures")
        for prop, counts in report["broken_rows"].items():
            if counts:
                inner = "  ".join(f"{k}={v}" for k, v in sorted(counts.items()))
                print(f"  {prop:<16} {inner}")

    if report["failures"]:
        print(f"\nfirst {min(6, len(report['failures']))} counterexamples:")
        for fail in report["failures"][:6]:
            print(f"  [{fail['prop']} / {fail['regime']} / draw {fail['draw']}]")
            for k, v in fail["detail"].items():
                if isinstance(v, list):
                    v = [round(z, 6) if isinstance(z, float) else z for z in v]
                print(f"      {k}: {v}")
    else:
        print("\nno counterexamples.")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
