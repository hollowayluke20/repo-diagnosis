---
status: found
source_project: SEED
source_commit: 
source_url: 
tags: encoding,file-io,portability
retrieved: 0
worked: 0
proven_on: 
---

## Problem

A file is opened in text mode with no encoding stated, so the interpreter falls
back to whatever the host machine happens to prefer. The code works on the
author's machine and raises a decoding error on someone else's, or silently
mangles characters outside the narrow range the fallback covers. The same class
of failure appears when bytes arriving from a network or a subprocess are
decoded with an assumed encoding rather than a declared one.

## Fix shape

State the encoding explicitly at every point where bytes become text, rather
than relying on a platform default. Where the encoding is genuinely unknown,
decide in advance what should happen to characters that cannot be decoded -
replace them, or refuse the input - and say so at the call site, so the
behaviour is the same everywhere the code runs. Treat a decoding failure as a
condition to handle, not as something that cannot happen.
