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

---

# PART 3 — Security check (Stage 6)

*Two checks that share nothing but plumbing. Both are mechanical - a lookup
and a pattern search - and neither uses an AI. Built in `check_known_holes.py`
and `check_exposed_secrets.py`, with `security_common.py` shared and
`security_selftest/` holding the fixtures. Isolated from the folders other
agents work in.*

## The one thing both checks must never do

Neither check ever says "this repository is at risk" or "this is
exploitable". Reachability - whether the vulnerable code path is actually hit
the way this project uses it - is a separate, much harder claim, and we do
not make it. The strongest thing either check says is:

- **check 1:** "this repo pins `<library>` to `<version>`, and advisory
  `<ID>` is recorded against that exact version."
- **check 2:** "at `<file>:<line>` there is a string matching the shape of a
  `<credential kind>`, and it is not one of the placeholder / example
  patterns we filter out."

## Check 1 - known holes in declared libraries

### What is checked

Every dependency the instance **pins to an exact version** (`==` or `===`).
Sources, in order: the pinned freeze BugsInPy captured for the bug
(`BugsInPy/projects/<p>/bugs/<b>/requirements.txt` - this is exactly what
`build_instances.py` installs, so it is the instance's real dependency set),
then any `requirements*.txt` shipped inside the repo, then `== ` pins found
in `setup.py` / `setup.cfg` / `pyproject.toml`.

The lookup is [OSV](https://osv.dev) - the same advisory data pip-audit and
Dependabot use. We send a package name and an exact version; OSV does the
version-range matching server-side and returns the advisories that apply.
Responses are cached under `security_cache/` (git-ignored) so a second run is
offline and repeatable. OSV returns the same underlying flaw as both a GHSA
and a PYSEC record; these are collapsed on the shared CVE so the count is
distinct advisories, not database duplication.

### The three verdicts

**HIT** - at least one pinned dependency matched at least one advisory. The
report lists library, version, advisory ID, CVE alias and summary for each.

**CLEAN** - at least one dependency was pinned, every lookup completed, and
nothing matched. *In practice no real corpus instance reaches this* - every
instance is pinned to 2020-era versions and old pins always have advisories
recorded against them by now. CLEAN is reachable and is proved reachable by
the `security_selftest/clean/` fixture (current, stable pins, stays silent);
it is just not where a five-year-old snapshot lands.

**UNKNOWN** - *nothing could be checked.* No dependency file found, or a file
was found but declares no exact pins (all `>=` / unpinned), or the advisory
database could not be reached. This is a **separate answer from CLEAN**. A
repo we could not check is not a repo we proved safe. `youtube-dl` is the
worked example: it declares zero install dependencies, so the honest verdict
is UNKNOWN, not "clean".

### Undecidable, spelled out

- **no manifest** -> UNKNOWN, reason "no dependency file found".
- **manifest present, nothing pinned** -> UNKNOWN, reason "dependencies are
  declared but none pin an exact version".
- **database unreachable** (any lookup failed) -> UNKNOWN if there are no
  hits, or HIT listing what did match with the verdict flagged incomplete -
  never CLEAN.
- **unreadable manifest** (binary / could not decode any text encoding) ->
  listed under `undecidable_files`; if it was the only source, UNKNOWN.
  Note: BugsInPy ships some `requirements.txt` as UTF-16 (luigi, black); the
  reader tries utf-8-sig / utf-16 / utf-8 / latin-1 before giving up, so
  those are read, not called undecidable.

### Worked example - a real hit

`tornado-1`, run 2026-09-08. The instance pins exactly one package,
`tornado==6.0.4` (from the BugsInPy freeze, which is UTF-16 - decoded fine).

OSV returns 17 distinct advisories recorded against `tornado==6.0.4`,
including `GHSA-hj3f-6gcp-jg8j` / `CVE-2023-28370` (open redirect),
`GHSA-8w49-h785-mj3c` / `CVE-2024-52804` (cookie-parsing DoS) and
`GHSA-753j-mpmx-qq6g` (HTTP request smuggling).

**How it is counted:** verdict **HIT**, 1 library, 17 advisory matches. The
report row is *"tornado==6.0.4 has 17 advisories recorded against it"* - not
*"tornado-1 is vulnerable to request smuggling"*. Several of these advisories
were published years after the instance was built; that does not change the
claim, which is only about what is recorded against the version. The advisory
set grows over time, so the number is dated in the report and re-runnable.

## Check 2 - exposed secrets in the repo text

### What is checked

Every readable text file under the instance (binaries, `.python/`,
`site-packages/`, `node_modules/`, caches and files over 1.5 MB are skipped).
Two kinds of match:

1. **Provider shapes** - regexes specific enough that the shape alone is
   meaningful: `AKIA…`/`ASIA…` AWS keys, `ghp_…` GitHub tokens, `xox[baprs]-`
   Slack tokens, `AIza…` Google keys, `sk_live_…` Stripe, `-----BEGIN …
   PRIVATE KEY-----` blocks, and a few more.
2. **Generic assignment** - a variable or key whose name contains
   `password` / `secret` / `token` / `api_key` / … assigned a quoted string
   that is the *entire* right-hand side (not a fragment of an expression or a
   URL template), at least 16 characters, high-entropy.

### Not crying wolf

A false alarm here reads as "you leaked a credential" - far scarier than "a
dependency is old" - so a match only becomes a finding after filters:

- **Known fakes** - AWS's own `AKIAIOSFODNN7EXAMPLE`, etc.
- **Placeholder values** - contains `example` / `sample` / `dummy` / `your` /
  `changeme` / `xxxx` / `<…>` / `{{…}}` / `getenv` / keyboard runs
  (`qwer5678`) / a value that is all one character / all digits / not random
  enough for its length.
- **Path trust** - a match in a `test` / `tests` / `docs` / `docs_src` /
  `example` / `demo` / `fixture` path, or in a `.pem` / `.key` / `.crt`
  file, is recorded as **review-only** and does **not** drive the verdict.
  That is where test certificates and tutorial keys live, and calling those
  a leak is the exact failure to avoid. Generic assignments are ignored
  entirely in those paths; only provider-shaped matches are even recorded.

### The three verdicts

**HIT** - at least one finding in a **normal source path** (not test / doc /
fixture) survived every filter.

**CLEAN** - text was scanned and nothing survived in a normal path. The
report still lists any review-only matches from test/doc/fixture paths.

**UNKNOWN** - no readable text file was found to search at all (everything
binary or undecodable). "Could not look" is not "looked and found nothing".

### Undecidable, spelled out

- **no readable text** (`files_scanned == 0`) -> UNKNOWN.
- **some files unreadable** -> counted in `files_unreadable` and sampled in
  the report, but if anything readable was scanned the verdict stands on
  what was scanned.
- **match only in a lower-trust path** -> `review_only`, verdict CLEAN.

### Worked example - a real hit and a real non-hit

`youtube-dl-1`, run 2026-09-08.

**Hit:** `youtube_dl/extractor/shahid.py:41` -
`'access_key': 'AKIAI6X4TYCIXM2B7MUQ'` - an AWS access key ID hardcoded in a
normal source file. Plus 11 more (`_API_KEY`, `_APIKEY`, `_CONSUMER_SECRET`,
`_AUTH_TOKEN` assignments, two hardcoded JWTs) across the extractor modules.
youtube-dl embeds the target sites' own API keys on purpose; that does not
change the claim, which is *"a credential-shaped string is at this line"*,
verifiable by opening the file. Verdict **HIT**, 12 findings, all redacted in
the report (first 4 and last 2 characters only).

**Non-hit, same repo:** `test/testcert.pem` contains a
`-----BEGIN PRIVATE KEY-----` block. It is a real private key by shape, but
it sits in a `test` path and a `.pem` file - a test fixture. Recorded as
**review-only**, does **not** make the verdict HIT.

**Non-hits elsewhere:** `fastapi`'s `docs_src/security/tutorial004.py` pins
`SECRET_KEY = "09d25e09…"` with a comment saying `# openssl rand -hex 32` -
a tutorial example in a `docs_src` path, filtered. `tornado`'s
`demos/twitter/twitterdemo.py` has `twitter_consumer_secret = 'qwer5678'`
inside a docstring - keyboard-run placeholder, filtered.

## Proving both checks can fail

`python check_known_holes.py --self-test` and
`python check_exposed_secrets.py --self-test`, both run before trusting the
checks on real instances:

**check 1**
1. `security_selftest/vulnerable/` (`Jinja2==2.11.2`, `PyYAML==5.3`,
   `urllib3==1.25.8`) -> must be **HIT** with named real advisories.
2. `security_selftest/clean/` (current stable pins) -> must be **CLEAN**,
   zero matches.
3. `security_selftest/unpinned/` (`requests`, `flask>=2.0`, …) -> must be
   **UNKNOWN**, never CLEAN.
4. Forced offline lookup of an uncached package -> must raise, producing
   **UNKNOWN**, never CLEAN.

**check 2**
1. Planted `AKIA…`, `ghp_…` and a private-key block in normal paths -> must
   all be **HIT**.
2. Planted `your-api-key-here`, `example_password`, `AKIAIOSFODNN7EXAMPLE`,
   `ghp_0000…`, `AIzaSy…DUMMY…` -> must be **CLEAN**, zero false alarms.
3. Planted real-shape private key in `tests/certs/server.key` -> must be
   **review-only**, verdict not HIT.
4. A directory with only an unreadable binary -> must be **UNKNOWN**, never
   CLEAN.

## Results

**Control (before real instances):** the `security_selftest/clean/` fixture
and the placeholder fixture both stay silent - the checks do not invent
findings on clean input. Proved by the self-tests above, every branch.

**Round 1 - 10 practice instances** (black-1, cookiecutter-1, fastapi-1,
httpie-1, luigi-1, sanic-3, thefuck-1, tornado-1, tqdm-4, youtube-dl-1),
2026-09-08:

- check 1: **9 HIT, 1 UNKNOWN** (youtube-dl, no declared dependencies),
  0 CLEAN. Every pinned old project has advisories - expected and correct.
- check 2: **1 HIT** (youtube-dl - real embedded API keys in extractor
  source), 9 CLEAN. First pass flagged 5; the extra 4 were test TLS certs
  and a FastAPI docs tutorial key. Reconfigured: test/doc/fixture/`.pem`
  paths are now review-only, generic assignments need a full 16+ char
  high-entropy RHS. After that: 0 false alarms.

**Round 2 - 10 fresh practice instances** (black-2, cookiecutter-2,
fastapi-2, httpie-2, luigi-10, sanic-5, spacy-2, thefuck-2, tornado-2,
tqdm-5), 2026-09-08: same shape - check 1 all HIT, check 2 all CLEAN (three
with review-only test-cert matches). No further reconfiguration needed; the
round-1 filters held on instances they had never seen.

**Full practice batch:** see `reports/known-holes.md` and
`reports/exposed-secrets.md`. `known-holes.md` is committed (it is a list of
public CVEs against old pins - no answer material). `exposed-secrets.*` is
git-ignored - it quotes real credential material where any exists.
