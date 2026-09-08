"""Run the first small, isolated on/off test of the fix-idea library.

This deliberately wraps ab_fix.py rather than reproducing its fixing or proof
logic. Its only extra jobs are to choose a varied, predeclared practice batch,
keep the experiment's library bookkeeping out of the real stores, and turn the
per-run verdicts into the agreed, answer-safe summary report.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

from progress_marker import progress_marker

ROOT = Path(__file__).parent.resolve()
REPORT = ROOT / "reports" / "library-batch-test.md"

# First findings, not selected for a promising retrieval result. There is one
# practice-pile instance per project, giving six different bug shapes.
BATCH = [
    ("black-1", 1),
    ("cookiecutter-1", 1),
    ("fastapi-1", 1),
    ("httpie-1", 1),
    ("spacy-3", 1),
    ("tornado-2", 1),
]


def run(cmd, *, cwd=None, timeout=None, capture=False):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, timeout=timeout,
                          text=True, encoding="utf-8", errors="replace",
                          capture_output=capture)


def practice_instances():
    text = (ROOT / "MANIFEST.md").read_text(encoding="utf-8")
    return {m.group(1) for m in re.finditer(
        r"^\|\s*([A-Za-z0-9_.-]+)\s*\|.*?\|\s*practice\s*\|$", text, re.M)}


def validate_batch():
    practice = practice_instances()
    projects, problems = set(), []
    for instance, finding_number in BATCH:
        project = instance.rsplit("-", 1)[0]
        result = ROOT / "results" / instance / "result.json"
        if project in projects:
            problems.append(f"{instance}: second finding from project {project}")
        projects.add(project)
        if instance not in practice:
            problems.append(f"{instance}: not in the practice pile")
        if not result.exists():
            problems.append(f"{instance}: no diagnosis result")
            continue
        findings = json.loads(result.read_text(encoding="utf-8")).get("findings", [])
        if not 1 <= finding_number <= len(findings):
            problems.append(f"{instance}: finding {finding_number} does not exist")
    if problems:
        raise RuntimeError("batch validation failed:\n  - " + "\n  - ".join(problems))


def make_junction(link, target):
    """Expose a read-only input tree to the worktree without copying gigabytes."""
    p = run(["cmd", "/c", "mklink", "/J", str(link), str(target)], capture=True)
    if p.returncode:
        raise RuntimeError(f"could not create junction for {link.name}: {p.stderr or p.stdout}")


@contextmanager
def isolated_worktree():
    """A temporary checkout whose library/database counters may safely change."""
    directory = Path(tempfile.mkdtemp(prefix="repo-diagnosis-library-batch-",
                                      dir=str(ROOT.parent)))
    made_worktree = False
    try:
        p = run(["git", "worktree", "add", "--detach", str(directory), "HEAD"],
                cwd=ROOT, capture=True)
        if p.returncode:
            raise RuntimeError(f"could not create isolated worktree: {p.stderr or p.stdout}")
        made_worktree = True
        # Results are tracked, so a worktree receives a separate checked-out
        # copy. Replace that copy with a junction to the existing diagnostics:
        # this sees uncommitted diagnosed results too and avoids a stale copy.
        shutil.rmtree(directory / "results")
        make_junction(directory / "instances", ROOT / "instances")
        make_junction(directory / "results", ROOT / "results")

        # ab_fix.py normally publishes its own progress marker. The outer
        # wrapper owns the one real marker; this no-op avoids a detached
        # worktree trying to push temporary marker commits to origin.
        (directory / "progress_marker.py").write_text(
            "import contextlib\n\ndef progress_marker(*args, **kwargs):\n"
            "    return contextlib.nullcontext()\n", encoding="ascii")
        yield directory
    finally:
        if made_worktree:
            # Remove junctions themselves, never their targets, before asking
            # Git to delete the temporary checkout.
            for name in ("instances", "results"):
                link = directory / name
                if link.exists():
                    run(["cmd", "/c", "rmdir", str(link)])
            run(["git", "worktree", "remove", "--force", str(directory)], cwd=ROOT)
        elif directory.exists():
            shutil.rmtree(directory, ignore_errors=True)


def load_verdict(worktree, instance, finding, with_library):
    suffix = "-lib" if with_library else ""
    path = worktree / "reports" / f"ab-{instance}-f{finding}.json"
    if not path.exists():
        raise RuntimeError(f"{instance}: ab_fix.py finished without {path.name}")
    data = json.loads(path.read_text(encoding="utf-8"))
    pairs = data.get("pairs", [])
    if len(pairs) != 1:
        raise RuntimeError(f"{instance}: expected one A/B pair, found {len(pairs)}")
    run_data = pairs[0]["on" if with_library else "off"]
    if run_data.get("state") != "completed":
        return None
    return run_data.get("verdict")


def score(verdict):
    """The pre-agreed 0--3 score; failed proof is deliberately not zero."""
    if not verdict or not verdict.get("proof_passed"):
        return "FAILED"
    changed = verdict.get("files_changed") or []
    real = {Path(p).name for p in verdict.get("real_fix_touched") or []}
    touched = {Path(p).name for p, _ in changed}
    return sum((
        verdict.get("attempts") == 1,
        bool(real & touched),
        len(changed) == 1,
    ))


def row(project, enabled, verdict):
    changed = (verdict or {}).get("files_changed") or []
    return {
        "project": project,
        "library": "on" if enabled else "off",
        "passed": "y" if verdict and verdict.get("proof_passed") else "n",
        "attempts": (verdict or {}).get("attempts", "-"),
        # Names can reveal an answer-key file. The report records the requested
        # file-touch information as a count; detailed verdicts stay disposable.
        "files": str(len(changed)),
        "score": score(verdict),
    }


def rate(items, predicate):
    return f"{sum(bool(predicate(x)) for x in items)}/{len(items)}" if items else "n/a"


def average_passing_score(items):
    values = [score(v) for v in items if score(v) != "FAILED"]
    return "n/a" if not values else f"{sum(values) / len(values):.2f}"


def write_report(records):
    on = [r["on"] for r in records]
    off = [r["off"] for r in records]
    offered = [v for v in on if v and v.get("library_offered")]
    credited = [v for v in offered if (v.get("library_entry_used") or "").strip()]
    credited_pairs = [r for r in records
                      if r["on"] in credited]

    rows = []
    for r in records:
        rows += [row(r["project"], True, r["on"]),
                 row(r["project"], False, r["off"])]
    lines = [
        "# First library A/B batch",
        "",
        "Six predeclared practice-pile findings, one per project, each run once",
        "with natural library retrieval and once without it. The fixer ran in an",
        "isolated worktree, so this experiment did not change the real library or",
        "database. `files touched` is a count rather than filenames, to avoid",
        "publishing answer-key material.",
        "",
        "| Project | Library | Passed proof | Attempts | Files touched | Score |",
        "|---|---|---|---:|---:|---|",
    ]
    lines += [f"| {r['project']} | {r['library']} | {r['passed']} | {r['attempts']} | {r['files']} | {r['score']} |" for r in rows]
    lines += [
        "",
        "## Headline numbers",
        "",
        f"- COVERAGE: {rate(on, lambda v: v and v.get('library_offered'))}. "
        "A library entry was offered for this many batch findings.",
        f"- CREDIT RATE: {rate(offered, lambda v: (v.get('library_entry_used') or '').strip())}. "
        "Of findings offered an entry, this many fixer replies said they used one.",
    ]
    if credited_pairs:
        lines += [
            f"- LIFT among credited uses ({len(credited_pairs)} paired finding(s)): "
            f"library on proof pass rate {rate([r['on'] for r in credited_pairs], lambda v: v and v.get('proof_passed'))}; "
            f"library off {rate([r['off'] for r in credited_pairs], lambda v: v and v.get('proof_passed'))}. "
            f"Average score among proof-passing runs: on {average_passing_score([r['on'] for r in credited_pairs])}; "
            f"off {average_passing_score([r['off'] for r in credited_pairs])}.",
        ]
    else:
        lines += ["- LIFT: n/a. No offered entry was claimed as used, so there is no credited use to compare."]
    lines += [
        "",
        "## Manual pairing check",
        "",
        "The credited entries and findings must be read together before any claimed",
        "lift is trusted. This section is completed by the batch reviewer after the",
        "fixer outputs are available.",
        "",
        "## Conclusion",
        "",
        "This first batch measures cost and gives an initial signal only. It is too",
        "small to justify scaling until the credited pairings have passed manual",
        "review and the on/off outcomes are compared.",
        "",
    ]
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="ascii")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="validate and list the fixed batch only")
    a = ap.parse_args()
    validate_batch()
    if a.dry_run:
        print("validated batch:")
        for instance, finding in BATCH:
            print(f"  {instance}, finding {finding}")
        return
    marker = ROOT / "IN-PROGRESS.md"
    if marker.exists():
        raise SystemExit("REFUSING: IN-PROGRESS.md belongs to another active or failed job. "
                         "Do not overlap this batch with it.")

    records = []
    with progress_marker("first library A/B batch, six practice findings",
                         "reports/library-batch-test.md", "~6-12h"):
        with isolated_worktree() as worktree:
            for instance, finding in BATCH:
                print(f"\n===== {instance}, finding {finding} =====", flush=True)
                p = run([sys.executable, "ab_fix.py", "--instance", instance,
                         "--finding", str(finding)], cwd=worktree, timeout=9000,
                        capture=True)
                print(p.stdout, end="")
                print(p.stderr, end="", file=sys.stderr)
                output = (p.stdout or "") + (p.stderr or "")
                if re.search(r"codex CLI not found|access is denied|access-denied", output, re.I):
                    raise RuntimeError("Codex could not be reached. Restart this session with "
                                       "codex --dangerously-bypass-approvals-and-sandbox; do not retry here.")
                if p.returncode:
                    raise RuntimeError(f"{instance}: ab_fix.py exited {p.returncode}")
                records.append({"project": instance.rsplit("-", 1)[0],
                                "on": load_verdict(worktree, instance, finding, True),
                                "off": load_verdict(worktree, instance, finding, False)})
    write_report(records)
    print(f"wrote {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
