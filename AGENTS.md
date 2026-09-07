# Standing instructions for agents working in this repo

## Always push when you finish a piece of work

When you finish a piece of work and commit it, **push it to origin before
telling Luke you are done.**

Work that only exists on this machine is invisible to the daily reviewer. The
reviewer runs at 02:00 on GitHub's servers, against whatever has been pushed.
It cannot see this machine, its processes, or anything sitting unpushed. An
unpushed day looks like an idle day, and it hands back tasks that are already
finished.

If a push fails, **say so plainly** rather than leaving it silently unpushed.

## Leave a note when a long job is running

The reviewer also cannot see a running process. A batch that takes three hours
looks identical to nothing happening at all.

So when starting a command expected to take **more than about twenty minutes**
— the batch paths in `run_diagnosis.py` and `build_instances.py` — write
`IN-PROGRESS.md` in the repo root, commit and push it:

```
# In progress
What: diagnosis batch, 30 instances
Started: 2026-09-07T21:14:03
Expected to finish: ~3h
Output lands in: results/
```

When the command finishes — **succeeded or failed** — delete the file, commit
and push again.

Two rules about it:

- **The marker must never delay or stop the actual work.** If a push fails,
  carry on with the batch. The marker is bookkeeping, not the job.
- **A marker still sitting there the next morning means the run died rather
  than finished.** That is useful information on its own, so do not clean up
  stale markers without saying what happened.

## Do not commit answer material

The whole point of this repo is that an AI under test cannot see the answers.
`keys/`, `BUILD-TASK.md` and anything derived from them stay out of git — see
`.gitignore`, which explains each exclusion. Before adding a new report or
output file, check whether it contains a bug's file, line or patch.

## Commit messages

Write a real sentence saying what changed. Not "update", not a version number.
The daily reviewer reads them.
