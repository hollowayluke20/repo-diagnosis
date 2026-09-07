"""
The sealed workspace.

Stage 8 in PLAN.md: every submitted repository executes inside a throwaway
sealed workspace -- no network, no access to the host filesystem, nothing
shared between runs, destroyed afterwards.

The standing decision this is built on: security by isolation, not inspection.
Nothing here looks at a repository and decides whether it seems safe. Hostile
code hides on purpose, so judging it by reading it fails eventually and fails
silently. Instead everything is contained, and the question of which submission
was dangerous never has to be answered.

How a run goes:

  1. A fresh folder is made outside this repository, named after the run.
  2. The submitted code is copied into it. The original is never executed.
  3. A container identity is created -- an account that owns nothing.
  4. That identity is granted access to exactly two folders: the workspace it
     may read and write, and a read-only copy of Python it may execute.
  5. The code runs as that identity, with the host's environment variables
     withheld and its output captured through pipes rather than files, so the
     code cannot edit the record of what it did.
  6. The folder is deleted and the container identity destroyed.

Everything else on the machine is untouched not because we forbade it, but
because the identity doing the running was never on the permission list.

The runtime, explained: Windows will not let a non-administrator change
permissions on a system-wide Python installation, and the container cannot
execute what it has no permission to read. So a copy of Python is made once,
in a folder this account owns, and granted read-and-execute to the container.
It is read-only and holds no run data, so sharing it between runs shares
nothing -- it is the equivalent of a container base image. The workspace, which
is the part that holds actual data, is never shared.
"""

import json
import os
import shutil
import subprocess
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _appcontainer as ac  # noqa: E402

# Everything lives outside the repository. Submitted code should not be able to
# see this project even by accident of layout.
BOX_ROOT = os.path.join(os.environ["LOCALAPPDATA"], "repo-diagnosis-box")
RUNTIME_DIR = os.path.join(BOX_ROOT, "runtime")
RUNS_DIR = os.path.join(BOX_ROOT, "runs")

# One stable name. Windows derives the container identity from it, so the
# read-only runtime can be granted once and stay valid across runs, while the
# profile itself is deleted and remade each time to clear its storage.
CONTAINER_NAME = "repo-diagnosis-box"


def _icacls(path, sid_string, rights):
    """Add one permission entry. Returns (ok, output).

    (OI) and (CI) mean the entry is inherited by files and folders underneath.
    """
    result = subprocess.run(
        ["icacls", path, "/grant", f"*{sid_string}:(OI)(CI){rights}", "/T", "/Q"],
        capture_output=True, text=True)
    return result.returncode == 0, (result.stdout + result.stderr).strip()


def provision_runtime(source_python=None, log=print):
    """Make the read-only copy of Python the container is allowed to execute.

    Done once. Later runs reuse it. Copying ~150MB takes a moment the first
    time and nothing thereafter.
    """
    source = source_python or os.path.dirname(sys.executable)
    marker = os.path.join(RUNTIME_DIR, "python.exe")
    if os.path.exists(marker):
        return RUNTIME_DIR

    log(f"  provisioning runtime (one-off copy of {source})")
    os.makedirs(BOX_ROOT, exist_ok=True)
    if os.path.exists(RUNTIME_DIR):
        shutil.rmtree(RUNTIME_DIR, ignore_errors=True)
    shutil.copytree(source, RUNTIME_DIR)
    log(f"  runtime ready at {RUNTIME_DIR}")
    return RUNTIME_DIR


def run_sealed(repo_dir, command, timeout_seconds=120, log=print,
               collect=()):
    """Run `command` against a copy of `repo_dir`, sealed. Returns a dict.

    `collect` names files to read back out of the workspace before it is
    destroyed, for the caller to inspect.
    """
    repo_dir = os.path.abspath(repo_dir)
    if not os.path.isdir(repo_dir):
        raise ValueError(f"not a directory: {repo_dir}")

    provision_runtime(log=log)

    run_id = uuid.uuid4().hex[:12]
    workspace = os.path.join(RUNS_DIR, run_id)
    work_repo = os.path.join(workspace, "repo")
    work_temp = os.path.join(workspace, "tmp")

    log(f"  workspace {workspace}")
    os.makedirs(workspace, exist_ok=True)
    shutil.copytree(repo_dir, work_repo)
    os.makedirs(work_temp, exist_ok=True)

    sid = ac.ContainerSid(CONTAINER_NAME)
    result = {"run_id": run_id, "workspace": workspace}

    try:
        sid.create()
        sid_string = sid.as_string()
        result["container_sid"] = sid_string
        log(f"  container identity {sid_string}")

        # The two grants. Nothing else on this machine names this identity,
        # which is what makes everything else unreachable.
        ok, detail = _icacls(workspace, sid_string, "(F)")
        if not ok:
            raise OSError(f"could not grant the workspace: {detail}")
        ok, detail = _icacls(RUNTIME_DIR, sid_string, "(RX)")
        if not ok:
            raise OSError(f"could not grant the runtime: {detail}")
        log("  granted: workspace (read/write), runtime (read/execute only)")

        python_exe = os.path.join(RUNTIME_DIR, "python.exe")
        full_command = command.replace("python", f'"{python_exe}"', 1)

        # An allowlist, not a filtered copy of the host's environment. The host
        # environment carries API keys and account paths; a denylist would leak
        # every variable we failed to think of, so nothing is inherited at all
        # and the few Windows needs are named here.
        #
        # LOCALAPPDATA is required: without it the container refuses to start
        # with error 203, because Windows redirects that path into the
        # container's own storage as the process launches. It is a path, not a
        # secret, and the container cannot read the real folder behind it.
        environment = {
            "SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"),
            "LOCALAPPDATA": os.environ.get("LOCALAPPDATA", ""),
            "PATH": RUNTIME_DIR,
            "TEMP": work_temp,
            "TMP": work_temp,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONUNBUFFERED": "1",
        }

        log(f"  running: {command}")
        exit_code, out, err, timed_out = ac.launch(
            full_command, work_repo, environment, sid, timeout_seconds)

        result.update({"exit_code": exit_code, "stdout": out, "stderr": err,
                       "timed_out": timed_out, "sealed": True})

        collected = {}
        for name in collect:
            path = os.path.join(work_repo, name)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    collected[name] = fh.read()
            except OSError as e:
                collected[name] = f"<could not read: {type(e).__name__}>"
        result["collected"] = collected

    finally:
        # Destroyed afterwards, whatever happened above.
        sid.destroy()
        shutil.rmtree(workspace, ignore_errors=True)
        result["workspace_still_exists"] = os.path.exists(workspace)
        log(f"  workspace destroyed (still exists: "
            f"{result['workspace_still_exists']})")

    return result


def run_unsealed(repo_dir, command, timeout_seconds=120, log=print,
                 collect=()):
    """The same run with no box at all -- the control.

    This exists so the sealed run has something to be compared against. A cage
    that has never held anything is not known to work, so we watch the code get
    out first, then watch the same code fail.
    """
    repo_dir = os.path.abspath(repo_dir)
    log(f"  running unsealed in {repo_dir}: {command}")
    proc = subprocess.run(command, cwd=repo_dir, shell=True,
                          capture_output=True, text=True,
                          timeout=timeout_seconds)
    collected = {}
    for name in collect:
        try:
            with open(os.path.join(repo_dir, name), "r", encoding="utf-8") as fh:
                collected[name] = fh.read()
        except OSError as e:
            collected[name] = f"<could not read: {type(e).__name__}>"
    return {"exit_code": proc.returncode, "stdout": proc.stdout,
            "stderr": proc.stderr, "timed_out": False, "sealed": False,
            "collected": collected}


if __name__ == "__main__":
    # Manual use: python box.py <repo dir> "<command>"
    if len(sys.argv) < 3:
        print(__doc__)
        print("usage: python box.py <repo-directory> \"<command>\"")
        sys.exit(2)
    outcome = run_sealed(sys.argv[1], sys.argv[2])
    print(json.dumps({k: v for k, v in outcome.items()
                      if k != "collected"}, indent=2))
