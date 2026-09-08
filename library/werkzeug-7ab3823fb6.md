---
status: found
source_project: werkzeug
source_commit: 7ab3823fb620d29bcfeeff7499dd9a64ad90f360
source_url: https://github.com/pallets/werkzeug/commit/7ab3823fb620d29bcfeeff7499dd9a64ad90f360
tags: inheritance,customization,types
retrieved: 0
worked: 0
proven_on:
---

## Problem

An extension point accepts a class, but compatibility was checked as though the supplied value were an instance. An already-compatible subclass was therefore wrapped again, changing its identity and potentially creating an invalid inheritance hierarchy.

## Fix shape

When an API receives a class for later instantiation, test subclass compatibility rather than instance membership. Reuse a supplied compatible subclass unchanged and synthesize a wrapper only for an incompatible class.
