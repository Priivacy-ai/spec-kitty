---
work_package_id: WP01
title: Extend the Common-Docs doctrine standard
dependencies: []
requirement_refs:
- C-005
- FR-006
- FR-011
planning_base_branch: docs/common-docs-section-audit
merge_target_branch: docs/common-docs-section-audit
branch_strategy: Planning artifacts for this mission were generated on docs/common-docs-section-audit. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/common-docs-section-audit unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-docs-structural-sanity-01KY53KJ
base_commit: f297f99aa505fc19e7964600d26317ce9e2badd8
created_at: '2026-07-22T16:58:31.731096+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
history:
- timestamp: '2026-07-22T16:30:00Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: src/doctrine/
create_intent: []
execution_mode: code_change
model: sonnet
owned_files:
- src/doctrine/directives/built-in/042-common-docs.directive.yaml
- src/doctrine/styleguides/built-in/common-docs.styleguide.yaml
- src/doctrine/tactics/built-in/common-docs-curation.tactic.yaml
- src/doctrine/tactics/built-in/common-docs-scaffold.tactic.yaml
role: implementer
tags: []
tracker_refs: []
---

# Work Package Prompt: WP01 – Extend the Common-Docs doctrine standard

## ⚡ Do This First: Load Agent Profile

**Before reading any further**, load the `doctrine-daphne` profile via the `/ad-hoc-profile-load` skill.
Adopt its identity, governance scope, boundaries, and the initialization declaration it prints. Everything
below is authored for that profile: doctrine-artifact curation, single-canonical-authority discipline,
extend-in-place (never mint a duplicate), terminology adherence. Do not begin editing until the profile is
loaded and its init declaration is on the record.

- **Profile**: `doctrine-daphne`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## Objectives & Success Criteria

Deliver FR-006 + FR-011 by **extending the artifacts that already exist** — never minting a new
`documentation-placement` directive (C-005). Concretely:

1. `DIRECTIVE_042` `validation_criteria` cites `scripts/docs/docs_structural_lint.py` as the live successor
   gate (today it notes the anti-sprawl ratchet was retired and wires no replacement).
2. `common-docs.styleguide.yaml` gains a **machine-parseable config block** — the single source of truth the
   lint LOADS (FR-011): the concern-bucket→canonical-section map, the "curated-complete" section list
   (initially `architecture/` only), the dated-filename patterns, the point-in-time allowlist
   (`adr/**`, `plans/research/**`, `plans/investigations/**`), and the required frontmatter fields + in-scope
   exclusions (section READMEs).
3. The styleguide `tooling:` / `quality_test` rows and the two `common-docs-*` tactics **stop naming** the
   retired "WP05 anti-sprawl structure ratchet" and name the lint instead.
4. The doctrine tree still loads clean (`spec-kitty doctor doctrine --json`) and the DRG/doctrine freshness
   gate is green.

**Success**: `#2302` becomes closable — the standard is doctrine-defined, no artifact points at a deleted
gate, and the styleguide config parses as the lint's policy store. **Done only when** a repo-wide grep for
`anti-sprawl` / `anti_sprawl_ratchet` / "structure ratchet" in `src/doctrine/` finds no live-gate reference,
and the config block round-trips through the doctrine loader.

## Context & Constraints

- **Charter**: `.kittify/charter/charter.md` — single canonical authority, unification-not-parity, extend
  don't duplicate. Load action context via `spec-kitty charter context --action plan` if unsure.
- **Read before editing**: `plan.md` (IC-01), `spec.md` (FR-006, FR-011, C-005; US2 acceptance scenarios 4+5),
  `research.md` (D1 — the ground-truth of what DIRECTIVE_042 already binds), `data-model.md` (the
  "Extended documentation doctrine" + config-block shape), `contracts/docs-structural-lint.md`
  (§"Configuration source of truth" — the exact keys the lint expects to read).
- **C-005 (binding)**: EXTEND `042-common-docs.directive.yaml` + `common-docs.styleguide.yaml` in place. Do
  NOT author a new directive or an ad-hoc `docs/` page. Highest existing directive number is 046 — no new
  number is minted.
- **Do not duplicate** a rule DIRECTIVE_042 already binds (single root, 13-section structure, `doc_status`
  frontmatter, `related:` validity, no-shadow-tree). The config block adds the *finer* bucket→section map +
  allowlist + machine-parseable form the ratchet's inline constants used to hold — it does not re-state 042.
- **Reverse edge (IC-02 → IC-01)**: `docs_structural_lint.py` does not exist yet (WP02 creates it). You cite
  its path now (`scripts/docs/docs_structural_lint.py`) as the agreed successor; T005 records the follow-up so
  the final module path is confirmed to match once WP02 lands.

## Branch Strategy

- **Strategy**: coord topology; execution worktree allocated per computed lane from `lanes.json`.
- **Planning base branch**: `docs/common-docs-section-audit`
- **Merge target branch**: `docs/common-docs-section-audit`

> Populated by `spec-kitty agent mission tasks` / `finalize-tasks`. Do not change manually.

## Subtasks & Detailed Guidance

### Subtask T001 — Extend DIRECTIVE_042 `validation_criteria` to cite the lint [P]

- **Purpose**: Close the live gap the audit surfaced — 042's `validation_criteria` notes the ratchet was
  retired but wires **no** replacement gate (US2 scenario 4).
- **Steps**:
  1. Open `src/doctrine/directives/built-in/042-common-docs.directive.yaml`. Read the whole file first —
     understand its existing `validation_criteria` block and how criteria are phrased (match the surrounding
     style/voice exactly; doctrine YAML is prose-in-fields, not free markdown).
  2. Locate the criterion/note that currently references the retired anti-sprawl ratchet. Replace the
     "retired, no replacement" language with a criterion that names `scripts/docs/docs_structural_lint.py` as
     the live mechanical gate enforcing the standard (index completeness for curated-complete sections,
     point-in-time placement, no shadow tree, in-scope frontmatter).
  3. Keep the enforcement level (`required`) and every other criterion unchanged — you are wiring one gate,
     not re-authoring the directive.
- **Files**: `src/doctrine/directives/built-in/042-common-docs.directive.yaml`.
- **Validation**: `spec-kitty doctor doctrine --json` still reports 042 healthy; a grep for `anti-sprawl` in
  this file returns nothing live; the new criterion reads as a peer of the existing ones.
- **Edge cases**: if 042 uses an `id`/`ref` convention for criteria, preserve it — do not renumber siblings.

### Subtask T002 — Add the FR-011 machine-parseable config block (SSOT) to the styleguide

- **Purpose**: Give the lint ONE policy store to LOAD (FR-011, C-005) so prose-standard and code-gate cannot
  drift. This is the load-bearing deliverable of the WP.
- **Steps**:
  1. Open `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml`; read it fully. The block's
     top-level wrapper key is the **concrete constant `structural_lint_config:`** (PINNED interface contract —
     WP02's `load_config()` codes against exactly this key and fails LOUD if it is absent, so it is not a free
     choice). Place it where it reads naturally in the styleguide's schema. Record the pinned key
     `structural_lint_config:` in T005's follow-up note for WP02.
  2. Populate the block with, at minimum (see `contracts/docs-structural-lint.md` §Configuration + `data-model.md`):
     - `curated_complete_sections:` — list, initially `["architecture"]` only (all other section indexes are
       landing pages, exempt from `index_completeness`).
     - `concern_bucket_to_section:` — the (a–e) bucket → canonical home map from `data-model.md`
       (`how_to`→`development/`, `reference_policy`→`development/`, `point_in_time`→`plans/engineering-notes/`,
       `ops_runbook`→`operations/`, `generated_nav`→pinned, `doctrine_artifact`→`src/doctrine/`).
     - `point_in_time_patterns:` — the dated-filename regex/patterns ONLY (e.g. `^\d{4}-\d{2}`).
     - `point_in_time_markers:` — a **machine-checkable** list encoding the "self-declares point-in-time"
       signal for files whose basename does NOT match a dated pattern (the `883-*` dossiers are point-in-time
       but do NOT match `^\d{4}-\d{2}`). Encode it concretely so WP02 T006 codes against a config field, NOT a
       guess — e.g. a list of frontmatter `field: value` pairs (`doc_status: point_in_time`,
       `doc_status: closeout`) and/or exact description phrases the lint can substring-match. Do NOT leave this
       as free-prose "use judgment".
     - `point_in_time_allowlist:` — `["adr/**", "plans/research/**", "plans/investigations/**"]` plus the
       broad `plans/**` allow-zone.
     - `frontmatter_required_fields:` — the fields every in-scope page must carry (`doc_status`/`updated`;
       `type` where applicable — mirror what 042 already binds, do not invent new fields).
     - `frontmatter_in_scope_exclusions:` — section `README.md` landing pages (the 3 frontmatter-less
       `docs/adr/{1.x,2.x,3.x}/README.md` are allowlisted / deferred to #2227).
     - `shadow_tree_nav_exemptions:` — `index.md`, `README.md`, `toc.yml`, and era files
       (`README-N.x.md`, `00-SYNTHESIS.md`).
     - `guides_boundary:` — restate the C-001 rule (nothing relocates into `docs/guides/`).
  3. Keep values as plain YAML scalars/lists (no anchors, no custom tags) so a stdlib/`ruamel` load is trivial
     for WP02.
- **Files**: `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml`.
- **Validation**: `python -c "import yaml,sys; yaml.safe_load(open('src/doctrine/styleguides/built-in/common-docs.styleguide.yaml'))"`
  succeeds; `spec-kitty doctor doctrine --json` reports the styleguide healthy; every key the contract's
  §Configuration names is present.
- **Edge cases**: do not encode a policy the lint cannot mechanically evaluate (e.g. free-prose "use judgment")
  — every entry must be a concrete list/pattern the lint can apply. This is what T010 (WP02) asserts agreement on.

### Subtask T003 — Rewrite the styleguide `tooling:` / `quality_test` rows: name the lint

- **Purpose**: Reconcile 2 of the 4 dangling-ratchet references (US2 scenario 5).
- **Steps**:
  1. In the same styleguide file, the **`tooling:` section still cites the retired "WP05 anti-sprawl structure
     ratchet"** as a live gate — this is a KNOWN live citation that MUST be reconciled (do not miss it). Find
     every `tooling:` map row and the `quality_test` field that names that ratchet (`research.md` D1 /
     `plan.md` IC-01 flag these rows).
  2. Rewrite each to name `scripts/docs/docs_structural_lint.py` (and its invocation
     `python -m scripts.docs.docs_structural_lint`, matching `quickstart.md`), describing it as the
     structural gate. Preserve the row structure/keys — swap the referent, not the schema.
- **Files**: `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml`.
- **Validation**: no `tooling`/`quality_test` row references the ratchet; the styleguide still loads.
- **Edge cases**: if a row references the ratchet's *file path* (`scripts/docs/anti_sprawl_ratchet.py`),
  it must change to the lint path — that file is deleted.

### Subtask T004 — Reconcile the two `common-docs-*` tactics

- **Purpose**: Reconcile the remaining 2 dangling-ratchet artifacts (US2 scenario 5).
- **Steps**:
  1. `common-docs-curation.tactic.yaml` — the "run the ruler/ratchet" steps + quality lines (plan.md flags
     ~lines 50/53/58). Rewrite each ratchet mention to invoke/name the lint.
  2. `common-docs-scaffold.tactic.yaml` — the "13-section-ratchet" references (plan.md flags ~lines
     50/52/55/60). Rewrite to the lint; where a step said "the ratchet asserts section index EXISTS", update
     to the lint's index **completeness** semantics for curated-complete sections (do not overstate — only
     `architecture/` is curated-complete initially).
  3. Match each tactic's step/verb phrasing; keep step ordering and IDs.
- **Files**: `src/doctrine/tactics/built-in/common-docs-curation.tactic.yaml`,
  `src/doctrine/tactics/built-in/common-docs-scaffold.tactic.yaml`.
- **Validation**: grep both tactics for `ratchet`/`anti-sprawl` → nothing live; both load via
  `spec-kitty doctor doctrine --json`.
- **Edge cases**: do not import lint *behaviour* that the styleguide config now owns (C-005 single source);
  the tactics only *name/invoke* the lint, they do not restate its policy.

### Subtask T005 — Doctrine freshness gate + record the reverse-edge follow-up

- **Purpose**: Prove the extended doctrine loads and hand the module-path confirmation to WP02.
- **Steps**:
  1. Run `spec-kitty doctor doctrine --json` — expect the pack healthy (no `skipped_profiles`, DRG counts
     valid). If a DRG/graph freshness test exists for doctrine (see the repo's doctrine freshness gate),
     run it and regenerate any derived graph artifact per its documented `--write` path (do NOT hand-edit
     generated graph files).
  2. Run the terminology guard on the doctrine edits:
     `pytest tests/architectural/test_no_legacy_terminology.py -q` (CI-only gate — run it locally before push).
  3. **Record the IC-02→IC-01 reverse edge** in this WP's Activity Log: the pinned config wrapper key
     `structural_lint_config:` (T002) and the lint module path (`scripts/docs/docs_structural_lint.py`) that
     WP02 must both LOAD and match. This is the interface contract between the two WPs — if WP02 lands the lint
     at a different path or reads a different key, this WP's citations must be reconciled.
- **Files**: none new (verification + log).
- **Validation**: `spec-kitty doctor doctrine --json` green; terminology guard green; the follow-up note is
  in the Activity Log.
- **Edge cases**: if the doctrine loader rejects the config block (schema mismatch), fix the block shape here
  — a pack with an invalid styleguide is NOT healthy even if DRG counts pass.

## Test Strategy

- No production code in this WP — verification is loader + gate based.
- `spec-kitty doctor doctrine --json` must report the pack healthy after every subtask.
- `pytest tests/architectural/test_no_legacy_terminology.py -q` green.
- The config block must `yaml.safe_load` cleanly (WP02's T010 will assert the lint reads it).

## Risks & Mitigations

- **Config/lint drift** (FR-011): mitigate by keeping every config value mechanically evaluable and recording
  the exact key path for WP02 (T005). The agreement is enforced by WP02 T010.
- **Accidental duplication** (C-005): re-stating a rule 042 already binds creates two authorities — add only
  the *finer* map/allowlist/machine form, not a paraphrase of 042.
- **Stale path citation**: you cite the lint before it exists — T005's follow-up is the safeguard that the
  path is confirmed once WP02 lands.

## Review Guidance (reviewer-renata / opus)

Verify: no new directive minted (grep `src/doctrine/directives/built-in/` for a `documentation-placement`
file = fail); no artifact names the retired ratchet (grep `anti-sprawl`/`anti_sprawl_ratchet`/"structure
ratchet" across the 4 owned files = must be empty); the styleguide config block carries every key the
contract's §Configuration lists and `yaml.safe_load`s; `spec-kitty doctor doctrine --json` is healthy; the
reverse-edge follow-up (config key path + lint module path) is recorded for WP02.

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Append at the END.

- 2026-07-22T16:30:00Z – system – Prompt created.
- 2026-07-22T18:05:00Z – doctrine-daphne – T001-T005 done. DIRECTIVE_042
  validation_criteria now cites `scripts/docs/docs_structural_lint.py`
  (no anti-sprawl/ratchet phrasing remains, verified by repo-wide grep of
  `src/doctrine/`). `common-docs.styleguide.yaml` gained the
  `structural_lint_config:` block (curated_complete_sections,
  concern_bucket_to_section, point_in_time_patterns, point_in_time_markers,
  point_in_time_allowlist, frontmatter_required_fields,
  frontmatter_in_scope_exclusions, shadow_tree_nav_exemptions,
  guides_boundary) plus reconciled `tooling:`/`quality_test` rows; both
  `common-docs-*` tactics reconciled to name the lint. **Reverse-edge
  IC-02→IC-01 handoff for WP02**: the pinned config wrapper key is
  `structural_lint_config:` inside
  `src/doctrine/styleguides/built-in/common-docs.styleguide.yaml`; the agreed
  lint module path is `scripts/docs/docs_structural_lint.py`
  (`python -m scripts.docs.docs_structural_lint`). If WP02 lands the lint at a
  different path or reads a different key, these 4 artifacts' citations must
  be reconciled to match. **Campsite note**: the built-in Styleguide Pydantic
  model (`src/doctrine/styleguides/models.py`, `extra="forbid"`) and the
  parallel JSON Schema (`src/doctrine/schemas/styleguide.schema.yaml`,
  `additionalProperties: false`) both rejected the new key until extended —
  added an optional `structural_lint_config` field/definition to both plus a
  focused round-trip test in `tests/doctrine/styleguides/test_models.py`;
  this was a load-bearing prerequisite for `spec-kitty doctrine validate` /
  `doctor doctrine` to accept the block, not a scope expansion for its own
  sake. Validation: `spec-kitty doctrine validate` OK on all 4 owned files;
  `spec-kitty doctor doctrine --json` healthy; `spec-kitty doctrine
  regenerate-graph --check` reports the DRG fresh; `pytest
  tests/architectural/test_no_legacy_terminology.py -q` — 4 passed; `pytest
  tests/doctrine/ -q` — 2837 passed; no new mypy/ruff issues introduced.
</content>
