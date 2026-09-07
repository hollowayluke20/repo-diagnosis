"""Build and validate diagnosis test instances from BugsInPy.

An instance only enters the corpus if its known bug is PROVED to reproduce:
the bug's own test must FAIL on the buggy commit. A broken instance and a
genuine miss otherwise produce identical results.

Usage:
  python build_instances.py --bug cookiecutter/1 --bug thefuck/2
  python build_instances.py --bug cookiecutter/1 --fixed   # gate self-test
"""
import argparse, contextlib, json, os, random, re, shlex, shutil, subprocess, sys
from progress_marker import progress_marker
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
BUGSINPY = ROOT / "BugsInPy"
INSTANCES = ROOT / "instances"
KEYS = ROOT.parent / "repo-diagnosis-keys"   # OUTSIDE the repo: an
# agent inside instances/<name> can walk up to the repo root, and the
# answers must not be reachable from there. Verified 2026-09-07 that
# ../../keys/ resolved from inside an instance.
REPORTS = ROOT / "reports"

LEAK_NAMES = re.compile(r"changelog|release[_-]?notes?|history\.(rst|md|txt)|news",
                        re.IGNORECASE)


def sh(cmd, cwd=None, timeout=900):
    """Run a command, return (returncode, combined output)."""
    p = subprocess.run(cmd, cwd=cwd, shell=isinstance(cmd, str),
                       capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL, errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def parse_info(path):
    """BugsInPy .info files are shell-style key="value" lines."""
    out = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = re.match(r'\s*([\w]+)\s*=\s*"?(.*?)"?\s*$', line)
        if m:
            out[m.group(1)] = m.group(2)
    return out


def rm_tree(p):
    """Windows marks .git objects read-only; clear that before deleting."""
    if not p.exists():
        return
    for r, dirs, files in os.walk(p):
        for f in files:
            try:
                os.chmod(os.path.join(r, f), 0o700)
            except OSError:
                pass
    shutil.rmtree(p, ignore_errors=True)


def provision_python(version, dest):
    """Copy a real interpreter INSIDE the instance.

    Not a venv pointing elsewhere: a venv whose base lived in AppData failed
    silently under the agent's sandbox and cost two runs on 2026-09-07.
    Returns (actual_version_used, note) or (None, reason).
    """
    wanted = ".".join(version.split(".")[:2]) if version else "3.9"
    tried = []
    for v in [version, wanted, "3.9", "3.8", "3.10"]:
        if not v or v in tried:
            continue
        tried.append(v)
        rc, out = sh(["python", "-m", "uv", "python", "install", v])
        rc2, path = sh(["python", "-m", "uv", "python", "find", v])
        path = path.strip().splitlines()[-1].strip() if path.strip() else ""
        if path and Path(path).exists():
            src = Path(path).parent
            if dest.exists():
                rm_tree(dest)
            shutil.copytree(src, dest)
            for marker in dest.rglob("EXTERNALLY-MANAGED"):
                marker.unlink(missing_ok=True)
            note = "" if v == version else f"requested {version}, used {v}"
            return v, note
    return None, f"no interpreter available (tried {tried})"


def first_error(out, limit=300):
    """The most informative line, not the last one.

    Slicing the tail of pytest output reliably returns the end of a warnings
    URL rather than the actual error, which hid the real cause of two
    rejections.
    """
    # in priority order - the cause beats the symptom beats the banner
    tiers = (("ModuleNotFoundError", "ImportError", "SyntaxError"),
             ("E   ",),
             ("error:", "unrecognized arguments"),
             ("found no collectors", "no tests ran",
              "file or directory not found"),
             ("ERROR",))
    lines = [l.strip() for l in out.splitlines() if l.strip()]
    # drop pytest's ==== / ____ / !!!! separator bars, which is what the old
    # tail-slicing kept returning instead of the actual error
    lines = [l for l in lines if len(set(l)) > 3]
    for tier in tiers:
        for s in lines:
            if any(m in s for m in tier):
                return s[:limit]
    return (lines[-1] if lines else out.strip())[:limit]


def test_command(bug_dir, py):
    """Honour whichever runner BugsInPy specifies, rather than forcing pytest.

    black, tornado and youtube-dl use `python -m unittest` with DOTTED MODULE
    paths (tests.test_black.BlackTestCase.test_x), which pytest cannot accept
    as a path at all. tqdm uses `python3`, not `python`. Assuming one runner
    cost 12 instances.
    """
    raw = (bug_dir / "run_test.sh").read_text(encoding="utf-8",
                                              errors="replace").strip()
    line = [l for l in raw.splitlines() if l.strip()][-1].strip()
    parts = shlex.split(line)

    # drop a leading interpreter: python, python3, python3.8, and its -m
    if parts and re.fullmatch(r"python\d*(\.\d+)?", parts[0]):
        parts = parts[1:]
        if parts[:1] == ["-m"]:
            parts = parts[1:]
    if not parts:
        return [str(py), "-m", "pytest"], line

    runner, args = parts[0], parts[1:]

    if runner == "unittest":
        # keep its own flags - they are unittest's, and it understands them
        return [str(py), "-m", "unittest"] + args, line

    if runner == "tox":
        # tox is a wrapper that would rebuild its own environment; run the
        # underlying test directly in the interpreter we provisioned
        args = [a for a in args if not a.startswith("-")]
    elif runner not in ("pytest", "py.test"):
        args = parts

    # -o addopts= clears the project's own pytest flags (coverage plugins we
    # have no reason to install); -p no:cacheprovider keeps the folder clean.
    return ([str(py), "-m", "pytest"] + args +
            ["-x", "-q", "-o", "addopts=", "-p", "no:cacheprovider"], line)


def build(spec, at_fixed=False):
    project, bug_id = spec.split("/")
    pdir = BUGSINPY / "projects" / project
    bdir = pdir / "bugs" / bug_id
    info = parse_info(bdir / "bug.info")
    pinfo = parse_info(pdir / "project.info")
    name = f"{project}-{bug_id}" + ("-FIXED" if at_fixed else "")
    inst = INSTANCES / name
    key = {"project": project, "bug_id": bug_id, "instance": name,
           "status": "INVALID", "invalid_reason": None, "files": [], "lines": [],
           "description": "", "failing_test": "", "leak_risks": [],
           "python_version": info.get("python_version", ""),
           "python_used": "", "size_files": 0, "size_lines": 0,
           "pile": random.choices(["practice", "locked"], [0.7, 0.3])[0],
           "built_at_fixed_commit": at_fixed}

    url = pinfo.get("github_url", "")
    commit = info.get("fixed_commit_id" if at_fixed else "buggy_commit_id", "")
    if not url or not commit:
        key["invalid_reason"] = "missing github_url or commit id"
        return key

    # --- clone at the target commit, then destroy the history ---
    if inst.exists():
        rm_tree(inst)
    INSTANCES.mkdir(exist_ok=True)
    rc, out = sh(["git", "clone", "--quiet", url, str(inst)])
    if rc != 0:
        key["invalid_reason"] = "clone failed: " + out.strip()[-200:]
        return key
    rc, out = sh(["git", "checkout", "--quiet", commit], cwd=str(inst))
    if rc != 0:
        key["invalid_reason"] = "checkout failed: " + out.strip()[-200:]
        return key

    # The bug's test is usually ADDED BY THE FIX, so it does not exist on the
    # buggy commit. Overlay it from the fixed commit purely to validate, then
    # take it away again before anything reads this folder - the test's own
    # name routinely states the bug outright.
    test_file = info.get("test_file", "").strip()
    overlaid = False
    existed_before = False
    if test_file and not at_fixed:
        tf = inst / test_file
        existed_before = tf.exists()
        rc, content = sh(["git", "show",
                          f"{info.get('fixed_commit_id','')}:{test_file}"],
                         cwd=str(inst))
        if rc == 0:
            tf.parent.mkdir(parents=True, exist_ok=True)
            tf.write_text(content, encoding="utf-8")
            overlaid = True
    key["test_overlaid_for_validation"] = overlaid

    # --- what is left that might name the bug ---
    key["leak_risks"] = sorted({p.name for p in inst.rglob("*")
                                if p.is_file() and LEAK_NAMES.search(p.name)})

    pyfiles = [p for p in inst.rglob("*.py") if ".python" not in p.parts]
    key["size_files"] = len(pyfiles)
    key["size_lines"] = sum(
        len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        for p in pyfiles)

    # --- a real interpreter, inside the folder ---
    used, note = provision_python(info.get("python_version", ""), inst / ".python")
    if not used:
        key["invalid_reason"] = "python: " + note
        return key
    key["python_used"] = used + ((" (" + note + ")") if note else "")
    py = inst / ".python" / "python.exe"

    sh([str(py), "-m", "pip", "install", "--quiet", "--upgrade", "pip"])
    req = bdir / "requirements.txt"
    if req.exists():
        sh([str(py), "-m", "pip", "install", "--quiet", "-r", str(req)])
    # run 5 reported freezegun/pytest-mock/pytest-cov missing, so the project's
    # own suite could not fully run - the bug's requirements.txt does not cover
    # test extras. Failures here are non-fatal; the gate is what decides.
    # nose is dead but several 2020-era suites still import it (tqdm does).
    # Failures here are non-fatal - the validation gate is what decides.
    sh([str(py), "-m", "pip", "install", "--quiet", "pytest", "ruff",
        "pytest-mock", "pytest-cov", "freezegun", "mock", "pytest-timeout",
        "nose", "parameterized", "pytest-asyncio"])
    for extra in ["requirements-dev.txt", "test_requirements.txt",
                  "requirements/test.txt", "dev-requirements.txt"]:
        if (inst / extra).exists():
            sh([str(py), "-m", "pip", "install", "--quiet", "-r", extra],
               cwd=str(inst))
    sh([str(py), "-m", "pip", "install", "--quiet", "-e", "."], cwd=str(inst))

    # --- THE VALIDATION GATE ---
    cmd, original = test_command(bdir, py)
    key["failing_test"] = original
    try:
        rc, out = sh(cmd, cwd=str(inst), timeout=900)
    except subprocess.TimeoutExpired:
        key["invalid_reason"] = "test run timed out"
        return key

    low = out.lower()
    could_not_run = any(s in low for s in (
        "modulenotfounderror", "importerror", "no tests ran",
        "file or directory not found", "found no collectors",
        "collected 0 items", "unrecognized arguments", "usage: __main__.py"))
    if rc == 0:
        key["invalid_reason"] = ("known test PASSED - bug does not reproduce here"
                                 + (" (expected: built at fixed commit)" if at_fixed else ""))
    elif could_not_run:
        key["invalid_reason"] = "could not run the test: " + first_error(out)
    else:
        # non-zero and it actually ran: the test failed, which is the point
        key["status"] = "VALID"

    # --- put the folder back to the buggy commit, then destroy the history ---
    if overlaid:
        tf = inst / test_file
        if existed_before:
            sh(["git", "checkout", "--", test_file], cwd=str(inst))
        else:
            tf.unlink(missing_ok=True)
    rm_tree(inst / ".git")
    if (inst / ".git").exists():
        key["status"] = "INVALID"
        key["invalid_reason"] = "could not delete .git - history would leak"
        return key
    # Prove the overlay is gone - but ONLY when the test did not exist on the
    # buggy commit. When it did exist, restoring the original is correct and it
    # is *supposed* to remain collectable; checking anyway rejected 4 perfectly
    # good instances. Also pytest-only: --collect-only means nothing to unittest.
    if overlaid and not existed_before and "pytest" in cmd:
        rc2, _ = sh(cmd + ["--collect-only"], cwd=str(inst), timeout=300)
        key["overlay_removed_verified"] = (rc2 != 0)
        if rc2 == 0:
            key["status"] = "INVALID"
            key["invalid_reason"] = "validation test still present after cleanup"
            return key

    # --- the answer, from the patch ---
    patch = bdir / "bug_patch.txt"
    if patch.exists():
        text = patch.read_text(encoding="utf-8", errors="replace")
        key["files"] = sorted({m for m in re.findall(r"^\+\+\+ b?/?(\S+)", text,
                                                     re.M) if m != "/dev/null"})
        key["lines"] = [int(m) for m in re.findall(r"^@@ -(\d+)", text, re.M)]
        key["description"] = text[:1500]
    return key


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bug", action="append", required=True,
                    help="project/bug_id, repeatable")
    ap.add_argument("--fixed", action="store_true",
                    help="build at the FIXED commit - the gate must reject it")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    if a.seed is not None:
        random.seed(a.seed)

    KEYS.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)
    keys = []
    marker = (progress_marker(f"instance build, {len(a.bug)} bugs",
                              "instances/ and keys/",
                              f"~{max(1, len(a.bug)*5//60)}h")
              if len(a.bug) > 3 else contextlib.nullcontext())
    with marker:
     for spec in a.bug:
         print(f"--- building {spec}{' (FIXED commit)' if a.fixed else ''} ...",
               flush=True)
         try:
             k = build(spec, a.fixed)
         except Exception as e:
             k = {"project": spec, "status": "INVALID",
                  "invalid_reason": f"{type(e).__name__}: {e}"}
         keys.append(k)
         (KEYS / f"{k.get('instance', spec.replace('/', '-'))}.json").write_text(
             json.dumps(k, indent=2), encoding="utf-8")
         print(f"    {k['status']}"
               + (f" - {k['invalid_reason']}" if k.get("invalid_reason") else "")
               + (f" [{k.get('pile')}]" if k["status"] == "VALID" else ""))

    valid = [k for k in keys if k["status"] == "VALID"]
    lines = ["# Rejection report", "",
             f"Attempted: {len(keys)}  |  Valid: {len(valid)}  |  "
             f"Rejected: {len(keys) - len(valid)}", "", "## Rejections by reason", ""]
    for k in keys:
        if k["status"] != "VALID":
            lines.append(f"- **{k.get('instance', k.get('project'))}** — "
                         f"{k.get('invalid_reason')}")
    lines += ["", "## Valid instances", ""]
    for k in valid:
        lines.append(f"- **{k['instance']}** — python {k['python_used']}, "
                     f"{k['size_files']} files / {k['size_lines']} lines, "
                     f"pile `{k['pile']}`"
                     + (f", leak risks: {k['leak_risks']}" if k["leak_risks"] else ""))
    (REPORTS / "rejections.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n{len(valid)}/{len(keys)} valid. Report: reports/rejections.md")


if __name__ == "__main__":
    main()
