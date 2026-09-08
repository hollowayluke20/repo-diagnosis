---
status: found
source_project: werkzeug
source_commit: 2f0d8a7725ef3ac606d022fb16333ed482bebeaf
source_url: https://github.com/pallets/werkzeug/commit/2f0d8a7725ef3ac606d022fb16333ed482bebeaf
tags: http,headers,validation
retrieved: 0
worked: 0
proven_on:
---

## Problem

A request body length accessor trusted a generic header helper even when transfer framing made the length header inapplicable. Malformed or negative header values could also be exposed as valid sizes.

## Fix shape

Apply the protocol framing rules before interpreting an optional length header. Return no known length for chunked framing, parse only a valid integer length, clamp invalid negative values, and otherwise report that the length is unknown.
