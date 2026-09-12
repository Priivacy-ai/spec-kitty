---
name: spk-doctrine-bulk-edit
description: "Recognize bulk-edit missions and apply occurrence classification guardrails before modifying many matching instances."
---

# spk-doctrine-bulk-edit

Use this skill when the user asks for a broad rename, replace, migration,
classification, or other multi-occurrence edit.

## Flow

1. Perform a manual pre-edit occurrence review before changing matches.
2. Align the occurrence map to the eight standard schema categories plus
   explicit exceptions and moves.
3. Treat runtime enforcement as a path-based review gate, not an AST-semantic
   classifier.
4. Confirm edit policy when the blast radius is unclear.
5. Execute the narrowest safe change and verify representative cases.

## Legacy Alias

For detailed DIRECTIVE_035 handling, use
`spec-kitty-bulk-edit-classification` when available.
