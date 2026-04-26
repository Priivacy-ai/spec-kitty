# Research: Doctrine Enrichment — Frontend, Brownfield, BDD, and Tactic Normalization

## 1. Tactic Loader Behavior (rglob — confirmed safe for normalization)

**Decision**: Tactic normalization (FR-004) requires no loader changes.

**Finding**: `src/doctrine/base.py` line 119 uses `self._shipped_dir.rglob(self._glob)` for shipped artifact discovery. The `refactoring/` subdirectory has been in production since the refactoring tactic pack was introduced — the loader already handles nested directories. WP01 can safely move files into subdirectories without touching any Python code.

**Rationale**: The `id` field inside each YAML file is the canonical identity; the file path is incidental. Any cross-references between tactics use the `id` field, not the file path.

**Verification**: Run `pytest -m doctrine` before and after WP01 and confirm `len(tactic_repo.load_all())` is unchanged.

---

## 2. `development-bdd` vs `behavior-driven-development` — Coexistence Rationale

**Decision**: Two separate tactic files with distinct purposes; they coexist without duplication.

| Tactic | ID | Location | Purpose |
|--------|-----|---------|---------|
| Existing | `behavior-driven-development` | `shipped/` root (then `testing/` after WP01) | *How to write BDD scenarios* — the technique: Given/When/Then, stakeholder validation, wiring to executable tests |
| New (WP03) | `development-bdd` | `shipped/architecture/` | *BDD as a design practice* — expressing observable behavioral contracts that define system boundaries before implementation begins; architecture-level concern |

**Rationale**: The quickstart `development-bdd.tactic.md` focuses on "defining system behavior through behavioral contracts" as a design artifact, while the existing spec-kitty tactic is a comprehensive step-by-step guide to writing BDD scenarios. They are used at different stages: `development-bdd` during design/architecture, `behavior-driven-development` during implementation.

The implementer must make this distinction clear in both `purpose` fields to avoid user confusion.

---

## 3. Profile Schema — `tactic-references` Field

**Decision**: Use the existing `tactic-references` array field in the agent profile schema; no schema changes needed.

**Finding**: `src/doctrine/schemas/agent-profile.schema.yaml` includes `tactic-references` as an optional array of `agent_tactic_reference` objects (required fields: `id`, `rationale`). All profile enrichment operations (WP06–WP08) use this existing field.

The `paradigm` field does not exist as a formal reference field in the profile schema — paradigm references appear in `context-sources.doctrine-layers` or as free-text in `purpose`. Architect Alphonso's BDD paradigm ref (FR-011) is expressed via `context-sources.doctrine-layers: [paradigms]` (already present) rather than a new field.

---

## 4. Profile Inheritance Resolution — How the Loader Works

**Decision**: The WP09 test must account for the actual resolution model: tactic references are currently NOT automatically inherited — they are declared per-profile.

**Finding**: Reviewing `src/doctrine/agent_profiles/` — the profile model stores `tactic_references` as a list on each profile. `specializes-from` is used for routing priority inheritance and `specialization-context` merging, but tactic references are NOT automatically propagated from base to specialist profiles. Each profile independently declares its tactic refs.

**Impact on WP09**: The generic inheritance test (FR-008) should verify that any tactic declared on a base profile ALSO appears explicitly on all specialist profiles. This is an assertion that the doctrine author has not missed adding a reference when creating a specialist — it is a documentation-completeness test, not a runtime inheritance assertion.

The test skeleton in the plan is correct: it checks that `profile.tactic_references` contains all the base's tactic IDs. The implementer should confirm this interpretation by reading `tests/doctrine/test_profile_inheritance.py` before writing new tests.

---

## 5. Attribution Format — Confirmed Pattern

**Decision**: Two-layer attribution:
1. `notes` field in shipped YAML: single line `Adapted from patterns.sddevelopment.be` (or `Source: patterns.sddevelopment.be/<path>`)
2. Import file in `src/doctrine/_reference/quickstart-agent-augmented-development/candidates/`: full provenance (source path, adaptation notes, external URL)

**Finding**: This matches the existing pattern in `_reference/quickstart-agent-augmented-development/candidates/tactic-input-validation-fail-fast.import.yaml` — the shipped YAML has a `references` entry pointing to the SDD Patterns URL; the import file records the full local path context.

**Note on local paths**: Import files in `_reference/` may reference the local quickstart path for traceability (these are not shipped, they are internal provenance records). The `--local-path` field must NOT appear in any file under `shipped/`.

---

## 6. `behavior-driven-development` Tactic — Current Location After Normalization

**Decision**: `behavior-driven-development.tactic.yaml` stays in `shipped/` root after WP01, enriched in WP03.

**Rationale**: The existing tactic covers both the technique (testing concern) and the design process (architecture concern). Classifying it under `testing/` alone would be too narrow. It remains in the root as a cross-cutting artifact, consistent with other cross-cutting tactics (`avoid-gold-plating`, `easy-to-change`, `change-apply-smallest-viable-diff`).

---

## 7. `bdd-scenario-lifecycle` Procedure — Schema Requirements

**Decision**: Use the existing `procedure.schema.yaml` which requires: `schema_version`, `id`, `name`, `purpose`, `entry_condition`, `exit_condition`, `steps[]` (each with `title`, `description`, `actor`). `anti_patterns` and `references` are optional but should be included.

**Finding**: `tests/doctrine/` contains procedure schema validation tests that will automatically cover the new file. No new test infrastructure needed for this artifact.

---

## 8. Tactic Classification — Ambiguous Items

Items that don't fit the 4 categories and remain in `shipped/` root:

| Tactic | Reason for staying in root |
|--------|---------------------------|
| `avoid-gold-plating` | General principle, applies equally to all categories |
| `autonomous-operation-protocol` | Agent behavior, not a development practice category |
| `behavior-driven-development` | Cross-cutting (see item 6 above) |
| `change-apply-smallest-viable-diff` | General change discipline |
| `code-review-incremental` | Hybrid: process + quality |
| `easy-to-change` | General design principle |
| `eisenhower-prioritisation` | Planning/prioritization — no matching category |
| `input-validation-fail-fast` | Guard-clause discipline — equally architecture and testing |
| `locality-of-change` | General implementation discipline |
| `occurrence-classification-workflow` | Spec-kitty-specific workflow |
| `review-intent-and-risk-first` | Review process — could be communication but is review-specific |
| `secure-design-checklist` | Cross-cutting security concern |
| `stopping-conditions` | Agent operation protocol |
| `work-package-completion-validation` | Spec-kitty workflow |

These 14 tactics remain in root. A future curation pass could introduce a `process/` or `general/` category.
