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
- **A change must improve one thing and harm none.** "Harmed nothing" is
  checkable; "worth it on balance" is a judgement, and judgements are what we
  are keeping out of the run.
- **Trade-offs are never applied, only proposed.** A change that improves one
  measure and worsens another goes into the suggestions with the downside
  spelled out — "closes a security hole but needs version X, which may break Y".
  The person who submitted the repo signs it off afterwards. Nobody is
  interrupted mid-run, so this does not break "no human guidance after
  submission".
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
- **Diagnose first, then take the wheel.** The six provable checks are what
  produce the list of problems; Alex's thesis is how each one gets solved. You
  cannot take a wheel until something tells you which is missing. Expect the
  first checks to feel mechanical - four of the six (still-runs, installs-
  cleanly, known holes, docs-mismatch) have fixes that need no searching at
  all. The searching earns its place on bugs and on speed, and most of all on
  the "smarter way" bucket that has no proof available.
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

Tuning uses **fresh instances each round** — roughly ten, adjust, then ten it has
never seen — rather than re-running the same set until the number rises. Reusing
a test teaches the test. The dataset holds 493 bugs and about 35 have been used,
so there is room for this.

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

**SCORING RULE DECIDED 2026-09-07:** "Still runs" is defined as:
test suite passes (if tests exist) OR package imports without error (if no tests).
With tests → proven. Without tests → proposed (downgraded). Full rules with
worked examples in SCORING.md.

Done when: every run emits that record, the system refuses to report "no
problems found" for any repo whose record shows it could not run anything, and
the check catches deliberately broken code (syntax errors, missing deps, etc.).

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
Alex's actual thesis - "why reinvent the wheel when you can just take it" -
and the reason the product exists at all. Turn a specific defect into a
searchable description, then return candidate approaches from open-source
projects, products, competitors and research, each with a citable source.

Done when: for defects from the corpus, an approach found by the search is
applied and **passes Stage 7's proof** - the failure gone, nothing else broken.

The earlier version of this finish line was "returns ranked candidates with a
recorded judgement of whether each transfers", which is a stage you complete by
producing a list. Plausible rubbish would have satisfied it. Searching is only
worth anything if something found outside the repo actually fixes something
inside it, so that is what gets measured.

### Design decided 2026-09-07

- **Two stores, never merged.**
  - *The LIBRARY* — fixes mined from other projects' git histories. Large,
    free, unverified. This is where the system goes looking.
  - *The DATABASE* — patterns that have actually worked on a real repository,
    with evidence attached. This is what makes the system smarter over time.
  - A pattern moves library -> database by being **used and proven** (Stage 7
    proof passed on a real instance), never by being found.
- **Promotion needs its own broken code, and it cannot be the corpus.** Raised
  by Luke 2026-09-07: the only repositories with known, proved-reproducible bugs
  are the corpus, and promoting entries by what works on the corpus, then
  measuring the database on that same corpus, is the "reusing a test teaches the
  test" failure from Stage 5 wearing a different hat. So a **third pile** is
  built - a *workshop pile* - from BugsInPy bugs that are in neither the
  practice nor the locked set. 493 bugs exist and about 35 are used, so there is
  ample room. Instances in the workshop pile are **never measured on**, and
  `manifest.py` records the split so the three cannot be confused.
  - Note the two bans are different and both hold: mining *from* cookiecutter is
    banned because cookiecutter's own fix **is** the exam answer. Fixing
    cookiecutter using a part mined from elsewhere is not an answer leak, it is
    simply the system doing its job. BugsInPy is therefore barred as a **source
    of parts** while remaining the right place to **prove** them.
- **Promotion requires repeated success, not a single one.** Luke's refinement,
  2026-09-07, adopted over the original "used and proven once": run the fixer
  across many broken repositories and promote what **keeps** working. One
  success is indistinguishable from luck or from a coincidental match.
  Provisional bar: passed Stage 7's proof on **3 different repositories**.
  - **Retrieval frequency is explicitly not evidence.** "Keeps getting pulled
    out" measures popularity, and popular junk is exactly what the found/proven
    split exists to keep off the shelf. Each entry therefore records *times
    retrieved* and *times it actually worked* separately; only the second
    promotes. The ratio between them is also the demotion signal - an entry
    retrieved often and working rarely is a bad match rule, and gets dropped.
- **An entry is a shape, not a diff.** Follows "take the idea, not the code":
  ideas are not copyrightable, specific code is, and an idea transfers to
  another codebase where a diff does not. Four fields:
  `Problem` (what was wrong, in transferable terms) / `Fix shape` (the approach,
  not the patch) / `Source` (project + commit) / `Status` (found | proven).
- **Raw material.** `build_instances.py` already finds the commit that fixed a
  bug and extracts its diff, then throws the fix away and keeps the broken
  version. Point the same machinery the other way: keep the diff + message +
  source as a library entry.
- **Contamination firewall.** Two project lists that must never touch. The
  mining list excludes every project named in `MANIFEST.md`. If the library
  holds fixes from the projects the exam uses, the system has been handed the
  answers and the catch rate rises for no real reason. The miner **refuses** a
  corpus project rather than relying on anyone remembering.
- **Integration point: the fixer.** When a defect is found, matching library /
  database entries are retrieved and injected into the fix prompt as candidate
  approaches. "Output" for the on/off check (Stage 13) is therefore the fix and
  whether it passes Stage 7's proof.
- **Build order.** The on/off check first (Stage 13), then the simplest store
  that works — one small file per entry, in a folder, in git, plain keyword
  search. Only reach for anything cleverer once simple matching can be **shown**
  failing.
- **Mining sources: a hand-picked list, outside BugsInPy entirely.** Decided by
  Luke 2026-09-07, choosing this over the six unused BugsInPy projects. Those
  six are too few, four are very large ML libraries, and using them would rule
  them out as future corpus instances. The list starts at 15-30 repositories and
  is expected to grow to 100-200; it therefore lives in a plain file
  (`mining-sources.txt`, one repository per line) rather than in code.
- **The firewall excludes all of BugsInPy, not just the corpus.** Excluding only
  what is in `MANIFEST.md` today leaves a retroactive hole: build a corpus
  instance from pandas next month and every pandas fix already in the library
  becomes an answer key, with nothing to flag it. So the miner refuses any
  repository matching a project in `MANIFEST.md` *or* present in `BugsInPy/
  projects/`, read at run time rather than copied into code, and refuses rather
  than warning.
- **The firewall is also a standing check**, in the manner of
  `check_prompt_sync.py`: a committed check that re-scans the library and fails
  if any entry's source is a corpus or BugsInPy project. Refusing at mine time
  only catches contamination going in; the check catches it after the fact, when
  the corpus is what changed.
- **Mining is free; labelling is metered.** Pulling fix commits out of git
  history costs nothing but disk. Turning a diff into the four-field shape needs
  a model to read it. Corrected 2026-09-07 after Luke pushed back: that is plan
  usage, not a cash bill, so the currency is **wall-clock time and plan quota**,
  not pounds. It still scales with the whole library while the benefit only
  applies to entries actually retrieved.
- **Measured yield, 2026-09-07** (not estimated): `requests` has 6,494 commits,
  729 whose message starts "fix", **365** of those touching 1-3 `.py` files.
  `click`: 3,362 / 497 / **239**. So roughly **300 candidate parts per
  repository** - about 9,000 at 30 repos, 60,000 at 200. Message noise is heavy
  and cheap to filter: a sample of 25 held "Fix remaining typos", "Fix typos
  discovered by codespell", "Fix CI and build failures", "Fix httpbin pin for
  test suite", alongside genuinely transferable ones like "Fix empty netrc entry
  usage" and "Fix malformed value parsing for Content-Type". A keyword blocklist
  (typo, docs, CI, lint, changelog, pin, format) removes roughly a third for
  free.
- **The label format is unproven, so it is not committed to at scale.** The
  four fields are a first guess. Labelling every part before retrieval has been
  shown to work locks in a format that has never been tested, and relabelling is
  the whole bill again.
- **Label a small batch first, not everything.** Decided by Luke 2026-09-07.
  The four fields are an untested guess, and labelling at scale before
  retrieval has been shown to work locks in a format that would then cost the
  whole run again to change.
- **Mine 20 and judge them before mining more.** Luke, 2026-09-07, same
  discipline: do not build a library on extraction nobody has looked at.

### Mining quality, measured by hand on 20 parts (2026-09-07)

Three rounds of hand-scoring moved usable parts from **13/20 to 15/20**. Each
round found a different dominant dud, and none of them was guessable up front:

1. **Fixes that only touch the project's own tests** (3 of the first 7 duds) -
   housekeeping, not a solved problem. A fix touching source *and* test is the
   best kind there is, since the test is the proof; test-only is worthless.
2. **Typing churn** ("Fix typing", "fix pyright findings", "Fix issues
   previously type ignored") became dominant once the test-only ones were gone.
   Changes annotations, not behaviour.
3. **Docs and packaging** - `docs/conf.py` slipped through an exclusion that
   named only `conftest.py`.

**The finding that matters is none of those.** Repo choice dominates filter
tuning:

| source | usable of 10 | ship a test with the fix |
|---|---|---|
| `psf/requests` | 9-10 | 7 |
| `pallets/click` | 5-6 | 3 |

Three rounds of blocklist tuning bought 10 percentage points; picking requests
over click buys 35. Mature libraries where "fix" means a real defect are worth
far more than clever filtering, and further blocklist tuning on a 20-part
sample would be fitting to noise. **So the next lever is the source list, not
the filters.**

Also worth carrying forward: **"ships a test alongside the fix" is a free
quality signal** and tracked per part as `has_test`. Those parts come with
the original project's own proof of what the fix was for.

### Labelling the first 20 (2026-09-07)

**15 became entries, 5 were refused, 0 failed.** Tags are free-form, per Luke's
call the same day.

**Letting the labeller refuse a part was the highest-value decision here.** All
five refusals were duds the mechanical filters had passed - "broadens a static
type annotation", "corrects a parameter name in documentation", "adds spacing
in help text", "corrects terminology in an error message". No blocklist would
have caught those; a model reading the diff caught every one. Refusals are now
recorded on the raw part, so a dud is never paid for twice.

**Two faults the run exposed, both fixed:**

1. **Replacement characters reached three entries.** Entries are injected
   verbatim into the fixer's prompt, so this is the corrupted-prompt bug from
   the harness bug list arriving by a new route. Entries are now forced to
   ASCII at write time, and `check_library_clean.py` fails on any non-ASCII
   character in a stored entry - the same rule `check_prompt_sync.py` applies
   to the prompt.
2. **The leak check rejected a good entry for containing the word
   "exceptions"** - an ordinary English word that is also a filename in the
   source project. Generic module names are now exempt.

**Retrieval after labelling: better, and not yet trustworthy.** The flagship
earlier failure is fixed - the mixed line-endings defect now ranks an encoding
entry first, where before it ranked a mutable-default entry on the words "one"
and "whose". But **15/15 findings now retrieve something, up from 10/15, and
that is not evidence of improvement**: more entries simply means more chances
to clear a two-word floor. Confident wrong matches remain, e.g. a
"chooses the lexicographically smallest path" defect matching a "spaces in
filepaths on Windows" entry at high score on shared path vocabulary. Whether
any of this helps is exactly what `ab_fix.py` exists to answer, and it has not
been run yet.

Embedding decision implemented: **search matches on the Problem text and tags
only, never the Fix shape.** A problem resembles another problem, not a cure;
matching symptoms against treatments is how retrieval quietly underperforms.

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

### Design decided 2026-09-07

- **This check is built before the store, not after.** Storing entries is easy;
  getting the right one back out is the whole difficulty, and a store you
  cannot show is contributing is decoration however many entries it holds.
- **What it does.** Run one instance through the fixer twice — once with
  retrieved entries in the prompt, once without — and record, for each side:
  did the fix pass Stage 7's proof (failure gone, project's own tests no worse),
  how many attempts it took, and whether it landed where the real fix landed.
- **The difference is the artefact.** Written to `reports/`. If enabling the
  database changes none of those, that is the finding and it is recorded as
  such.
- **First run uses a hand-made library** of a few entries, before the miner
  exists, so the A/B plumbing is proved on something cheap.

### Built 2026-09-07

`library.py`, `ab_fix.py`, `check_library_clean.py`, `--library` on
`fix_bug.py`, and three hand-written seed entries. Two folders, `library/` and
`database/`; promotion is a literal file move, so the stores can be counted and
cannot quietly merge.

Proved by breaking on purpose, in this repo's usual manner: a planted
cookiecutter-sourced entry is refused by `check_library_clean.py`, and
promotion was shown to require three *different* repositories (two bugs in the
same project correctly counted once).

**Credit is attributed to one entry, not smeared.** With the store on, the
fixer must name the `[id]` it actually used, and credit is refused if the fix
did not pass the proof or if it names an entry it was never offered.

**Already measured, before any fixer run: simple keyword search is noisy.**
Across 15 real findings and 3 entries, single-word matches were junk without
exception - a Windows CPU-count crash matched a text-encoding entry on
"fallback"; an `IndexError` matched a path-traversal entry on "containing". A
floor of two shared words removed those (10 of 15 findings still retrieve
something). What remains is wrong *ranking*: a CRLF/decoding defect ranks the
mutable-default entry above the encoding entry, on the words "one" and "whose".
Recorded in `reports/retrieval-seed-probe.txt`. This is the "show simple
matching failing" evidence the brief asks for, though it is not yet decisive -
three hand-written entries is too small a library to conclude from, and it must
be re-measured against mined entries.

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
Six kinds of improvement that can be proved rather than argued:

- **Security** — a dependency with a publicly known hole either has it or does
  not. Cheap, objective, and needs no AI.
- **Still runs** — does it work on current versions of the language? Cheap, and
  invisible to the owner, whose own machine works fine.
- **Speed** — time it before and after. Harder than it sounds: most projects
  have nothing to time, so a benchmark has to be written, and then part of what
  is being measured is our own benchmark.
- **Dead code** — delete it, the tests still pass.
- **Does what its documentation claims** - the README says this returns a
  list; run it, it returns a generator. The provable slice of functional
  suitability: you cannot check whether software does what a user wanted, but
  you can check whether it does what it says about itself.
- **Installs cleanly from scratch** - the provable slice of compatibility.
  Projects routinely import something they forgot to declare; it works on the
  author's machine and nowhere else. Install in a clean environment with only
  what it declares, and run it. Seen live: luigi failed exactly this way
  during corpus building.

Usability is excluded outright: for a library it means whether the design
is pleasant, which is taste with no test behind it.

"A smarter way to do this" has no proof available and ships as *proposed*,
never *proven*. Metrics that score how tangled code is are guesses about
quality, not measures of it — a number can improve while the code gets worse.

Done when: each of the four reports improvements with evidence attached, and
anything unprovable appears only in the proposed section.

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
- **Scope is Luke's call, and it is made: all five parts.** The brief came from
  Alex but the decision about how much of it gets built does not. Recorded here
  so nobody re-opens it by going back to the brief and reading ambition into it.
- **How long this gets — deliberately left open.** Luke declined a deadline on
  2026-09-07. Worth revisiting only if Part 2 stalls, since everything
  downstream assumes it works.
