# sandbox/ — Stage 8: run a stranger's code safely

A throwaway sealed workspace for executing an untrusted repository: no
network, no access to the host filesystem, nothing shared between runs,
destroyed afterwards. See `PLAN.md` Stage 8 for the decision and the result.

## Files

- `_appcontainer.py` — the Win32 plumbing (via `ctypes`) that creates a
  Windows AppContainer and launches a process inside it. Builds a sandbox;
  does not break one. Read its module docstring first.
- `box.py` — the usable interface: `run_sealed(repo_dir, command)` and
  `run_unsealed(...)` for comparison. Handles provisioning the read-only
  Python runtime, granting exactly two folders, capturing output, and
  destroying the workspace afterwards.
- `canary-repo/canary.py` — the deliberately hostile test repository. Tries to
  read outside its workspace, reach the network, and write to the host.
  Never raises; reports `BLOCKED` or `NOT BLOCKED` for each attempt.
- `prove.py` — runs the canary unsealed (must escape on all three) and then
  sealed (must be blocked on all three), checking the host itself rather than
  trusting the canary's self-report. Writes `proof/unsealed.log`,
  `proof/sealed.log`, `proof/verdict.json`.

## Run it

```
python prove.py
```

## What "sealed" means here

Windows file permissions are a list of identities allowed to touch a file. The
sealed run executes as a throwaway identity that owns nothing on this machine
and is on nobody's permission list except the one workspace folder it is
explicitly granted for that run, plus a read-only copy of Python it needs to
execute. It has no network capability, so Windows Firewall refuses every
connection outright — confirmed against both a hostname lookup and a raw TCP
connection to a hardcoded IP, so a DNS failure can't be mistaken for a real
block.

## Known limitation

The container identity is currently derived from a fixed name
(`repo-diagnosis-box`), so two sealed runs at the same instant would collide.
Fine for proving the seal holds; needs a per-run identity before this is used
for concurrent, real submissions.
