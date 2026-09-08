---
status: found
source_project: werkzeug
source_commit: a7ee5b10bb7a05d1859e735d7d5e96be7279285d
source_url: https://github.com/pallets/werkzeug/commit/a7ee5b10bb7a05d1859e735d7d5e96be7279285d
tags: optional-values,error-handling,validation
retrieved: 0
worked: 0
proven_on:
---

## Problem

Error-reporting code assumed an optional collection was always present. A valid absent value caused a secondary exception while building the original error message, hiding the real problem.

## Fix shape

Check that optional data is present before applying membership tests, sorting, or iteration. Keep diagnostic paths at least as defensive as the normal path so they cannot replace a useful error with a crash.
