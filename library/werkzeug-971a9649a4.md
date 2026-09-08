---
status: found
source_project: werkzeug
source_commit: 971a9649a45a17590dc98ec7c977562e0078cdd5
source_url: https://github.com/pallets/werkzeug/commit/971a9649a45a17590dc98ec7c977562e0078cdd5
tags: streams,io,partial-reads
retrieved: 0
worked: 0
proven_on:
---

## Problem

A bounded reader assumed every underlying read would fill the requested size. Raw streams may legally return a short non-empty read, so the reader treated valid data as a disconnect and a request to read all data could stop early.

## Fix shape

Treat only an empty read before the limit as an unexpected disconnect. For a read-to-end operation, keep reading in bounded chunks until the limit is reached, accumulating every non-empty partial result.
