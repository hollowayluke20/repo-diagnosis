# The library

Fix shapes mined from other projects' git histories. Large, free, and
**unverified** - nothing in here has been shown to work on anything. This is
where the system goes looking.

`../database/` is the other store, and they are never merged. An entry moves
here -> there by being **used and proven**, never by being found and never by
being popular. Promotion is a file move, so the two can always be counted.

## What an entry is

A shape, not a diff:

| | |
|---|---|
| **Problem** | what was wrong, described so it transfers to another codebase |
| **Fix shape** | the approach, in words |
| **Source** | which project, which commit |
| **Status** | `found` (unproven) / `proven` (worked, evidence attached) |

No source code, deliberately. Ideas are not copyrightable and specific code is,
and an idea transfers to a different codebase where a patch does not.

## The two tallies

`retrieved` counts how often an entry was offered as a candidate. `worked`
counts how often a fix that actually **used** it went on to pass the proof.
Only the second promotes. An entry retrieved constantly that never works is a
bad matching rule, and the gap between the two numbers is what says so.

## Where entries may NOT come from

Nothing in here may be mined from a project in the test corpus, or from
anything in `BugsInPy/projects/`. A fix mined from cookiecutter **is** the
answer to the cookiecutter exam paper, and a library holding it would raise the
catch rate for no real reason.

`check_library_clean.py` enforces this, and the miner refuses at source rather
than relying on anyone remembering. The ban is wider than the corpus on purpose:
adding a BugsInPy project to the corpus later would otherwise turn entries
already sitting here into answers, with nothing to flag it.

Note the ban is on mining **from** those projects. *Fixing* one of them using an
idea taken from elsewhere is not a leak - that is the system doing its job.

## The SEED entries

Three entries are marked `source_project: SEED`. They were hand-written to test
the retrieval and A/B plumbing before the miner existed, and were deliberately
written **without reading any finding they might be matched against** - the same
contamination rule in miniature.

They are scaffolding. Delete them once mined entries exist, and never count them
in any figure about how well the library is doing.
