# Scores

Instances scored: 1  |  Findings reported: 3  |  Reached stage 2: 1

**Catch rate and false-alarm rate are NOT computed here.** Stage 2 is a
judgement call and guessing it would invent a number. Rule on the entries
in `reports/needs_judgement.json`, then fill these in:

- Catch rate = hits / instances scored
- False-alarm rate = false alarms / findings reported
- Unknowns = real defects that are not the catalogued one (**never folded into either number**)

## Per instance

| Instance | Findings | Reached stage 2 | Key file(s) |
|---|---|---|---|
| cookiecutter-1 | 3 | 1 | cookiecutter/generate.py |

## What each run said it examined

- **cookiecutter-1** — Reviewed all application modules under cookiecutter/, exercised generation, template discovery, and ZIP extraction paths, and attempted the test suite. The bundled environment lacks freezegun, pytest-

## Reminder

Four hand runs on PySnooper produced six verified real defects and a
catch rate of 0%. BugsInPy catalogues one bug per instance, so a finding
outside the key is UNKNOWN, not wrong. If unknowns keep outnumbering
hits, the ruler is wrong rather than the system.
