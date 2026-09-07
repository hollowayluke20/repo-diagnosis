---
status: found
source_project: requests
source_commit: 3ff3ff21dd45957c9e143cd500291959bb15f690
source_url: https://github.com/psf/requests/commit/3ff3ff21dd45957c9e143cd500291959bb15f690
tags: serialization,multiple-inheritance,error-handling,concurrency
retrieved: 0
worked: 0
proven_on: 
---

## Problem

An exception type using multiple inheritance could be serialized but failed during deserialization because method resolution selected a parent's serialization protocol with an incompatible constructor shape. Required reconstruction arguments were omitted, causing round trips to raise errors and potentially break process-pool result handling.

## Fix shape

Explicitly delegate serialization metadata generation to the parent that knows the exception's complete reconstruction arguments, bypassing the unsuitable method selected by inheritance order.
