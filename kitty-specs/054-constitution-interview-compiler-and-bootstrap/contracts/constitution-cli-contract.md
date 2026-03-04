# Contract: Constitution CLI and Reference Manifest

**Feature**: 054-constitution-interview-compiler-and-bootstrap  
**Date**: 2026-03-09

## Overview

This contract defines the Phase 1 planning agreement for constitution CLI behavior and the artifact shapes used by `interview`, `generate`, and `context`.

## 1. Catalog Authority

- Normal constitution validation uses canonised `shipped/` doctrine artifacts only.
- `_proposed/` doctrine artifacts are excluded unless a caller explicitly opts into curation-mode catalog loading.
- Project-local support files are not discovered by scanning; they must be declared explicitly in `answers.yaml` and materialized into `references.yaml`.

## 2. Local Support File Declarations

### Declaration rules

- The declaration source of truth is `answers.yaml`, mirrored into `references.yaml`.
- Each declaration uses an explicit file path.
- Directory declarations and glob patterns are invalid.
- Declarations may be global or action-scoped (`specify`, `plan`, `implement`, `review`).

### Conflict rules

- If a local file targets the same doctrine concept as a shipped artifact, shipped doctrine remains authoritative.
- The local file is additive only.
- The system emits a warning describing the overlap.

## 3. `constitution interview`

### Success contract

Writes:

- `.kittify/constitution/interview/answers.yaml`

JSON success payload:

```json
{
  "result": "success",
  "answers_file": "<path>"
}
```

## 4. `constitution generate`

### Failure contract

If `.kittify/constitution/interview/answers.yaml` is missing and `--from-interview` is in effect:

- exit non-zero
- print an actionable error
- JSON mode returns exactly:

```json
{
  "error": "No interview answers found. Run 'spec-kitty constitution interview' first."
}
```

### Success contract

Generated files:

- `constitution.md`
- `references.yaml`
- `governance.yaml`
- `directives.yaml`
- `metadata.yaml`

Must not generate:

- `agents.yaml`
- `library/` materialization output

JSON success payload:

```json
{
  "result": "success",
  "constitution_file": "<path>",
  "references_file": "<path>",
  "generated_files": ["constitution.md", "references.yaml", "governance.yaml", "directives.yaml", "metadata.yaml"],
  "library_files": ["<explicit local support file path>"]
}
```

`library_files` lists explicit project-local support files actually used. It is empty when only shipped doctrine participates.

## 5. `constitution context`

### Request contract

```text
spec-kitty constitution context --action <specify|plan|implement|review> [--depth 1|2|3] [--json]
```

### Behavior contract

- First call for an action defaults to depth 2 bootstrap mode.
- Subsequent calls default to depth 1 compact mode.
- Explicit `--depth` overrides the bootstrap-derived default.
- Action-scoped local support files appear only for the matching action.

### JSON success payload

```json
{
  "result": "success",
  "context": "<rendered text>",
  "text": "<rendered text>",
  "mode": "bootstrap|compact",
  "depth": 1
}
```

`context` and `text` are identical for compatibility.

## 6. `references.yaml` Minimum Shape

```yaml
mission: software-dev
template_set: software-dev-default
references:
  - id: "DIRECTIVE:003-decision-documentation-requirement"
    kind: directive
    summary: "Record material decisions and rationale."
  - id: "LOCAL:docs/governance/project-planning.md"
    kind: local_support
    path: docs/governance/project-planning.md
    action: plan
    target_kind: directive
    target_id: 003-decision-documentation-requirement
    relationship: additive
    warning: "Local support file overlaps shipped directive 003-decision-documentation-requirement; shipped content remains primary."
```

This contract is planning guidance for implementation and tests. If implementation needs a narrower field set, it must preserve the semantics above.
