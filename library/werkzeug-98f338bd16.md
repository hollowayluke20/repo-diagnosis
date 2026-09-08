---
status: found
source_project: werkzeug
source_commit: 98f338bd16a6ff52a56fe2cf98c3b0829bbc576b
source_url: https://github.com/pallets/werkzeug/commit/98f338bd16a6ff52a56fe2cf98c3b0829bbc576b
tags: paths,windows,portability
retrieved: 0
worked: 0
proven_on:
---

## Problem

Path hierarchy code split and rebuilt paths with a hard-coded separator. It produced incorrect roots on platforms whose path syntax differs from the current process assumptions.

## Fix shape

Use a path abstraction to obtain path components and the platform path join operation to rebuild them. Do not treat paths as slash-delimited strings when comparing or reconstructing their hierarchy.
