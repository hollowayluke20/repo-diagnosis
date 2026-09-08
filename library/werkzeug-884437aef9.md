---
status: found
source_project: werkzeug
source_commit: 884437aef93e543ebaff3b9cdbe857ee47e7e00c
source_url: https://github.com/pallets/werkzeug/commit/884437aef93e543ebaff3b9cdbe857ee47e7e00c
tags: routing,boolean-logic,urls
retrieved: 0
worked: 0
proven_on:
---

## Problem

Output selection used a condition that required an optional matching mode to be enabled before it could choose the ordinary local form. With no matching modes enabled, equivalent targets incorrectly produced an external form.

## Fix shape

Express the default case separately from enabled optional modes. Use the local form when no mode applies, or when an enabled mode confirms equivalence; reserve the external form for a forced request or a real mismatch.
