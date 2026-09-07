#!/usr/bin/env python3
"""Reconcile every number in the dissertation against the stored results.

Phase 0 of the 2026-09-07 review pass. Reads nothing but results/ and prints
what is actually on disk, grouped the way the thesis tables group it. It makes
no claim about the LaTeX; the diff against the .tex is done by hand from this
output, and recorded in docs/audit_numbers_report.md.

    uv run python scripts/audit_numbers.py
"""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from collections import defaultdict

RES = Path(__file__).resolve().parents[1] / "results"


def families() -> dict[str, list[Path]]:
    """Group run directories by family, stripping the _v<n> seed suffix."""
    out: dict[str, list[Path]] = defaultdict(list)
    for d in sorted(RES.iterdir()):
        if not (d / "report.json").exists():
            continue
        out[re.sub(r"_v\d+$", "", d.name)].append(d)
    return out


def per_family() -> list[dict]:
    rows = []
    for fam, dirs in sorted(families().items()):
        gov = breach = corr = unsat_pairs = 0
        gammas, modes = set(), set()
        for d in dirs:
            j = json.loads((d / "report.json").read_text())
            r = j["report"]
            gov += int(r.get("rounds") or 0)
            breach += int(r.get("breach_rounds") or 0)
            corr += round(float(r.get("intervention_rate") or 0) * int(r.get("rounds") or 0))
            unsat_pairs += int(r.get("pairs_unsatisfiable") or 0)
            if j.get("gamma") is not None:
                gammas.add(j["gamma"])
            if j.get("mode"):
                modes.add(j["mode"])
        rows.append(dict(family=fam, seeds=len(dirs), rounds=gov, breaching=breach,
                         corrected=corr, unsat=unsat_pairs,
                         gamma=",".join(str(g) for g in sorted(gammas)) or "-",
                         mode=",".join(sorted(modes)) or "-"))
    return rows


def summaries() -> None:
    """Print the aggregated files the thesis tables were built from."""
    def show(name, fn):
        p = RES / "summary" / name
        if not p.exists():
            print(f"  {name}: ABSENT"); return
        try:
            fn(json.loads(p.read_text()))
        except Exception as e:  # noqa: BLE001
            print(f"  {name}: unreadable ({e})")

    print("\n" + "=" * 78)
    print("AGGREGATES THE THESIS TABLES WERE BUILT FROM")
    print("=" * 78)

    def arms(d):
        print("\n  five_arms.json / arms.json  (Tables 5.3, 5.4, 5.7, Fig 5.4)")
        print(f"    {'arm':<12}{'gov':>10}{'gov breach':>12}{'deals':>8}"
              f"{'breached':>10}{'trivial':>9}{'meaningful':>12}{'overspend':>11}")
        for arm, v in d.get("arms", {}).items():
            gs, hl = v.get("governed_split", {}), v.get("headline", {})
            print(f"    {arm:<12}{gs.get('governed_rounds',0):>10.0f}"
                  f"{gs.get('governed_breaches',0):>12.0f}{hl.get('deals_settled',0):>8.0f}"
                  f"{hl.get('deals_breached',0):>10.0f}{hl.get('deals_trivial',0):>9.0f}"
                  f"{hl.get('deals_meaningful',0):>12.0f}"
                  f"{hl.get('total_overspend',0):>11.4f}")
    show("five_arms.json", arms)
    show("arms.json", arms)

    def gsweep(d):
        print("\n  gamma_sweep.json  (Table B.2)")
        print(f"    {'gamma':>7}{'governed':>12}{'corrected':>12}{'deals':>8}{'rounds/pair':>13}{'margin':>12}")
        for g, v in sorted(d.items(), key=lambda kv: float(kv[0])):
            print(f"    {g:>7}{v.get('gov','-'):>12}{v.get('corrected','-'):>12}"
                  f"{v.get('deals',0):>8}{v.get('rounds',0):>13}{v.get('margin',0):>12.3g}")
    show("gamma_sweep.json", gsweep)

    def models(d):
        print("\n  models.json  (Table B.1)")
        print(json.dumps(d, indent=1)[:1400])
    show("models.json", models)


def main() -> int:
    print("=" * 78)
    print("PER-FAMILY TOTALS FROM results/**/report.json")
    print("=" * 78)
    print(f"{'family':<34}{'seeds':>6}{'rounds':>8}{'breach':>8}{'corr':>7}"
          f"{'unsat':>7}{'gamma':>7}  mode")
    for r in per_family():
        print(f"{r['family']:<34}{r['seeds']:>6}{r['rounds']:>8}{r['breaching']:>8}"
              f"{r['corrected']:>7}{r['unsat']:>7}{r['gamma']:>7}  {r['mode']}")
    summaries()

    print("\n" + "=" * 78)
    print("THE FOUR SUSPECTS NAMED IN THE REVIEW")
    print("=" * 78)
    fam = families()
    for a, b in [("arm_b_bargain", "arm_b_g0_4")]:
        print(f"\n  S1  arm B at gamma=0.4 on bargain_3_9 — one batch or two?")
        for f in (a, b):
            ds = fam.get(f, [])
            print(f"      {f:<22} {len(ds)} seeds: {', '.join(d.name for d in ds)}")
        print("      -> if both exist with different seed names they are DIFFERENT BATCHES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
