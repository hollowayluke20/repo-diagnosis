"""Check whether corpus projects still run on this machine's current Python.

An old project can appear healthy only because its bundled interpreter is old.
This compares its own test command before and after a clean current-Python
install, so a known intentionally failing bug does not mask a portability break.

Usage:
  python check_still_runs.py
  python check_still_runs.py --only httpie-1
  python check_still_runs.py --self-test
"""
import argparse, contextlib, json, re, shutil, subprocess, sys, uuid
from pathlib import Path

from build_instances import first_error, rm_tree, sh, test_command
from progress_marker import progress_marker

ROOT = Path(__file__).parent.resolve()
INSTANCES, REPORTS = ROOT / "instances", ROOT / "reports"
KEYS = ROOT.parent / "repo-diagnosis-keys"
BUGSINPY = ROOT / "BugsInPy"
SCRATCH = ROOT / "portability_scratch"
TEST_EXTRAS = ["pytest", "ruff", "pytest-mock", "pytest-cov", "freezegun",
               "mock", "pytest-timeout", "nose", "parameterized",
               "pytest-asyncio"]
EXTRA_REQUIREMENTS = ["requirements-dev.txt", "test_requirements.txt",
                      "requirements/test.txt", "dev-requirements.txt"]
IGNORE_COPY = shutil.ignore_patterns(".python", ".git", "__pycache__",
                                    ".pytest_cache", ".ruff_cache", "*.pyc")


def run_tests(work, bug_dir, py):
    """Run the declared command and return the signals used by the gate."""
    cmd, declared = test_command(bug_dir, py)
    try:
        rc, out = sh(cmd, cwd=str(work), timeout=900)
    except subprocess.TimeoutExpired:
        return {"ran": False, "failed": None, "returncode": None,
                "command": cmd, "declared_command": declared,
                "error": "test run timed out", "output": ""}
    except OSError as e:
        return {"ran": False, "failed": None, "returncode": None,
                "command": cmd, "declared_command": declared,
                "error": f"{type(e).__name__}: {e}", "output": ""}

    low = out.lower()
    collection_failure = any(marker in low for marker in (
        "modulenotfounderror", "importerror", "syntaxerror", "collected 0 items",
        "no tests ran", "found no collectors"))
    pytest_summary = re.search(r"(?:\d+\s+(?:failed|passed|error|errors)[, ]*)+in\s+",
                               out, re.IGNORECASE)
    unittest_summary = (re.search(r"Ran\s+\d+\s+tests?", out, re.IGNORECASE)
                        or re.search(r"^OK$|^FAILED\s*\(", out, re.MULTILINE))
    ran = bool((pytest_summary or unittest_summary) and not collection_failure)
    failures = sum(int(n) for n in re.findall(r"(\d+)\s+failed\b", out,
                                               re.IGNORECASE))
    failures += sum(int(n) for n in re.findall(r"(\d+)\s+errors?\b", out,
                                                re.IGNORECASE))
    match = re.search(r"FAILED\s*\(([^)]*)\)", out, re.IGNORECASE)
    if match:
        values = re.findall(r"(?:failures|errors)=(\d+)", match.group(1), re.I)
        failures = sum(map(int, values))
    error = "" if ran else first_error(out)
    return {"ran": ran, "failed": failures if ran else None, "returncode": rc,
            "command": cmd, "declared_command": declared, "error": error,
            "output": out}


def scratch_copy(instance, bug_dir, label):
    """Copy an instance without its interpreter or mutable test caches."""
    SCRATCH.mkdir(exist_ok=True)
    work = SCRATCH / f"{instance.name}-{label}-{uuid.uuid4().hex[:8]}"
    shutil.copytree(instance, work, ignore=IGNORE_COPY)
    # Keep the source requirements path alongside the copy without putting
    # answer material in it. Path attributes are not available on pathlib.
    return work


def new_run(instance, bug_dir, label, mutate=None):
    """Execute the NEW side, always removing its disposable copy afterwards."""
    work = scratch_copy(instance, bug_dir, label)
    try:
        # make_current_venv deliberately consumes this ordinary local variable
        # via its explicit parameter instead of provisioning an old interpreter.
        venv = work / ".portability-venv"
        rc, out = sh([sys.executable, "-m", "venv", str(venv)], timeout=900)
        py = venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        if rc != 0 or not py.exists():
            return {"ran": False, "failed": None, "returncode": rc,
                    "command": [], "declared_command": "", "output": out,
                    "error": first_error(out) or "could not create current-Python venv"}
        req = bug_dir / "requirements.txt"
        commands = []
        if req.exists():
            commands.append([str(py), "-m", "pip", "install", "--quiet", "-r", str(req)])
        commands.append([str(py), "-m", "pip", "install", "--quiet", *TEST_EXTRAS])
        for name in EXTRA_REQUIREMENTS:
            if (work / name).exists():
                commands.append([str(py), "-m", "pip", "install", "--quiet", "-r", name])
        commands.append([str(py), "-m", "pip", "install", "--quiet", "-e", "."])
        for cmd in commands:
            rc, out = sh(cmd, cwd=str(work), timeout=900)
            if rc != 0:
                return {"ran": False, "failed": None, "returncode": rc,
                        "command": cmd, "declared_command": "", "output": out,
                        "error": first_error(out)}
        if mutate:
            return mutate(work, py)
        return run_tests(work, bug_dir, py)
    finally:
        rm_tree(work)


def verdict(old, new):
    """Apply Stage 6 in its stated order: no OLD baseline means no claim."""
    if not old["ran"]:
        return "NOT_APPLICABLE"
    if not new["ran"] or new["failed"] > old["failed"]:
        return "BROKEN"
    return "PORTABLE"


def check_one(key):
    instance = INSTANCES / key["instance"]
    bug_dir = BUGSINPY / "projects" / key["project"] / "bugs" / str(key["bug_id"])
    py = instance / ".python" / "python.exe"
    old = run_tests(instance, bug_dir, py)
    new = new_run(instance, bug_dir, "run")
    result = {"instance": key["instance"], "project": key["project"],
              "bug_id": key["bug_id"], "verdict": verdict(old, new),
              "old": old, "new": new}
    result["evidence"] = (old["error"] if result["verdict"] == "NOT_APPLICABLE"
                          else new["error"] if result["verdict"] == "BROKEN" else "")
    return result


def self_test(keys):
    """Prove each verdict branch with mutations confined to disposable copies."""
    key = keys.get("youtube-dl-1") or keys.get("tornado-1") or keys.get("httpie-1") or next(
        iter(sorted(keys.values(), key=lambda k: k["instance"])))
    instance = INSTANCES / key["instance"]
    bug_dir = BUGSINPY / "projects" / key["project"] / "bugs" / str(key["bug_id"])
    old = run_tests(instance, bug_dir, instance / ".python" / "python.exe")
    print(f"self-test source: {key['instance']}")

    def both_failures(work, py):
        target = work / key["project"].replace("-", "_") / "__init__.py"
        if not target.exists():
            target = next(work.rglob("__init__.py"))
        original = target.read_bytes()
        target.write_text("def deliberately_broken(\n", encoding="utf-8")
        syntax_new = run_tests(work, bug_dir, py)
        target.write_bytes(original)
        target.write_text(
            "raise ImportError('self-test removed project dependency')\n",
            encoding="utf-8")
        return syntax_new, run_tests(work, bug_dir, py)

    self_new = new_run(instance, bug_dir, "self-failures", both_failures)
    if isinstance(self_new, tuple):
        syntax_new, dep_new = self_new
    else:
        syntax_new = dep_new = self_new
    syntax_ok = (not syntax_new["ran"] and verdict(old, syntax_new) == "BROKEN"
                 and "syntaxerror" in syntax_new["error"].lower())
    print("  syntax error:", "PASS" if syntax_ok else "FAIL",
          "-", syntax_new["error"] or "test unexpectedly ran")
    dep_ok = (not dep_new["ran"] and verdict(old, dep_new) == "BROKEN"
              and "importerror" in dep_new["error"].lower())
    print("  missing dependency:", "PASS" if dep_ok else "FAIL",
          "-", dep_new["error"] or "test unexpectedly ran")

    corrupt_old = run_tests(instance, bug_dir, instance / ".python" / "missing-python.exe")
    corrupt_verdict = verdict(corrupt_old, {"ran": True, "failed": 0, "error": ""})
    old_ok = not corrupt_old["ran"] and corrupt_verdict == "NOT_APPLICABLE"
    print("  unusable OLD baseline:", "PASS" if old_ok else "FAIL",
          "-", corrupt_old["error"] or "old test unexpectedly ran")
    return syntax_ok and dep_ok and old_ok


def write_reports(results):
    REPORTS.mkdir(exist_ok=True)
    lines = ["# Portability", "", "| Instance | Verdict | OLD failed | NEW failed | Evidence |",
             "| --- | --- | ---: | ---: | --- |"]
    for item in results:
        def number(run):
            return str(run["failed"]) if run["failed"] is not None else "-"
        evidence = item["evidence"].replace("|", "\\|")
        lines.append(f"| {item['instance']} | {item['verdict']} | {number(item['old'])} | "
                     f"{number(item['new'])} | {evidence} |")
    (REPORTS / "portability.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (REPORTS / "portability_detail.json").write_text(json.dumps(results, indent=2),
                                                       encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="run one VALID instance")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    keys = {key["instance"]: key for key in
            (json.loads(path.read_text(encoding="utf-8")) for path in KEYS.glob("*.json"))
            if key.get("status") == "VALID" and not key.get("built_at_fixed_commit")}
    if a.self_test:
        raise SystemExit(0 if self_test(keys) else 1)
    if a.only:
        if a.only not in keys:
            raise SystemExit(f"not a valid, non-fixed instance: {a.only}")
        selected = [keys[a.only]]
    else:
        selected = [keys[name] for name in sorted(keys)]
    marker = (progress_marker(f"portability batch, {len(selected)} instances",
                              "reports/portability.*", f"~{len(selected) * 5 // 60 + 1}h")
              if len(selected) > 6 else contextlib.nullcontext())
    results = []
    with marker:
        for key in selected:
            print(f"--- checking {key['instance']} ...", flush=True)
            item = check_one(key)
            results.append(item)
            print(f"    {item['verdict']} (old failed: {item['old']['failed']}, "
                  f"new failed: {item['new']['failed']})", flush=True)
    write_reports(results)
    print("Report: reports/portability.md")


if __name__ == "__main__":
    main()
