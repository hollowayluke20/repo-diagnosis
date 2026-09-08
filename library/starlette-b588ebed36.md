---
status: found
source_project: starlette
source_commit: b588ebed36c2934b33ad3b0221d79bd8b7a4817f
source_url: https://github.com/encode/starlette/commit/b588ebed36c2934b33ad3b0221d79bd8b7a4817f
tags: routing,parsing,urls
retrieved: 0
worked: 0
proven_on:
---

## Problem

A route-pattern compiler discarded everything after a colon in literal path text. A delimiter meaningful in one grammar context was incorrectly treated as syntax everywhere, making legitimate routes unreachable.

## Fix shape

Parse delimiters only where the grammar recognizes them. Once parameter parsing has finished, escape and retain all remaining literal text; apply separate delimiter handling for structurally different forms such as hosts.
