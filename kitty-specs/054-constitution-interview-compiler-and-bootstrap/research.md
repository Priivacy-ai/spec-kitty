# Research: Constitution Interview Compiler and Context Bootstrap

**Feature**: 054 | **Date**: 2026-03-09

---

## Decision 1: The authoritative doctrine catalog is shipped-only by default

**Decision**: `load_doctrine_catalog()` must scan canonised `shipped/` doctrine artifacts by default and exclude `_proposed/` artifacts unless a caller explicitly opts into them for a curation workflow.

**Rationale**: Constitution validation needs a stable, authoritative catalog. Treating `_proposed/` artifacts as normal validation inputs would make pre-canonisation content accidentally authoritative and would blur the curation boundary documented in `src/doctrine/README.md`.

**Alternatives considered**:
- Scan both `shipped/` and `_proposed/` by default: rejected because it makes curation drafts silently affect production validation.
- Ignore `_proposed/` entirely with no opt-in: rejected because curation workflows still need a way to inspect proposed artifacts intentionally.

---

## Decision 2: Project-local doctrine support files are declared explicitly in constitution artifacts

**Decision**: Project-local override/supporting doctrine files are discovered only through explicit declarations in `answers.yaml` and the compiled `references.yaml`.

**Rationale**: The user confirmed these documents should be the authoritative declaration surface. This keeps local support files reviewable, deterministic, and visible in the generated constitution bundle instead of relying on implicit scanning rules.

**Alternatives considered**:
- Fixed project directory scanning under `src/doctrine/`: rejected because it creates hidden coupling and makes accidental files visible.
- Hybrid implicit + explicit discovery: rejected because it weakens determinism and complicates debugging.

---

## Decision 3: Local doctrine file declarations use explicit file paths only

**Decision**: Local doctrine declarations accept explicit file paths only. Directory declarations and glob patterns are out of scope.

**Rationale**: The user called glob and directory patterns risky. Explicit paths keep the constitution deterministic, prevent broad unintended inclusion, and make review diffs much easier to understand.

**Alternatives considered**:
- Directory-level declarations: rejected because they can silently expand as files are added later.
- Glob patterns: rejected because they create hard-to-review expansion behavior and platform-specific edge cases.

---

## Decision 4: Shipped artifacts remain primary when local files target the same concept

**Decision**: If a local supporting file targets the same doctrine concept as a shipped artifact, the shipped artifact stays authoritative. The local file is additive only, and the system emits a warning about the overlap.

**Rationale**: This preserves the integrity of the canonised doctrine catalog while still allowing teams to attach project-specific support material. The warning surfaces potential ambiguity without rejecting the local file outright.

**Alternatives considered**:
- Local file fully supersedes shipped artifact: rejected because it undermines the authoritative shipped doctrine model.
- Merge shipped and local content by field automatically: rejected because free-form markdown support files do not guarantee a safe merge shape.

---

## Decision 5: Local support files may be action-scoped

**Decision**: Local override/supporting file declarations may be global or tied to a specific action (`specify`, `plan`, `implement`, `review`).

**Rationale**: The feature already introduces action-scoped context retrieval. Allowing action-specific local declarations fits the same retrieval model and avoids leaking planning-only or review-only material into unrelated phases.

**Alternatives considered**:
- Global-only declarations: rejected because they force low-signal material into every action.
- Action-only declarations: rejected because some project governance files are intentionally cross-cutting.

---

## Decision 6: Template-set validation still needs a fallback when catalog metadata is empty

**Decision**: If `doctrine_catalog.template_sets` is empty, validate `template_set` against the packaged mission directories under `src/doctrine/missions/` rather than silently skipping validation.

**Rationale**: Template-set validation should never disappear just because an index is missing. The mission directories are the next-best authoritative source already packaged with the CLI.

**Alternatives considered**:
- Silent skip when the catalog has no template sets: rejected because it creates hidden acceptance of invalid values.
- Hard-fail on empty template-set catalog: rejected because it is stricter than the rest of the offline-friendly constitution behavior.

---

## Decision 7: Constitution output remains a configuration layer, not a materialized doctrine copy

**Decision**: `constitution generate` writes `constitution.md`, `references.yaml`, and sync artifacts only. Runtime doctrine prose is fetched on demand from shipped doctrine assets or declared local support files; no generated `library/` directory is maintained.

**Rationale**: Materialized doctrine copies drift from the source catalog. Treating the constitution as a selection/configuration layer keeps generation deterministic and makes runtime retrieval the single source of truth.

**Alternatives considered**:
- Keep a generated `library/` cache: rejected because it creates stale copies and cleanup complexity.
- Make materialization optional: rejected because it would leave two behavior paths to maintain and test.

---

## Decision 8: Action-scoped context uses index intersection plus dedicated repositories

**Decision**: `constitution context --action <action>` scopes retrieval using the intersection of the action index and the project's selected references. Each artifact type is fetched only through its matching repository service.

**Rationale**: This prevents `plan` or `specify` bootstrap from pulling unrelated `implement` or `review` doctrine. It also preserves type boundaries between directives, tactics, styleguides, and toolguides.

**Alternatives considered**:
- Return all selected doctrine for every action: rejected because it adds noise and weakens the action model.
- Fetch all artifact types through a single generic file scanner: rejected because it blurs repository ownership and makes cross-domain mistakes easier.

---

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Existing code paths assume `_proposed/` artifacts are visible during normal validation | Add shipped-only catalog tests and an explicit `include_proposed` opt-in path |
| Local support file declarations become too loose or non-deterministic | Restrict to explicit file paths and record them in `references.yaml` |
| Teams may assume local files override shipped doctrine | Emit warnings on conflicts and document shipped-primary additive semantics |
| Action-scoped local declarations could be ignored at runtime | Model `action` directly in the declaration shape and test retrieval against per-action context calls |
