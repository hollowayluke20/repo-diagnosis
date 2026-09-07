---
status: found
source_project: click
source_commit: 1c20dc6e724cd5625faaa17b715ba928d44c08bf
source_url: https://github.com/pallets/click/commit/1c20dc6e724cd5625faaa17b715ba928d44c08bf
tags: parsing,defaults,sentinels,ordering
retrieved: 0
worked: 0
proven_on: 
---

## Problem

When multiple inputs targeted the same destination, an absent-value sentinel from the first input was prematurely converted into an ordinary null value. That made the destination appear already resolved, preventing a later input with a real default from supplying it and causing behavior to depend on processing order.

## Fix shape

Preserve the distinct unresolved sentinel throughout input processing, and allow a later contributor to replace it with an actual value, including an explicitly configured null. Only after every contributor has been considered should any still-unresolved sentinels be converted to the public null representation.
