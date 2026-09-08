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

**12 practice projects and 3 controls**, all scored by running the AI's own
reproduction scripts rather than by reading them.

| | |
|---|---|
| Confirmation rate | **97%** - 36 of 37 findings actually broke the code |
| Noise | 3% - one reproduction that ran without failing |
| Catch rate | **8%** - 1 of 12 found the bug the dataset catalogued |

**The controls passed.** Three projects rebuilt at the commit where their bug
was *fixed*, 11 findings between them, 10 confirmed real, and **not one claimed
the fixed bug was still there.** It does not invent work on code that has been
repaired. That was the largest untested hole on the bug side.

One control finding was flagged by the scorer as landing on the fixed bug and
turned out not to be: same file, neighbouring function, a genuinely different
defect. The +/-15 line proximity window is too loose for dense files.

**On the catch rate.** 8% is a fact about the dataset, not the AI. BugsInPy
records one bug per project; the system finds real ones nobody wrote down. On
12 projects it produced 36 demonstrable defects and matched the catalogued one
once. `SCORING.md` predicted this before any batch ran, which is the only
reason it can be reported rather than argued about.

**Fixing, demonstrated on 3 projects:** black fixed a real bug in one attempt
with all 127 of its own tests still passing; httpie found and fixed one in a
project it had never seen; and the phantom control - told a defect existed
where none did - refused and changed nothing.

**Still-runs (portability), full corpus, 2026-09-07:** 33 of 33 instances
checked, comparing each one's own test suite on its original Python against a
freshly-provisioned current Python.

| | |
|---|---|
| BROKEN | **11** - a real, present-day break on current Python |
| PORTABLE | 5 - nothing that worked before stopped working |
| NOT_APPLICABLE | 17 - the instance's own baseline could not run at all, for reasons unrelated to Python version, so no claim is made |

All 11 BROKEN instances trace to one root cause: `pkg_resources`, which used
to ship bundled with every Python install, is either missing from current
setuptools or pinned as an uninstallable `pkg-resources==0.0.0` dependency -
across 5 different projects (black, cookiecutter, luigi, sanic, tqdm). See
`SCORING.md` for the worked example and `reports/portability.md` for the full
table.

## VERIFIED DONE

Each entry below is done AND was proved by breaking it on purpose (the
project's own standard). This section is read by the daily project reviewer,
so it can trust that these are finished and stop proposing them as tomorrow's
work. A thing is only added here once it has been demonstrated, never because
it was written.

- **Stage 1 (scoring rules)** — DONE. The two questions, the categories, and a
  worked example are written down in `SCORING.md`, before any batch ran.
  Proved: the worked example (a real finding that is not the sought one) is in
  the file.
- **Stage 2 (corpus, the gate)** — DONE. `build_instances.py` only admits an
  instance after its bug's own test is observed to fail. Proved: an instance
  built at the *fixed* commit is rejected by the gate.
- **Stage 3 (agent in front, answers out of reach)** — DONE. `run_diagnosis.py`
  has all three required guards. Proved by breaking each on purpose: it refuses
  to start without the internet block, refuses held-back instances without
  explicit confirmation, and records the exact prompt sent alongside every reply.
- **Stage 8 (run stranger's code safely)** — DONE. The sealed `sandbox/`
  workspace blocks network, host filesystem, and writes. Proved by escaping
  first: a canary that succeeds unsealed is refused by the OS when sealed.
- **`score.py`** — DONE. Runs the reproductions automatically and reports catch
  rate and confirmation rate.
- **`fix_bug.py`** — DONE. Works on a copy, keeps a before-and-after test
  baseline, and has a `--phantom` mode.
- **`check_still_runs.py`** — DONE. Compares each original-Python test baseline
  with a clean current-Python copy and rejects any newly worse suite. Proved by
  its `--self-test` (injects a syntax error and a missing dependency).
- **Security check (Stage 6)** — DONE. Two separate checks, no AI:
  `check_known_holes.py` (pinned deps looked up against the OSV advisory
  database) and `check_exposed_secrets.py` (credential-shape pattern search
  with placeholder/test-path filtering). Both have `--self-test` proving every
  verdict branch including cry-wolf and database-unreachable. Ran round 1 (10
  practice), round 2 (10 fresh), then the full practice batch (43): known-holes
  32 HIT / 11 UNKNOWN / 0 CLEAN (2020 pins always have CVEs recorded by now;
  UNKNOWN = no declared deps or unpinned manifest); exposed-secrets 6 HIT (all
  youtube-dl, real API keys embedded in extractor source) / 37 CLEAN, zero
  false alarms after the round-1 path-trust fix. Rules + worked examples in
  SCORING.md PART 3. `reports/known-holes.md` committed;
  `reports/exposed-secrets.*` git-ignored (quotes real secrets).
- **`manifest.py`, `check_prompt_sync.py`, `progress_marker.py`** — DONE.

## What is half-built

- **The diagnosis batch has not been run.** 3 of 33 instances. Everything
  measured on the bug-finding side comes from those three. (The portability
  batch, a separate check, has now been run on all 33 - see above.)
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
6. **The portability checker misread a passing test as an unusable baseline.**
   Its regex required a pass/fail count to sit immediately before the "in
   Xs" time footer, but pytest inserts a warnings clause between them ("1
   passed, 2 warnings in 0.33s"), so a real pass was read as "could not run
   at all" - a false NOT_APPLICABLE on tqdm-1, caught by testing on a handful
   of real instances before trusting the full batch. Fixed: the count and the
   time footer are matched separately rather than as one contiguous pattern.

## Not in this repo

`keys/` and the run history live in `../repo-diagnosis-keys/`, outside this
repository on purpose. `instances/`, `BugsInPy/`, `src/` and `fixes/` are
excluded from git — see `.gitignore`.
