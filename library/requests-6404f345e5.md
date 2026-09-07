---
status: found
source_project: requests
source_commit: 6404f345e562d962abe6700a1c357ec1e7e18232
source_url: https://github.com/psf/requests/commit/6404f345e562d962abe6700a1c357ec1e7e18232
tags: streams,protocol-detection,attribute-proxying,redirects
retrieved: 0
worked: 0
proven_on: 
---

## Problem

File-like wrappers that delegated missing attributes to an underlying stream were not recognized as iterable streams because the runtime interface check only considered methods defined directly on the wrapper's type. As a result, streamed request bodies could be processed through the wrong path and fail to survive redirects correctly.

## Fix shape

Detect stream-like iterability through both the formal runtime interface and dynamic attribute availability, while retaining exclusions for ordinary scalar, collection, and mapping inputs.
