---
status: found
source_project: starlette
source_commit: 7d79ad96d5aaee71f16ac9f4e41072e81d18ab86
source_url: https://github.com/encode/starlette/commit/7d79ad96d5aaee71f16ac9f4e41072e81d18ab86
tags: compatibility,cryptography,platforms
retrieved: 0
worked: 0
proven_on:
---

## Problem

A compatibility probe for a hash API tested it in security-sensitive mode even though the application only needed a non-security checksum. Hardened environments rejected the probe, so the intended compatible code path was never selected.

## Fix shape

Probe optional API support using the same non-security mode required by the real operation. Hide version-specific call signatures behind one compatibility helper and explicitly declare non-security checksum use.
