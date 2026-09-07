"""Pull raw fix commits out of other projects' git histories.

Every "fix" commit in any open-source project is a solved problem: a diff plus
a message saying why. build_instances.py already finds exactly this - the commit
that fixed a bug - and then throws the fix away to keep the broken version. This
points the same machinery the other way.

This step is FREE. No model, no API, no quota: it is reading git. What comes out
is a raw part - a commit message and a diff - not a library entry. Turning one
into the four-field shape is a separate, metered step (label_parts.py).

Three stores, and it matters which is which:

  mining-cache/  cloned repositories.            not in git (large)
  raw-parts/     extracted commits, with diffs.  not in git (verbatim code)
  library/       labelled shapes, no code.       IN git

raw-parts/ is deliberately excluded from git. It holds other projects' source
code verbatim, and "take the idea, not the code" is not much of a policy if the
code is committed anyway.

THE REFUSAL
-----------
A source that is a corpus project, or anything in BugsInPy/projects/, is
refused outright - not warned about. If the library holds fixes from
cookiecutter and black while the exam papers are cookiecutter and black, the
catch rate rises and means nothing, and every visible sign says it is learning.

Usage:
  python mine_library.py --limit 20            # a small batch, to judge quality
  python mine_library.py --limit 20 --repo pallets/click
  python mine_library.py                       # everything in mining-sources.txt
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

from check_library_clean import banned_projects

ROOT = Path(__file__).parent.resolve()
SOURCES = ROOT / "mining-sources.txt"
CACHE = ROOT / "mining-cache"
RAW = ROOT / "raw-parts"

# A fix commit says a problem was solved. These say something was tidied.
# Measured on a sample of 25 real messages from psf/requests: roughly a third
# were of this kind ("Fix remaining typos", "Fix CI and build failures",
# "Fix httpbin pin for test suite").
NOISE = re.compile(r"""
    typo|spelling|misspell|whitespace|indent|formatting|reformat|lint|flake8|
    black|isort|mypy|pyupgrade|docstring|\bdocs?\b|readme|changelog|comment|
    \bci\b|travis|appveyor|workflow|\bbuild\b|packaging|\bpin\b|bump|
    dependabot|pre-commit|coverage|badge|copyright|licence|license|
    \btests?\b|test\s+suite|testcase|deprecation\s+warning|
    \btype\s+hints?\b|annotations?|
    # added 2026-09-07 after hand-scoring the first 20 mined parts, where these
    # were 3 of the 7 duds. Named lint codes and cosmetic wording get through a
    # blocklist built only from generic words like "lint".
    \bruff\b|\bE\d{3}\b|line-too-long|pyflakes|pylint|codestyle|
    missing\s+space|\balign\b|\blayout\b|cosmetic|wording|
    python_requires|classifiers?\b|
    # second hand-scoring pass: with test-only fixes gone, TYPING churn became
    # the dominant dud - "Fix typing", "fix pyright findings", "Fix issues
    # previously type ignored". These change annotations, not behaviour.
    \btyping\b|pyright|pyre\b|type[- ]ignored?|type:\s*ignore|
    warnings?\s+message|error\s+message
""", re.IGNORECASE | re.VERBOSE)

# A fix that changes only the project's own tests is housekeeping, not a solved
# problem - it was the single largest cause of duds in the first mined batch
# (3 of 7). A fix that changes source AND test is the best kind there is: the
# test is the proof, so those are kept.
TEST_PATH = re.compile(r"(^|/)tests?(/|$)|(^|/)test_[^/]*\.py$|_test\.py$",
                       re.IGNORECASE)
# Packaging and test scaffolding describe how the project is assembled, not how
# it behaves, so nothing in them transfers as a fix shape.
NON_BEHAVIOUR = re.compile(
    r"(^|/)(setup|conftest|conf|_version|version|__about__)\.py$"
    r"|^(docs?|examples?|scripts?|benchmarks?)/",
    re.IGNORECASE)

# The message has to claim a fix. Conventional commits ("fix:", "fix(core):")
# and plain English ("Fix the ...", "Fixes #123") both count.
FIX = re.compile(r"^\s*(bug\s*fix|fix(es|ed)?)\b|^\s*fix\s*\([^)]*\)\s*:",
                 re.IGNORECASE)

MAX_FILES = 3        # one clean idea rarely spans more
MAX_LINES = 50       # a 400-line change labelled "fix" is a refactor, not an idea


def sh(cmd, cwd=None, timeout=1800):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                       errors="replace", stdin=subprocess.DEVNULL,
                       timeout=timeout)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def read_sources():
    if not SOURCES.exists():
        sys.exit(f"missing {SOURCES.name}")
    out = []
    for line in SOURCES.read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            out.append(line)
    return out


def refuse_banned(repos):
    """Refuse, do not warn. Relying on remembering is what the check exists
    to replace."""
    banned = banned_projects()
    if not banned:
        sys.exit("REFUSING: could not read the banned list (MANIFEST.md / "
                 "BugsInPy/projects). A miner that cannot see what it must "
                 "avoid must not run.")
    bad = []
    for r in repos:
        name = r.split("/")[-1].lower()
        if name in banned or r.split("/")[0].lower() in banned:
            bad.append(r)
    if bad:
        sys.exit(f"REFUSING to mine {bad}: these are corpus / BugsInPy "
                 f"projects, and their fixes are the answers to exam papers. "
                 f"Remove them from {SOURCES.name}.")
    return banned


def clone(repo):
    """Cached, and history-only: we never check the working tree out.

    --filter=blob:none fetches file contents lazily, so cloning is fast and
    only the diffs actually kept get downloaded.
    """
    dest = CACHE / repo.replace("/", "__")
    if (dest / "HEAD").exists() or (dest / ".git").exists():
        return dest
    CACHE.mkdir(exist_ok=True)
    print(f"  cloning {repo} ...", flush=True)
    rc, out = sh(["git", "clone", "--quiet", "--filter=blob:none",
                  "--no-checkout", f"https://github.com/{repo}", str(dest)])
    if rc != 0:
        print(f"  !! clone failed: {out.strip()[-200:]}")
        return None
    return dest


def candidate_commits(path):
    """Commits whose message claims a fix and does not look like tidying.

    Uses --name-only, which needs only directory listings, not file contents -
    so this whole pass runs without downloading a single blob.
    """
    rc, out = sh(["git", "-C", str(path), "log", "--no-merges",
                  "--pretty=format:%x1e%H%x1f%s%x1f%b%x1f", "--name-only"])
    if rc != 0:
        return []
    found = []
    for record in out.split("\x1e"):
        if not record.strip():
            continue
        parts = record.split("\x1f")
        if len(parts) < 4:
            continue
        sha, subject, body, files_blob = parts[0], parts[1], parts[2], parts[3]
        if not FIX.search(subject) or NOISE.search(subject):
            continue
        files = [f.strip() for f in files_blob.splitlines() if f.strip()]
        py = [f for f in files if f.endswith(".py")]
        # every changed file must be Python, and few of them: a fix that also
        # edits templates or config is usually several ideas at once
        if not py or len(files) != len(py) or len(py) > MAX_FILES:
            continue
        # at least one changed file must be real source: something that is all
        # tests, or all packaging, changed no behaviour to learn from
        source = [f for f in py
                  if not TEST_PATH.search(f) and not NON_BEHAVIOUR.search(f)]
        if not source:
            continue
        found.append({"sha": sha.strip(), "subject": subject.strip(),
                      "body": body.strip(), "files": py,
                      "source_files": source})
    return found


def fetch_diff(path, sha):
    """The actual change. This is the step that downloads file contents, so it
    runs only for commits that already passed every cheap filter."""
    rc, out = sh(["git", "-C", str(path), "show", sha, "--format=", "--unified=3"])
    return out if rc == 0 else ""


def mine(repo, want, seen):
    path = clone(repo)
    if not path:
        return []
    cands = candidate_commits(path)
    print(f"  {repo}: {len(cands)} candidate commits after message and file "
          f"filters", flush=True)
    kept = []
    for c in cands:
        if len(kept) >= want:
            break
        pid = f"{repo.split('/')[-1]}-{c['sha'][:10]}"
        if pid in seen or (RAW / f"{pid}.json").exists():
            continue
        diff = fetch_diff(path, c["sha"])
        if not diff:
            continue
        changed = sum(1 for line in diff.splitlines()
                      if (line.startswith(("+", "-"))
                          and not line.startswith(("+++", "---"))))
        if changed == 0 or changed > MAX_LINES:
            continue
        kept.append({
            "id": pid,
            "project": repo.split("/")[-1],
            "repo": repo,
            "commit": c["sha"],
            "url": f"https://github.com/{repo}/commit/{c['sha']}",
            "subject": c["subject"],
            "body": c["body"][:2000],
            "files": c["files"],
            "source_files": c["source_files"],
            "has_test": len(c["files"]) > len(c["source_files"]),
            "changed_lines": changed,
            "diff": diff[:20000],
            "labelled": False,
        })
        seen.add(pid)
    print(f"  {repo}: kept {len(kept)} after the size filter", flush=True)
    return kept


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int,
                    help="stop once this many raw parts have been kept")
    ap.add_argument("--repo", action="append",
                    help="mine only this repo, repeatable. Still refused if "
                         "it is a corpus project.")
    ap.add_argument("--per-repo", type=int, default=40,
                    help="cap per repository, so one project cannot dominate")
    a = ap.parse_args()

    repos = a.repo or read_sources()
    refuse_banned(repos)
    RAW.mkdir(exist_ok=True)

    seen = {p.stem for p in RAW.glob("*.json")}
    print(f"{len(repos)} source repo(s); {len(seen)} raw parts already held\n")

    total = []
    for repo in repos:
        if a.limit and len(total) >= a.limit:
            break
        want = a.per_repo
        if a.limit:
            want = min(want, a.limit - len(total))
        got = mine(repo, want, seen)
        for part in got:
            (RAW / f"{part['id']}.json").write_text(
                json.dumps(part, indent=2), encoding="utf-8")
        total += got

    print(f"\nkept {len(total)} new raw parts -> raw-parts/ "
          f"({len(list(RAW.glob('*.json')))} held in total)")
    if total:
        print("\nA raw part is not a library entry. Run label_parts.py to turn "
              "these\ninto fix shapes before anything can retrieve them.")


if __name__ == "__main__":
    main()
