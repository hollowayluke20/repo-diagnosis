---
status: found
source_project: starlette
source_commit: ada99beee530e7b841ce320bc6e66f6dbd9ad781
source_url: https://github.com/encode/starlette/commit/ada99beee530e7b841ce320bc6e66f6dbd9ad781
tags: cookies,security,http
retrieved: 0
worked: 0
proven_on:
---

## Problem

A delete operation issued an expired cookie without retaining the security and scope attributes used when it was created. The browser could retain the original cookie or receive a mismatched replacement under stricter policies.

## Fix shape

Expose the relevant scope and security attributes on the delete operation and pass them through to the expiry-setting operation. Deletion must target the same cookie identity and policy as creation.
