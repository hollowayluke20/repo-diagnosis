---
status: found
source_project: starlette
source_commit: 24887d681593795b5c0025d54fce744227313464
source_url: https://github.com/encode/starlette/commit/24887d681593795b5c0025d54fce744227313464
tags: urls,encoding,parsing
retrieved: 0
worked: 0
proven_on:
---

## Problem

A transport decoded already-normalized URL components a second time before placing them in a request representation. Percent-encoded query values were corrupted because the second decoding changed data that should have remained encoded until the receiving layer handled it.

## Fix shape

Keep URL components in their normalized representation while transferring them between layers. Decode exactly once at the layer that owns interpretation of that component.
