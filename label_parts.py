"""Turn raw mined commits into library entries: the shape, not the code.

Mining is free - it reads git. This step is the metered one: a model has to
read each diff and write what the problem WAS, in words that transfer to a
codebase that shares none of this project's names.

That is why it runs on a small batch first. The field format is an untested
guess, and labelling at scale before retrieval has been shown to work would
lock in a format that costs the whole run again to change.

The labeller may also REFUSE a part. Mechanical filters catch fixes to tests,
to typing and to docs, but they cannot catch "this is cosmetic" or "this is
too specific to transfer". A model reading the diff can, and a refusal here is
cheaper than a useless entry retrieved forever afterwards.

Tags are deliberately FREE-FORM. A fixed list of categories invented before
seeing 200 entries is a guess, and the expensive kind: changing it later means
relabelling everything. Let the clusters appear first, then name them.

Usage:
  python label_parts.py --limit 20
  python label_parts.py --limit 5 --dry-run    # show a prompt, spend nothing
"""
import argparse, contextlib, json, shutil, subprocess, sys
from pathlib import Path

import library
from progress_marker import progress_marker

ROOT = Path(__file__).parent.resolve()
RAW = ROOT / "raw-parts"
SCRATCH = ROOT / "_label_scratch"

PROMPT = """You are reading one real bug fix from an open-source project. Write
down the IDEA behind it so it can be reused on a completely different codebase.

Commit message:
{subject}
{body}

Files changed: {files}

The change itself:
{diff}

Write four things.

problem - what was actually WRONG, before the fix. Describe the situation, not
this project. Someone reading it must be able to recognise the same problem in
software that shares none of these names. Write it the way a bug report is
written, describing the faulty behaviour and what causes it. Two or three
sentences.

fix_shape - the approach that fixed it, in words. The reasoning, not the patch.
Again: no names from this project, and no code.

tags - two to four short lowercase words for the area this belongs to, your own
choice of words. Examples of the KIND of thing: parsing, encoding, file-paths,
validation, concurrency, error-handling. Do not feel limited to those.

usable - true if this is a real defect whose idea would transfer. false if it is
cosmetic, a wording or formatting change, a change to types or tests only, or so
specific to this project's internals that nothing carries across. If false, say
why in why_not and leave the other fields empty.

Rules
- Never include source code, and never name a function, class, variable, file or
  project from the change above. If you cannot describe it without naming them,
  it does not transfer: set usable false.
- Describe what WAS wrong, in the past. Do not describe the new code.
- Do not guess at intent the change does not show. If the message and the diff
  disagree, trust the diff.
"""

SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["usable", "problem", "fix_shape", "tags", "why_not"],
    "properties": {
        "usable": {"type": "boolean"},
        "problem": {"type": "string"},
        "fix_shape": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}, "maxItems": 4},
        "why_not": {"type": "string"},
    },
}


def label(part, schema_path):
    SCRATCH.mkdir(exist_ok=True)
    out = SCRATCH / "out.json"
    out.unlink(missing_ok=True)
    prompt = PROMPT.format(subject=part["subject"],
                           body=(part["body"] or "")[:800],
                           files=", ".join(part["source_files"]),
                           diff=part["diff"][:12000])
    exe = shutil.which("codex") or "codex"
    p = subprocess.run(
        [exe, "exec", "-C", str(SCRATCH), "--skip-git-repo-check",
         "--ephemeral", "--ignore-user-config", "--approve-for-me",
         "-c", "web_search=disabled",
         "--output-schema", str(schema_path), "-o", str(out), "-"],
        capture_output=True, encoding="utf-8", errors="replace",
        input=prompt, timeout=900)
    if not out.exists():
        return None, f"no output (exit {p.returncode})"
    try:
        return json.loads(out.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as e:
        return None, f"unparseable output: {e}"


def leaks_identifiers(text, part):
    """The one rule worth checking rather than trusting.

    'Take the idea, not the code' fails quietly if the entry carries the
    original function names, so an entry that names them is rejected here
    instead of being retrieved forever afterwards.
    """
    low = (text or "").lower()
    names = {part["project"].lower()}
    for f in part["source_files"]:
        names.add(Path(f).stem.lower())
    return sorted(n for n in names if len(n) > 3 and n in low)


def write_entry(part, result):
    tags = [t.strip().lower() for t in result.get("tags", []) if t.strip()]
    body = (f"## Problem\n\n{result['problem'].strip()}\n\n"
            f"## Fix shape\n\n{result['fix_shape'].strip()}\n")
    head = (f"---\n"
            f"status: found\n"
            f"source_project: {part['project']}\n"
            f"source_commit: {part['commit']}\n"
            f"source_url: {part['url']}\n"
            f"tags: {','.join(tags)}\n"
            f"retrieved: 0\n"
            f"worked: 0\n"
            f"proven_on: \n"
            f"---\n\n")
    library.LIBRARY.mkdir(exist_ok=True)
    (library.LIBRARY / f"{part['id']}.md").write_text(head + body,
                                                      encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true",
                    help="print one prompt and exit, spending nothing")
    a = ap.parse_args()

    parts = []
    for p in sorted(RAW.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if not (library.LIBRARY / f"{d['id']}.md").exists():
            parts.append(d)
    parts = parts[:a.limit]
    if not parts:
        sys.exit("nothing unlabelled in raw-parts/ - run mine_library.py first")

    if a.dry_run:
        print(PROMPT.format(subject=parts[0]["subject"],
                            body=parts[0]["body"][:800],
                            files=", ".join(parts[0]["source_files"]),
                            diff=parts[0]["diff"][:2000]))
        return

    if not shutil.which("codex"):
        sys.exit("codex CLI not on PATH")
    SCRATCH.mkdir(exist_ok=True)
    schema_path = ROOT / "_label_schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")

    kept, refused, failed = [], [], []
    marker = (progress_marker(f"labelling {len(parts)} mined parts", "library/",
                              f"~{max(1, len(parts)//3)}0m")
              if len(parts) > 20 else contextlib.nullcontext())
    with marker:
        for i, part in enumerate(parts, 1):
            print(f"--- {i}/{len(parts)}  {part['id']}: "
                  f"{part['subject'][:60]}", flush=True)
            result, err = label(part, schema_path)
            if err:
                print(f"    !! {err}")
                failed.append((part["id"], err))
                continue
            if not result.get("usable"):
                print(f"    refused: {result.get('why_not','')[:90]}")
                refused.append((part["id"], result.get("why_not", "")))
                continue
            leaked = leaks_identifiers(
                result.get("problem", "") + " " + result.get("fix_shape", ""),
                part)
            if leaked:
                print(f"    !! names its source ({', '.join(leaked)}) - "
                      f"not an idea, refused")
                refused.append((part["id"], f"named identifiers: {leaked}"))
                continue
            write_entry(part, result)
            print(f"    kept  tags={result.get('tags')}")
            kept.append(part["id"])

    print(f"\nlabelled {len(kept)}, refused {len(refused)}, failed "
          f"{len(failed)}  ->  stores now {library.stats()}")
    for pid, why in refused:
        print(f"  refused {pid}: {why[:100]}")
    for pid, why in failed:
        print(f"  FAILED  {pid}: {why[:100]}")


if __name__ == "__main__":
    main()
