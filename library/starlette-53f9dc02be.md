---
status: found
source_project: starlette
source_commit: 53f9dc02be5b41f31ba096c8a5d65a6e6ca94fe0
source_url: https://github.com/encode/starlette/commit/53f9dc02be5b41f31ba096c8a5d65a6e6ca94fe0
tags: middleware,background-tasks,lifecycle
retrieved: 0
worked: 0
proven_on:
---

## Problem

A response wrapper used by middleware did not carry out background work attached after the wrapper was created. Work scheduled by middleware was silently lost even though the response completed normally.

## Fix shape

Preserve a background-work slot on wrapper responses and invoke it after the final response body has been sent. Ensure response adapters retain lifecycle hooks added by each layer.
