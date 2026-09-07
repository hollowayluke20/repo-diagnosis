"""
The proof that the box does something.

Runs the canary repository twice against the same three attacks:

    once with no box    -> all three attempts must SUCCEED
    once inside the box -> all three attempts must be BLOCKED

Both halves matter. A cage that has never held anything is not known to work,
so the escape is demonstrated first. If the unsealed run does not get out, the
test proves nothing about the seal and this script says so rather than
reporting a pass.

Nothing here trusts the canary's own account of itself. Submitted code reporting
"I was blocked" is worth nothing -- it could simply lie. So after each run the
host is checked directly, from outside, for the file the canary tries to drop.
That check is the one that counts.

Writes sandbox/proof/unsealed.log, sealed.log and verdict.json.

    python prove.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import box  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
CANARY_REPO = os.path.join(HERE, "canary-repo")
PROOF_DIR = os.path.join(HERE, "proof")

# The canary tries to create this on the host. We check for it ourselves rather
# than believing what the canary says about it.
HOST_FILE = r"C:\Users\hollo\sandbox-leak-canary.txt"

ATTEMPTS = ["read-outside-workspace", "reach-network", "write-to-host"]


def parse_attempts(stdout):
    """Read the canary's per-attempt lines back out of its output."""
    found = {}
    for line in stdout.splitlines():
        line = line.strip()
        for attempt in ATTEMPTS:
            if f"] {attempt}:" in line:
                found[attempt] = {
                    "blocked": line.startswith("[BLOCKED]"),
                    "line": line,
                }
    return found


def host_file_present():
    return os.path.exists(HOST_FILE)


def clear_host_file():
    """Remove the dropped file, so each half starts from the same clean state."""
    try:
        os.remove(HOST_FILE)
        return True
    except FileNotFoundError:
        return False


def write_log(name, title, outcome, host_before, host_after):
    path = os.path.join(PROOF_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"{title}\n{'=' * len(title)}\n\n")
        fh.write(f"exit code: {outcome['exit_code']}\n")
        fh.write(f"timed out: {outcome['timed_out']}\n")
        fh.write(f"host file {HOST_FILE}\n")
        fh.write(f"  present before run: {host_before}\n")
        fh.write(f"  present after run:  {host_after}   "
                 f"<- checked from outside, not self-reported\n\n")
        fh.write("--- stdout ---\n")
        fh.write(outcome["stdout"] or "(nothing)\n")
        fh.write("\n--- stderr ---\n")
        fh.write(outcome["stderr"] or "(nothing)\n")
    return path


def main():
    os.makedirs(PROOF_DIR, exist_ok=True)
    print(f"canary repository: {CANARY_REPO}\n")

    # ---- half one: no box. The code should get out. ----
    print("[1/2] running the canary with NO box (expecting it to escape)")
    clear_host_file()
    before = host_file_present()
    unsealed = box.run_unsealed(CANARY_REPO, "python canary.py",
                                log=lambda m: print(m))
    after_unsealed = host_file_present()
    write_log("unsealed.log", "UNSEALED RUN - no box, code runs as you do",
              unsealed, before, after_unsealed)
    unsealed_attempts = parse_attempts(unsealed["stdout"])
    print(unsealed["stdout"])

    # Clean up whatever it managed to leave behind before the sealed half.
    removed = clear_host_file()
    # The canary also writes its verdict beside itself; do not leave that in git.
    stray = os.path.join(CANARY_REPO, "canary_result.json")
    if os.path.exists(stray):
        os.remove(stray)

    # ---- half two: sealed. The same code should fail. ----
    print("[2/2] running the SAME canary inside the box (expecting all blocked)")
    before_sealed = host_file_present()
    sealed = box.run_sealed(CANARY_REPO, "python canary.py",
                            log=lambda m: print(m),
                            collect=("canary_result.json",))
    after_sealed = host_file_present()
    write_log("sealed.log", "SEALED RUN - inside the box", sealed,
              before_sealed, after_sealed)
    sealed_attempts = parse_attempts(sealed["stdout"])
    print(sealed["stdout"])

    # ---- judgement ----
    escaped_unsealed = [a for a in ATTEMPTS
                        if a in unsealed_attempts
                        and not unsealed_attempts[a]["blocked"]]
    blocked_sealed = [a for a in ATTEMPTS
                      if a in sealed_attempts and sealed_attempts[a]["blocked"]]

    control_valid = len(escaped_unsealed) == 3 and after_unsealed
    seal_holds = (len(blocked_sealed) == 3
                  and not after_sealed
                  and not sealed["timed_out"])

    verdict = {
        "control_run_proves_the_attacks_work": control_valid,
        "unsealed": {
            "attempts_that_succeeded": escaped_unsealed,
            "host_file_created": after_unsealed,
            "host_file_removed_afterwards": removed,
        },
        "sealed": {
            "attempts_blocked": blocked_sealed,
            "host_file_created": after_sealed,
            "timed_out": sealed["timed_out"],
            "workspace_destroyed": not sealed.get("workspace_still_exists", True),
            "container_sid": sealed.get("container_sid"),
        },
        "detail": {
            "unsealed": {a: unsealed_attempts.get(a, {}).get("line")
                         for a in ATTEMPTS},
            "sealed": {a: sealed_attempts.get(a, {}).get("line")
                       for a in ATTEMPTS},
        },
        "seal_holds": seal_holds,
    }
    with open(os.path.join(PROOF_DIR, "verdict.json"), "w",
              encoding="utf-8") as fh:
        json.dump(verdict, fh, indent=2)

    print("=" * 68)
    if not control_valid:
        print("INCONCLUSIVE: the unsealed run did not manage all three attacks,")
        print("so this proves nothing about the seal. Attacks that worked:",
              escaped_unsealed or "none")
        print("=" * 68)
        return 2

    print(f"control:  unsealed run escaped on all three  ({', '.join(escaped_unsealed)})")
    print(f"sealed:   blocked {len(blocked_sealed)} of 3  ({', '.join(blocked_sealed)})")
    print(f"host file created by sealed run: {after_sealed}  (checked from outside)")
    print(f"workspace destroyed afterwards:  "
          f"{not sealed.get('workspace_still_exists', True)}")
    print("=" * 68)
    print("SEAL HOLDS" if seal_holds else "SEAL FAILED")
    print(f"logs: {PROOF_DIR}")
    return 0 if seal_holds else 1


if __name__ == "__main__":
    sys.exit(main())
