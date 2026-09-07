# Project state

Written 2026-09-07, from the code in this folder. Deliberately written without
opening `BUILD-TASK.md`, `keys/`, or `subject-staging/` — those hold the answers
to the experiment this repo runs, and reading them would defeat the point.

## What this actually does

It measures how well an AI finds bugs in code it has never seen, and tries to do
it honestly rather than impressionistically.

The method is an exam with a marked answer sheet:

1. Take a real open-source project and rewind it to a point in its history where
   it contained a bug someone later fixed.
2. Strip out everything that would give the answer away — the version history,
   and the test that was added alongside the fix.
3. Hand that folder to an AI agent that knows nothing about it, and ask what is
   wrong with the code.
4. Compare what it reports against the answer, which is kept in a separate
   folder the agent cannot reach.

The bugs and their answers come from **BugsInPy**, a published dataset of real
bugs in real Python projects. It is downloaded, not written here.

## The scripts

**`build_instances.py`** — builds the exam papers. For each bug it clones the
project at the buggy commit, deletes `.git` (the fixing commit lives in that
history), works out which Python version the project needs and copies a real
interpreter *inside* the instance folder, then installs its dependencies.

Its most important part is the **validation gate**: it runs the bug's own test
and requires it to *fail*. An instance whose bug has not been proved to
reproduce does not enter the corpus. Without that, a broken instance and a
genuine miss look identical, and the score ends up measuring how well the corpus
was built.

There is a wrinkle it handles: the test that proves the bug was usually **added
by the fix**, so it does not exist on the buggy commit. The script overlays that
test temporarily to validate, then removes it again — because such a test's own
name routinely states the bug outright.

**`run_diagnosis.py`** — sits the exam. Sends the prompt to each valid instance
using `codex exec` headlessly. Several flags are load-bearing rather than
decorative, and the comments in the file say why. Two guards refuse to run
rather than warn:

- it will not start unless internet search is disabled for the agent
- it will not touch the held-back instances without an explicit flag, and then
  demands typed confirmation

**`score.py`** — marks the paper, in two stages. Stage one is automatic and
cheap: a finding that names a file the bug is not in cannot be the bug, so most
findings are dismissed for free. Stage two — whether a described trigger would
actually produce the known failure — is **deliberately left to a human**.
Guessing it automatically would invent a score.

**`findings-schema.json`** — forces the agent to answer in a fixed shape, so
results are data rather than prose. An empty result is explicitly allowed:
"I found nothing" has to remain a legitimate answer, or the false-alarm number
becomes meaningless.

**`prompts/diagnosis-v3.txt`** — the instructions given to the agent under test.
Version 3. It asks for three separate passes: the structure of the code, the
*type* of data arriving, and the *content* of that data.

## What is finished

- `build_instances.py` — working and proved. Its rejection gate has been tested
  by deliberately building an instance that should fail validation, and it did.
- `run_diagnosis.py` — working end to end. Both guards have been tested by
  breaking them on purpose and watching them refuse.
- `findings-schema.json` — done.
- The prompt — v3, in use.

## What is half-built

- **`score.py`** produces stage one only. Stage two being manual is a design
  decision, not an omission, but it does mean **no catch rate or false-alarm
  rate is computed anywhere in this repo yet.** Those numbers currently live in
  a scoring sheet kept outside this folder.
- **The corpus.** `instances/` holds 28 built instances but a batch build was
  still running when this was written, and a known bug in the builder's
  post-validation cleanup check has been wrongly rejecting instances where the
  bug's test already existed on the buggy commit. That is not yet fixed.
- **`results/`** contains exactly one run. The batch has not been executed.

## What is only a stub, or looks abandoned

These were all throwaway probes written to answer one question and never
revisited. None are referenced by the three real scripts:

- `smoke_out.json`, `smoke2.json`, `smoke5.json` — output from testing whether
  the agent CLI could run headlessly and whether its internet access could be
  switched off. Three near-identical files; only the last was informative.
- `schema_test.json` — a two-field throwaway schema used for those smoke tests.
  Superseded by `findings-schema.json`.
- `probe.json` — output from one more permissions test.
- `lint_probe.py` — a six-line file written to check exactly when an off-the-
  shelf linter's rule fires and when it silently does not.

`prompts/` contains both `diagnosis-v3.txt` and `diagnosis-v3-source.md`. The
`.txt` is what the runner actually reads; the `.md` is the same content with
formatting. **They can drift apart, and nothing checks that they agree.**

`reports/build.log` is a live log from the batch build that was in progress at
the time of the commit, so it is captured mid-write.

## Not in this repo

`subject/` is a **sibling folder** (`C:\Users\hollo\dev\subject`), not part of
this repository. It holds a single hand-built instance from before the harness
existed.

`instances/`, `BugsInPy/` and `src/` are excluded from version control — see
`.gitignore` for what each is and why. All three are reproducible or downloaded;
none contain anything written for this project.
