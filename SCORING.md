# Scoring rules

Written before the batch runs. Changing these after seeing a score is moving
the goalposts; if they need to change, the change and its reason go in this file
with a date, and the old numbers are marked as computed under the old rules.

## The problem these rules solve

The dataset records **one** bug per project. In five hand runs the AI reported
**nine genuinely real defects and not one of them was the catalogued one** —
including a path-traversal hole that lets a crafted project name write files
outside the output directory.

Scored the obvious way, that is 0%. But a bug finder that finds nine real bugs
is not a 0% bug finder. The number was measuring the dataset, not the AI.

So we measure two different things, and never mix them.

## The two questions

**1. Can it find a specific bug we already know about?**
Ground truth is unarguable here — someone else catalogued it years ago and we
have proved it reproduces. But it only ever asks about one bug per project.

**2. Are the things it reports actually real?**
This is what matters for a product. Nobody submitting a repository cares
whether the system found a bug that a researcher happened to write down in 2020.

## Making "is it real?" objective

The obvious way to answer question 2 is for a human to read each finding and
judge it. That does not scale, and it makes the score somebody's opinion.

Instead: **every finding must arrive with a reproduction that can be run.**

Not prose. A short, self-contained script that fails on this code, and that
would stop failing if the defect were fixed. That is the same fail-to-pass shape
the dataset itself uses to define a bug.

Then judging is not judgement at all. We run it.

## The categories

Applied to every finding, in this order.

**CONFIRMED** — the reproduction was run against the instance and it failed.
The defect is real, whether or not anyone catalogued it.

**UNCONFIRMED** — the reproduction was run and nothing failed. Either the
finding is wrong, or it was described too vaguely to demonstrate. Both count the
same: a defect you cannot demonstrate is not usable.

**MALFORMED** — no reproduction supplied, or it could not be run at all
(syntax error, missing import it never sets up). Counted with UNCONFIRMED, but
recorded separately so we can tell "wrong" apart from "did not answer properly."

Then, for CONFIRMED findings only, one further label:

**CATALOGUED** — this confirmed finding is the bug the dataset recorded. It
matches the key's file, and its reproduction triggers the same failure. Right
file alone is never enough.

## The numbers

- **Catch rate** = instances where a CATALOGUED finding was made ÷ instances run.
  *Ground truth. Expect it to be low. Report it anyway.*
- **Confirmation rate** = CONFIRMED ÷ all findings.
  *The quality measure. Fully automatic — no human judgement anywhere in it.*
- **Noise rate** = (UNCONFIRMED + MALFORMED) ÷ all findings.
  *What proportion of its output wastes your time.*
- **Silence check** = findings reported on instances with no known defect.
  *Anything here is noise by definition.*

**A finding that is CONFIRMED but not CATALOGUED is a success, not a miss.** It
raises the confirmation rate and does not touch the catch rate. That is the
whole point of separating the two.

## Worked example — a real finding that is not the one sought

From the cookiecutter run on 2026-09-07.

The catalogued bug is in `cookiecutter/generate.py` at line 82.

The AI reported, among others, a defect in **`cookiecutter/generate.py` at line
199**: rendered template paths are joined to the output directory without
checking the result stays inside it, so a project name of `../escaped` writes
files outside the target directory.

Same file. Different line. Different defect. Arguably more serious than the one
we were looking for.

**How it is counted:**

- Its reproduction is run. It fails → **CONFIRMED**.
- Compared against the key: right file, but the failure it triggers is not the
  catalogued one → **not CATALOGUED**.
- Effect: **confirmation rate up, catch rate unchanged.**

Under the old rules this was a miss, and the run scored 0%. Under these rules
the run scores 0% on catch rate — unchanged, because it genuinely did not find
the catalogued bug — and separately scores well on confirmation rate. Both facts
are true and neither is hidden.

## What is deliberately not measured

- **Severity.** Whether a defect matters more than another is a judgement, and
  there is no honest automatic version of it.
- **Whether the fix is any good.** That belongs to the proof stage, not here.
- **How long it took.** Worth logging, not worth optimising yet.

## Note on running AI-written code

Scoring executes reproduction scripts written by the system under test. For now
that is our own instances and a known agent, which is acceptable. It stops being
acceptable the moment anything from the public internet is involved — that is
what the sealed workspace stage exists for, and this file should be revisited
when it lands.

---

# PART 2 — "Still runs" quality check (Stage 6)

*Detects when a project that worked on its author's machine breaks on current
language versions. This is provable and cheap, and invisible to the owner.*

## What "still runs" means

**Does the project's own test suite get worse when moved from its original
Python to a current one?**

Not "does every test pass" — for this corpus, every instance carries a
deliberately-failing test by construction (that is the catalogued bug). A rule
that required 100% green would report every single instance as broken,
regardless of Python version, which is a check that can never pass and
therefore proves nothing. So the comparison is **before vs after**, the same
idea `fix_bug.py` already uses to judge a fix: not "is it perfect" but "did
this make it worse."

## Why not just read the project's own CI config?

Many mature projects already test themselves across Python versions (GitHub
Actions matrices, tox). That is not usable here for two reasons:

1. `build_instances.py` deletes `.git` on purpose, so CI configs are gone by
   design — nothing to read even if we wanted to.
2. Even where a CI config exists, a passing badge is a claim about the past,
   not evidence about now — the exact trap this session started from ("an
   agent saying it finished is a claim, not a result"). A project's CI last
   ran against whatever Python was current *then*. It says nothing about
   whether it still works on the Python installed on this machine *today*.
   Real, current example: **luigi failed to install cleanly** during corpus
   building — a live failure a stale green checkmark would never have shown.

So: run it, don't read about it, on both sides of the comparison.

## How to measure it

For a given instance:

1. **OLD run** — run the project's own test command (whatever `run_test.sh`
   specifies — pytest, unittest, tox) using the Python already provisioned
   inside the instance. Record `old_failed` (count of failing tests) and
   whether the suite could be collected/run at all.
2. **NEW run** — copy the project to a scratch folder, provision a **current**
   Python there, reinstall the same declared dependencies, run the identical
   test command. Record `new_failed` and whether it could collect/run at all.
3. **Compare, don't grade in isolation:**
   - **PORTABLE** — the new run collected and ran, and `new_failed <=
     old_failed`. Nothing that worked before stopped working.
   - **BROKEN** — the new run could not even collect/start (e.g. an import
     the project relies on no longer exists in current Python), OR
     `new_failed > old_failed`. This is the concrete, provable portability
     break, and the error message from the new run is the evidence.
   - **NOT APPLICABLE** — the *old* run itself could not collect/run at all.
     There is no usable baseline, so no claim is made either way. Honest
     "cannot test this one," not a guess.

## Worked example

From the full-corpus run on 2026-09-07 (`reports/portability.md`).

**black-1**

- OLD run (the Python the instance was built with): 1 test failed. Collected
  and ran fine otherwise.
- NEW run (a fresh current Python, same declared dependencies reinstalled):
  could not even start. `ModuleNotFoundError: No module named 'pkg_resources'`.
- **BROKEN.** `pkg_resources` used to ship bundled with setuptools/pip on
  every Python install; current setuptools stopped including it by default.
  black never declared it as an explicit dependency because it never had to -
  it worked by accident, and current Python breaks that accident.

**tornado-1**

- OLD run: 1 test failed.
- NEW run: 1 test failed. Same count.
- **PORTABLE.** Nothing that worked before stopped working.

**httpie-1**

- OLD run: could not collect at all - `ImportError while loading conftest`,
  a pre-existing problem with the instance's own test setup, unrelated to
  Python version.
- **NOT_APPLICABLE.** There is no working baseline to compare against, so no
  portability claim is made either way.

Full-corpus result (33 instances, 2026-09-07): 11 BROKEN, 5 PORTABLE, 17
NOT_APPLICABLE. Of the 11 BROKEN, all 11 trace to the same root cause -
`pkg_resources` either missing from current setuptools or pinned as an
uninstallable `pkg-resources==0.0.0` dependency - across 5 different
projects (black, cookiecutter, luigi, sanic, tqdm). One real, fixable defect
class, not 11 unrelated ones.

## Ensuring this can fail

Before trusting the check on real instances, break it on purpose:

1. **Inject a syntax error** into a source file the new environment imports —
   the NEW run must report BROKEN (collection fails).
2. **Delete a required dependency's import** in the scratch copy only — the
   NEW run must report BROKEN, not silently pass.
3. **Run it against an instance where OLD itself cannot run** (a deliberately
   corrupted requirements file) — the result must be NOT APPLICABLE, never a
   false PORTABLE.

All three must be observed to fail correctly before the check is trusted on
the real 33 instances.
