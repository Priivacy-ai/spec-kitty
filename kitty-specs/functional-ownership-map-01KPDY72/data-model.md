# Phase 1 — Data Model

**Mission**: Functional Ownership Map (`functional-ownership-map-01KPDY72`)
**Scope**: Define the structural shape of the Markdown map and the YAML manifest. These shapes are validated by the schema test in `tests/architecture/test_ownership_manifest_schema.py`.

---

## 1. Slice Entry (common to map + manifest)

A **slice entry** is the unit of ownership information for one functional slice. Each slice has exactly one entry in the Markdown map and exactly one entry in the YAML manifest, keyed identically.

### 1.1 Required fields

| Field                          | Type               | Cardinality | Spec refs                         | Notes                                                                                                                     |
|--------------------------------|--------------------|-------------|-----------------------------------|---------------------------------------------------------------------------------------------------------------------------|
| `canonical_package`            | string             | 1..1        | FR-003                            | Filesystem-form path (e.g. `src/runtime/`) or dotted name (e.g. `charter`). Must be non-empty.                             |
| `current_state`                | list[string]       | 1..n        | FR-003                            | Files or directories where the slice lives today. Non-empty. No trailing slash convention enforced — authored consistently. |
| `adapter_responsibilities`     | list[string]       | 0..n        | FR-003                            | CLI-only work that legitimately remains in `src/specify_cli/` post-extraction. Empty list is valid.                        |
| `shims`                        | list[mapping]      | 0..n        | FR-003                            | See §1.2. Empty list is valid.                                                                                             |
| `seams`                        | list[string]       | 0..n        | FR-003                            | Free-form "slice X reads slice Y through Z" sentences. Empty list is valid.                                                |
| `extraction_sequencing_notes`  | string             | 1..1        | FR-003                            | Short paragraph describing when this slice extracts relative to others; references downstream missions by number.          |

### 1.2 `shims` sub-entry shape

| Field              | Type   | Cardinality | Notes                                                                                                                            |
|--------------------|--------|-------------|----------------------------------------------------------------------------------------------------------------------------------|
| `path`             | string | 1..1        | Filesystem path to the shim module or package, relative to repo root (e.g. `src/specify_cli/runtime/home.py`).                    |
| `canonical_import` | string | 1..1        | Dotted import of the canonical replacement (e.g. `kernel.paths`).                                                                 |
| `removal_release`  | string | 1..1        | Target removal release (e.g. `3.4.0`). Empty string is not permitted; if a removal date is undecided the entry should not exist. |
| `notes`            | string | 0..1        | Optional free-form note (e.g. "re-export shim; silent; no DeprecationWarning").                                                   |

### 1.3 Runtime-only: `dependency_rules`

Required on — and **only** on — the `runtime_mission_execution` slice entry (FR-004).

| Field             | Type          | Cardinality | Notes                                                                                                                           |
|-------------------|---------------|-------------|---------------------------------------------------------------------------------------------------------------------------------|
| `may_call`        | list[string]  | 0..n        | Slice canonical keys that runtime is permitted to call into (e.g. `charter_governance`, `doctrine`, `lifecycle_status`).         |
| `may_be_called_by`| list[string]  | 0..n        | Slice canonical keys permitted to call into runtime (e.g. `cli_shell`).                                                          |

Any slice key cited in `may_call` or `may_be_called_by` must exist as a top-level key in the manifest.

---

## 2. Manifest Top-Level Shape

```yaml
# architecture/2.x/05_ownership_manifest.yaml
cli_shell:
  canonical_package: …
  current_state: […]
  adapter_responsibilities: […]
  shims: […]
  seams: […]
  extraction_sequencing_notes: "…"
charter_governance:
  …
doctrine:
  …
runtime_mission_execution:
  canonical_package: src/runtime/
  current_state: […]
  adapter_responsibilities: […]
  shims: […]
  seams: […]
  extraction_sequencing_notes: "…"
  dependency_rules:
    may_call: […]
    may_be_called_by: […]
glossary:
  …
lifecycle_status:
  …
orchestrator_sync_tracker_saas:
  …
migration_versioning:
  …
```

### 2.1 Canonical slice keys (8, fixed set)

| Key                                | Spec ref     | Canonical package target                                    | Notes                                                                                                   |
|------------------------------------|--------------|-------------------------------------------------------------|---------------------------------------------------------------------------------------------------------|
| `cli_shell`                        | FR-002       | `src/specify_cli/cli/` (stays)                              | CLI shell is the permanent home for CLI-only code; not extracted.                                        |
| `charter_governance`               | FR-002, FR-006 | `charter` (= `src/charter/`)                                 | Already extracted. `shims: []` after this mission lands (FR-012).                                        |
| `doctrine`                         | FR-002       | `doctrine` (= `src/doctrine/`)                               | Already extracted.                                                                                       |
| `runtime_mission_execution`        | FR-002, FR-004 | `src/runtime/`                                               | Target for mission #612. Carries `dependency_rules` (FR-004).                                           |
| `glossary`                         | FR-002       | `src/glossary/`                                              | Target for mission #613. Canonical path pinned by parent-scope context.                                  |
| `lifecycle_status`                 | FR-002       | `src/lifecycle/`                                             | Target for mission #614. Canonical path pinned in `plan.md` Structure Decisions.                         |
| `orchestrator_sync_tracker_saas`   | FR-002       | `src/orchestrator/` (forward-looking)                        | Fragmented today across 7 subdirectories; not extracted by this mission. Target recorded for later work. |
| `migration_versioning`             | FR-002       | `src/specify_cli/migration/` + `upgrade/` (stays for now)    | No near-term extraction. Entry documents current state honestly.                                         |

---

## 3. Markdown Map Structural Shape

`architecture/2.x/05_ownership_map.md` consists of these sections in order:

| # | Section                                | Purpose                                                                                                                                                        | FR refs |
|---|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| 1 | Front matter + legend                  | Title, status, date, links to spec, manifest, and exemplar mission. Terminology legend stating "Mission / Work Package" canon (C-005).                          | FR-001 |
| 2 | How to use this map                    | Two-audience quickstart: extraction-PR author and reviewer. Mirrors `quickstart.md`.                                                                            | FR-001 |
| 3 | Eight slice entries (in canonical order) | One H2 heading per slice key. Each slice section renders every required field from §1.1 plus the runtime-only §1.3 fields as sub-sections.                    | FR-002, FR-003 |
| 4 | Charter slice — reference exemplar     | A callout box under the charter slice entry (§3.2) naming mission `01KPD880` as the exemplar pattern that other slices follow.                                   | FR-006 |
| 5 | Safeguards and direction               | Map references #393 (architectural tests), #394 (deprecation scaffolding), #395 (import-graph tooling), #461 (direction). States which safeguards must land before which slice extracts (from R-003). | FR-008, FR-009 |
| 6 | Downstream missions                    | Table listing #612, #613, #614, #615 with one-sentence summaries of what each consumes from the map.                                                             | FR-001 |
| 7 | Change control                         | Short paragraph: map is a living document; edits land in-place; each extraction PR confirms its slice entry is honoured.                                         | Spec §Edge cases |

---

## 4. Test Contract

`tests/architecture/test_ownership_manifest_schema.py` asserts:

1. `architecture/2.x/05_ownership_manifest.yaml` exists.
2. It parses as YAML.
3. Its top-level is a mapping whose keys exactly match the set `{cli_shell, charter_governance, doctrine, runtime_mission_execution, glossary, lifecycle_status, orchestrator_sync_tracker_saas, migration_versioning}`.
4. For each slice entry, every required field in §1.1 is present with the right type.
5. For the `runtime_mission_execution` slice entry, `dependency_rules` is present with `may_call` and `may_be_called_by` as lists.
6. For every other slice entry, `dependency_rules` is **absent**.
7. `charter_governance.shims` is an empty list (captures acceptance scenario 4).
8. Every `may_call` / `may_be_called_by` entry is a recognised slice key.
9. Test completes in ≤1s (NFR-002, asserted by a pytest fixture or pytest-timeout plug-in if available — soft check otherwise).

---

## 5. Traceability

| FR / NFR / C | Data-model anchor                                                                                                           |
|--------------|-----------------------------------------------------------------------------------------------------------------------------|
| FR-001       | §3 (map document)                                                                                                           |
| FR-002       | §2.1 (eight canonical slice keys)                                                                                           |
| FR-003       | §1.1 (required slice-entry fields)                                                                                          |
| FR-004       | §1.3 (runtime-only `dependency_rules`); §4 checks 5 and 6                                                                   |
| FR-005       | §3 row 3 (doctrine slice entry carries the `model_task_routing` disposition); parent kind pinned in `research.md` R-006    |
| FR-006       | §3 row 4 (charter exemplar callout)                                                                                         |
| FR-007       | See `contracts/cross_reference.md`                                                                                          |
| FR-008       | §3 row 5 (safeguards)                                                                                                       |
| FR-009       | §3 row 5 (direction)                                                                                                        |
| FR-010       | §2 (manifest shape)                                                                                                         |
| FR-011       | §4 (test contract)                                                                                                          |
| FR-012       | Shim deletion is code-level, not data-model. Verified by §4 check 7 (charter `shims: []`).                                  |
| FR-013       | See `contracts/changelog_entry.md`                                                                                          |
| FR-014       | Commit-message `Closes #611` — verified at merge time, not by schema test.                                                  |
| FR-015       | No data-model item permits adding movement of any other slice; out-of-scope enforcement is by review.                       |
| NFR-001      | §3 structural readability (human review during `/spec-kitty.review`).                                                        |
| NFR-002      | §4 check 9 (≤1s).                                                                                                           |
| NFR-003      | Not a data-model item. Verified by running existing test suite.                                                              |
| NFR-004      | Not a data-model item. Verified by a runtime check in the deletion WP (optional one-liner test).                             |
| C-001        | No mention of `pyproject.toml` version anywhere in map or manifest.                                                          |
| C-002        | Slice entries describe current state and a future canonical target; they do not *perform* extraction.                        |
| C-003        | `shims[]` sub-entries reference #615 rulebook in the `notes` field where appropriate; the manifest does not define the rulebook. |
| C-004        | The doctrine slice entry records `model_task_routing` disposition only; it does not port the doctrine.                      |
| C-005        | Map legend calls out Mission / Work Package canon explicitly.                                                                |
| C-006        | `change_mode: standard`; no `occurrence_map.yaml` in the mission directory.                                                  |
