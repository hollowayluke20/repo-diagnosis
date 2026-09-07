---
status: found
source_project: click
source_commit: d340b0c1202284a1b9d0ca892549208527d586ce
source_url: https://github.com/pallets/click/commit/d340b0c1202284a1b9d0ca892549208527d586ce
tags: type-checking,formatting,error-handling
retrieved: 0
worked: 0
proven_on: 
---

## Problem

Help or display rendering checked whether an arbitrary default value was an empty string by comparing it directly with a string. Objects with strict equality implementations could raise an exception when compared with a different type, causing rendering to fail instead of displaying their string representation.

## Fix shape

Confirm that the value is a string before performing the empty-string comparison; otherwise, format it through the normal conversion path.
