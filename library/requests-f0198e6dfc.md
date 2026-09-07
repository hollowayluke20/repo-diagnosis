---
status: found
source_project: requests
source_commit: f0198e6dfc431a2293dc16e1b1e8fcddc910a7f3
source_url: https://github.com/psf/requests/commit/f0198e6dfc431a2293dc16e1b1e8fcddc910a7f3
tags: parsing,validation,headers,error-handling
retrieved: 0
worked: 0
proven_on: 
---

## Problem

A structured header parser treated malformed parameter fragments without an equals sign as valid flag-style parameters with a boolean value. Downstream logic could then mistake an incomplete field such as a bare character-set label for meaningful metadata instead of ignoring it and applying the appropriate fallback.

## Fix shape

Accept parameter fragments only when they contain a key-value delimiter; discard nonempty fragments that lack one, while continuing to normalize and store valid key-value pairs.
