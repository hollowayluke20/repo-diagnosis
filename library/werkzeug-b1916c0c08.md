---
status: found
source_project: werkzeug
source_commit: b1916c0c083e0be1c9d887ee2f3d696922bfc5c1
source_url: https://github.com/pallets/werkzeug/commit/b1916c0c083e0be1c9d887ee2f3d696922bfc5c1
tags: parsing,streaming,performance
retrieved: 0
worked: 0
proven_on:
---

## Problem

A streaming delimiter parser retained almost an entire large buffer while waiting for a possible partial delimiter near the end. Inputs with few line breaks caused excessive buffering and very slow parsing even though most buffered bytes could not begin a delimiter.

## Fix shape

When no complete delimiter is present, retain only the short suffix that could still become a delimiter. If the bytes after the last plausible delimiter prefix exceed that maximum suffix length, emit them as ordinary data immediately.
