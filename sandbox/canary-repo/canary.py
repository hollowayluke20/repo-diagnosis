"""
The canary repository.

This stands in for a repository a stranger submitted to the platform. It is
written to be badly behaved on purpose, so that we can tell whether the box we
put it in actually holds. A cage that has never had anything thrown at it is
not known to work.

It makes the three attempts Stage 8 names:

  1. read a file outside its own workspace
  2. reach the network
  3. write to the host filesystem

Run it outside the box and all three should succeed. Run it inside the box and
all three must fail, with the operating system doing the refusing. The gap
between those two runs is the entire proof.

Every attempt is wrapped so it can never raise. A crash and a refusal look
identical from outside the process, and we need to tell them apart, so each
attempt reports its own outcome:

  NOT BLOCKED -> the attempt worked
  BLOCKED     -> the operating system refused it

Nothing here is clever, and it is not supposed to be. Clever would prove less:
if the plain version gets through, there is no point testing the subtle one.
"""

import json
import os
import sys
import urllib.request

# Files that belong to the host, not to this repository. The answer keys are
# the ones that genuinely matter -- the whole harness depends on submitted code
# never reaching them -- and the reports are our own output. If this process can
# open either, the platform has already lost.
FILES_IT_SHOULD_NOT_REACH = [
    r"C:\Users\hollo\dev\repo-diagnosis-keys\cookiecutter-1.json",
    r"C:\Users\hollo\dev\repo-diagnosis\reports\portability.md",
]
SITE_IT_SHOULD_NOT_REACH = "http://example.com/"
FILE_IT_SHOULD_NOT_CREATE = r"C:\Users\hollo\sandbox-leak-canary.txt"

results = []


def record(attempt, blocked, detail):
    print(f"[{'BLOCKED' if blocked else 'NOT BLOCKED'}] {attempt}: {detail}",
          flush=True)
    results.append({"attempt": attempt, "blocked": blocked, "detail": detail})


def attempt_read_outside_workspace():
    """Attempt 1: read a file that lives outside the workspace."""
    refusals = []
    for path in FILES_IT_SHOULD_NOT_REACH:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                first_line = fh.read(100).replace("\n", " ")
            record("read-outside-workspace", False,
                   f"opened {path} and read: {first_line!r}")
            return  # one success is a full breach, no need to prove it twice
        except FileNotFoundError:
            # Absent rather than forbidden. That proves nothing either way, so
            # it is not counted as a block -- move on to the next target.
            refusals.append(f"{path}: not present")
        except OSError as e:
            refusals.append(f"{path}: {type(e).__name__}")
    record("read-outside-workspace", True,
           "refused every target -- " + "; ".join(refusals))


def attempt_reach_network():
    """Attempt 2: open a connection to the outside world."""
    try:
        with urllib.request.urlopen(SITE_IT_SHOULD_NOT_REACH, timeout=10) as r:
            record("reach-network", False,
                   f"connected to {SITE_IT_SHOULD_NOT_REACH}, HTTP {r.status}")
    except Exception as e:  # noqa: BLE001 -- any failure to connect is a block
        record("reach-network", True,
               f"could not reach {SITE_IT_SHOULD_NOT_REACH} -- "
               f"{type(e).__name__}: {e}")


def attempt_write_to_host():
    """Attempt 3: create a file on the host, outside the workspace."""
    try:
        with open(FILE_IT_SHOULD_NOT_CREATE, "w", encoding="utf-8") as fh:
            fh.write("Submitted code was able to write here.\n")
        record("write-to-host", False, f"created {FILE_IT_SHOULD_NOT_CREATE}")
    except OSError as e:
        record("write-to-host", True,
               f"could not create {FILE_IT_SHOULD_NOT_CREATE} -- "
               f"{type(e).__name__}: {e}")


def main():
    print("canary repo starting", flush=True)
    print(f"  working directory: {os.getcwd()}", flush=True)

    attempt_read_outside_workspace()
    attempt_reach_network()
    attempt_write_to_host()

    blocked = sum(1 for r in results if r["blocked"])
    print(f"canary repo finished: {blocked} blocked, "
          f"{len(results) - blocked} not blocked", flush=True)

    # Leave the verdict beside the code as well as on stdout. Writing inside its
    # own workspace is allowed; if even this fails, stdout still tells the story.
    try:
        with open("canary_result.json", "w", encoding="utf-8") as fh:
            json.dump({"blocked": blocked,
                       "not_blocked": len(results) - blocked,
                       "results": results}, fh, indent=2)
    except OSError:
        pass

    # Always exit 0. Whether the box held is judged from the log by the harness,
    # not self-reported by the code under test.
    sys.exit(0)


if __name__ == "__main__":
    main()
