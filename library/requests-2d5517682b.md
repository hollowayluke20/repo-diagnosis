---
status: found
source_project: requests
source_commit: 2d5517682b3b38547634d153cea43d48fbc8cdb5
source_url: https://github.com/psf/requests/commit/2d5517682b3b38547634d153cea43d48fbc8cdb5
tags: parsing,encoding,error-handling,api-consistency
retrieved: 0
worked: 0
proven_on: 
---

## Problem

Malformed JSON produced different exception types depending on whether the input took the byte-decoding path or the text-decoding path. Callers therefore could not reliably handle parse failures through one documented exception contract, and one path could also expose decoded response content in the error message.

## Fix shape

Catch parser failures in every decoding branch and translate them into the same public exception type while preserving structured error details such as the message, input document, and failure position. Ensure that constructing the public exception does not accidentally include the full decoded payload in its string representation.
