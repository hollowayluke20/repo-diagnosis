"""Score findings by RUNNING their reproductions.

The rules live in SCORING.md and were written before any batch ran. In short:
a finding is real if its reproduction script fails on the instance, and that
question is settled by executing it rather than by anybody's opinion.

Two numbers, kept apart on purpose:
  catch rate        - did it find the bug the dataset catalogued (low, expected)
  confirmation rate - are the things it reports actually real (the useful one)

A finding that is CONFIRMED but not CATALOGUED is a success, not a miss.

Usage:  python score.py
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
INSTANCES, RESULTS, REPORTS = (ROOT / "instances", ROOT / "results",
                               ROOT / "reports")
KEYS = ROOT.parent / "repo-diagnosis-keys"   # OUTSIDE the repo: an
# agent inside instances/<name> can walk up to the repo root, and the
# answers must not be reachable from there. Verified 2026-09-07 that
# ../../keys/ resolved from inside an instance.
REPRO_TIMEOUT = 120


NEAR = 15  # lines either side of a patched hunk that still count as "here"


def norm(p):
    return str(p).replace("\\", "/").lstrip("./").lower()


def patched_regions(project, bug_id):
    """Which lines the real fix actually touched, per file.

    Matching on filename alone is not a catch - SCORING.md says so explicitly,
    and scoring it that way turned a 1-of-3 into a 100% that was fiction. A
    finding counts only if it lands where the fix landed.
    """
    import re
    p = (ROOT / "BugsInPy" / "projects" / project / "bugs" / bug_id
         / "bug_patch.txt")
    if not p.exists():
        return {}
    regions, current = {}, None
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r"^\+\+\+ b?/?(\S+)", line)
        if m and m.group(1) != "/dev/null":
            current = norm(m.group(1))
            regions.setdefault(current, [])
            continue
        m = re.match(r"^@@ -(\d+)(?:,(\d+))?", line)
        if m and current:
            start = int(m.group(1))
            length = int(m.group(2) or 1)
            regions[current].append((start, start + length))
    return regions


def is_catalogued(regions, file, line):
    f = norm(file)
    for kf, spans in regions.items():
        if not (f.endswith(kf) or kf.endswith(f)):
            continue
        for lo, hi in spans:
            if lo - NEAR <= (line or -999) <= hi + NEAR:
                return True
    return False


def run_reproduction(instance_dir, script, tag):
    """Run one reproduction inside its instance. Returns (verdict, detail).

    CONFIRMED   - it failed, which is what a real defect does
    UNCONFIRMED - it ran and did not fail
    MALFORMED   - it could not be run at all
    """
    if not script or len(script.strip()) < 20:
        return "MALFORMED", "no reproduction supplied"
    py = instance_dir / ".python" / "python.exe"
    if not py.exists():
        return "MALFORMED", "instance has no interpreter"

    path = instance_dir / f"_repro_{tag}.py"
    try:
        path.write_text(script, encoding="utf-8")
    except OSError as e:
        return "MALFORMED", f"could not write script: {e}"

    try:
        p = subprocess.run([str(py), path.name], cwd=str(instance_dir),
                           capture_output=True, text=True, errors="replace",
                           stdin=subprocess.DEVNULL, timeout=REPRO_TIMEOUT)
        out = (p.stdout or "") + (p.stderr or "")
        if p.returncode == 0:
            return "UNCONFIRMED", "ran without failing"
        # a script that dies before reaching the code under test proves nothing
        if "SyntaxError" in out or "IndentationError" in out:
            return "MALFORMED", "script does not parse"
        first = next((l.strip() for l in reversed(out.splitlines())
                      if l.strip()), "")
        if "ModuleNotFoundError" in out and "import" in out.split("\n")[0].lower():
            return "MALFORMED", first[:200]
        return "CONFIRMED", first[:200]
    except subprocess.TimeoutExpired:
        return "MALFORMED", f"timed out after {REPRO_TIMEOUT}s"
    finally:
        path.unlink(missing_ok=True)


def main():
    REPORTS.mkdir(exist_ok=True)
    keys = {k["instance"]: k for k in
            (json.loads(p.read_text(encoding="utf-8")) for p in KEYS.glob("*.json"))
            if k.get("status") == "VALID" and not k.get("built_at_fixed_commit")}

    tally = {"CONFIRMED": 0, "UNCONFIRMED": 0, "MALFORMED": 0}
    instances_run = 0
    instances_caught = 0
    rows, detail = [], []

    for name, key in sorted(keys.items()):
        res = RESULTS / name / "result.json"
        if not res.exists():
            continue
        instances_run += 1
        findings = json.loads(res.read_text(encoding="utf-8")).get("findings", [])
        key_files = {norm(f) for f in key.get("files", []) if f}
        regions = patched_regions(key["project"], key["bug_id"])
        caught = False

        for i, f in enumerate(findings, 1):
            verdict, why = run_reproduction(INSTANCES / name,
                                            f.get("reproduction", ""), i)
            tally[verdict] += 1
            ff = norm(f.get("file", ""))
            right_file = any(ff.endswith(kf) or kf.endswith(ff)
                             for kf in key_files)
            catalogued = (verdict == "CONFIRMED"
                          and is_catalogued(regions, f.get("file", ""),
                                            f.get("line")))
            if catalogued:
                caught = True
            detail.append({"instance": name, "finding_no": i,
                           "file": f.get("file"), "line": f.get("line"),
                           "claim": f.get("what_goes_wrong", "")[:200],
                           "verdict": verdict, "why": why,
                           "right_file": right_file,
                           "catalogued_candidate": catalogued})
            print(f"  {name} #{i}: {verdict}"
                  + ("  [CATALOGUED]" if catalogued
                     else "  [right file, wrong place]" if right_file else ""))
        if caught:
            instances_caught += 1
        rows.append((name, len(findings), caught))

    total = sum(tally.values())
    pct = lambda n, d: f"{100*n/d:.0f}%" if d else "n/a"
    out = [
        "# Scores", "",
        "Rules: `SCORING.md`. Every finding below was scored by **running its",
        "reproduction**, not by reading it.", "",
        f"- **Catch rate: {pct(instances_caught, instances_run)}** "
        f"({instances_caught} of {instances_run} instances) — found the bug the",
        "  dataset catalogued. Low is expected; the dataset records one bug per",
        "  project.",
        f"- **Confirmation rate: {pct(tally['CONFIRMED'], total)}** "
        f"({tally['CONFIRMED']} of {total} findings) — reproductions that",
        "  actually failed. This is the quality measure.",
        f"- **Noise rate: {pct(tally['UNCONFIRMED'] + tally['MALFORMED'], total)}** "
        f"({tally['UNCONFIRMED']} unconfirmed, {tally['MALFORMED']} malformed).",
        "", "## Per instance", "",
        "| Instance | Findings | Caught the catalogued bug |", "|---|---|---|"]
    for name, n, caught in rows:
        out.append(f"| {name} | {n} | {'yes' if caught else 'no'} |")
    (REPORTS / "scores.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    (REPORTS / "verdicts.json").write_text(json.dumps(detail, indent=2),
                                           encoding="utf-8")
    print("\n".join(out[3:12]))
    print("\n-> reports/scores.md and reports/verdicts.json")


if __name__ == "__main__":
    main()
