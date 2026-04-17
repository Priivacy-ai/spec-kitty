# Quickstart — Charter Synthesizer (Phase 3)

**Audience**: operators configuring a project's charter and generating project-local doctrine for the first time (US-1), plus reviewers running targeted resynthesis (US-2 / US-3 / US-4).
**Mission**: `phase-3-charter-synthesizer-pipeline-01KPE222`
**Status**: forward-looking — describes the operator experience once WP3.1 → WP3.8 have merged. Commands below do not yet exist on `main`.

---

## Prerequisites

- spec-kitty version ≥ the release that ships this tranche.
- A project whose charter interview has been completed (i.e. `.kittify/charter/charter.md` is present and fresh).
- A configured synthesis adapter (governed by ADR-6, #521). For local dry runs without a production adapter, `--adapter fixture` opts into the test-only adapter (R-0-5).

---

## 1 · First-time synthesis for a fresh project (US-1)

```bash
# From your project root (NOT a worktree).
# Assumes /spec-kitty.charter has already run.

# Inspect what synthesis will produce before committing:
spec-kitty charter synthesize --dry-run

# Run the real synthesis. Artifacts, provenance, project DRG, and manifest
# land under .kittify/doctrine/ (content) and .kittify/charter/ (bookkeeping)
# in a single atomic promote.
spec-kitty charter synthesize

# Verify the committed bundle:
spec-kitty charter bundle validate
```

What you should see afterwards:

```
.kittify/
├── doctrine/                                       # NEW / extended — synthesized CONTENT
│   ├── directives/
│   │   └── <NNN>-<slug>.directive.yaml             # NEW — directive artifacts (IDs like PROJECT_001)
│   ├── tactics/
│   │   └── <slug>.tactic.yaml                      # NEW — tactic artifacts
│   ├── styleguides/
│   │   └── <slug>.styleguide.yaml                  # NEW — styleguide artifacts
│   └── graph.yaml                                  # NEW — project DRG overlay (path already read
│                                                   #         by src/charter/_drg_helpers.py)
└── charter/                                        # pre-existing tree — synthesis bookkeeping added
    ├── charter.md                                  # unchanged (human-authored)
    ├── governance.yaml                             # unchanged (derived from charter.md)
    ├── directives.yaml                             # unchanged (derived from charter.md)
    ├── metadata.yaml                               # unchanged (derived from charter.md)
    ├── provenance/<kind>-<slug>.yaml               # NEW — per-artifact provenance sidecars
    └── synthesis-manifest.yaml                     # NEW — commit marker (manifest-last)
```

Confirm project-specific content is now flowing into `charter context`:

```bash
# Before synthesis, this surfaced only shipped-layer content.
# After synthesis, at least one project-specific item is present (SC-005).
spec-kitty charter context --action specify --json | jq '.context' | head -40
```

### What just happened under the hood

1. Orchestrator read interview answers + shipped doctrine + shipped DRG.
2. Interview-mapping selected `SynthesisTarget`s (see `data-model.md §E-2`).
3. Each target was passed through the adapter seam (fixture or production).
4. Every returned body was schema-validated against its shipped-kind schema (FR-019).
5. All artifacts + provenance sidecars + project DRG overlay were staged under `.kittify/charter/.staging/<runid>/` with internal `doctrine/` and `charter/` subtrees mirroring the final layout.
6. The merged (shipped + project) DRG was validated — zero dangling refs (FR-008), zero duplicate edges, no cycles.
7. On pass, files were promoted via ordered `os.replace` into their final trees (content → `.kittify/doctrine/`, bookkeeping → `.kittify/charter/`); the synthesis manifest was written last as the authoritative commit marker (KD-2).
8. Staging dir was wiped on success.

### If something goes wrong

- **Schema failure** from an adapter output → `SynthesisSchemaError`, exit nonzero, staging dir preserved at `.kittify/charter/.staging/<runid>.failed/` for diagnosis.
- **Dangling reference** in the project DRG layer → `ProjectDRGValidationError`, same preservation.
- **Path-guard violation** (write attempt outside `.kittify/doctrine/` or `.kittify/charter/`) → `PathGuardViolation`, fails before filesystem is touched.

In every failure case, no files are committed to the live tree. Your working state is unchanged.

---

## 2 · Targeted resynthesis by shipped DRG URN (US-2)

You changed `DIRECTIVE_003` in your interview and want every project-local artifact whose provenance references it regenerated, leaving everything else alone.

```bash
spec-kitty charter resynthesize --topic directive:DIRECTIVE_003
```

Why this routes to tier 2 (DRG URN) rather than tier 1 (project-local kind+slug): shipped directives use IDs like `DIRECTIVE_003`, and synthesized directives use `PROJECT_<NNN>`, so no project-local artifact has the id `DIRECTIVE_003` — tier 1 misses, tier 2 matches the shipped DRG node, and the resolver expands to every artifact whose provenance `source_urns` contains `directive:DIRECTIVE_003`.

Observable outcome:
- Only artifacts whose provenance references `directive:DIRECTIVE_003` are regenerated.
- Untouched artifact files have byte-identical `content_hash` before and after — verify with `git diff .kittify/doctrine/ .kittify/charter/`.
- The synthesis manifest is rewritten with a new `run_id` and updated entries for the regenerated artifacts; entries for untouched artifacts retain their prior `content_hash`.

---

## 3 · Targeted resynthesis by project-local artifact kind + slug (US-3)

You want to regenerate exactly one project-local tactic. The slug is the one you can read in `.kittify/doctrine/tactics/`.

```bash
spec-kitty charter resynthesize --topic tactic:how-we-apply-directive-003
```

This hits tier 1 (kind+slug against the project-local artifact set). The resolver sees a project-local tactic at `.kittify/doctrine/tactics/how-we-apply-directive-003.tactic.yaml` and regenerates only that one artifact.

---

## 4 · Targeted resynthesis by interview section (US-4)

You revised your testing-philosophy answers and want every artifact derived from that section regenerated.

```bash
spec-kitty charter resynthesize --topic testing-philosophy
```

Resolves via tier 3 (interview-section label) — the string has no colon, so tiers 1 and 2 cannot apply.

---

## 5 · Handling ambiguous or invalid selectors (US-6)

```bash
spec-kitty charter resynthesize --topic styleguide:nonexistent
```

Output (exit code 2):

```
┌─ Cannot resolve --topic "styleguide:nonexistent" ─────────────┐
│ Tried: kind_slug, drg_urn                                     │
│                                                               │
│ Nearest candidates:                                           │
│   - styleguide:python-testing-style   (distance 5)            │
│   - styleguide:docs-style-guide       (distance 6)            │
│                                                               │
│ Remediation:                                                  │
│   Use one of the enumerated candidates, or run                │
│   `spec-kitty charter resynthesize --list-topics`             │
│   to see all valid selectors.                                 │
└───────────────────────────────────────────────────────────────┘
```

No files are written. No model call was made.

---

## 6 · Dry-run for fixture / CI environments

```bash
# Uses the test-only fixture adapter. Requires corresponding fixture files
# under tests/charter/fixtures/synthesizer/<kind>/<slug>/<hash>.<kind>.yaml.
# Missing fixtures fail loudly with the expected path.
spec-kitty charter synthesize --adapter fixture
```

Useful for:
- Local smoke tests without spending model tokens.
- CI jobs that verify layout + provenance + manifest integrity without live model access.
- Regression tests on the fixture set itself.

Do NOT use `--adapter fixture` for production synthesis. The fixture adapter's output is test data, and the provenance stamp (`adapter_id=fixture`) makes that obvious to any later auditor.

---

## 7 · Common operator operations

```bash
# List every currently-committed synthesized artifact:
yq '.artifacts[] | .path' .kittify/charter/synthesis-manifest.yaml

# Show provenance for a specific artifact:
cat .kittify/charter/provenance/tactic-how-we-apply-directive-003.yaml

# Verify the bundle end-to-end (extended in this tranche per FR-015):
spec-kitty charter bundle validate

# Remove all synthesized state (returns the project to pre-synthesis):
rm -rf .kittify/doctrine/{directives,tactics,styleguides}
rm -f  .kittify/doctrine/graph.yaml
rm -rf .kittify/charter/provenance
rm -f  .kittify/charter/synthesis-manifest.yaml
```

The last step — removing synthesized state — is a supported reset path. The
shipped layer is entirely read-only (C-001), so it's safe to delete project-layer
state under both trees and rerun `spec-kitty charter synthesize` at any time.
Do not delete `.kittify/charter/charter.md`, `governance.yaml`, `directives.yaml`,
or `metadata.yaml` — those are the charter interview / compile artifacts, not
synthesis output.

---

## 8 · Troubleshooting

### "I see a `.staging/<runid>.failed/` directory"

A previous synthesis run failed after staging. The live tree is unaffected. Inspect `.kittify/charter/.staging/<runid>.failed/cause.yaml` for the failure reason. Once diagnosed, remove the directory and rerun `spec-kitty charter synthesize`.

### "charter context output doesn't show my synthesized content"

Check that `.kittify/charter/synthesis-manifest.yaml` exists. If missing, the live tree is being treated as partial and `DoctrineService` is not loading the project layer. Rerun `spec-kitty charter synthesize`. If the manifest exists but `content_hash` checks fail, that is a `ManifestIntegrityError` — typically caused by manual edits to generated files; revert or regenerate. Also confirm `.kittify/doctrine/` is present: if the directory is missing, the extended project-root candidate list (FR-009) falls back to shipped-only, which is the legacy-project behaviour.

### "FixtureAdapterMissingError — expected_path=..."

You're in `--adapter fixture` mode and the fixture for this request is missing. The error names the exact path at which the fixture should live. Record it (run the production adapter once, capture its output, copy to the named path) and rerun.

### "I want to regenerate everything"

Full rerun is always legal:
```bash
spec-kitty charter synthesize
```
It will replace every artifact + provenance + DRG overlay with a fresh run, then rewrite the manifest. Artifacts with identical normalized inputs and identical adapter identity will have identical `content_hash` values — git diffs will show only what actually changed.

---

## 9 · What's deliberately not in this tranche

- No free-text `--topic` (C-004).
- No synthesis of paradigms, procedures, toolguides, or agent-profiles (C-005).
- No automatic code-reading / URL-fetching / repo crawl.
- No migration tooling for pre-Phase-3 projects (ADR-7, out of scope).
- No monorepo / cross-repo visibility (ADR-8, out of scope).

Each of these has a clear upgrade path in a later tranche. They are deferred to keep this mission reviewable.
