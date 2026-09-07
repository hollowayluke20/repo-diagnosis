# Scores

Rules: `SCORING.md`. Every finding below was scored by **running its
reproduction**, not by reading it.

- **Catch rate: 17%** (2 of 12 instances) — found the bug the
  dataset catalogued. Low is expected; the dataset records one bug per
  project.
- **Confirmation rate: 100%** (40 of 40 findings) — reproductions that
  actually failed. This is the quality measure.
- **Noise rate: 0%** (0 unconfirmed, 0 malformed).

## Per instance

| Instance | Findings | Caught the catalogued bug |
|---|---|---|
| black-1 | 4 | no |
| black-2 | 4 | no |
| black-3 | 4 | no |
| cookiecutter-1 | 3 | no |
| cookiecutter-2 | 5 | no |
| fastapi-1 | 5 | yes |
| fastapi-2 | 4 | no |
| fastapi-3 | 3 | no |
| httpie-2 | 2 | no |
| httpie-3 | 3 | yes |
| spacy-3 | 2 | no |
| tornado-2 | 1 | no |
