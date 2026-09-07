"""Score findings against the answer keys.

Stage 1 is automatic and kills most findings for free: a finding whose file is
not in the key cannot be the catalogued bug.

Stage 2 is NOT automated on purpose. Whether a described trigger would actually
produce the catalogued failure is a judgement, and an automatic guess there
would quietly invent a catch rate. Survivors are written out for a human (or
Claude) to rule on.

Usage:  python score.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
KEYS, RESULTS, REPORTS = ROOT / "keys", ROOT / "results", ROOT / "reports"


def norm(p):
    return str(p).replace("\\", "/").lstrip("./").lower()


def main():
    REPORTS.mkdir(exist_ok=True)
    keys = {k["instance"]: k for k in
            (json.loads(p.read_text(encoding="utf-8")) for p in KEYS.glob("*.json"))
            if k.get("status") == "VALID"}

    rows, judge, totals = [], [], {"instances": 0, "findings": 0, "needs": 0}
    for name, key in sorted(keys.items()):
        res = RESULTS / name / "result.json"
        if not res.exists():
            continue
        totals["instances"] += 1
        data = json.loads(res.read_text(encoding="utf-8"))
        findings = data.get("findings", [])
        totals["findings"] += len(findings)
        key_files = {norm(f) for f in key.get("files", [])}

        hits_possible = 0
        for i, f in enumerate(findings, 1):
            ff = norm(f.get("file", ""))
            match = any(ff.endswith(kf) or kf.endswith(ff) for kf in key_files if kf)
            if match:
                hits_possible += 1
                totals["needs"] += 1
                judge.append({"instance": name, "finding_no": i, "finding": f,
                              "key_files": sorted(key_files),
                              "key_lines": key.get("lines", []),
                              "key_description": key.get("description", "")[:600],
                              "verdict": "NEEDS_JUDGEMENT"})
        rows.append((name, len(findings), hits_possible,
                     sorted(key_files), data.get("what_examined", "")[:200]))

    (REPORTS / "needs_judgement.json").write_text(
        json.dumps(judge, indent=2), encoding="utf-8")

    out = ["# Scores", "",
           f"Instances scored: {totals['instances']}  |  "
           f"Findings reported: {totals['findings']}  |  "
           f"Reached stage 2: {totals['needs']}", "",
           "**Catch rate and false-alarm rate are NOT computed here.** Stage 2 is a",
           "judgement call and guessing it would invent a number. Rule on the entries",
           "in `reports/needs_judgement.json`, then fill these in:", "",
           "- Catch rate = hits / instances scored",
           "- False-alarm rate = false alarms / findings reported",
           "- Unknowns = real defects that are not the catalogued one "
           "(**never folded into either number**)", "",
           "## Per instance", "",
           "| Instance | Findings | Reached stage 2 | Key file(s) |",
           "|---|---|---|---|"]
    for name, n, hp, kf, _ in rows:
        out.append(f"| {name} | {n} | {hp} | {', '.join(kf)} |")

    out += ["", "## What each run said it examined", ""]
    for name, _, _, _, examined in rows:
        out.append(f"- **{name}** — {examined}")

    out += ["", "## Reminder", "",
            "Four hand runs on PySnooper produced six verified real defects and a",
            "catch rate of 0%. BugsInPy catalogues one bug per instance, so a finding",
            "outside the key is UNKNOWN, not wrong. If unknowns keep outnumbering",
            "hits, the ruler is wrong rather than the system."]
    (REPORTS / "scores.md").write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"{totals['instances']} instances, {totals['findings']} findings, "
          f"{totals['needs']} need judgement.")
    print("-> reports/scores.md and reports/needs_judgement.json")


if __name__ == "__main__":
    main()
