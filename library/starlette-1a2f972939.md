---
status: found
source_project: starlette
source_commit: 1a2f97293966f3e6549e4da3d00d526915b03b3b
source_url: https://github.com/encode/starlette/commit/1a2f97293966f3e6549e4da3d00d526915b03b3b
tags: urls,edge-cases,validation
retrieved: 0
worked: 0
proven_on:
---

## Problem

A URL component replacement operation indexed the final character of an authority string without allowing for a URL that had no authority. Updating an authority component on a relative URL therefore raised an index error.

## Fix shape

Guard character-level parsing with a non-empty check. For an absent optional component, skip the parsing step and build the requested replacement from the available values.
