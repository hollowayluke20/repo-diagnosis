---
status: found
source_project: starlette
source_commit: 865efebac909f7bfcd83451cf6bab725dddfe02d
source_url: https://github.com/encode/starlette/commit/865efebac909f7bfcd83451cf6bab725dddfe02d
tags: parsing,regular-expressions,validation
retrieved: 0
worked: 0
proven_on:
---

## Problem

A numeric input pattern used an unescaped punctuation character. The pattern accepted any character in that position, so malformed values passed routing or validation and failed later.

## Fix shape

Escape punctuation that is meant to be literal in a regular expression. Add a negative case near the positive example so a broad wildcard cannot silently return.
