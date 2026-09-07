---
status: found
source_project: SEED
source_commit: 
source_url: 
retrieved: 0
worked: 0
proven_on: 
---

## Problem

A function or constructor declares a parameter whose default is a container
that can be changed in place - a list, a dictionary, a set. The default object
is created once, when the function is defined, not each time it is called. Every
caller who omits that argument therefore shares one object, so anything added
during one call is still present on the next, and state leaks between calls
that are supposed to be independent. The symptom usually appears as results
that are correct the first time and accumulate afterwards.

## Fix shape

Default the parameter to a sentinel meaning "nothing was supplied" - typically
none - and build a fresh container inside the function body when the sentinel
is seen. Where the value is genuinely meant to persist between calls, make that
explicit by storing it somewhere named rather than leaving it hidden in the
signature, so the sharing is a stated decision rather than an accident.
