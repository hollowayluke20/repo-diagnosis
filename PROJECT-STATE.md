# Project state

Last updated end of 2026-09-07.

## What this is

A harness that measures how well an AI finds bugs in code it has never seen,
and — as of today — whether it can fix them. See `README.md` for how to run it,
`PLAN.md` for where it is going, `SCORING.md` for how results are judged.

## Where it stands

**The measuring half works end to end.** Build the exam papers, sit the AI down
with the answers out of reach, mark it automatically by running the proof
scripts it supplies.

**The fixing half has been demonstrated once**, on three projects, and it
worked twice with one honest refusal.

| | |
|---|---|
| Corpus | **33 instances**, 11 projects, 23 practice / 10 held back |
| Diagnosis | works; every finding must ship a runnable reproduction |
| Scoring | automatic — reproductions are executed, not read |
| Fixing | demonstrated on 3 projects |
| Product itself | **nothing built** |

## Results so far

Numbers are from **three projects**, which is not yet evidence.

- 6 findings, **all confirmed real** by running their reproductions
- 1 of 3 was the bug the dataset catalogued
- black: fixed a real bug in 1 attempt, all 127 of its own tests still passing
- httpie: found and fixed a bug on a project it had never seen, 1 attempt
- phantom (told a bug existed where none did): **refused and changed nothing**,
  correctly identifying the test as the problem

The phantom test was easier than it should be — the script announced itself.
A harder version would import the module, do real work, and fail subtly.

## What is finished

- `build_instances.py` — its gate is proved: an instance built at the *fixed*
  commit is rejected
- `run_diagnosis.py` — three guards, each proved by breaking it on purpose:
  refuses without the internet block, refuses held-back instances, warns if the
  prompt arrives truncated
- `score.py` — runs reproductions, reports catch rate and confirmation rate
- `fix_bug.py` — works on a copy, before-and-after test baseline, `--phantom`
- `manifest.py`, `check_prompt_sync.py`, `progress_marker.py`

## What is half-built

- **The batch has not been run.** 3 of 33 instances. Everything measured comes
  from those three.
- **Speed and the two newest quality checks** (docs-match-behaviour,
  installs-cleanly) are decided but not built.
- The `--phantom` control needs a harder version.

## Bugs found in this harness today, all now fixed

Kept because every one of them produced confident, plausible, wrong output and
none of them threw an error:

1. **Prompts were truncated at the first newline** passing through npm's `.CMD`
   shim. Every automated run received one sentence. Fixed: stdin, plus a canary
   that shouts if the tail of the prompt is missing from the log.
2. **The prompt file was corrupted** — every em dash had become a replacement
   character. Fixed: rewritten in ASCII, with a check that fails on any
   non-ASCII character.
3. **The scorer counted a matching filename as a catch**, turning 1-of-3 into a
   fake 100%. Fixed: a finding must land where the real fix landed.
4. **The answer keys were reachable** from inside every instance at `../../keys`.
   Fixed: they now live outside the repository entirely.
5. **The builder rejected 17 good instances** through four separate bugs —
   assuming one test runner, a cleanup check that was too strict, a missing
   dependency, and error reporting that returned separator bars.

## Not in this repo

`keys/` and the run history live in `../repo-diagnosis-keys/`, outside this
repository on purpose. `instances/`, `BugsInPy/`, `src/` and `fixes/` are
excluded from git — see `.gitignore`.
