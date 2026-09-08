"""Shared helpers for the two security checks (Stage 6).

Two checks, deliberately separate, sharing only plumbing:

  check_known_holes.py    - does a declared dependency pin to a version that
                            has a recorded public advisory? A lookup, no AI.
  check_exposed_secrets.py - does the repo text contain something shaped like
                            a real credential? A pattern search, no AI.

Neither check ever claims "this repo is at risk". The strongest thing either
one says is "this exact version has an advisory recorded against it" or "this
exact line matches the shape of a credential".
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
INSTANCES = ROOT / "instances"
REPORTS = ROOT / "reports"
BUGSINPY = ROOT / "BugsInPy"
KEYS = ROOT.parent / "repo-diagnosis-keys"
CACHE = ROOT / "security_cache"


# --------------------------------------------------------------------------
# keys / instance selection  (same rules the other batch scripts use)
# --------------------------------------------------------------------------
def load_keys():
    """Every key file, indexed by instance name."""
    out = {}
    for path in KEYS.glob("*.json"):
        try:
            key = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if "instance" in key:
            out[key["instance"]] = key
    return out


def corpus_keys(all_keys, include_locked=False):
    """The default batch: VALID, real-bug, PRACTICE instances - not
    fixed-commit controls, and not the locked pile unless asked. Mirrors
    check_still_runs.py / run_diagnosis.py so the checks agree on what
    'the corpus' means and never quietly train on held-back instances."""
    out = {}
    for name, k in all_keys.items():
        if k.get("status") != "VALID" or k.get("built_at_fixed_commit"):
            continue
        if not include_locked and k.get("pile") == "locked":
            continue
        out[name] = k
    return out


# --------------------------------------------------------------------------
# reading text that might not be UTF-8
# --------------------------------------------------------------------------
def read_text_guess(path):
    """Return (text, encoding) or (None, reason).

    BugsInPy ships some requirements.txt files as UTF-16 (luigi, black). A
    naive read gives one BOM char and mojibake, which would look like an
    unreadable / obfuscated file and wrongly be called 'undecidable'. So try
    the encodings that actually turn up here before giving up.
    """
    try:
        raw = path.read_bytes()
    except OSError as e:
        return None, f"{type(e).__name__}: {e}"
    if not raw.strip():
        return "", "empty"
    for enc in ("utf-8-sig", "utf-16", "utf-8", "latin-1"):
        try:
            text = raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue
        # a real decode of source/text has no NUL bytes; if it does we picked
        # the wrong codec (or the file is genuinely binary)
        if "\x00" not in text:
            return text, enc
    return None, "no text encoding decoded it cleanly (looks binary)"


# --------------------------------------------------------------------------
# dependency manifest parsing
# --------------------------------------------------------------------------
_NAME = r"[A-Za-z0-9][A-Za-z0-9._-]*"
_REQ_LINE = re.compile(
    rf"^\s*(?P<name>{_NAME})\s*(?:\[[^\]]*\])?\s*(?P<op>===|==|~=|>=|<=|>|<|!=)?\s*"
    rf"(?P<ver>[A-Za-z0-9][A-Za-z0-9._*+!-]*)?")


def normalise_name(name):
    """PEP 503: lowercase, runs of . _ - collapse to a single -."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirements(text):
    """requirements.txt -> list of dicts.

    Each dict: {name, raw_name, version|None, pinned: bool, line}
    pinned means '== x' or '=== x' with a concrete version - the only case
    an advisory lookup can make a claim about.
    """
    deps = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # options and VCS/editable installs carry no queryable version
        if line.startswith("-") or "://" in line:
            if "#egg=" in line:
                egg = line.split("#egg=", 1)[1].split("&")[0].split()[0]
                deps.append({"name": normalise_name(egg), "raw_name": egg,
                             "version": None, "pinned": False,
                             "line": line, "note": "VCS/editable install"})
            continue
        # drop inline comments and environment markers
        line = line.split(" #", 1)[0].split(";", 1)[0].strip()
        m = _REQ_LINE.match(line)
        if not m or not m.group("name"):
            continue
        op, ver = m.group("op"), m.group("ver")
        pinned = op in ("==", "===") and bool(ver) and "*" not in ver
        deps.append({"name": normalise_name(m.group("name")),
                     "raw_name": m.group("name"),
                     "version": ver if pinned else None,
                     "pinned": pinned, "line": raw.strip()})
    return deps


# pinned "name==1.2.3" pairs that appear inside setup.py / setup.cfg /
# pyproject.toml. Unpinned deps there are common and are counted as
# undecidable rather than parsed into a false version.
_PINNED_IN_SOURCE = re.compile(
    rf"['\"]({_NAME})\s*==\s*([A-Za-z0-9][A-Za-z0-9._-]*)['\"]")


def collect_dependencies(instance_name, key):
    """Every declared dependency we can find for one instance.

    Returns (deps, sources, undecidable) where:
      deps        - parsed dependency dicts (see parse_requirements)
      sources     - list of (path, encoding) actually read
      undecidable - list of (path, reason) we could not read
    """
    deps, sources, undecidable = [], [], []
    seen_files = set()

    def take(path, parser):
        if not path.exists() or path in seen_files:
            return
        seen_files.add(path)
        text, enc = read_text_guess(path)
        if text is None:
            undecidable.append((str(path), enc))
            return
        if not text.strip():
            return                      # empty file is not a declared manifest
        sources.append((str(path.relative_to(ROOT) if ROOT in path.parents
                            else path), enc))
        deps.extend(parser(text))

    # 1. the pinned freeze BugsInPy captured for this bug - this is exactly
    #    what build_instances.py installs, so it is the instance's real
    #    dependency set. Primary source.
    if key:
        bug_req = (BUGSINPY / "projects" / key["project"] / "bugs"
                   / str(key["bug_id"]) / "requirements.txt")
        take(bug_req, parse_requirements)

    inst = INSTANCES / instance_name
    # 2. any requirements file shipped inside the repo itself
    if inst.exists():
        for path in sorted(inst.glob("requirements*.txt")):
            take(path, parse_requirements)
        for path in sorted(inst.glob("requirements/*.txt")):
            take(path, parse_requirements)
        for path in sorted(inst.glob("*requirements*.txt")):
            take(path, parse_requirements)
        # 3. best-effort: only pinned == deps out of the packaging files.
        for fname in ("setup.py", "setup.cfg", "pyproject.toml"):
            p = inst / fname
            if not p.exists():
                continue
            text, enc = read_text_guess(p)
            if text is None:
                continue
            found = _PINNED_IN_SOURCE.findall(text)
            if found and p not in seen_files:
                sources.append((str(p.relative_to(ROOT)), enc))
                for name, ver in found:
                    deps.append({"name": normalise_name(name), "raw_name": name,
                                 "version": ver, "pinned": True,
                                 "line": f"{name}=={ver}  (from {fname})"})

    # de-duplicate on (name, version)
    uniq, key_set = [], set()
    for d in deps:
        k = (d["name"], d["version"])
        if k in key_set:
            continue
        key_set.add(k)
        uniq.append(d)
    return uniq, sources, undecidable


# --------------------------------------------------------------------------
# report merge (same pattern check_still_runs.py uses)
# --------------------------------------------------------------------------
def merge_json_report(path, results, key="instance"):
    """Running --only twice must add to the report, not wipe the rest."""
    existing = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = []
    merged = {item[key]: item for item in existing}
    for item in results:
        merged[item[key]] = item
    return [merged[k] for k in sorted(merged)]
