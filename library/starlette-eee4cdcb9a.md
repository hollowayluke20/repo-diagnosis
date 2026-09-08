---
status: found
source_project: starlette
source_commit: eee4cdcb9a4e787d53df88ccbee2861a0bb9b0a8
source_url: https://github.com/encode/starlette/commit/eee4cdcb9a4e787d53df88ccbee2861a0bb9b0a8
tags: paths,symlinks,security
retrieved: 0
worked: 0
proven_on:
---

## Problem

A static-file containment check canonicalized the configured base directory even when configured to follow symlinks. A request through a symlinked base directory then compared paths in different namespaces and was rejected despite remaining inside the configured tree.

## Fix shape

Canonicalize both sides of a containment check according to the selected symlink policy. When following symlinks is enabled, preserve the configured base spelling for both the target and base comparison; otherwise resolve both before comparison.
