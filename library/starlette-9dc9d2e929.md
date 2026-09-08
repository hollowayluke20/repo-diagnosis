---
status: found
source_project: starlette
source_commit: 9dc9d2e92919306fae683746e38530ff55ed3092
source_url: https://github.com/encode/starlette/commit/9dc9d2e92919306fae683746e38530ff55ed3092
tags: urls,http,request-metadata
retrieved: 0
worked: 0
proven_on:
---

## Problem

A request transport put the full raw target, including its query string, into the raw path field. Consumers that rely on path and query being distinct received incorrect request metadata.

## Fix shape

Split the raw target at the first query separator before assigning path metadata. Keep the query bytes in their dedicated field and do the same for every transport path, including upgraded connections.
