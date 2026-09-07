---
status: found
source_project: requests
source_commit: 38f3f8ecb93cadfac03a6b7b3173018ac829d0cf
source_url: https://github.com/psf/requests/commit/38f3f8ecb93cadfac03a6b7b3173018ac829d0cf
tags: url-parsing,authentication,proxies
retrieved: 0
worked: 0
proven_on: 
---

## Problem

A URL normalization step lost embedded credentials when parsing and reconstructing URLs, because the parser returned authentication data separately from the host portion. As a result, URLs containing either a username alone or a username and password were silently rewritten without their authentication information.

## Fix shape

When reconstructing a parsed URL, explicitly restore any separately parsed authentication component ahead of the authority before applying the default scheme and assembling the final URL.
