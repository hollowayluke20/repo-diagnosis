---
status: found
source_project: requests
source_commit: 1604e20fc87ce212cf3a02474a6d7509b640cbbb
source_url: https://github.com/psf/requests/commit/1604e20fc87ce212cf3a02474a6d7509b640cbbb
tags: parsing,filtering,pattern-matching,configuration
retrieved: 0
worked: 0
proven_on: 
---

## Problem

A delimiter-separated list of matching patterns could contain empty entries, such as from a trailing delimiter or consecutive delimiters. An empty pattern matched every candidate, causing the bypass check to return true even when no configured non-empty pattern matched.

## Fix shape

Discard empty entries after splitting the configuration and before applying pattern matching.
