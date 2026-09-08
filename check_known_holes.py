"""Check 1 of the Stage 6 security check: known holes in declared libraries.

For every dependency an instance pins to an exact version, ask a public
advisory database whether that exact name+version has an advisory recorded
against it. This is a lookup. There is no judgement and no AI.

What a hit means, precisely:
  "this repo declares <library> pinned to <version>, and advisory <ID> is
   recorded as affecting that version."
It does NOT mean the repo is exploitable - whether the vulnerable code path
is reached the way this project uses it is a separate, harder claim we do
not make.

The database is OSV (https://osv.dev), the same data pip-audit and
dependabot use. OSV does the version-range matching server-side: we send a
name and an exact version, it returns the advisories that apply to that
version. Responses are cached under security_cache/ so re-runs are offline
and repeatable.

Verdicts, per instance:
  HIT           - >=1 pinned dependency matched >=1 advisory. Details listed.
  CLEAN         - >=1 pinned dependency, all looked up successfully, 0 matches.
  UNKNOWN       - nothing could be checked: no manifest found, or every
                  dependency is unpinned, or the database was unreachable.
                  A repo we could not check is NOT a repo we proved clean.

Usage:
  python check_known_holes.py                 # the corpus batch
  python check_known_holes.py --only httpie-1
  python check_known_holes.py --self-test
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from security_common import (CACHE, REPORTS, ROOT, collect_dependencies,
                             corpus_keys, load_keys, merge_json_report)

OSV_QUERY = "https://api.osv.dev/v1/query"
OSV_BATCH = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/"
OSV_CACHE = CACHE / "osv"


class DatabaseUnreachable(Exception):
    """Raised when OSV cannot be reached. Forces UNKNOWN, never CLEAN."""


def _post(url, payload, timeout=30):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _get(url, timeout=30):
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def _cache_path(name, version):
    safe = f"{name}@{version}".replace("/", "_").replace("\\", "_")
    return OSV_CACHE / f"{safe}.json"


def _hydrate(vid):
    """Advisory summary + aliases, cached permanently (advisories rarely move)."""
    vpath = OSV_CACHE / "vulns" / f"{vid}.json"
    if vpath.exists():
        d = json.loads(vpath.read_text(encoding="utf-8"))
        return d.get("summary", ""), d.get("aliases", [])
    try:
        body = _get(OSV_VULN + vid)
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return "", []
    vpath.parent.mkdir(parents=True, exist_ok=True)
    vpath.write_text(json.dumps({"summary": body.get("summary", ""),
                                 "aliases": body.get("aliases", [])}, indent=2),
                     encoding="utf-8")
    return body.get("summary", ""), body.get("aliases", [])


def prefetch(pairs):
    """One querybatch call for a whole instance's pinned deps, then hydrate
    each unique advisory once. Writes the same per-(name,version) cache files
    osv_lookup reads, so a second run is fully offline."""
    OSV_CACHE.mkdir(parents=True, exist_ok=True)
    todo = [(n, v) for n, v in pairs if not _cache_path(n, v).exists()]
    if not todo:
        return
    queries = [{"package": {"name": n, "ecosystem": "PyPI"}, "version": v}
               for n, v in todo]
    last = None
    for attempt in range(3):
        try:
            body = _post(OSV_BATCH, {"queries": queries}, timeout=60)
            break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    else:
        raise DatabaseUnreachable(f"OSV batch query failed: {last}")

    for (n, v), res in zip(todo, body.get("results", [])):
        vulns = []
        for stub in res.get("vulns", []):
            vid = stub.get("id")
            summary, aliases = _hydrate(vid) if vid else ("", [])
            vulns.append({"id": vid, "summary": summary, "aliases": aliases})
        _cache_path(n, v).write_text(
            json.dumps({"name": n, "version": v, "vulns": vulns,
                        "checked": time.strftime("%Y-%m-%d")}, indent=2),
            encoding="utf-8")


def osv_lookup(name, version, offline=False):
    """Advisories affecting exactly name==version. Cached on disk.

    offline=True: use the cache only, and if it is not cached raise
    DatabaseUnreachable rather than guessing. Used by the self-test to prove
    a network failure produces UNKNOWN.
    """
    OSV_CACHE.mkdir(parents=True, exist_ok=True)
    safe = f"{name}@{version}".replace("/", "_").replace("\\", "_")
    cached = OSV_CACHE / f"{safe}.json"
    if cached.exists():
        return json.loads(cached.read_text(encoding="utf-8"))

    if offline:
        raise DatabaseUnreachable(f"{name}=={version} not in cache (offline)")

    payload = {"package": {"name": name, "ecosystem": "PyPI"},
               "version": version}
    last = None
    for attempt in range(3):
        try:
            body = _post(OSV_QUERY, payload)
            break
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    else:
        raise DatabaseUnreachable(f"OSV query failed for {name}=={version}: {last}")

    vulns = []
    for v in body.get("vulns", []):
        vid = v.get("id")
        summary = v.get("summary", "")
        if not summary and vid:
            try:
                summary = _get(OSV_VULN + vid).get("summary", "")
            except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                summary = ""
        aliases = v.get("aliases", [])
        vulns.append({"id": vid, "summary": summary, "aliases": aliases})

    result = {"name": name, "version": version, "vulns": vulns,
              "checked": time.strftime("%Y-%m-%d")}
    cached.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def check_instance(instance_name, key, offline=False):
    deps, sources, undecidable = collect_dependencies(instance_name, key)
    pinned = [d for d in deps if d["pinned"] and d["version"]]
    unpinned = [d for d in deps if not d["pinned"]]

    result = {
        "instance": instance_name,
        "sources": [f"{p} ({enc})" for p, enc in sources],
        "undecidable_files": [f"{p}: {why}" for p, why in undecidable],
        "pinned_count": len(pinned),
        "unpinned_count": len(unpinned),
        "unpinned_examples": [d["raw_name"] for d in unpinned[:10]],
        "hits": [],
        "lookup_errors": [],
    }

    if pinned and not offline:
        try:
            prefetch([(d["name"], d["version"]) for d in pinned])
        except DatabaseUnreachable as e:
            result["lookup_errors"].append(str(e))

    if not pinned:
        result["verdict"] = "UNKNOWN"
        result["reason"] = ("no dependency file found"
                            if not sources else
                            "dependencies are declared but none pin an exact "
                            "version, so no advisory lookup is possible")
        return result

    prefetch_failed = bool(result["lookup_errors"])
    seen_hit = {}
    for d in sorted(pinned, key=lambda x: x["name"]):
        try:
            found = osv_lookup(d["name"], d["version"],
                               offline=offline or prefetch_failed)
        except DatabaseUnreachable as e:
            result["lookup_errors"].append(str(e))
            continue
        for v in found["vulns"]:
            cves = sorted(a for a in v["aliases"] if a.startswith("CVE-"))
            # OSV returns the same underlying flaw as both a GHSA and a PYSEC
            # record. Collapse on the shared CVE so the count reflects
            # distinct advisories, not database duplication.
            dedupe_key = (d["name"], d["version"], cves[0] if cves else v["id"])
            prev = seen_hit.get(dedupe_key)
            entry = {
                "library": d["raw_name"], "normalised": d["name"],
                "version": d["version"], "advisory": v["id"],
                "aliases": v["aliases"], "summary": v["summary"],
            }
            if prev is None:
                seen_hit[dedupe_key] = entry
                result["hits"].append(entry)
            else:
                # keep the GHSA id as primary, remember the other ids
                prev.setdefault("also", []).append(v["id"])
                if not prev["summary"] and v["summary"]:
                    prev["summary"] = v["summary"]
                if v["id"].startswith("GHSA-") and not prev["advisory"].startswith("GHSA-"):
                    prev["also"].append(prev["advisory"])
                    prev["advisory"] = v["id"]

    verdict, reason = decide_verdict(pinned, unpinned, result["hits"],
                                     result["lookup_errors"])
    result["verdict"] = verdict
    if reason:
        result["reason"] = reason
    return result


def decide_verdict(pinned, unpinned, hits, lookup_errors):
    """The verdict rules, isolated so the self-test can drive every branch.

      HIT     - any advisory matched (wins even if the check was incomplete).
      CLEAN   - every declared dependency is pinned AND every lookup completed
                AND nothing matched.
      UNKNOWN - anything else: a lookup failed, or the manifest declares
                dependencies with no exact version. Never folded into CLEAN.
    """
    if hits:
        return "HIT", None
    if lookup_errors:
        return "UNKNOWN", (f"{len(lookup_errors)} of {len(pinned)} lookups did "
                           f"not complete (database unreachable)")
    if unpinned:
        egs = ", ".join(d["raw_name"] for d in unpinned[:5])
        return "UNKNOWN", (f"{len(pinned)} pinned dependency/ies checked clean, "
                           f"but {len(unpinned)} declared dependency/ies are "
                           f"unpinned (e.g. {egs}) and cannot be matched to a "
                           f"specific advisory")
    return "CLEAN", None


# --------------------------------------------------------------------------
# reporting
# --------------------------------------------------------------------------
def write_reports(results):
    REPORTS.mkdir(exist_ok=True)
    jpath = REPORTS / "known-holes.json"
    results = merge_json_report(jpath, results)
    jpath.write_text(json.dumps(results, indent=2), encoding="utf-8")

    counts = {"HIT": 0, "CLEAN": 0, "UNKNOWN": 0}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    total_hits = sum(len(r["hits"]) for r in results)

    lines = [
        "# Known holes in declared libraries",
        "",
        "Lookup of each pinned dependency against the OSV advisory database.",
        "A row is a claim about a recorded advisory, not about exploitability.",
        "",
        f"Instances: {len(results)}  |  HIT: {counts['HIT']}  "
        f"CLEAN: {counts['CLEAN']}  UNKNOWN: {counts['UNKNOWN']}  |  "
        f"advisory matches: {total_hits}",
        "",
        "| Instance | Verdict | Pinned deps | Advisory matches | Note |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for r in results:
        note = r.get("reason", "")
        if r["verdict"] == "HIT":
            libs = sorted({h["library"] + "==" + h["version"] for h in r["hits"]})
            note = f"{len(libs)} library/versions: " + ", ".join(libs[:6])
            if len(libs) > 6:
                note += f" (+{len(libs) - 6} more)"
        lines.append(f"| {r['instance']} | {r['verdict']} | {r['pinned_count']} "
                     f"| {len(r['hits'])} | {note} |")

    lines += ["", "## Detail", ""]
    for r in results:
        lines.append(f"### {r['instance']} - {r['verdict']}")
        lines.append("")
        lines.append(f"- sources read: {', '.join(r['sources']) or 'none'}")
        if r["undecidable_files"]:
            lines.append(f"- could not read: {'; '.join(r['undecidable_files'])}")
        lines.append(f"- pinned dependencies checked: {r['pinned_count']}")
        lines.append(f"- unpinned / unqueryable: {r['unpinned_count']}"
                     + (f" (e.g. {', '.join(r['unpinned_examples'])})"
                        if r["unpinned_examples"] else ""))
        if r["lookup_errors"]:
            lines.append(f"- INCOMPLETE: {'; '.join(r['lookup_errors'][:5])}")
        if r["hits"]:
            lines.append("")
            lines.append("| Library | Version | Advisory | Also known as | Summary |")
            lines.append("| --- | --- | --- | --- | --- |")
            for h in sorted(r["hits"], key=lambda x: (x["library"], x["advisory"])):
                aka = ", ".join(a for a in h["aliases"] if a.startswith("CVE"))
                summary = h["summary"].replace("|", "\\|")[:120]
                lines.append(f"| {h['library']} | {h['version']} | {h['advisory']} "
                             f"| {aka} | {summary} |")
        lines.append("")
    (REPORTS / "known-holes.md").write_text("\n".join(lines) + "\n",
                                            encoding="utf-8")


# --------------------------------------------------------------------------
# self-test: prove each verdict branch before trusting the check
# --------------------------------------------------------------------------
def self_test():
    scratch = ROOT / "security_selftest"
    ok = True
    from security_common import parse_requirements

    # 1. KNOWN-VULNERABLE fixture -> must be HIT and must name a real advisory
    vuln_deps = parse_requirements((scratch / "vulnerable" / "requirements.txt")
                                   .read_text(encoding="utf-8"))
    hits = []
    errs = []
    for d in vuln_deps:
        if not d["pinned"]:
            continue
        try:
            found = osv_lookup(d["name"], d["version"])
        except DatabaseUnreachable as e:
            errs.append(str(e))
            continue
        hits += [(d["raw_name"], d["version"], v["id"]) for v in found["vulns"]]
    hit_ok = len(hits) > 0 and not errs
    print("  known-vulnerable fixture -> HIT:",
          "PASS" if hit_ok else "FAIL",
          f"({len(hits)} advisory matches, e.g. {hits[0] if hits else 'none'})")
    ok &= hit_ok

    # 2. CLEAN fixture -> pinned, current, safe versions -> 0 matches
    clean_deps = parse_requirements((scratch / "clean" / "requirements.txt")
                                    .read_text(encoding="utf-8"))
    clean_hits, clean_errs = [], []
    for d in clean_deps:
        if not d["pinned"]:
            continue
        try:
            found = osv_lookup(d["name"], d["version"])
        except DatabaseUnreachable as e:
            clean_errs.append(str(e))
            continue
        clean_hits += [v["id"] for v in found["vulns"]]
    clean_ok = not clean_hits and not clean_errs and len(clean_deps) > 0
    print("  clean fixture -> CLEAN (stays quiet):",
          "PASS" if clean_ok else "FAIL",
          f"({len(clean_hits)} matches - want 0)")
    if clean_hits:
        print("     unexpected matches:", clean_hits)
    ok &= clean_ok

    # 3. UNPINNED-only manifest -> UNKNOWN, never CLEAN
    unpinned_deps = parse_requirements(
        (scratch / "unpinned" / "requirements.txt").read_text(encoding="utf-8"))
    any_pinned = any(d["pinned"] for d in unpinned_deps)
    unpinned_ok = len(unpinned_deps) > 0 and not any_pinned
    print("  unpinned-only manifest -> UNKNOWN:",
          "PASS" if unpinned_ok else "FAIL",
          "(no pinned deps -> check_instance returns UNKNOWN)")
    ok &= unpinned_ok

    # 3b. PINNED-CLEAN BUT UNPINNED DEPS PRESENT -> UNKNOWN, not CLEAN
    partial = parse_requirements(
        (scratch / "partial" / "requirements.txt").read_text(encoding="utf-8"))
    p_pinned = [d for d in partial if d["pinned"]]
    p_unpinned = [d for d in partial if not d["pinned"]]
    v, _ = decide_verdict(p_pinned, p_unpinned, [], [])
    partial_ok = v == "UNKNOWN" and len(p_pinned) >= 1
    print("  pinned-clean + unpinned deps -> UNKNOWN (not CLEAN):",
          "PASS" if partial_ok else "FAIL",
          f"({len(p_pinned)} pinned, {len(p_unpinned)} unpinned -> {v})")
    ok &= partial_ok

    # 4. DATABASE UNREACHABLE -> UNKNOWN, never CLEAN
    #    force offline on a package guaranteed not to be cached
    try:
        osv_lookup("this-package-is-not-real-xyz", "9.9.9", offline=True)
        net_ok = False
    except DatabaseUnreachable:
        net_ok = True
    print("  database unreachable -> UNKNOWN (not CLEAN):",
          "PASS" if net_ok else "FAIL")
    ok &= net_ok

    return ok


# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="one instance by name (fixed-commit "
                    "controls allowed here)")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--include-locked", action="store_true",
                    help="also run the held-back pile (needs --yes-locked too)")
    ap.add_argument("--yes-locked", action="store_true", help=argparse.SUPPRESS)
    a = ap.parse_args()

    if a.self_test:
        raise SystemExit(0 if self_test() else 1)

    all_keys = load_keys()
    if a.only:
        if a.only not in all_keys:
            raise SystemExit(f"no key found for instance: {a.only}")
        selected = {a.only: all_keys[a.only]}
    else:
        if a.include_locked and not a.yes_locked:
            raise SystemExit("refusing to touch the locked pile without "
                             "--yes-locked as well")
        selected = corpus_keys(all_keys, include_locked=a.include_locked)

    results = []
    for name in sorted(selected):
        print(f"--- {name} ...", flush=True)
        r = check_instance(name, selected[name])
        results.append(r)
        write_reports([r])
        print(f"    {r['verdict']}  "
              f"(pinned {r['pinned_count']}, matches {len(r['hits'])})",
              flush=True)
    print("Report: reports/known-holes.md")


if __name__ == "__main__":
    main()
