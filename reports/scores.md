# Scores

Rules: `SCORING.md`. Every finding below was scored by **running its
reproduction**, not by reading it.

- **Catch rate: 33%** (1 of 3 instances) — found the bug the
  dataset catalogued. Low is expected; the dataset records one bug per
  project.
- **Confirmation rate: 100%** (6 of 6 findings) — reproductions that
  actually failed. This is the quality measure.
- **Noise rate: 0%** (0 unconfirmed, 0 malformed).

## Per instance

| Instance | Findings | Caught the catalogued bug |
|---|---|---|
| black-1 | 1 | yes |
| cookiecutter-1 | 4 | no |
| fastapi-1 | 1 | no |
