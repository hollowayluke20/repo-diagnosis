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
