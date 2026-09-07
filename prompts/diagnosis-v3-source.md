# Prompt B — diagnosis, v3

Run in a **fresh** VS Code window on the subject folder. Never the setup session.

Changes from v2.2: the lens splits into three (structure / shape / content),
defaults become an explicit target, and ruff is available as a lead generator.

---

You are auditing the Python codebase in this folder for defects.

A complete Python installation is at `.python\python.exe`, with pytest and ruff
installed. Use it for anything you run.

**Available tools**

You may run ruff (`.python\python.exe -m ruff check`). Treat anything it reports
as a **lead to investigate, not a finding**. Most of what it reports is style
rather than defect, and none of it meets the bar below on its own. Only report
something if you have independently established it is a defect and can give a
concrete trigger for it.

You may run the project's own test suite, and you may write and run your own
throwaway scripts to test a hypothesis. Do not add anything to the project's own
test files.

Examine the code and report any defects you find. **It is entirely possible that
there are none.** If you find nothing you are genuinely confident about, say so —
reporting nothing is a valid answer and is sometimes the correct one.

**Rules**

- Do not fix anything. Do not edit any file belonging to the project.
- Do not read the git history or git log.
- Do not read the issue tracker, CHANGELOG, release notes, or commit messages.
- Do not search the internet.
- Base every finding only on the code as it stands in front of you.

**How to look**

Examine three things, not one.

1. **The structure** — does the code do what it is written to do? Control flow,
   types, imports, logic.
2. **The shape of the data** — what type of thing arrives at each boundary? What
   if a caller passes something valid but unusual?
3. **The content of the data** — separately from its type, what is *inside* it?
   What did the author assume about the actual values: their size, range, format
   and origin? Pay particular attention to hardcoded defaults and constants — **a
   default is an assumption written down.** Ask what happens when the real data
   does not match it.

Code can be structurally correct, receive exactly the type it expected, and still
be wrong for the content that actually passes through it.

**What counts as a defect**

The code does something other than what it is clearly intended to do.

These are **not** defects: style you would have written differently; behaviour
that is unusual but intended; missing features; code failing on input it was
never meant to accept; anything you cannot point at a specific trigger for.

**Report at most five defects, ranked most serious first.**

For each one, give exactly:

1. **File and line**
2. **What goes wrong** — one sentence
3. **Trigger** — the specific input, argument or condition that causes it. Be
   concrete: real values, not "invalid input" or "certain conditions".
4. **Expected vs actual** — what should happen, and what happens instead
5. **Confidence** — high / medium / low
6. **Verified?** — say whether you actually ran something that demonstrated it,
   or whether this is from reading alone.

Then one final line, separately: **what you examined, and how you decided where
to look.**
