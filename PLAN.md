# Project plan

## END GOAL

A public web platform where anyone submits a repository and gets back a better
one, with evidence. It understands the repo, finds how comparable problems have
already been solved in open source, products, competitors and research,
implements the best transferable improvements, and proves the result is better
than what went in. It also offers a genuinely useful software search interface,
and becomes more capable the more repositories it sees.

Finished means a stranger can submit a repository nobody here has seen, over the
public internet, with no human touching the run after submission, and get back a
changed repository plus evidence that holds up: every claimed improvement backed
by something that demonstrably failed before and passes now, and everything
unproven labelled a suggestion rather than a result.

status: proposed

## Hard constraints

From the brief, all three pointing the same way:

- **No localhost-only demo.** It must be live and public.
- **No predefined repository.** It must work on whatever is submitted.
- **No human guidance after submission.** Fully unattended end to end.

Curating the fix database between runs is *not* guidance during a run, and is
allowed.

## Standing decisions

These are settled and should not be silently reopened.

- **Two roles.** A *Breaker* finds bugs and fragility; an *Auditor* finds
  inefficiency, dead code and better approaches. **Prototype 1 is the Breaker
  only** — the Auditor's hardest third has no answer key anywhere, because
  there is no agreed test for whether something is an improvement.
- **Proof has two halves**: the failure is gone, *and* everything that worked
  before still works. Without the second half, "swallow the error" and "delete
  the feature" both score perfectly.
- **The success test is written at the moment the break is found**, before any
  searching. A test written after seeing a candidate fix is a test that fix
  passes.
- **Output separates proven from proposed.** Never claim a proof that does not
  exist.
- **Security by isolation, not inspection.** Hostile code hides; containment
  works whether or not you spotted it.
- **Take the idea, not the code.** Ideas are not copyrightable, specific code
  is. This also solves "the fix does not fit this repo".
- **Public repositories only in prototype 1.** A privacy promise can be added
  later and never retracted.
- **Scanning runs cheapest-first**: existing tools, then the project's own
  tests, then the AI, then actually breaking it. Anything a linter finds should
  never cost an API call.

---

# PART 1 — Can it find problems? (measurement)

*Scaffolding, not product. Nothing here ships to a user; it exists so the rest
can be judged rather than guessed at.*

## Stage 1: Build the exam papers
Rebuild each project at its buggy commit, strip the history and the giveaway
test, and refuse any instance whose bug has not been proved to fail.

Done when: `build_instances.py` builds an instance and rejects it unless the
bug's own test is observed to fail.

## Stage 2: Sit the exam, safely
Drive an AI agent over an instance without internet access, and keep the
held-back instances out of reach unless deliberately unlocked.

Done when: `run_diagnosis.py` runs an agent per instance and refuses to start
when search is enabled or when held-back instances are targeted without
explicit confirmation.

## Stage 3: Answers in a fixed shape
Force the agent's report into a defined structure so results can be counted,
with "I found nothing" a permitted answer.

Done when: `findings-schema.json` defines the answer shape, the runner enforces
it, and an empty result is valid against it.

## Stage 4: A corpus worth measuring
Fix the builder's cleanup check that wrongly rejects instances whose bug test
already existed, and record which instances passed validation.

Done when: the wrongly-rejecting cleanup check is corrected, and a committed
manifest lists every validated instance in the corpus.

## Stage 5: Run the whole batch
Run every instance in the corpus in one pass and keep the output.

Done when: `results/` holds one recorded result per instance in the manifest,
from a single batch run.

## Stage 6: Produce the two numbers
Complete the marking so the catch rate and the false-alarm rate are computed
inside this repo, with the human judgement step recorded here rather than in a
sheet elsewhere.

Done when: `score.py` outputs a catch rate and a false-alarm rate, and the human
judgements it depends on are stored in this repo.

## Stage 7: Someone else could run it
Document the whole route from clone to numbers, and stop the two copies of the
prompt drifting apart.

Done when: the README documents building the corpus, running the batch and
scoring it, and a check fails if `prompts/diagnosis-v3.txt` and
`diagnosis-v3-source.md` disagree.

## Stage 8: Decide whether the ruler is right
Five hand runs produced nine verified real defects and a catch rate of zero,
because the dataset catalogues one bug per project and scores everything else
as a miss. Settle whether diagnosis is judged against the catalogued bug or on
whether its findings are real and worth fixing.

Done when: the batch numbers from Stage 6 are in, a decision is written down
with its reasoning, and `score.py` computes whichever measure was chosen.

---

# PART 2 — Can it prove an improvement? (the crux)

*This is where the project lives or dies, so it comes before building any more
pipeline. Everything downstream is worthless if "better" cannot be demonstrated
without a human.*

## Stage 9: Know what you are holding
Before any judgement about a submitted repo, record whether it builds, whether
it runs, whether it has tests, and whether those tests pass.

Done when: every run emits that record, and the system refuses to report "no
problems found" for any repo whose record shows it could not run anything.
*(Three of the first four hand runs were decided by the environment rather than
the code, and each time the failure looked like a clean result.)*

## Stage 10: Prove a fix is better
Given a repo, a defect and a candidate change, decide whether the repo is
genuinely better afterwards — the defining failure gone, and nothing else
broken.

Done when: given a known-buggy instance and its real fix, the proof step reports
*better*; and given the same instance with a change that merely suppresses the
symptom (swallowing the error, or deleting the feature), it reports *not
better*.

## Stage 11: Run a stranger's code safely
Every submitted repo executes inside a throwaway sealed workspace with no
network, no access to the host filesystem, and nothing shared between runs.

Done when: a deliberately hostile test repo — one that tries to read outside its
workspace, reach the network, and write to the host — runs to completion with
all three attempts blocked and logged.

---

# PART 3 — Can it make the improvement?

## Stage 12: Find how others solved it
Turn a specific defect into a searchable description, then return candidate
approaches from open source, products and research, each with a citable source.

Done when: given a defect from the corpus, the search step returns ranked
candidate approaches with sources, plus a recorded judgement for each of whether
it transfers to this repo.

## Stage 13: Make the fix
Write the change into the repo — the idea taken from the source, the code
written fresh for this codebase.

Done when: for an agreed number of corpus instances, the system produces a
change that passes Stage 10's proof with no human involvement.

## Stage 14: Hand back a result
Deliver the improved repository in a form the submitter can actually use.

Done when: a completed run outputs an applicable change set with proven and
proposed changes separated, every proven change carrying the evidence that
backs it, and every proposed one carrying the source that inspired it.

## Stage 15: Get better with use
Store the *idea and shape* of each proven fix, indexed by the problem it solved,
and use it on later repositories.

Done when: running the same repository twice — once with the database enabled
and once without — produces measurably different output, and that difference is
recorded. *(Without this check the database can grow to thousands of entries,
contribute nothing, and look exactly like learning.)*

---

# PART 4 — Can anyone use it?

## Stage 16: Public platform
A live site where anyone submits a public repository URL and gets a result,
running nowhere near Luke's laptop.

Done when: a person who is neither Luke nor Alex submits a public repository
from their own machine and receives a result, with nothing running locally.

## Stage 17: Software discovery interface
The search side of the brief: a way to find software by the problem it solves,
built on what the platform has learned.

Done when: Alex can use it without instruction and find a project relevant to a
problem he describes, that he did not already know about.

---

# PART 5 — Prototype 2

*Deferred deliberately. Neither is needed to demonstrate the thesis.*

## Stage 18: The Auditor
Dead code and measurable slowness, both of which prove themselves — delete it
and the tests still pass; time it before and after. "A smarter way to do this"
ships as *proposed*, never *proven*.

Done when: the Auditor reports dead code and speed improvements with evidence
attached, and anything unprovable appears only in the proposed section.

## Stage 19: Private repositories
Accept code that is not already public, with the promises that entails.

Done when: submitted code is provably deleted after a run, and every third party
it passes through is named on the page before submission.

---

# Known open questions

- **Corpus reach.** If most published bug datasets cannot be made to run on a
  modern machine, that is a hard limit on Part 2 — you cannot prove anything
  about code you cannot execute.
- **Contamination.** Every public dataset may sit inside the models' training
  data. Bugs fixed after the training cutoff are the only clean measure.
- **What "two bug-fixing formulas" means** — from an early session, never
  pinned down. Working assumption: fix from the database vs fix from fresh
  search.
- **Where it runs.** Deferred. Needed by Stage 16, not before.
