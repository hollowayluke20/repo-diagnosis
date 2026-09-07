---
status: found
source_project: requests
source_commit: 6f205ff422bccd5e4c4fc0b64c5f3e7df5181db6
source_url: https://github.com/psf/requests/commit/6f205ff422bccd5e4c4fc0b64c5f3e7df5181db6
tags: file-uploads,duck-typing,proxies,validation
retrieved: 0
worked: 0
proven_on: 
---

## Problem

File-like wrapper objects that exposed reading dynamically through attribute delegation were rejected as unsupported inputs. The capability check relied only on runtime protocol recognition, which can miss attributes supplied through dynamic lookup, so valid wrapped files were not read or uploaded.

## Fix shape

Combine the formal interface check with a direct runtime capability check for the required read operation, allowing proxy-based wrappers while preserving the existing handling of other input types.
