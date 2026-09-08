---
status: found
source_project: starlette
source_commit: 94a22b865e7b9828fcc06771e25c9be33364b24b
source_url: https://github.com/encode/starlette/commit/94a22b865e7b9828fcc06771e25c9be33364b24b
tags: urls,ipv6,parsing
retrieved: 0
worked: 0
proven_on:
---

## Problem

Replacing one URL authority component reused a parsed hostname that did not preserve bracketed address syntax. The operation then split an address containing colons as though it were a host and port pair, corrupting the rebuilt URL.

## Fix shape

When reconstructing an authority from partial updates, start from its serialized form and remove user information and port only when their delimiters are structurally valid. Preserve bracketed address literals as one hostname unit.
