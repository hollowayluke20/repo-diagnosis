---
status: found
source_project: starlette
source_commit: 07427f86474b15d648497014eb19c41f01317f15
source_url: https://github.com/encode/starlette/commit/07427f86474b15d648497014eb19c41f01317f15
tags: introspection,callables,robustness
retrieved: 0
worked: 0
proven_on:
---

## Problem

Code deriving a display name from a callable assumed every routine exposes a name attribute. Callable objects and wrapped callables may not, causing introspection used for normal operation to crash.

## Fix shape

Read the optional name attribute with a safe fallback to the callable object's type name. Make metadata and diagnostic introspection tolerate every supported callable form.
