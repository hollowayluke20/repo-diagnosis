# repo-diagnosis

A test harness that measures, honestly and repeatably, how well an AI finds
bugs in code it has never seen — and, increasingly, whether it can fix them.

Real bugs come from [BugsInPy](https://github.com/soarsmu/BugsInPy). Each
project is rebuilt at the moment its bug existed, everything that gives the
answer away is stripped out, and the bug is **proved to reproduce** before the
instance counts. An AI agent is then put in front of it with no internet, no
memory between runs, and no path to the answers.

The full project plan is in `PLAN.md`. The scoring rules are in `SCORING.md`
and were written before any batch ran.

## The route from clone to numbers

```
python build_instances.py --bug cookiecutter/1 --bug httpie/3 ...
    Builds each instance: clone at the buggy commit, delete .git, provision
    the Python version the project needs INSIDE the instance folder, install
    its dependencies, then run the bug's own test and require it to FAIL.
    Writes keys/<instance>.json and reports/rejections.md.

python manifest.py
    Writes MANIFEST.md, the committed list of what is in the corpus.
    --rebalance 0.7 reassigns the practice/locked split, and refuses once any
    results exist.

python run_diagnosis.py               # the practice pile
python run_diagnosis.py --only NAME   # one instance
    Sends prompts/diagnosis-v3.txt to each instance via headless Codex.
    Saves the prompt actually sent alongside the raw reply in results/.

python score.py
    Runs every reproduction script the AI supplied and reports two numbers:
    catch rate (did it find the catalogued bug) and confirmation rate (are its
    findings real at all). Writes reports/scores.md.

python fix_bug.py --instance NAME --finding 1
    Asks the AI to fix a defect it found, on a COPY, then checks the
    reproduction passes, the project's own tests still pass, and whether it
    changed where the real fix changed.
    --phantom invents a defect that is not there, to see whether it says so.

python check_prompt_sync.py
    Fails if a second copy of the prompt appears, or if the prompt contains
    any non-ASCII character. Both have caused silent corruption already.
```

## IN-PROGRESS.md

**If you see a file called `IN-PROGRESS.md` in this repo, it is not stray
junk.**

The daily reviewer runs at 02:00 on GitHub's servers and can only see what has
been pushed. It cannot see this machine or anything running on it, so a batch
that takes three hours looks exactly like an idle evening.

So when a long job starts — the batch paths in `run_diagnosis.py` and
`build_instances.py`, anything over about twenty minutes — that file is written,
committed and pushed automatically. It says what is running, when it started,
roughly how long it should take, and where the output will land. When the job
ends, succeeded or failed, the file is deleted and that is pushed too.

**A marker still present the next morning means the run died rather than
finished.** That is useful on its own, so do not quietly delete a stale one —
say what happened to it.

Writing the marker is best-effort and never blocks the job. If the push fails,
the batch carries on and the failure is printed.

## What is deliberately not in git

`keys/`, `BUILD-TASK.md`, and any report derived from them. The whole point of
the setup is that the AI under test cannot reach the answers, and that extends
to anything reading this repository. `.gitignore` explains each exclusion.

Also excluded: `instances/` (about 3.4GB — each carries its own Python
installation, all reproducible from `build_instances.py`), `BugsInPy/` and
`src/` (downloaded, not written here), and `fixes/` (working copies).

See `AGENTS.md` for standing instructions if you are an agent working here.
