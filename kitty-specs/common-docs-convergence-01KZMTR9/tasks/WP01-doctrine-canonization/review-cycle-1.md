---
affected_files: []
cycle_number: 1
mission_slug: common-docs-convergence-01KZMTR9
reproduction_command:
reviewed_at: '2026-08-10T05:32:46Z'
reviewer_agent: user
wp_id: WP01
---

# WP01 Review — REJECTED

Reviewer: claude (independent). Reviewed diff `kitty/mission-common-docs-convergence-01KZMTR9...HEAD` on lane-a worktree.

## Summary
Criteria 1–6 pass. Criterion 7 FAILS: the edited styleguide YAML is **not valid against its own generated schema**. WP01's four new T004 `structural_lint_config` fields turn a previously-green architectural-gate test **red**.

## Failing criterion

### Criterion 7 — "The edited YAML is valid" — FAIL
`tests/doctrine/test_schema_generation_integrity.py::test_generated_styleguide_schema_validates_the_shipped_common_docs_artefact`

```
AssertionError: ["Additional properties are not allowed
('non_content_dirs', 'one_index_per_dir', 'root_allowlist',
 'sanctioned_content_sections' were unexpected)"]
```

Proof it is WP01-introduced (not a pre-existing red):
- Base branch (`kitty/mission-common-docs-convergence-01KZMTR9`, i.e. styleguide WITHOUT the four new fields): test **PASSES** (1 passed).
- WP01 worktree (styleguide WITH the four new fields): test **FAILS** (1 failed, 36 passed in the file).

Root cause: the generated styleguide schema defines `structural_lint_config` with
`additionalProperties: False` and a closed property allowlist in
`scripts/generate_schemas.py` (`STRUCTURAL_LINT_CONFIG_SCHEMA`). That allowlist does
NOT include the four T004 fields WP01 added:
`sanctioned_content_sections`, `non_content_dirs`, `root_allowlist`, `one_index_per_dir`.
The paired assertion in `tests/doctrine/test_schema_generation_integrity.py` (~line 121)
also pins the exact property set and omits these four.

Note: the narrowly-named test in the criterion, `tests/docs/test_docs_structural_lint.py`,
DOES pass (30 passed against the worktree) — `load_config` tolerates the extra keys.
But "the edited YAML is valid" is broader than load_config, and the shipped schema
validation is a real, currently-green gate that this change breaks.

## Scope tension the implementer must resolve
The fix requires editing files OUTSIDE WP01's three owned files:
- `scripts/generate_schemas.py` — add the four properties to
  `STRUCTURAL_LINT_CONFIG_SCHEMA.properties` (type: array-of-string for the three
  lists, boolean for `one_index_per_dir`).
- `tests/doctrine/test_schema_generation_integrity.py` — add the four keys to the
  expected property set (~line 121).

Because criterion 6 confines WP01 to the three doctrine YAML files, the T004 fields
cannot be landed green under the current file scope. Options for the implementer:
1. Escalate the scope gap — the mission plan appears to assume "WP04 owns the asset
   code (`docs_structural_lint.py`)" but does NOT assign ownership of the schema
   generator (`scripts/generate_schemas.py`) or its integrity test. Someone must own
   the schema extension, sequenced no later than the WP that lands the T004 fields.
2. Defer the four T004 field declarations to the WP that owns the schema, so WP01 does
   not land a red architectural-gate test.

Do NOT land the T004 fields while `generate_schemas.py`'s schema still rejects them —
that green-washes a branch-introduced red on an architectural gate.

## What is correct (no change needed)
- C-012 (blocking): `audience:` is NOT in `frontmatter_required_fields` — verified
  (only `doc_status`, `updated`). PASS.
- `audience:` canonized in DIRECTIVE_042 (semantics + resolvable repo-relative `.md`
  path into `docs/context/audience/` + `audience-resolvable` tooling row naming the
  resolver) and DIRECTIVE_047 (procedure + validation criterion + refs to 042 and
  common-docs). PASS.
- Common-docs styleguide declares the `audience:` rule (principle + `audience-resolvable`
  pattern + tooling row). PASS.
- `concern_bucket_to_section` split into `how_to_internal: development/` /
  `how_to_external: guides/` and `guides_boundary` rewritten to audience-based routing,
  both with recorded rationale. PASS.
- Diff confined to the three owned files. PASS.
