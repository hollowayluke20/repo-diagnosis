"""The library and the database: two folders, deliberately never merged.

  library/    fix shapes mined from other projects' git histories. Large, free,
              UNVERIFIED. This is where the system goes looking.
  database/   shapes that have actually worked on a real repository, with the
              evidence attached. This is what makes the system smarter.

An entry moves library/ -> database/ by being USED AND PROVEN, never by being
found and never by being popular. Promotion is a literal file move, so the two
stores can be counted and cannot quietly become one.

An entry is a SHAPE, not a diff. Ideas are not copyrightable, specific code is,
and an idea transfers to another codebase where a patch does not. So an entry
carries a problem description and an approach in words, and no source code.

Two tallies per entry, and only one of them promotes:

  retrieved  how often it was offered as a candidate  -> popularity, NOT evidence
  worked     how often a fix that USED it passed the proof -> evidence

Keeping them apart is the point. An entry retrieved constantly that never works
is a bad match rule, and the ratio is what says so.

Search is deliberately dumb - lowercased word overlap against the problem text.
Anything cleverer waits until this can be SHOWN failing.
"""
import re, shutil
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
LIBRARY = ROOT / "library"
DATABASE = ROOT / "database"

# Proven on this many DIFFERENT repositories before promotion. One success is
# indistinguishable from luck or from a coincidental match.
PROVEN_BAR = 3

# Words carried by nearly every finding, so they separate nothing. Dropping them
# is the whole job of a stopword list.
STOP = set("""
a an the and or but if then than that this these those is are was were be been
being do does did doing have has had having it its of in on at to from by for
with without into over under not no so such only own same too very can could
will would should just now when where which who what how why while during since
because as also may might must us we you your our their there here any all each
both more most other some no nor own s t don should've now
raise raises raised raising error errors fail fails failed failing failure
exception exceptions bug bugs defect defects issue issues problem problems fix
fixes fixed code line lines file files function functions method methods class
classes value values return returns returned instead expected actual trigger
""".split())

WORD = re.compile(r"[a-z][a-z0-9_]{2,}")


def _tokens(text):
    """Lowercase words of 3+ characters, minus the ones that separate nothing."""
    return {w for w in WORD.findall((text or "").lower()) if w not in STOP}


def _parse(path):
    """Entries are markdown with a simple `key: value` header block.

    Hand-rolled rather than pulling in a YAML parser: the header is four flat
    string fields and two counters, and a dependency for that is not worth it.
    """
    raw = path.read_text(encoding="utf-8", errors="replace")
    meta, body = {}, raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            for line in parts[1].splitlines():
                m = re.match(r"\s*([a-z_]+)\s*:\s*(.*?)\s*$", line)
                if m:
                    meta[m.group(1)] = m.group(2)
            body = parts[2]
    e = {
        "id": path.stem,
        "path": path,
        "store": path.parent.name,
        "status": meta.get("status", "found"),
        "source_project": meta.get("source_project", ""),
        "source_commit": meta.get("source_commit", ""),
        "source_url": meta.get("source_url", ""),
        "tags": [t for t in meta.get("tags", "").split(",") if t.strip()],
        "retrieved": int(meta.get("retrieved", "0") or 0),
        "worked": int(meta.get("worked", "0") or 0),
        "proven_on": [s for s in meta.get("proven_on", "").split(",") if s.strip()],
        "body": body.strip(),
    }
    e["problem"] = _section(body, "Problem")
    e["fix_shape"] = _section(body, "Fix shape")
    return e


def _section(body, name):
    m = re.search(rf"^##\s*{re.escape(name)}\s*$(.*?)(?=^##\s|\Z)",
                  body, re.M | re.S)
    return m.group(1).strip() if m else ""


def _write(e):
    """Rewrite an entry in place, header first. Keeps the body untouched."""
    head = (f"---\n"
            f"status: {e['status']}\n"
            f"source_project: {e['source_project']}\n"
            f"source_commit: {e['source_commit']}\n"
            f"source_url: {e['source_url']}\n"
            f"tags: {','.join(e['tags'])}\n"
            f"retrieved: {e['retrieved']}\n"
            f"worked: {e['worked']}\n"
            f"proven_on: {','.join(e['proven_on'])}\n"
            f"---\n\n")
    e["path"].write_text(head + e["body"].strip() + "\n", encoding="utf-8")


def _entry_files(folder):
    """Every *.md in a store except its own README, which is documentation and
    would otherwise be parsed as an entry and matched against queries."""
    if not folder.exists():
        return []
    return [p for p in sorted(folder.glob("*.md")) if p.stem.lower() != "readme"]


def load_all():
    """Every entry in both stores. Database first - proven outranks unproven."""
    out = []
    for folder in (DATABASE, LIBRARY):
        out += [_parse(p) for p in _entry_files(folder)]
    return out


def query_from_finding(f):
    """The words we search on, taken from how the defect was described."""
    return " ".join(str(f.get(k, "")) for k in
                    ("what_goes_wrong", "trigger", "expected", "actual", "file"))


# A single shared word is not a match. Measured 2026-09-07 against 15 real
# findings and 3 entries: every one-word hit was junk - a CPU-count crash
# matched a text-encoding entry on "fallback", an IndexError matched a
# path-traversal entry on "containing". Provisional, and to be re-measured once
# the library holds mined entries rather than three hand-written ones.
MIN_OVERLAP = 2


def search(query, limit=3, entries=None):
    """Plain word overlap against the problem text. Returns [(entry, score)].

    Proven entries win ties: the database is the shelf of parts already known
    to fit, so at equal evidence of relevance it is the safer suggestion.

    Returning nothing is a legitimate and important answer. A store that always
    offers its best guess cannot tell "I have something for this" apart from
    "this is the least irrelevant thing I hold", and the second one wastes the
    fixer's attention on a wrong idea.
    """
    qt = _tokens(query)
    if not qt:
        return []
    scored = []
    for e in (load_all() if entries is None else entries):
        # Problem text plus tags only. The FIX SHAPE is deliberately excluded:
        # at search time we are holding a problem, and a problem description
        # resembles another problem description, not a description of a cure.
        # Matching symptoms against treatments is how retrieval quietly
        # underperforms - so the fix rides along once found, and is never what
        # the match is made on.
        et = _tokens(e["problem"] + " " + " ".join(e["tags"]))
        overlap = qt & et
        if len(overlap) < MIN_OVERLAP:
            continue
        # normalise by entry length so a rambling entry cannot win on bulk alone
        score = len(overlap) / (len(et) ** 0.5 or 1)
        scored.append((e, round(score, 4), sorted(overlap)))
    scored.sort(key=lambda r: (r[1], r[0]["store"] == "database"), reverse=True)
    return scored[:limit]


def as_prompt_section(hits):
    """Candidate approaches, in words, for injection into the fixer's prompt.

    No code is included, by design - "take the idea, not the code". The fixer is
    told to say which one it used so credit can be attributed to a single entry
    rather than smeared across everything that happened to be offered.
    """
    if not hits:
        return ""
    lines = ["",
             "APPROACHES THAT HAVE WORKED ELSEWHERE",
             "",
             "These are descriptions of how similar problems were solved in other",
             "projects. They are ideas, not code, and they may not fit. Judge them.",
             "Adapt anything you use to this codebase - do not copy it in.",
             ""]
    for e, score, _ in hits:
        status = ("PROVEN - has fixed this shape of problem before"
                  if e["store"] == "database" else "UNPROVEN - never yet tested")
        lines += [f"[{e['id']}]  ({status})",
                  f"  Problem:   {e['problem']}",
                  f"  Fix shape: {e['fix_shape']}",
                  f"  Source:    {e['source_project']} {e['source_commit'][:10]}",
                  ""]
    lines += ["If you used one of these ideas, put its [id] in the",
              "library_entry_used field. If you solved it another way, or none of",
              "them fitted, leave that field empty. An honest empty is worth more",
              "than a credit that is not true.", ""]
    return "\n".join(lines)


def record_retrieved(hits):
    for e, _, _ in hits:
        e["retrieved"] += 1
        _write(e)


def record_worked(entry_id, instance):
    """Credit a single entry for a fix that PASSED the proof, then promote if
    it has now done so on enough different repositories."""
    for e in load_all():
        if e["id"] != entry_id:
            continue
        e["worked"] += 1
        repo = instance.rsplit("-", 1)[0]      # cookiecutter-1 -> cookiecutter
        if repo not in e["proven_on"]:
            e["proven_on"].append(repo)
        promoted = False
        if e["store"] == "library" and len(e["proven_on"]) >= PROVEN_BAR:
            e["status"] = "proven"
            DATABASE.mkdir(exist_ok=True)
            _write(e)
            shutil.move(str(e["path"]), str(DATABASE / e["path"].name))
            promoted = True
        else:
            _write(e)
        return e, promoted
    return None, False


def stats():
    return {"library": len(_entry_files(LIBRARY)),
            "database": len(_entry_files(DATABASE))}


if __name__ == "__main__":
    import argparse, json
    ap = argparse.ArgumentParser(description="inspect the stores")
    ap.add_argument("--search", help="free text to search for")
    ap.add_argument("--limit", type=int, default=5)
    a = ap.parse_args()
    print(json.dumps(stats()))
    if a.search:
        for e, score, overlap in search(a.search, a.limit):
            print(f"\n{score:>7}  [{e['store']}] {e['id']}"
                  f"  (retrieved {e['retrieved']}, worked {e['worked']})")
            print(f"         matched on: {', '.join(overlap)}")
            print(f"         {e['problem'][:150]}")
