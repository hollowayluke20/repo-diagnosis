"""Feed the diagnosis prompt to each valid instance via headless Codex.

Refuses to run without the web-search guard: codex exec searches the internet
by default and will look the project up on GitHub. On 2026-09-07 it was
observed hitting api.github.com to answer a question about a folder it was
sitting in - and then reporting that it had used no external sources.

Usage:
  python run_diagnosis.py                  # practice pile
  python run_diagnosis.py --locked         # the held-back set. Think first.
"""
import argparse, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
KEYS, INSTANCES, RESULTS = ROOT / "keys", ROOT / "instances", ROOT / "results"
PROMPT = ROOT / "prompts" / "diagnosis-v3.txt"
SCHEMA = ROOT / "findings-schema.json"

WEB_GUARD = "web_search=disabled"


def codex_cmd(instance_dir, out_file, prompt_text):
    # npm installs codex as a .CMD shim on Windows; subprocess needs the
    # resolved path, not the bare name.
    exe = shutil.which("codex") or "codex"
    return [exe, "exec",
            "-C", str(instance_dir),
            "--skip-git-repo-check",
            "--ephemeral",             # no session persists - enforced amnesia
            # --approve-for-me auto-approves inside a workspace-write sandbox.
            # Without it a headless run has no command allowlist and EVERY shell
            # command is rejected by policy - the agent can't even list files,
            # and returns zero findings that look like a clean bill of health.
            # It conflicts with -s, so it replaces it.
            "--approve-for-me",
            "-c", WEB_GUARD,
            "--output-schema", str(SCHEMA),
            "-o", str(out_file),
            # "-" means: read the prompt from stdin.
            # Passing it as an argument silently truncates at the first
            # newline through npm's .CMD shim on Windows - every run before
            # this fix received ONLY the first line of the prompt.
            "-"]
    # NOT --ignore-rules: it blocks local shell tools, and a blocked agent
    # goes looking elsewhere.


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--locked", action="store_true",
                    help="run the held-back pile. One look spends it.")
    ap.add_argument("--only", help="single instance name")
    a = ap.parse_args()

    if not shutil.which("codex"):
        sys.exit("codex CLI not on PATH")
    if not PROMPT.exists():
        sys.exit(f"missing prompt file: {PROMPT}")
    prompt_text = PROMPT.read_text(encoding="utf-8")

    pile = "locked" if a.locked else "practice"
    keys = [json.loads(p.read_text(encoding="utf-8")) for p in KEYS.glob("*.json")]
    todo = [k for k in keys if k.get("status") == "VALID" and k.get("pile") == pile]
    if a.only:
        todo = [k for k in todo if k["instance"] == a.only]
    if not todo:
        sys.exit(f"no VALID instances in the '{pile}' pile"
                 + ("" if a.locked else " (locked ones need --locked)"))

    if a.locked:
        print("*** LOCKED PILE ***")
        print("This is the only independent measurement you will ever get.")
        print("Looking at the result and changing the prompt spends it permanently.")
        if input("Type RUN to continue: ").strip() != "RUN":
            sys.exit("aborted")

    RESULTS.mkdir(exist_ok=True)
    for k in todo:
        name = k["instance"]
        outdir = RESULTS / name
        outdir.mkdir(parents=True, exist_ok=True)
        # log the input, not just the output
        (outdir / "prompt_sent.txt").write_text(prompt_text, encoding="utf-8")
        result = outdir / "result.json"
        cmd = codex_cmd(INSTANCES / name, result, prompt_text)

        # the guard, checked against the command actually about to run
        if not any(WEB_GUARD in str(x) for x in cmd):
            sys.exit("REFUSING: web-search guard missing from the command")

        print(f"--- {name} ...", flush=True)
        p = subprocess.run(cmd, capture_output=True,
                           # encoding must be explicit: on Windows, text=True
                           # encodes stdin as cp1252 and codex rejects it as
                           # invalid UTF-8 the moment the prompt has an em dash
                           encoding="utf-8", errors="replace",
                           input=prompt_text, timeout=3600)
        log = (p.stdout or "") + (p.stderr or "")
        (outdir / "stdout.log").write_text(log, encoding="utf-8")
        # did the whole prompt actually arrive? check for a phrase from the end
        # of it, not the beginning.
        canary = "what you examined"
        if canary not in log.lower():
            print("    !! PROMPT TRUNCATED - the agent did not receive the "
                  "full instructions. Result is not comparable.")
        searched = (p.stdout or "").lower().count("web search")
        if searched:
            print(f"    !! {searched} web searches despite the guard - "
                  f"treat this result as contaminated")
        if result.exists():
            n = len(json.loads(result.read_text(encoding="utf-8")).get("findings", []))
            print(f"    ok, {n} findings")
        else:
            print(f"    no result written (exit {p.returncode})")


if __name__ == "__main__":
    main()
