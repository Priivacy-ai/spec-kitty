---
title: Contracts
description: 'Contract-ownership boundary registry for Spec Kitty: the seeded contract manifest and its validation schema, checked by the doctor contracts gate.'
doc_status: active
updated: '2026-07-07'
related:
- docs/api/cli-commands.md
- docs/index.md
---
# Contracts

This section holds the **Contract Registry** for the contract-ownership
boundary (#2441): the single, canonical manifest of ownership contracts that
Spec Kitty enforces, plus the schema that validates it.

## Files

- `contract-registry.yaml` — the seeded contract manifest. Each record declares
  a contract's kind, status, enforcement level, owning boundary, semver, and
  tracker references, along with the anchors that pin it to the code or docs it
  governs.
- `contract-registry-schema.yaml` — the schema every registry record is
  validated against: required fields, allowed `kind`/`status`/`enforcement`
  ranges, well-formed semver and tracker references, resolvable anchors, and the
  DIR-041 self-consistency rule that forbids positional `file:line` anchoring.

## Validation

The registry is validated by the CLI gate:

```
spec-kitty doctor contracts
```

Structural validation is the only enforcing gate in v1 — a malformed record or a
positional `file:line` anchor exits non-zero. The retirement absence-sweep is
advisory. See `spec-kitty doctor contracts --help` (documented in
`docs/api/cli-commands.md`) for exit codes and options.
