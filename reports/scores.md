# Scores

Rules: `SCORING.md`. Every finding below was scored by **running its
reproduction**, not by reading it.

- **Catch rate: 8%** (1 of 12 instances) — found the bug the
  dataset catalogued. Low is expected; the dataset records one bug per
  project.
- **Confirmation rate: 97%** (36 of 37 findings) — reproductions that
  actually failed. This is the quality measure.
- **Noise rate: 3%** (1 unconfirmed, 0 malformed).

## Per instance

| Instance | Findings | Caught the catalogued bug |
|---|---|---|
| black-1 | 2 | no |
| black-2 | 2 | no |
| black-3 | 3 | no |
| cookiecutter-1 | 4 | no |
| cookiecutter-2 | 3 | no |
| fastapi-1 | 2 | yes |
| fastapi-2 | 4 | no |
| httpie-2 | 3 | no |
| httpie-3 | 4 | no |
| spacy-3 | 4 | no |
| tornado-2 | 4 | no |
| youtube-dl-1 | 2 | no |
