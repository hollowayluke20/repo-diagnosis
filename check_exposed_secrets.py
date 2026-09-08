"""Check 2 of the Stage 6 security check: exposed secrets in the repo text.

Search the actual text of the repository for strings shaped like a real API
key, token, password or private key. This is a pattern search, not a lookup.
Every hit quotes the exact file and line.

This check is dangerous to get wrong in one specific direction. A false alarm
here reads as "you have leaked a credential" - far scarier than "a dependency
is old". Test suites are full of fake example keys ("your-api-key-here", a
variable literally named example_password, AWS's own AKIAIOSFODNN7EXAMPLE)
that match the shape of a real secret and are not one. So a match only
becomes a hit after passing filters that throw out placeholders, doc
examples, and obvious test scaffolding.

Verdicts, per instance:
  HIT     - >=1 line matched a credential shape with a value that survived
            every placeholder / example filter.
  CLEAN   - text was scanned and nothing survived the filters.
  UNKNOWN - no readable text was found to search (everything binary or
            undecodable). "Could not look" is not "looked and found nothing".

Usage:
  python check_exposed_secrets.py
  python check_exposed_secrets.py --only httpie-1
  python check_exposed_secrets.py --self-test
"""
import argparse
import json
import math
import re
import shutil
import tempfile
from pathlib import Path

from security_common import (INSTANCES, REPORTS, ROOT, corpus_keys, load_keys,
                             merge_json_report, read_text_guess)

# --------------------------------------------------------------------------
# what to look at
# --------------------------------------------------------------------------
SKIP_DIRS = {".git", ".python", ".portability-venv", ".portability-venv",
             "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache",
             "node_modules", ".tox", "site-packages", "venv", ".venv",
             "dist", "build", ".eggs"}
SKIP_SUFFIX = {".pyc", ".pyo", ".so", ".dll", ".dylib", ".exe", ".bin",
               ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip",
               ".gz", ".tar", ".whl", ".egg", ".woff", ".woff2", ".ttf",
               ".eot", ".mo", ".pkl", ".pickle", ".npy", ".npz", ".parquet",
               ".jar", ".class", ".wasm", ".map"}
MAX_BYTES = 1_500_000

# path fragments that mean "treat a match here with extra suspicion" - a
# match still counts, but only if it is a provider-shaped pattern, never a
# generic password=... assignment
LOWER_TRUST = ("test", "tests", "conftest", "fixture", "fixtures", "docs/",
               "docs\\", "doc/", "docs_src", "doc_src", "/doc_", "tutorial",
               "example", "examples", "sample", "samples", "demo", "demos",
               "changelog", "changes.rst", "changes.md", "readme", "spec",
               "mock", "stub", "dummy", "factories", "factory", "cert", "certs",
               ".pem", ".key", ".crt", ".cer", ".p12", "_rsa", "id_dsa")


# --------------------------------------------------------------------------
# credential shapes
# --------------------------------------------------------------------------
# (name, compiled regex, high_confidence)
# high_confidence patterns have a shape specific enough that a match is worth
# reporting even from a lower-trust path (a real AKIA... key in a test file is
# still a real key). The known-fake denylist below still applies to them.
PROVIDER_PATTERNS = [
    ("AWS access key id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), True),
    ("GitHub token", re.compile(r"\bgh[posur]_[A-Za-z0-9]{36,}\b"), True),
    ("GitHub fine-grained PAT", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{60,}\b"), True),
    ("Slack token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"), True),
    ("Slack webhook URL", re.compile(r"https://hooks\.slack\.com/services/[A-Za-z0-9/_-]{20,}"), True),
    ("Google API key", re.compile(r"\bAIza[0-9A-Za-z_\-]{35}\b"), True),
    ("Stripe live key", re.compile(r"\b[rs]k_live_[0-9A-Za-z]{24,}\b"), True),
    ("SendGrid key", re.compile(r"\bSG\.[A-Za-z0-9_\-]{22}\.[A-Za-z0-9_\-]{43}\b"), True),
    ("OpenAI key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_\-]{20,}\b"), False),
    ("Twilio API key SID", re.compile(r"\bSK[0-9a-fA-F]{32}\b"), False),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"), True),
    ("JSON Web Token", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b"), False),
]

# generic "<secret-ish name> = '<value>'" - only from normal-trust paths.
# Anchored so the quoted value is the ENTIRE right-hand side: a bare NAME
# then = or :, then a quoted string, then end-of-line / , / ) / } / comment.
# This stops mid-expression matches like  token=' + auth['x']  and
# url = 'http://.../%s?token='.
GENERIC_ASSIGN = re.compile(
    r"""(?:^|[\s,{(])
        (?P<key>[A-Za-z0-9_.\-]*(?:password|passwd|pwd|secret|token|api[_-]?key
        |access[_-]?key|auth[_-]?token|client[_-]?secret|private[_-]?key
        |session[_-]?key|app[_-]?secret|consumer[_-]?secret)[A-Za-z0-9_.\-]*)
        \s*[:=]\s*
        (?P<q>['"])(?P<val>[A-Za-z0-9_.\-=~]{16,120})(?P=q)
        \s*(?:[#,)}\]]|$)""",
    re.IGNORECASE | re.VERBOSE | re.MULTILINE)

# characters that mean "this is a URL / template / expression, not a literal
# credential" - the generic matcher already excludes them from the value, kept
# here for clarity and the provider path
_NOT_A_SECRET = re.compile(r"[/\s{}%<>$()\\]")

# exact values that are famously fake
KNOWN_FAKE = {
    "akiaiosfodnn7example",
    "wjalrxutnfemi/k7mdeng/bpxrficyexamplekey",
    "aws_secret_access_key",
    "0123456789abcdef0123456789abcdef",
}

# substrings that mark a value as a placeholder rather than a live secret
PLACEHOLDER_BITS = (
    "example", "sample", "dummy", "fake", "placeholder", "your", "xxxx",
    "changeme", "change-me", "change_me", "redacted", "replace", "notreal",
    "not-real", "insert", "todo", "fixme", "foobar", "abc123", "123456",
    "password", "passw0rd", "secret", "token", "apikey", "api-key", "api_key",
    "deadbeef", "n/a", "none", "null", "test", "<", ">", "{{", "}}", "${",
    "%(", "getenv", "environ", "process.env", "s3cr3t", "hunter2", "lorem",
    "qwer", "asdf", "zxcv", "qwerty", "1234", "abcd", "aaaa", "0000",
)


def shannon(s):
    if not s:
        return 0.0
    counts = {c: s.count(c) for c in set(s)}
    return -sum((n / len(s)) * math.log2(n / len(s)) for n in counts.values())


def looks_placeholder(value):
    v = value.strip().lower()
    if not v or v in KNOWN_FAKE:
        return True
    if any(bit in v for bit in PLACEHOLDER_BITS):
        return True
    if len(set(v)) <= 3:                       # "aaaaaaaa", "abababab"
        return True
    if re.fullmatch(r"(.)\1*", v):             # one repeated char
        return True
    if re.fullmatch(r"[0-9]+", v):             # all digits
        return True
    if len(v) >= 16 and shannon(v) < 2.6:      # not random enough
        return True
    if re.fullmatch(r"[a-z]+", v) and len(v) >= 12:   # dictionary-ish
        return True
    return False


def redact(secret):
    s = secret.strip()
    if len(s) <= 8:
        return s[0] + "***"
    return f"{s[:4]}...{s[-2:]} ({len(s)} chars)"


# --------------------------------------------------------------------------
# scanning
# --------------------------------------------------------------------------
def scan_file(path, rel, lower_trust):
    """Yield finding dicts for one file."""
    text, enc = read_text_guess(path)
    if text is None:
        return None                            # signal: unreadable
    findings = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if len(line) > 4000:                    # minified / data blob
            continue
        for name, rx, high_conf in PROVIDER_PATTERNS:
            for m in rx.finditer(line):
                token = m.group(0)
                val_for_filter = token
                if name == "Private key block":
                    val_for_filter = "-----begin-private-key-block-marker-----"
                elif looks_placeholder(token):
                    continue
                if token.lower() in KNOWN_FAKE:
                    continue
                if lower_trust and not high_conf:
                    continue
                findings.append({
                    "file": rel, "line": lineno, "kind": name,
                    "confidence": "high" if high_conf else "medium",
                    "match": redact(token),
                    "context": _ctx(line, m.start(), m.end()),
                    "path_trust": "low" if lower_trust else "normal",
                })
        if not lower_trust:
            for m in GENERIC_ASSIGN.finditer(line):
                val = m.group("val")
                if looks_placeholder(val) or _NOT_A_SECRET.search(val):
                    continue
                # a real key/secret literal is high-entropy; dictionary-ish
                # strings ("curatedlists", "defaultpassword") are not
                if shannon(val) < 3.2:
                    continue
                findings.append({
                    "file": rel, "line": lineno,
                    "kind": f"assignment to '{m.group('key')}'",
                    "confidence": "medium",
                    "match": redact(val),
                    "context": _ctx(line, m.start("val"), m.end("val")),
                    "path_trust": "normal",
                })
    return findings


def _ctx(line, start, end):
    """The line with the secret itself masked, trimmed to something printable."""
    masked = line[:start] + "<REDACTED>" + line[end:]
    masked = masked.strip()
    return masked[:200]


def walk_repo(root):
    """Yield (path, relpath) for every candidate text file under root."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in SKIP_SUFFIX:
            continue
        if path.name.endswith(".egg-info") or ".egg-info" in str(path):
            continue
        try:
            if path.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        yield path, str(path.relative_to(root)).replace("\\", "/")


def check_dir(root, label):
    scanned = skipped = 0
    skipped_files = []
    findings = []
    for path, rel in walk_repo(root):
        lower_trust = any(frag in rel.lower() for frag in LOWER_TRUST)
        res = scan_file(path, rel, lower_trust)
        if res is None:
            skipped += 1
            if len(skipped_files) < 25:
                skipped_files.append(rel)
            continue
        scanned += 1
        findings.extend(res)

    # a finding only counts as a HIT if it sits in a normal-trust path. The
    # same shape in tests/ , docs/ , a .pem fixture or a demo is listed for
    # review but does not drive the verdict - that is where fake keys live,
    # and calling those a leak is the cry-wolf failure the brief warns about.
    counted = [f for f in findings if f["path_trust"] == "normal"]
    review = [f for f in findings if f["path_trust"] != "normal"]

    if scanned == 0:
        verdict = "UNKNOWN"
        reason = (f"no readable text file found under {label} "
                  f"({skipped} unreadable/binary)")
    elif counted:
        verdict = "HIT"
        reason = f"{len(counted)} match(es) in normal source paths"
    else:
        verdict = "CLEAN"
        reason = f"scanned {scanned} files, nothing survived in normal paths"
        if review:
            reason += (f"; {len(review)} shape match(es) in "
                       f"test/doc/fixture paths listed for review only")

    return {
        "instance": label,
        "verdict": verdict,
        "reason": reason,
        "files_scanned": scanned,
        "files_unreadable": skipped,
        "unreadable_examples": skipped_files,
        "findings": counted,
        "review_only": review,
    }


# --------------------------------------------------------------------------
# reporting  (raw report is gitignored - it quotes real secrets if any exist)
# --------------------------------------------------------------------------
def write_reports(results):
    REPORTS.mkdir(exist_ok=True)
    jpath = REPORTS / "exposed-secrets.json"
    results = merge_json_report(jpath, results)
    jpath.write_text(json.dumps(results, indent=2), encoding="utf-8")

    counts = {"HIT": 0, "CLEAN": 0, "UNKNOWN": 0}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1

    lines = [
        "# Exposed secrets",
        "",
        "Pattern search over repository text for credential shapes. Matched",
        "values are redacted here; the shape, file and line are not.",
        "",
        f"Instances: {len(results)}  |  HIT: {counts['HIT']}  "
        f"CLEAN: {counts['CLEAN']}  UNKNOWN: {counts['UNKNOWN']}",
        "",
        "| Instance | Verdict | Files scanned | Unreadable | Findings |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for r in results:
        lines.append(f"| {r['instance']} | {r['verdict']} | {r['files_scanned']} "
                     f"| {r['files_unreadable']} | {len(r['findings'])} |")
    lines += ["", "## Detail", ""]
    for r in results:
        lines.append(f"### {r['instance']} - {r['verdict']}")
        lines.append(f"- {r['reason']}")
        if r["unreadable_examples"]:
            lines.append(f"- unreadable (sample): {', '.join(r['unreadable_examples'][:8])}")
        for f in r["findings"]:
            lines.append(f"  - `{f['file']}:{f['line']}` - {f['kind']} "
                         f"[{f['confidence']}] - match `{f['match']}`")
            lines.append(f"    line: `{f['context']}`")
        for f in r.get("review_only", []):
            lines.append(f"  - (review only, {f['path_trust']}-trust path) "
                         f"`{f['file']}:{f['line']}` - {f['kind']} "
                         f"- match `{f['match']}`")
        lines.append("")
    (REPORTS / "exposed-secrets.md").write_text("\n".join(lines) + "\n",
                                                encoding="utf-8")


# --------------------------------------------------------------------------
# self-test
# --------------------------------------------------------------------------
def self_test():
    ok = True
    work = Path(tempfile.mkdtemp(prefix="sec-selftest-"))
    try:
        real = work / "real"
        real.mkdir()
        # planted secrets that SHOULD be caught - shaped like the real thing,
        # values that are not obvious placeholders
        (real / "config.py").write_text(
            "AWS_ACCESS_KEY_ID = 'AKIA' + 'QR7NJS4LMZ9WVBKT'\n"
            "aws_key = 'AKIAQR7NJS4LMZ9WVBKT'\n"
            "GH_TOKEN = 'ghp_1a2B3c4D5e6F7g8H9i0JkLmNoPqRsTuVwXyZ'\n"
            "db_password = 'Rk9wLm2Qz7Xv4Tb8Np1Yc3Hd6Fj0Sg5'\n", encoding="utf-8")
        (real / "deploy_credentials.txt").write_text(
            "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA1a2b3c\n"
            "-----END RSA PRIVATE KEY-----\n", encoding="utf-8")
        r = check_dir(real, "selftest-real")
        kinds = {f["kind"] for f in r["findings"]}
        want = {"AWS access key id", "GitHub token", "Private key block"}
        real_ok = r["verdict"] == "HIT" and want <= kinds
        print("  planted real-shape secrets -> HIT:",
              "PASS" if real_ok else "FAIL",
              f"(found: {sorted(kinds)})")
        ok &= real_ok

        # planted placeholders that MUST NOT be caught
        fake = work / "fake"
        (fake / "tests").mkdir(parents=True)
        (fake / "settings.py").write_text(
            "API_KEY = 'your-api-key-here'\n"
            "example_password = 'changeme'\n"
            "SECRET_KEY = os.environ.get('SECRET_KEY')\n"
            "aws_key = 'AKIAIOSFODNN7EXAMPLE'\n"
            "token = 'xxxxxxxxxxxxxxxx'\n"
            "password = 'password123'\n", encoding="utf-8")
        (fake / "tests" / "test_auth.py").write_text(
            "FAKE_TOKEN = 'ghp_000000000000000000000000000000000000'\n"
            "sample_key = 'AIzaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMYDUM'\n"
            "test_secret = 'aaaaaaaaaaaaaaaaaaaaaaaa'\n", encoding="utf-8")
        r2 = check_dir(fake, "selftest-fake")
        fake_ok = r2["verdict"] == "CLEAN"
        print("  planted placeholders/examples -> CLEAN (no cry wolf):",
              "PASS" if fake_ok else "FAIL",
              f"({len(r2['findings'])} false alarms - want 0)")
        if r2["findings"]:
            for f in r2["findings"]:
                print("     FALSE ALARM:", f["file"], f["line"], f["kind"], f["match"])
        ok &= fake_ok

        # a real-shape private key in a test/cert fixture path -> review only,
        # must NOT by itself make the verdict HIT (this is where test certs live)
        certdir = work / "certfix"
        (certdir / "tests" / "certs").mkdir(parents=True)
        (certdir / "tests" / "certs" / "server.key").write_text(
            "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBg\n"
            "-----END PRIVATE KEY-----\n", encoding="utf-8")
        (certdir / "app.py").write_text("x = 1\n", encoding="utf-8")
        r4 = check_dir(certdir, "selftest-certfix")
        cert_ok = r4["verdict"] == "CLEAN" and len(r4["review_only"]) == 1
        print("  private key in tests/certs -> review only, not HIT:",
              "PASS" if cert_ok else "FAIL",
              f"({r4['verdict']}, {len(r4['review_only'])} review)")
        ok &= cert_ok

        # a directory with only an unreadable binary -> UNKNOWN, not CLEAN
        binonly = work / "binonly"
        binonly.mkdir()
        (binonly / "blob.dat").write_bytes(bytes(range(256)) * 40)
        (binonly / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 200)
        r3 = check_dir(binonly, "selftest-binonly")
        bin_ok = r3["verdict"] == "UNKNOWN"
        print("  nothing readable -> UNKNOWN (not CLEAN):",
              "PASS" if bin_ok else "FAIL", f"({r3['reason']})")
        ok &= bin_ok
    finally:
        shutil.rmtree(work, ignore_errors=True)
    return ok


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--include-locked", action="store_true",
                    help="also run the held-back pile (needs --yes-locked too)")
    ap.add_argument("--yes-locked", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()

    if a.self_test:
        raise SystemExit(0 if self_test() else 1)

    all_keys = load_keys()
    if a.only:
        names = [a.only]
    else:
        if a.include_locked and not a.yes_locked:
            raise SystemExit("refusing to touch the locked pile without "
                             "--yes-locked as well")
        names = sorted(corpus_keys(all_keys, include_locked=a.include_locked))

    results = []
    for name in names:
        inst = INSTANCES / name
        if not inst.exists():
            print(f"--- {name}: no instance directory, skipping")
            continue
        print(f"--- {name} ...", flush=True)
        r = check_dir(inst, name)
        results.append(r)
        write_reports([r])
        print(f"    {r['verdict']}  ({r['reason']})", flush=True)
    print("Report: reports/exposed-secrets.md")


if __name__ == "__main__":
    main()
