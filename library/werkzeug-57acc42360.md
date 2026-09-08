---
status: found
source_project: werkzeug
source_commit: 57acc4236044803956686c3f0f6ae0cacd2986b0
source_url: https://github.com/pallets/werkzeug/commit/57acc4236044803956686c3f0f6ae0cacd2986b0
tags: http,headers,parsing
retrieved: 0
worked: 0
proven_on:
---

## Problem

A parser read only the first occurrence of a repeatable request header. Valid values carried in later occurrences were silently lost, producing incomplete parsed request state.

## Fix shape

Collect every occurrence of a repeatable header and combine them with the separator defined by the protocol before parsing. Preserve the order in which the field values arrived.
