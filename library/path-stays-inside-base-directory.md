---
status: found
source_project: SEED
source_commit: 
source_url: 
tags: file-paths,security,validation
retrieved: 0
worked: 0
proven_on: 
---

## Problem

A filesystem path is assembled from text the caller supplied - a name, a
template variable, an archive member, a URL segment - and is then opened,
written or extracted without checking where it actually lands. Text containing
parent-directory steps, an absolute path, or a symbolic link escapes the
directory that was meant to contain it, so the operation touches a file
somewhere else entirely.

## Fix shape

Resolve the assembled path to its real, absolute form, resolving links and
parent steps as the filesystem would. Resolve the intended base directory the
same way. Confirm the resolved path is genuinely underneath the resolved base -
by path components, not by comparing the start of the strings, since a sibling
directory whose name merely begins with the base name passes a string check.
If it is not underneath, refuse the whole operation and report why. Do not try
to sanitise the input into something safe; rejecting is checkable, cleaning is
a guess.
