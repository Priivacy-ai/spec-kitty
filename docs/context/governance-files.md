---
title: Governance Files Reference
description: Authoritative reference for every file under .kittify/charter/ — who writes it, what it contains, and whether you can edit it.
doc_status: active
updated: '2026-06-03'
related:
- docs/context/charter-overview.md
---
# Governance Files Reference

The Charter governance layer lives primarily in `.kittify/charter/`, with promoted project-local
doctrine under `.kittify/doctrine/`. Most files are derived, runtime-managed, or agent-generated
inputs and must not be hand-edited. This page describes the common Charter-era files and the
commands that own them.

> **Key rule**: edit `.kittify/charter/charter.md` for Spec Kitty runtime policy changes.
> External governance docs such as `spec/constitution.md` are supporting context referenced
> from the charter, not alternate authoritative charter paths. Re-run `charter sync` and
> `charter synthesize` instead of patching derived YAML, runtime state, or synthesis outputs
> by hand.

---

## File Table

| File path | Who writes it | Contains | Edit directly? |
|---|---|---|---|
| `.kittify/charter/charter.md` | **Human** via interview/generate, then direct edits | Mission vision, directives, doctrine selections, policy decisions | Yes |
| `.kittify/charter/interview/answers.yaml` | `charter interview` | Captured answers used by `charter generate` | Prefer re-running `charter interview` |
| `.kittify/charter/references.yaml` | `charter generate` | Reference manifest for built-in doctrine and local support files | No |
| `.kittify/charter/governance.yaml` | `charter sync` / `charter generate` | Testing, quality, performance, branch, and doctrine-selection config | No |
| `.kittify/charter/directives.yaml` | `charter sync` / `charter generate` | Extracted directives with IDs, descriptions, and severity | No |
| `.kittify/charter/metadata.yaml` | `charter sync` / `charter generate` | Charter hash, extraction timestamp, source path, parser stats | No |
| `.kittify/charter/context-state.json` | Runtime context loader | Per-action first-load state for compact/bootstrap context | No |
| `.kittify/charter/generated/{directives,tactics,styleguides}/` | Agent harness | Candidate YAML artifacts consumed by `charter synthesize` | No routine hand edits |
| `.kittify/charter/synthesis-manifest.yaml` | `charter synthesize` / `charter resynthesize` | Manifest of promoted synthesized artifacts and content hashes | No |
| `.kittify/charter/provenance/*.yaml` | `charter synthesize` / `charter resynthesize` | Provenance sidecars for project-local doctrine artifacts | No |
| `.kittify/charter/.staging/` | Synthesizer | Temporary validation/promote workspace; `.failed` dirs may remain for diagnosis | No |
| `.kittify/doctrine/` | `charter synthesize` / `charter resynthesize` | Project-local doctrine overlay used with built-in doctrine | No |
| `.kittify/doctrine/PROVENANCE.md` | `charter synthesize` fresh-project path | Human-readable provenance for the minimal fresh-project doctrine seed | No |

Current `charter generate` writes `charter.md` and `references.yaml`, then runs `charter sync`.
It no longer materializes doctrine library pages as authoritative `library/*.md` files; doctrine
content is resolved through `references.yaml` and the built-in/project doctrine service.

Normal hand-authored `.kittify/charter/charter.md` is the supported default. `charter generate`
refuses to overwrite a symlinked `charter.md`, including with `--force`; replace the symlink with
a normal file before generation.

---

## External Governance Documents

Some repositories already have a public constitution, governance policy, or engineering handbook
outside `.kittify/` (for example `spec/constitution.md`). Do not treat `.kittify/charter/charter.md`
as a second full copy that must stay byte-for-byte equal to that document.

Use this ownership model instead:

| Document | Role |
|---|---|
| Public governance document outside `.kittify/` | Human-facing policy, historical record, or public project constitution. |
| `.kittify/charter/charter.md` | Runtime charter consumed by Spec Kitty. It should contain the operative directives agents need, plus pointers to external authority when useful. |
| `.kittify/charter/governance.yaml`, `directives.yaml`, `metadata.yaml` | Generated runtime bundle derived only from the current contents of `.kittify/charter/charter.md`. |

Recommended pattern:

1. Keep the external constitution as the public source for long-form governance.
2. Keep `.kittify/charter/charter.md` concise and runtime-oriented: summarize the binding
   directives, name the public constitution, and record where agents should look for supporting
   policy.
3. If agents should inspect a directory of supporting policy, declare that directory in the
   charter's fenced `authority_paths` block:

````markdown
## External Governance Authority

The public project constitution lives in `spec/constitution.md`. The Spec Kitty runtime charter
summarizes the directives that must be injected into mission prompts; the public constitution
remains the long-form public governance record.

```yaml
authority_paths:
  - spec/
```
````

Current Spec Kitty does not support a configured external charter path that replaces
`.kittify/charter/charter.md`. If a project needs a single physical file for sync-only extraction,
a symlink can point `.kittify/charter/charter.md` at another markdown file, subject to the sync and
generate behavior below. Do not use the symlink model for Windows or mixed-platform projects unless
native Windows CI proves the checkout can create and preserve the symlink; use a runtime summary or
generated copy instead.

### Sync Behavior by Charter Shape

`spec-kitty charter sync` always treats `.kittify/charter/charter.md` as the input path and writes
the generated YAML bundle into `.kittify/charter/`.

| Charter shape | Command behavior | Operator responsibility |
|---|---|---|
| Hand-authored `.kittify/charter/charter.md` | `charter sync` reads that file and writes `governance.yaml`, `directives.yaml`, and `metadata.yaml` next to it. `charter generate --force` may overwrite it. | Edit `charter.md`, run `spec-kitty charter sync`, then review drift with `charter status`. |
| Generated copy in `.kittify/charter/charter.md` | `charter sync` reads the generated copy as the source for runtime extraction. It does not pull from the external document that produced the copy. | Re-run the external copy/generation step first, then run `spec-kitty charter sync`. Do not hand-edit the generated copy unless it has become the runtime source. |
| Symlink at `.kittify/charter/charter.md` | `charter sync` follows the symlink for reading charter content. Generated YAML still lands in `.kittify/charter/`, not beside the symlink target. `charter generate` refuses to overwrite a symlinked charter before compilation, sync, gitignore updates, or staging. | Treat this as a sync-only, Unix-oriented model. Keep the symlink target committed and available on every checkout. Broken or platform-incompatible symlinks make sync fail. Prefer another model for Windows/shared checkouts. |

Avoid equality checks between a public constitution and `.kittify/charter/charter.md` unless the
project has deliberately adopted a mirror policy. A better check is that the runtime charter
names the public authority and that `charter status` reports no drift in the generated bundle.

---

## Git Policy

Fresh checkouts must contain human-owned policy and must not require operators
to commit local build products. Use this policy for Spec Kitty-governed
projects:

| Path | Git policy | Refresh command |
|---|---|---|
| `.kittify/charter/charter.md` | Commit. This is the Spec Kitty runtime policy source. | Edit directly, then run `spec-kitty charter sync`. |
| `.kittify/charter/governance.yaml` | Do not commit. Generated from `charter.md`. | `spec-kitty charter sync` |
| `.kittify/charter/directives.yaml` | Do not commit. Generated from `charter.md`. | `spec-kitty charter sync` |
| `.kittify/charter/metadata.yaml` | Do not commit. Generated hash/parser state. | `spec-kitty charter sync` |
| `.kittify/charter/references.yaml` | Do not commit by default. Generated by `charter generate`; treat as derived unless a project explicitly adopts a stricter tracked-reference policy. | `spec-kitty charter generate --from-interview` |
| `.kittify/charter/provenance/*` | Do not commit. Synthesis provenance is regenerated with the promoted doctrine overlay. | `spec-kitty charter synthesize` |
| `.kittify/charter/synthesis-manifest.yaml` | Do not commit. Generated synthesis manifest. | `spec-kitty charter synthesize` |
| `.kittify/doctrine/graph.yaml` | Do not commit. Project-local DRG overlay synthesized locally when needed. | `spec-kitty charter synthesize` |
| `.kittify/doctrine/{directive,tactic,procedure,overlays}/` | Commit only when the project intentionally carries a durable project-local doctrine overlay. | `spec-kitty charter synthesize` or `spec-kitty charter resynthesize` |

If a project has a public governance document, keep it in that public location and reference it
from `charter.md`:

```yaml
governance_references:
  - spec/constitution.md
```

Do not enforce markdown equality between the public document and `.kittify/charter/charter.md`
unless the project deliberately adopts a mirror policy outside Spec Kitty's defaults.

The `.gitignore` should match that policy: ignore generated charter YAML,
provenance, synthesis manifests, and `.kittify/doctrine/**`, then re-include
only durable doctrine overlay subdirectories if the project commits them.
Spec Kitty's own repository follows that split: `charter.md` and selected
project-local doctrine overlays are tracked, while generated charter YAML and
`graph.yaml` remain local.

When a required local generated file is missing, do not hand-create it. Run:

```bash
spec-kitty charter sync
spec-kitty charter status
spec-kitty charter synthesize
spec-kitty charter bundle validate
```

Use `charter status` to detect missing or stale local synthesis state such as
a missing synthesized DRG. Use `charter synthesize` to regenerate that local
state. `charter bundle validate` validates the committed charter-bundle
manifest and reports missing tracked policy, missing generated charter YAML,
missing `.gitignore` entries, and invalid synthesis state when synthesis
artifacts are present; it does not require a project-local DRG to exist in
fresh checkouts that intentionally rely on built-in doctrine.

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

## Migrating Constitution-Era Files

Projects upgraded from early Spec Kitty layouts may still have stale governance files:

| Legacy path | Current action |
|---|---|
| `.kittify/memory/constitution.md` | Move current runtime policy into `.kittify/charter/charter.md`, or keep the old file only as archived project history. |
| `.kittify/constitution/constitution.md` | Move current runtime policy into `.kittify/charter/charter.md`; do not keep it as an alternate runtime source. |
| `.kittify/constitution/{governance,directives,metadata}.yaml` | Delete or archive after confirming `.kittify/charter/{governance,directives,metadata}.yaml` is generated by `charter sync`. |

If the old constitution file is still useful as public or organizational context, put it in a
normal project path such as `spec/constitution.md` and list that path in `governance_references`.

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
superseded built-in directive).

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
- [How to Synthesize and Maintain Doctrine](../guides/synthesize-doctrine.md) — day-to-day synthesis workflow
