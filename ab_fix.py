"""Stage 13's on/off check: does the store change anything at all?

Run the SAME defect through the fixer twice - once with the library and
database switched on, once with them switched off - and record whether the two
outcomes differ.

This exists before the store is worth building, and that order is deliberate.
Storing entries is easy; getting the right one back out is the entire
difficulty. Build this check afterwards and you end up with ten thousand
entries contributing nothing while every visible sign says the system is
learning.

**A "no difference" result is a real result and is reported as one.** If
switching the store on changes neither the proof, nor the number of attempts,
nor where the fix landed, then the store is decoration however many entries it
holds. That finding is the point of this script, not a failure of it.

What is compared, per side:

  proof_passed      the failure is gone AND the project's own tests are no
                    worse. Either half alone is passed by deleting the feature.
  attempts          how many tries it took
  files_changed     where it landed
  landed_on_real    did it touch what the real fix touched (corpus only - the
                    product will not have this, it is here to tell "fixed the
                    cause" from "silenced the symptom")

Usage:
  python ab_fix.py --instance black-1 --finding 2
  python ab_fix.py --instance black-1 --finding 2 --repeat 3
"""
import argparse, json, subprocess, sys
from datetime import datetime
from pathlib import Path

import library
from progress_marker import progress_marker

ROOT = Path(__file__).parent.resolve()
REPORTS = ROOT / "reports"
RESULTS = ROOT / "results"


def run_side(instance, finding, with_library):
    """One fixer run. Returns its verdict dict, or None if it produced none."""
    tag = f"{instance}-f{finding}" + ("-lib" if with_library else "")
    cmd = [sys.executable, str(ROOT / "fix_bug.py"),
           "--instance", instance, "--finding", str(finding)]
    if with_library:
        cmd.append("--library")
    label = "ON " if with_library else "OFF"
    print(f"\n{'='*66}\n  library {label} : {instance} finding {finding}\n{'='*66}",
          flush=True)
    p = subprocess.run(cmd, cwd=str(ROOT))
    verdict_path = REPORTS / f"fix-{tag}.json"
    if p.returncode != 0 or not verdict_path.exists():
        print(f"  !! no verdict written (exit {p.returncode})")
        return None
    return json.loads(verdict_path.read_text(encoding="utf-8"))


def landed_on_real(v):
    """Did it change a file the catalogued fix changed?"""
    if not v:
        return None
    real = {Path(f).name for f in v.get("real_fix_touched", [])}
    touched = {Path(f).name for f, _ in v.get("files_changed", [])}
    return bool(real & touched)


def compare(off, on):
    """The differences that matter, and whether there were any."""
    def g(v, k, d=None):
        return v.get(k, d) if v else d
    rows = [
        ("ran at all", off is not None, on is not None),
        ("proof passed", g(off, "proof_passed"), g(on, "proof_passed")),
        ("reproduction passes", g(off, "repro_after_passes"), g(on, "repro_after_passes")),
        ("tests no worse", g(off, "tests_still_ok"), g(on, "tests_still_ok")),
        ("attempts", g(off, "attempts"), g(on, "attempts")),
        ("files changed", sorted(f for f, _ in g(off, "files_changed", []) or []),
                          sorted(f for f, _ in g(on, "files_changed", []) or [])),
        ("landed where real fix did", landed_on_real(off), landed_on_real(on)),
    ]
    differs = [name for name, a, b in rows if a != b]
    return rows, differs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", required=True)
    ap.add_argument("--finding", type=int, default=1)
    ap.add_argument("--repeat", type=int, default=1,
                    help="run the pair this many times. The fixer is not "
                         "deterministic, so a single pair cannot tell a real "
                         "effect from run-to-run noise.")
    a = ap.parse_args()

    res = RESULTS / a.instance / "result.json"
    if not res.exists():
        sys.exit(f"no findings for {a.instance} - run run_diagnosis.py first")
    findings = json.loads(res.read_text(encoding="utf-8")).get("findings", [])
    if not 1 <= a.finding <= len(findings):
        sys.exit(f"{a.instance} has {len(findings)} findings; asked for "
                 f"{a.finding}")

    before = library.stats()
    query = library.query_from_finding(findings[a.finding - 1])
    would_offer = library.search(query, limit=3)
    print(f"stores: {before['library']} in library, {before['database']} in "
          f"database")
    print(f"this finding would be offered: "
          + (", ".join(e["id"] for e, _, _ in would_offer) or "NOTHING"))
    if not would_offer:
        print("\n  NOTE: retrieval matches nothing, so the two sides receive an\n"
              "  identical prompt. Any difference seen is run-to-run noise, and\n"
              "  that is worth recording as the baseline for what noise looks\n"
              "  like - but it is not evidence about the store.")

    pairs = []
    # a pair is two fixer runs, each with a full before/after test suite - well
    # over the twenty-minute mark the daily reviewer needs warning about
    with progress_marker(f"A/B fix check, {a.instance} f{a.finding} "
                         f"x{a.repeat}", "reports/ab-*.json",
                         f"~{max(1, a.repeat)}h"):
        for i in range(a.repeat):
            if a.repeat > 1:
                print(f"\n########## pair {i+1} of {a.repeat} ##########")
            off = run_side(a.instance, a.finding, False)
            on = run_side(a.instance, a.finding, True)
            pairs.append((off, on))

    print(f"\n{'='*66}\n  RESULT\n{'='*66}")
    all_differs = []
    report_pairs = []
    for i, (off, on) in enumerate(pairs, 1):
        rows, differs = compare(off, on)
        all_differs.append(differs)
        if len(pairs) > 1:
            print(f"\n-- pair {i} --")
        print(f"  {'':32} {'OFF':<22} ON")
        for name, x, y in rows:
            mark = "  " if x == y else "->"
            print(f"{mark} {name:32} {str(x):<22} {y}")
        print(f"  differences: {differs or 'NONE'}")
        report_pairs.append({"pair": i, "differences": differs,
                             "off": off, "on": on})

    ever = sorted({d for ds in all_differs for d in ds})
    after = library.stats()
    print(f"\n  across {len(pairs)} pair(s), things that ever differed: "
          f"{ever or 'NOTHING'}")
    if not ever:
        print("\n  THE STORE CHANGED NOTHING. On this evidence it is decoration.")
    print(f"  stores now: {after['library']} library, {after['database']} database")

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"ab-{a.instance}-f{a.finding}.json"
    out.write_text(json.dumps({
        "instance": a.instance, "finding": a.finding,
        "when": datetime.now().isoformat(timespec="seconds"),
        "repeats": a.repeat,
        "retrieval_offered": [e["id"] for e, _, _ in would_offer],
        "store_before": before, "store_after": after,
        "ever_differed": ever,
        "store_made_a_difference": bool(ever),
        "pairs": report_pairs,
    }, indent=2), encoding="utf-8")
    print(f"  -> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
