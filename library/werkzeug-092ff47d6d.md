---
status: found
source_project: werkzeug
source_commit: 092ff47d6d48ed084d75283ab25917b94975b939
source_url: https://github.com/pallets/werkzeug/commit/092ff47d6d48ed084d75283ab25917b94975b939
tags: concurrency,context-state,mutable-data
retrieved: 0
worked: 0
proven_on:
---

## Problem

Mutable state stored for a logical execution context was changed in place. Concurrent tasks inherited the same object, so a change made by one task leaked into the state seen by another.

## Fix shape

Copy the context-local collection before changing it, then store the new collection back in the current context. Treat the value in a context variable as immutable once it may be shared with derived tasks.
