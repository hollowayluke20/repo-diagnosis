"""IN-PROGRESS.md: a note to the daily reviewer that a long job is running.

The reviewer runs at 02:00 on GitHub's servers and can only see what has been
pushed. A three-hour batch and an idle evening look identical to it.

Nothing in here may ever delay or break the job it is marking. Every git call
is best-effort and every failure is swallowed with a printed warning.

Usage:
    with progress_marker("diagnosis batch, 23 instances", "results/", "~2h"):
        ...the long job...
"""
import contextlib, subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
MARKER = ROOT / "IN-PROGRESS.md"


def _git(*args):
    """Best effort. A failed push must not stop a batch."""
    try:
        p = subprocess.run(["git", *args], cwd=str(ROOT), capture_output=True,
                           text=True, errors="replace", timeout=120)
        return p.returncode == 0, (p.stdout or "") + (p.stderr or "")
    except Exception as e:
        return False, str(e)


def _commit_and_push(message):
    ok, out = _git("add", "IN-PROGRESS.md")
    ok, out = _git("commit", "-m", message, "--", "IN-PROGRESS.md")
    if not ok and "nothing to commit" not in out:
        print(f"  [marker] commit failed: {out.strip()[:160]}")
    ok, out = _git("push", "origin", "HEAD")
    if not ok:
        # say so plainly, then carry on - the batch matters more
        print(f"  [marker] PUSH FAILED, marker is local only: "
              f"{out.strip()[:160]}")


@contextlib.contextmanager
def progress_marker(what, output_path, expected="unknown"):
    MARKER.write_text(
        "# In progress\n\n"
        f"What: {what}\n"
        f"Started: {datetime.now().isoformat(timespec='seconds')}\n"
        f"Expected to finish: {expected}\n"
        f"Output lands in: {output_path}\n\n"
        "This file is written automatically when a long job starts and deleted\n"
        "when it ends. If it is still here, either the job is running or it\n"
        "died. See README.\n",
        encoding="utf-8")
    _commit_and_push(f"Start: {what}")
    try:
        yield
    finally:
        # deleted whether the job succeeded or blew up - a marker that outlives
        # the run is exactly the signal we want
        MARKER.unlink(missing_ok=True)
        _commit_and_push(f"Finished: {what}")
