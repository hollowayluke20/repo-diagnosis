"""Fail if the library or database holds a fix mined from a corpus project.

The trap this exists to catch is quiet. If the library contains fixes taken from
cookiecutter and black, and the exam papers are cookiecutter and black, the
system has been handed the answers: the catch rate rises and means nothing, and
every visible sign says it is learning.

The miner refuses at source, but refusing at source only catches contamination
going IN. This catches it after the fact, when the CORPUS is what changed -
add a BugsInPy project to the corpus next month and entries already sitting in
the library silently become answers.

So the banned list is read at run time from two places and never copied into
code:

  MANIFEST.md            what is in the corpus today
  BugsInPy/projects/     everything that could be put in it tomorrow

Run it like check_prompt_sync.py: it exits non-zero and says what is wrong.
"""
import re, sys
from pathlib import Path

import library

ROOT = Path(__file__).parent.resolve()
MANIFEST = ROOT / "MANIFEST.md"
BUGSINPY = ROOT / "BugsInPy" / "projects"


def banned_projects():
    """Every project name that must never be a source. Read, never hardcoded."""
    names = set()
    if MANIFEST.exists():
        # rows look like: | black-1 | 3.8.3 | 80 | ... -> take the instance name
        # and strip the trailing -<number>
        for m in re.findall(r"^\|\s*([A-Za-z0-9_.-]+?)-\d+\s*\|",
                            MANIFEST.read_text(encoding="utf-8"), re.M):
            names.add(m.lower())
    if BUGSINPY.exists():
        for p in BUGSINPY.iterdir():
            if p.is_dir():
                names.add(p.name.lower())
    return names


def main():
    banned = banned_projects()
    if not banned:
        sys.exit("REFUSING to pass: found no banned list at all. Expected "
                 "MANIFEST.md rows or BugsInPy/projects/. A check that cannot "
                 "see what it is protecting is worse than no check.")

    problems = []
    entries = library.load_all()
    for e in entries:
        src = (e["source_project"] or "").strip().lower()
        if not src:
            problems.append(f"{e['store']}/{e['id']}: no source_project recorded "
                            f"- an entry with no source cannot be checked")
            continue
        if src == "seed":
            continue
        if src in banned:
            problems.append(f"{e['store']}/{e['id']}: mined from '{src}', which "
                            f"is a corpus / BugsInPy project")
        # also catch a source recorded as a URL or owner/repo pair
        for part in re.split(r"[/\\:. ]+", src):
            if part and part in banned and src not in banned:
                problems.append(f"{e['store']}/{e['id']}: source '{src}' "
                                f"contains banned project '{part}'")

    print(f"checked {len(entries)} entries against {len(banned)} banned projects")
    if problems:
        print("\nCONTAMINATED:")
        for p in problems:
            print("  - " + p)
        sys.exit(f"\n{len(problems)} problem(s). These entries are answers to "
                 f"exam papers and must be deleted before any figure is quoted.")
    print("clean - no entry is sourced from a corpus or BugsInPy project")


if __name__ == "__main__":
    main()
