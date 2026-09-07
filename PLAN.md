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

status: agreed

## Hard constraints

From the brief, all three pointing the same way:

- **No localhost-only demo.** It must be live and public.
- **No predefined repository.** It must work on whatever is submitted.
- **No human guidance after submission.** Fully unattended end to end.

Curating the fix database between runs is not guidance during a run, and is
allowed.

## Design decisions taken up front

- **Two roles.** A *Breaker* finds bugs and fragility; an *Auditor* finds
  inefficiency, dead code and better approaches. Prototype 1 is the Breaker
  only — the Auditor's hardest third has no answer key anywhere, because there
  is no agreed test for whether something is an improvement.
- **Proof has two halves**: the failure is gone, *and* everything that worked
  before still works. Without the second half, "swallow the error" and "delete
  the feature" both score perfectly.
- **The success test is written at the moment a break is found**, before any
  searching. A test written after seeing a candidate fix is a test that fix
  passes.
- **Output separates proven from proposed.** Never claim a proof that does not
  exist.
- **Security by isolation, not inspection.** Hostile code hides on purpose;
  containment works whether or not you spotted it.
- **Take the idea, not the code.** Ideas are not copyrightable, specific code
  is. This also solves "the fix does not fit this repo".
- **Public repositories only in prototype 1.** A privacy promise can be added
  later and never retracted.
- **A repo with no usable tests is served, not refused** — but every claim made
  about it is downgraded to *proposed*, because the second half of the proof
  ("nothing else broke") leans on the repository's own test suite. The system
  degrades honestly rather than either turning people away or overclaiming.
- **Proof comes before pipeline.** Part 2 is sequenced ahead of Part 3
  deliberately: if "better" cannot be shown without a human, then searching,
  fixing and the database are decoration on an unprovable core.
- **Scan cheapest-first**: existing tools, then the project's own tests, then
  the AI, then actually breaking it. Anything a linter finds should never cost
  an API call.

---

# PART 1 — Can it find problems, and can that be measured?

*Scaffolding, not product. Nothing here ships to a user. It exists so every
later claim can be judged rather than asserted.*

## Stage 1: Decide what is being measured, before measuring it
Define what counts as a correct finding, what counts as a false alarm, and what
happens to a genuine defect that is not the one being looked for. Set the pass
mark now, not after seeing a score.

Done when: the scoring rules are written down, including a worked example of a
finding that is real but not the one sought, and how it is counted.

## Stage 2: Build a corpus of real bugs with known answers
Take bugs from a published dataset, rebuild each project at the moment the bug
existed, and strip out everything that gives the answer away — the version
history, and any test added alongside the fix.

Done when: an instance is only admitted after its bug's own test has been
observed to fail on it, and an instance built at the fixed commit is rejected.

## Stage 3: Put an agent in front of it, with the answers out of reach
Run an AI agent over each instance with no internet access, no session memory
between runs, and no path to the answer material.

Done when: the runner refuses to start with search enabled, refuses to touch
held-back instances without explicit confirmation, and records the exact prompt
sent alongside every reply.

## Stage 4: Answers in a countable shape
Force each report into a defined structure, with a concrete trigger required for
every finding and "I found nothing" a permitted answer.

Done when: results are machine-readable, a finding without a concrete trigger is
rejected, and an empty result validates.

## Stage 5: A baseline number
Run the whole corpus in one pass and produce the agreed measure.

Done when: one recorded result exists per instance from a single batch, the
measure from Stage 1 is computed inside the repo from those results, and a
README documents the route from clone to that number so somebody else could
reproduce it. A committed check must also fail if a second copy of the prompt
ever appears alongside the one the runner actually sends — two copies drift, and
the copy that drifted was the one a person would read.

---

# PART 2 — Can an improvement be proved? *(the crux)*

*This decides whether the project is possible. It comes before building any
pipeline, because everything downstream is decoration if "better" cannot be
demonstrated without a human.*

## Stage 6: Know what you are holding
Before any judgement about a submitted repo, record whether it builds, whether
it runs, whether it has tests, and whether those tests pass.

Done when: every run emits that record, and the system refuses to report "no
problems found" for any repo whose record shows it could not run anything.

## Stage 7: Prove a fix is better
Given a repo, a defect and a candidate change, decide whether the repo is
genuinely better afterwards.

Done when: given a known-buggy instance and its real fix, the proof step reports
*better* — and given the same instance with a change that merely suppresses the
symptom, or deletes the feature, it reports *not better*.

## Stage 8: Run a stranger's code safely
Every submitted repo executes inside a throwaway sealed workspace: no network,
no access to the host filesystem, nothing shared between runs.

Done when: a deliberately hostile test repo — one that tries to read outside its
workspace, reach the network, and write to the host — runs to completion with
all three attempts blocked and logged.

---

# PART 3 — Can it make the improvement?

## Stage 9: Break it on purpose
Generate inputs and conditions the code was never tried against, run them, and
capture the ones that cause a real failure. This is the strongest diagnosis
available, and it hands over the proof for free: a break comes with the exact
input that caused it.

Done when: breaking finds defects the reading-based diagnosis missed, measured
on the same corpus with the same scoring rules from Stage 1.

## Stage 10: Find how others solved it
Turn a specific defect into a searchable description, then return candidate
approaches from open source, products and research, each with a citable source.

Done when: given a defect from the corpus, the search returns ranked candidate
approaches with sources, plus a recorded judgement for each of whether it
transfers to this repo.

## Stage 11: Make the fix
Write the change into the repo — the idea taken from the source, the code
written fresh for this codebase.

Done when: for an agreed number of corpus instances, the system produces a
change that passes Stage 7's proof with no human involvement.

## Stage 12: Hand back a result
Deliver the improved repository in a form the submitter can use.

Done when: a completed run outputs an applicable change set with proven and
proposed changes separated, every proven change carrying its evidence, and every
proposed one carrying the source that inspired it — and a run against a repo
with no usable test suite produces *proposed* changes only, never *proven*.

## Stage 13: Get better with use
Store the idea and shape of each proven fix, indexed by the problem it solved,
and apply it to later repositories.

Done when: running the same repository twice — once with the database enabled,
once without — produces measurably different output, and that difference is
recorded.

---

# PART 4 — Can anyone use it?

## Stage 14: Public platform
A live site where anyone submits a public repository URL and gets a result,
running nowhere near a personal laptop.

Done when: a person who is neither Luke nor Alex submits a public repository
from their own machine and receives a result, with nothing running locally.

## Stage 15: Software discovery interface
The search half of the brief: find software by the problem it solves, built on
what the platform has learned.

Done when: Alex can use it without instruction and find a project relevant to a
problem he describes, that he did not already know about.

---

# PART 5 — Prototype 2

*In scope, sequenced last. Neither is needed to demonstrate the thesis, so
neither should delay Parts 1-3 — but the end goal is the whole brief, not a
prototype, and this part is where the rest of it lands.*

## Stage 16: The Auditor
Dead code and measurable slowness, both of which prove themselves: delete it and
the tests still pass, or time it before and after. "A smarter way to do this"
ships as *proposed*, never *proven*.

Done when: the Auditor reports dead code and speed improvements with evidence
attached, and anything unprovable appears only in the proposed section.

## Stage 17: Private repositories
Accept code that is not already public, with the promises that entails.

Done when: submitted code is provably deleted after a run, and every third party
it passes through is named on the page before submission.

---

# Open questions

Unresolved by design, each with the evidence that would settle it.

- **Corpus reach.** Published bug datasets are several years old, and old code
  needs old dependencies. If most instances cannot be made to run, that is a
  hard limit on Part 2 — nothing can be proved about code that cannot be
  executed. *Settled by: the proportion of the corpus that survives Stage 2.*
- **Contamination.** Every public dataset may sit inside the models' training
  data, so a good score may mean the fix was memorised. Bugs fixed after the
  training cutoff are the only clean measure. *Settled by: comparing scores on
  well-known versus obscure instances.*
- **What "finished" means to Alex.** The brief describes a company, and the
  committed scope here is all five parts. Whether he expects that, or a working
  demonstration of the thesis, changes how long Parts 4 and 5 are allowed to
  take. *Settled by: asking him.*
- **How long this gets.** Scope is the full brief with no stated deadline, and
  third year plus an existing daily newsletter are both live. *Settled by:
  putting a date on Part 2 specifically — if "better" cannot be proved by then,
  narrow the project to what can be.*
