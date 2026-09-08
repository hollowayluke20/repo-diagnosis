---
status: found
source_project: werkzeug
source_commit: 45c1e774eb77a91b6de2c1923c77d7c7aceaf946
source_url: https://github.com/pallets/werkzeug/commit/45c1e774eb77a91b6de2c1923c77d7c7aceaf946
tags: validation,unicode,error-handling
retrieved: 0
worked: 0
proven_on:
---

## Problem

Validation converted user-supplied text to a restricted character form but caught only one possible Unicode failure. Other conversion failures escaped as internal errors instead of being reported as invalid input.

## Fix shape

At the input-validation boundary, catch the full family of Unicode conversion errors and translate each into the public invalid-input error. Do not let implementation-specific encoding failures become server failures.
