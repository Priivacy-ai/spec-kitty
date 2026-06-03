---
name: spk-doctrine-bulk-edit
description: "Recognize bulk-edit missions and apply occurrence classification guardrails before modifying many matching instances."
---

# spk-doctrine-bulk-edit

Use this skill when the user asks for a broad rename, replace, migration,
classification, or other multi-occurrence edit.

## Flow

1. Classify occurrences before changing them.
2. Separate true matches, false positives, generated artifacts, and unrelated
   homonyms.
3. Confirm edit policy when the blast radius is unclear.
4. Execute the narrowest safe change and verify representative cases.

## Legacy Alias

For detailed DIRECTIVE_035 handling, use
`spec-kitty-bulk-edit-classification` when available.
