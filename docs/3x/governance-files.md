---
title: Governance Files Reference
description: Authoritative reference for every file under .kittify/charter/ — who writes it, what it contains, and whether you can edit it.
---

# Governance Files Reference

The Charter governance layer lives primarily in `.kittify/charter/`, with promoted project-local
doctrine under `.kittify/doctrine/`. Most files are derived, runtime-managed, or agent-generated
inputs and must not be hand-edited. This page describes the common Charter-era files and the
commands that own them.

> **Key rule**: edit `.kittify/charter/charter.md` for policy changes. Re-run `charter sync` and
> `charter synthesize` instead of patching derived YAML, runtime state, or synthesis outputs by
> hand.

---

## File Table

| File path | Who writes it | Contains | Edit directly? |
|---|---|---|---|
| `.kittify/charter/charter.md` | **Human** via interview/generate, then direct edits | Mission vision, directives, doctrine selections, policy decisions | Yes |
| `.kittify/charter/interview/answers.yaml` | `charter interview` | Captured answers used by `charter generate` | Prefer re-running `charter interview` |
| `.kittify/charter/references.yaml` | `charter generate` | Reference manifest for shipped doctrine and local support files | No |
| `.kittify/charter/governance.yaml` | `charter sync` / `charter generate` | Testing, quality, performance, branch, and doctrine-selection config | No |
| `.kittify/charter/directives.yaml` | `charter sync` / `charter generate` | Extracted directives with IDs, descriptions, and severity | No |
| `.kittify/charter/metadata.yaml` | `charter sync` / `charter generate` | Charter hash, extraction timestamp, source path, parser stats | No |
| `.kittify/charter/context-state.json` | Runtime context loader | Per-action first-load state for compact/bootstrap context | No |
| `.kittify/charter/generated/{directives,tactics,styleguides}/` | Agent harness | Candidate YAML artifacts consumed by `charter synthesize` | No routine hand edits |
| `.kittify/charter/synthesis-manifest.yaml` | `charter synthesize` / `charter resynthesize` | Manifest of promoted synthesized artifacts and content hashes | No |
| `.kittify/charter/provenance/*.yaml` | `charter synthesize` / `charter resynthesize` | Provenance sidecars for project-local doctrine artifacts | No |
| `.kittify/charter/.staging/` | Synthesizer | Temporary validation/promote workspace; `.failed` dirs may remain for diagnosis | No |
| `.kittify/doctrine/` | `charter synthesize` / `charter resynthesize` | Project-local doctrine overlay used with shipped doctrine | No |
| `.kittify/doctrine/PROVENANCE.md` | `charter synthesize` fresh-project path | Human-readable provenance for the minimal fresh-project doctrine seed | No |

Current `charter generate` writes `charter.md` and `references.yaml`, then runs `charter sync`.
It no longer materializes doctrine library pages as authoritative `library/*.md` files; doctrine
content is resolved through `references.yaml` and the shipped/project doctrine service.

---

## What Happens If You Edit a Generated File

The owning command can overwrite generated-file edits. If you edit `governance.yaml` or
`directives.yaml` directly and then run `charter sync` or `charter generate`, your edits will be
lost because those files are re-derived from `charter.md`.

Use these commands to detect drift before relying on the bundle:

```bash
# Check whether charter.md is out of sync with the bundle
uv run spec-kitty charter status

# Detect orphaned artifacts, contradictions, and staleness in the graph
uv run spec-kitty charter lint

# Validate the bundle against the canonical schema
uv run spec-kitty charter bundle validate
```

If `charter status` reports drift, run `charter sync` first to update the deterministic YAML from
the current `charter.md`, then run `charter synthesize` if project-local doctrine also needs to be
promoted.

---

## Bundle Validation

The core charter bundle is validated against the **CharterBundleManifest v1.0.0** schema by:

```bash
uv run spec-kitty charter bundle validate
```

The v1.0.0 manifest scope is intentionally narrow: tracked `charter.md` plus the derived
`governance.yaml`, `directives.yaml`, and `metadata.yaml` files, with required `.gitignore`
entries for the derived files. `references.yaml` and `context-state.json` are valid Charter files
but are out of v1.0.0 manifest scope, so validation may report them as informational
out-of-scope files rather than errors.

Bundle validation also performs additive synthesis-state checks when `.kittify/doctrine/`,
`.kittify/charter/provenance/`, or `.kittify/charter/synthesis-manifest.yaml` are present.
Run it after generation and synthesis before relying on governed mission prompts.

`charter lint` performs graph-native decay checks — it detects orphaned directives (directives
that appear in the DRG but have no referencing tactic), contradictions (two directives with
conflicting instructions), and staleness (a directive whose provenance references a deleted or
superseded shipped directive).

---

## Sync vs Synthesize

These two operations are different:

| Command | What it does |
|---|---|
| `charter generate` | Renders `charter.md` and `references.yaml` from interview answers, then runs sync. |
| `charter sync` | Syncs `charter.md` content to `governance.yaml`, `directives.yaml`, and `metadata.yaml`. Use after hand-editing `charter.md`. |
| `charter synthesize` | Validates and promotes agent-generated project-local doctrine artifacts from `.kittify/charter/generated/` to `.kittify/doctrine/`. |

Run `charter sync` first when you have edited `charter.md` by hand, then `charter synthesize`
when the doctrine overlay needs to be refreshed.

---

## See Also

- [How Charter Works](charter-overview.md) — mental model and synthesis flow
- [How to Synthesize and Maintain Doctrine](../how-to/synthesize-doctrine.md) — day-to-day synthesis workflow
