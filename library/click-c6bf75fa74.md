---
status: found
source_project: click
source_commit: c6bf75fa74bff6523375cf91f97af0a7aae85fce
source_url: https://github.com/pallets/click/commit/c6bf75fa74bff6523375cf91f97af0a7aae85fce
tags: windows,file-paths,subprocess,argument-parsing
retrieved: 0
worked: 0
proven_on: 
---

## Problem

On Windows, a command-line option and its file-path operand were combined into one argument. When the path contained spaces, the receiving program parsed it incorrectly and failed to locate or select the requested file.

## Fix shape

Pass the command-line option and the file path as separate arguments so the path remains an intact operand regardless of spaces.
