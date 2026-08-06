"""Do offers drift toward the bargaining solution, and does the contract funnel them?

Two supervision questions, answered from data already on disk. No API calls.

**Question 1 — drift.** The arm notes report only the distance of *settled* terms
to x*_NBS. Nobody has asked whether the sequence of offers moves toward it
during the negotiation. This computes the distance at every round.

What it can and cannot prove. Live agents have no step-size schedule, so a
decrease fraction here is **not** a test of the formulation's convergence
theorem (outline G4) — that theorem is about a specific dynamic, and these
agents are not running it. The question is the weaker, descriptive one: *do
observed negotiations drift toward the bargaining solution at all?* Read as
anything stronger it would be a category error.

**Question 2 — funnelling.** Arm D established a claim about the *mechanism*:
96% of governed rounds would need flagging on an ungoverned trajectory, while
the filter corrects 11%, because enforcement changes the path. This tests it as
a claim about *outcomes* — does governance narrow where negotiations end up?

Two methodological choices that decide whether the numbers mean anything:

  * **dispersion is computed within pair, never pooled across customers.** The
    three customers have different baskets, so a pooled spread would mostly
    measure the scenario. Only the across-seed spread for a fixed pair is
    attributable to governance.
  * **arms A and D are the bar.** They are behaviourally identical, so any A/D
    difference is seed noise. A governance effect has to clear it.

Every fraction is printed with its n, and "too short to say" is a reported
outcome rather than a silent omission — most trajectories here are two or three
points long.

Usage:
    uv run python experiments/analyse_trajectories.py --arms a b d
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.certificates.energy import phi, phi_projected  # noqa: E402
from src.marketplace_integration.theta import ContractRegistry  # noqa: E402
from src.payoffs import SCALE, PayoffModel, dist_M  # noqa: E402

# A trajectory needs at least this many points to say anything about direction:
# three points give two steps, which is the minimum for "decreasing" to mean
# more than "the single step happened to go down".
MIN_POINTS_FOR_DIRECTION = 3


def load_rounds(path: Path) -> dict[str, list[dict[str, Any]]]:
    """Per-round certificate records, grouped by pair, in round order."""
    by_pair: dict[str, list[dict[str, Any]]] = defaultdict(list)
    if not path.exists():
        return by_pair
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            record = json.loads(line)
            by_pair[record["pair_id"]].append(record)
    for records in by_pair.values():
        records.sort(key=lambda r: r["round_index"])
    return by_pair


def classify(distances: list[float]) -> str:
    """monotone / noisy-decreasing / flat / non-convergent / too-short."""
    if len(distances) < MIN_POINTS_FOR_DIRECTION:
        return "too-short"
    steps = np.diff(distances)
    if np.all(steps <= 1e-9):
        return "monotone"
    net = distances[-1] - distances[0]
    if net < -1e-9 and np.mean(steps <= 0) > 0.5:
        return "noisy-decreasing"
    if abs(net) <= 1e-9:
        return "flat"
    return "non-convergent"


def analyse_arm(arm: str, registry: ContractRegistry, results: Path) -> dict[str, Any]:
    """Drift and dispersion for one arm, over its seeds."""
    models: dict[str, PayoffModel] = {}
    star: dict[str, np.ndarray] = {}

    def model_for(pair_id: str) -> PayoffModel | None:
        if pair_id not in models:
            business_id, customer_id = pair_id.split("|", 1)
            business = registry.businesses.get(business_id)
            customer = registry.customers.get(customer_id)
            if business is None or customer is None:
                return None
            try:
                models[pair_id] = PayoffModel.from_scenario(business, customer)
            except ValueError:
                return None
            star[pair_id] = models[pair_id].nash_bargaining_solution()[0]
        return models.get(pair_id)

    binding_classes: dict[str, int] = defaultdict(int)
    binding_steps_down = binding_steps = 0
    lengths: list[int] = []
    settled_by_pair: dict[str, list[np.ndarray]] = defaultdict(list)
    settled_distance_by_pair: dict[str, list[float]] = defaultdict(list)
    proposals_by_pair: dict[str, list[np.ndarray]] = defaultdict(list)
    per_trajectory: list[dict[str, Any]] = []
    phi_steps: list[float] = []
    phi_net_down: list[bool] = []
    proj_defined_rounds = [0, 0]

    for run in sorted(results.glob(f"arm_{arm}_*/certificates.jsonl")):
        for pair_id, records in load_rounds(run).items():
            model = model_for(pair_id)
            if model is None:
                continue
            terms = [np.array(r["x_applied"], dtype=float) for r in records]
            lengths.append(len(terms))
            proposals_by_pair[pair_id].extend(terms)

            distances = [dist_M(x, star[pair_id]) for x in terms]
            label = classify(distances)
            binding_classes[label] += 1
            if len(distances) >= 2:
                steps = np.diff(distances)
                binding_steps += len(steps)
                binding_steps_down += int(np.sum(steps <= 1e-9))
            per_trajectory.append(
                {
                    "run": run.parent.name,
                    "pair": pair_id,
                    "points": len(terms),
                    "distances": distances,
                    "class": label,
                }
            )

            # The last applied terms of a pair that reached a deal are its
            # settled point. Deals are identified in the summary artefacts;
            # here the final round is a good proxy and is what dispersion needs.
            settled_by_pair[pair_id].append(terms[-1])
            settled_distance_by_pair[pair_id].append(distances[-1])

            # Phi on the SAME (binding) sequence as the distance above, so the
            # two convergence measures are like-for-like. Phi_proj is NaN
            # outside C(theta) and those rounds are excluded, not zero-filled.
            contract = registry.get(*pair_id.split("|", 1))
            phi_seq = [phi(model, x) for x in terms]
            proj_seq = [phi_projected(model, x, contract) for x in terms]
            per_trajectory[-1]["phi"] = phi_seq
            per_trajectory[-1]["phi_proj_defined"] = int(
                np.sum(np.isfinite(proj_seq))
            )
            if len(phi_seq) >= 2:
                phi_steps.extend(np.diff(phi_seq))
                phi_net_down.append(phi_seq[-1] < phi_seq[0])
            proj_defined_rounds[0] += int(np.sum(np.isfinite(proj_seq)))
            proj_defined_rounds[1] += len(proj_seq)

    return {
        "arm": arm,
        "trajectories": len(per_trajectory),
        "lengths": lengths,
        "classes": dict(binding_classes),
        "steps": binding_steps,
        "steps_down": binding_steps_down,
        "per_trajectory": per_trajectory,
        "phi_binding": {
            "steps": len(phi_steps),
            "fraction_decreasing": (
                float(np.mean([d <= 1e-9 for d in phi_steps])) if phi_steps else None
            ),
            "fraction_net_down": (
                float(np.mean(phi_net_down)) if phi_net_down else None
            ),
            "phi_proj_defined_rounds": proj_defined_rounds[0],
            "phi_proj_total_rounds": proj_defined_rounds[1],
        },
        "dispersion": _dispersion(settled_by_pair, settled_distance_by_pair),
        "proposal_dispersion": _proposal_dispersion(proposals_by_pair),
    }


def _dispersion(
    settled: dict[str, list[np.ndarray]], distances: dict[str, list[float]]
) -> dict[str, Any]:
    """Within-pair spread of settled terms, pooled over pairs.

    Pooling ACROSS pairs would measure the scenario — the three customers buy
    different baskets at different price levels. Only the across-seed spread at
    a fixed pair is attributable to governance, so the per-pair SDs are computed
    first and averaged after.
    """
    per_dim: list[np.ndarray] = []
    per_distance: list[float] = []
    contributing = 0
    for pair_id, points in settled.items():
        if len(points) < 2:
            continue
        contributing += 1
        scaled = np.array(points) / SCALE
        per_dim.append(np.std(scaled, axis=0, ddof=1))
        if len(distances[pair_id]) >= 2:
            per_distance.append(float(np.std(distances[pair_id], ddof=1)))
    if not per_dim:
        return {"pairs_contributing": 0}
    mean_dim = np.mean(per_dim, axis=0)
    return {
        "pairs_contributing": contributing,
        "sd_price": float(mean_dim[0]),
        "sd_quantity": float(mean_dim[1]),
        "sd_deadline": float(mean_dim[2]),
        "sd_overall": float(np.linalg.norm(mean_dim)),
        "sd_distance_to_nbs": float(np.mean(per_distance)) if per_distance else None,
    }


def _proposal_dispersion(proposals: dict[str, list[np.ndarray]]) -> dict[str, Any]:
    """How much of term space the per-round proposals occupy, within pair."""
    spreads: list[np.ndarray] = []
    for points in proposals.values():
        if len(points) < 2:
            continue
        spreads.append(np.std(np.array(points) / SCALE, axis=0, ddof=1))
    if not spreads:
        return {"pairs_contributing": 0}
    mean = np.mean(spreads, axis=0)
    return {
        "pairs_contributing": len(spreads),
        "sd_price": float(mean[0]),
        "sd_quantity": float(mean[1]),
        "sd_overall": float(np.linalg.norm(mean)),
    }


def phi_series(arm: str, results: Path) -> dict[str, Any]:
    """Phi and Phi_proj along the observed trajectories.

    Collected since the section 11 layer landed and never analysed until now.
    The observed trajectory interleaves the buyer's regex-extracted
    counter-offers, so it is longer than the binding one and carries the
    extraction caveat with it.
    """
    phis: list[list[float]] = []
    projs: list[list[float]] = []
    for run in sorted(results.glob(f"arm_{arm}_*/section_11.json")):
        for negotiation in json.load(run.open())["negotiations"]:
            if negotiation.get("status") != "ok":
                continue
            phis.append(negotiation["phi"]["series"])
            projs.append(negotiation["phi_projected"]["series"])

    def summarise(series: list[list[float]]) -> dict[str, Any]:
        usable = [s for s in series if len(s) >= MIN_POINTS_FOR_DIRECTION]
        steps = [d for s in usable for d in np.diff(s)]
        net_down = [s[-1] < s[0] for s in usable]
        return {
            "trajectories": len(series),
            "usable": len(usable),
            "steps": len(steps),
            "fraction_decreasing": (
                float(np.mean([d <= 1e-9 for d in steps])) if steps else None
            ),
            "fraction_net_down": float(np.mean(net_down)) if net_down else None,
        }

    return {"phi": summarise(phis), "phi_projected": summarise(projs)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arms", nargs="+", default=["a", "b", "d"])
    parser.add_argument("--data", default="data/bargain_3_9")
    parser.add_argument("--results", default="results")
    parser.add_argument("--out", default="results/summary/trajectories.json")
    args = parser.parse_args()

    registry = ContractRegistry.from_data_dir(args.data)
    results = Path(args.results)
    report = {arm: analyse_arm(arm, registry, results) for arm in args.arms}
    for arm in args.arms:
        report[arm]["phi"] = phi_series(arm, results)

    # ---------------------------------------------------------------- drift --
    print("=" * 78)
    print("QUESTION 1 — do offers drift toward the bargaining solution?")
    print("=" * 78)
    print("  Descriptive only. Live agents have no step schedule, so this is NOT")
    print("  a test of the convergence theorem (outline G4).\n")

    print("  binding trajectories (seller proposals only, exact terms)")
    print(f"  {'arm':<6}{'traj':>6}{'median len':>12}{'>=3 pts':>9}"
          f"{'steps':>7}{'down':>7}{'frac down':>11}")
    print("  " + "-" * 60)
    for arm in args.arms:
        r = report[arm]
        usable = sum(1 for t in r["per_trajectory"] if t["points"] >= 3)
        frac = (
            f"{r['steps_down'] / r['steps']:.2f}" if r["steps"] else "n/a"
        )
        median = f"{np.median(r['lengths']):.0f}" if r["lengths"] else "-"
        print(f"  {arm:<6}{r['trajectories']:>6}{median:>12}{usable:>9}"
              f"{r['steps']:>7}{r['steps_down']:>7}{frac:>11}")

    print("\n  trajectory classes (binding)")
    classes = ["monotone", "noisy-decreasing", "flat", "non-convergent", "too-short"]
    print(f"  {'arm':<6}" + "".join(f"{c:>18}" for c in classes))
    print("  " + "-" * 76)
    for arm in args.arms:
        line = f"  {arm:<6}"
        for c in classes:
            line += f"{report[arm]['classes'].get(c, 0):>18}"
        print(line)

    print("\n  Phi on the BINDING trajectory — like-for-like with the distance above")
    print(f"  {'arm':<6}{'steps':>7}{'frac dec':>10}{'net down':>10}"
          f"{'Phi_proj defined':>19}")
    print("  " + "-" * 52)
    for arm in args.arms:
        b = report[arm]["phi_binding"]
        fd = (
            f"{b['fraction_decreasing']:.2f}"
            if b["fraction_decreasing"] is not None
            else "n/a"
        )
        nd = (
            f"{b['fraction_net_down']:.2f}"
            if b["fraction_net_down"] is not None
            else "n/a"
        )
        defined = f"{b['phi_proj_defined_rounds']}/{b['phi_proj_total_rounds']}"
        print(f"  {arm:<6}{b['steps']:>7}{fd:>10}{nd:>10}{defined:>19}")
    print("  Phi_proj is undefined (NaN) outside C(theta); the ratio shows how")
    print("  often the state was IN the set at all.")

    print("\n  Phi / Phi_proj on the OBSERVED trajectory (includes regex-extracted")
    print("  buyer counter-offers, so longer but noisier)")
    print(f"  {'arm':<6}{'series':>8}{'usable':>8}{'steps':>7}"
          f"{'frac dec':>10}{'net down':>10}")
    print("  " + "-" * 52)
    for arm in args.arms:
        for label in ("phi", "phi_projected"):
            s = report[arm]["phi"][label]
            fd = (
                f"{s['fraction_decreasing']:.2f}"
                if s["fraction_decreasing"] is not None
                else "n/a"
            )
            nd = (
                f"{s['fraction_net_down']:.2f}"
                if s["fraction_net_down"] is not None
                else "n/a"
            )
            print(f"  {arm + ':' + label[:9]:<6}{s['trajectories']:>8}"
                  f"{s['usable']:>8}{s['steps']:>7}{fd:>10}{nd:>10}")

    # ------------------------------------------------------------- funnelling --
    print("\n" + "=" * 78)
    print("QUESTION 2 — does the contract funnel outcomes?")
    print("=" * 78)
    print("  Dispersion is WITHIN pair across seeds, never pooled across customers.\n")

    print("  spread of settled terms (scaled units; lower = more funnelled)")
    print(f"  {'arm':<6}{'pairs':>7}{'sd price':>10}{'sd qty':>9}"
          f"{'sd overall':>12}{'sd dist-NBS':>13}")
    print("  " + "-" * 58)
    for arm in args.arms:
        d = report[arm]["dispersion"]
        if not d.get("pairs_contributing"):
            print(f"  {arm:<6}{'no pair has 2+ settled points':>50}")
            continue
        sdd = f"{d['sd_distance_to_nbs']:.3f}" if d["sd_distance_to_nbs"] else "n/a"
        print(f"  {arm:<6}{d['pairs_contributing']:>7}{d['sd_price']:>10.3f}"
              f"{d['sd_quantity']:>9.3f}{d['sd_overall']:>12.3f}{sdd:>13}")

    print("\n  spread of per-round proposals (region of term space occupied)")
    print(f"  {'arm':<6}{'pairs':>7}{'sd price':>10}{'sd qty':>9}{'sd overall':>12}")
    print("  " + "-" * 46)
    for arm in args.arms:
        d = report[arm]["proposal_dispersion"]
        if not d.get("pairs_contributing"):
            print(f"  {arm:<6}{'no pair has 2+ proposals':>44}")
            continue
        print(f"  {arm:<6}{d['pairs_contributing']:>7}{d['sd_price']:>10.3f}"
              f"{d['sd_quantity']:>9.3f}{d['sd_overall']:>12.3f}")

    print("\n  negotiation length — the compression measure")
    print(f"  {'arm':<6}{'median':>8}{'mean':>8}{'max':>6}")
    print("  " + "-" * 28)
    for arm in args.arms:
        lengths = report[arm]["lengths"]
        if lengths:
            print(f"  {arm:<6}{np.median(lengths):>8.1f}{np.mean(lengths):>8.2f}"
                  f"{max(lengths):>6}")

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2, default=float), encoding="utf-8")
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
