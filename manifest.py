"""Write the corpus manifest, and rebalance the practice/locked split.

The manifest is Stage 2's remaining deliverable: a committed list of what is
actually in the corpus. It carries no answers - no files, no lines, no patch -
so it is safe to track in git.

Rebalancing is only legitimate BEFORE any instance has been run. Moving an
instance out of the locked pile after seeing how it went is the exact cheat the
lock exists to prevent, so this refuses once results exist.

Usage:
  python manifest.py                 # write the manifest
  python manifest.py --rebalance 0.6 # reassign piles, 60% practice
"""
import argparse, json, random
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
RESULTS = ROOT / "results"
KEYS = ROOT.parent / "repo-diagnosis-keys"   # OUTSIDE the repo: an
# agent inside instances/<name> can walk up to the repo root, and the
# answers must not be reachable from there. Verified 2026-09-07 that
# ../../keys/ resolved from inside an instance.


def load():
    out = []
    for p in sorted(KEYS.glob("*.json")):
        k = json.loads(p.read_text(encoding="utf-8"))
        if k.get("status") == "VALID" and not k.get("built_at_fixed_commit"):
            out.append((p, k))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebalance", type=float, metavar="PRACTICE_FRACTION")
    ap.add_argument("--seed", type=int, default=11)
    a = ap.parse_args()

    entries = load()
    if not entries:
        raise SystemExit("no valid instances yet")

    if a.rebalance is not None:
        already_run = [d.name for d in RESULTS.glob("*") if (d / "result.json").exists()]
        if already_run:
            raise SystemExit(
                "REFUSING to rebalance: results already exist for "
                + ", ".join(already_run)
                + "\nReassigning piles after a run is the cheat the lock exists "
                  "to prevent. Delete those results first, or leave the split alone.")
        random.seed(a.seed)
        names = sorted(k["instance"] for _, k in entries)
        random.shuffle(names)
        cut = round(len(names) * a.rebalance)
        practice = set(names[:cut])
        for p, k in entries:
            k["pile"] = "practice" if k["instance"] in practice else "locked"
            p.write_text(json.dumps(k, indent=2), encoding="utf-8")
        print(f"rebalanced: {cut} practice / {len(names)-cut} locked")
        entries = load()

    entries.sort(key=lambda e: e[1]["instance"])
    practice = [k for _, k in entries if k["pile"] == "practice"]
    locked = [k for _, k in entries if k["pile"] == "locked"]

    lines = ["# Corpus manifest", "",
             "Every instance below has been PROVED to contain a reproducible bug:",
             "its own test was observed to fail on it. Instances that could not be",
             "built, or whose bug did not reproduce, are not here - see",
             "`reports/rejections.md` for those and why.", "",
             "No answers in this file: no file names, no line numbers, no patch.", "",
             f"**{len(entries)} instances — {len(practice)} practice, "
             f"{len(locked)} locked.**", "",
             "| Instance | Python | Files | Lines | Pile |", "|---|---|---|---|---|"]
    for _, k in entries:
        lines.append(f"| {k['instance']} | {k.get('python_used','?')} | "
                     f"{k.get('size_files',0)} | {k.get('size_lines',0)} | "
                     f"{k['pile']} |")
    lines += ["", "## The locked pile", "",
              "These are the only independent measurement this project will ever",
              "get. Running them requires an explicit flag and typed confirmation.",
              "Looking at the result and then changing the prompt spends them",
              "permanently.", ""]
    for k in locked:
        lines.append(f"- {k['instance']}")

    (ROOT / "MANIFEST.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"MANIFEST.md written: {len(entries)} instances "
          f"({len(practice)} practice / {len(locked)} locked)")


if __name__ == "__main__":
    main()
