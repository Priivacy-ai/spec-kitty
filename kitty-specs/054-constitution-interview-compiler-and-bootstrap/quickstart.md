# Quickstart: Constitution Interview Compiler and Context Bootstrap

**Feature**: 054 | **Date**: 2026-03-09

---

## 1. Capture interview answers

```bash
spec-kitty constitution interview
```

This writes `/home/stijn/Documents/_code/fork/spec-kitty/.kittify/constitution/interview/answers.yaml`.

---

## 2. Add explicit local supporting files if the project needs them

Use explicit file paths only. Directory and glob expansion are intentionally out of scope.

```yaml
# .kittify/constitution/interview/answers.yaml
local_supporting_files:
  - path: docs/governance/project-planning.md
    action: plan
    target_kind: directive
    target_id: 003-decision-documentation-requirement
  - path: docs/governance/project-review-checklist.md
    action: review
```

Notes:

- Local supporting files are discovered only from declarations in `answers.yaml` / `references.yaml`.
- If a declaration targets the same concept as a shipped doctrine artifact, shipped doctrine stays primary, the local file is additive only, and the command should warn about the overlap.

---

## 3. Generate the constitution bundle

```bash
spec-kitty constitution generate --json
```

Expected success payload shape:

```json
{
  "result": "success",
  "constitution_file": ".kittify/constitution/constitution.md",
  "references_file": ".kittify/constitution/references.yaml",
  "generated_files": [
    "constitution.md",
    "references.yaml",
    "governance.yaml",
    "directives.yaml",
    "metadata.yaml"
  ],
  "library_files": [
    "docs/governance/project-planning.md"
  ]
}
```

`library_files` lists declared project-local supporting files actually used. It is empty when the bundle relies only on shipped doctrine.

---

## 4. Observe the hard-fail when interview answers are missing

```bash
$ spec-kitty constitution generate
Error: No interview answers found. Run 'spec-kitty constitution interview' first.
```

The error must also identify `/home/stijn/Documents/_code/fork/spec-kitty/.kittify/constitution/interview/answers.yaml`.

---

## 5. Load action-scoped planning context

```bash
spec-kitty constitution context --action plan --json
spec-kitty constitution context --action plan --depth 3 --json
```

Expected behavior:

- First call for `plan` defaults to bootstrap depth 2.
- Subsequent calls default to compact depth 1.
- Explicit `--depth` overrides the bootstrap default.
- Action-scoped local support files declared for `plan` appear only in `plan` context, not in `specify` or `implement`.

---

## 6. Verify the shipped-only doctrine contract

The authoritative validation catalog uses canonised `shipped/` doctrine artifacts by default. `_proposed/` artifacts are not part of normal constitution validation unless a curation-oriented caller explicitly opts into them.

---

## 7. Verify generated files

```bash
ls .kittify/constitution/
```

Expected:

- `constitution.md`
- `references.yaml`
- `governance.yaml`
- `directives.yaml`
- `metadata.yaml`
- `context-state.json` after the first context load

Not expected:

- `agents.yaml`
- generated `library/` directory
