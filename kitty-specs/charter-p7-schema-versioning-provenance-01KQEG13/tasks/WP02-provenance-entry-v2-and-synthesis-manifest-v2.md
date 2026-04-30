---
work_package_id: WP02
title: ProvenanceEntry v2 and SynthesisManifest v2
dependencies: []
requirement_refs:
- FR-005
- FR-006
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
- T013
- T014
phase: Phase 1 - Foundation
agent: claude:opus-4-7:reviewer-renata:reviewer
history:
- at: '2026-04-30T06:23:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/charter/synthesizer/
execution_mode: code_change
owned_files:
- src/charter/synthesizer/synthesize_pipeline.py
- src/charter/synthesizer/manifest.py
- src/charter/synthesizer/provenance.py
- src/charter/synthesizer/write_pipeline.py
- src/charter/synthesizer/resynthesize_pipeline.py
- tests/charter/synthesizer/test_provenance.py
- tests/charter/synthesizer/test_manifest.py
- tests/charter/synthesizer/test_adapter_contract.py
- tests/charter/fixtures/synthesizer/**
tags: []
task_type: implement
---

# Work Package Prompt: WP02 — ProvenanceEntry v2 and SynthesisManifest v2

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load the agent profile assigned to this work package:

```
/ad-hoc-profile-load reviewer-renata
```

This loads domain knowledge, tool preferences, and behavioral guidelines. Do not proceed until the profile confirms it has loaded.

## Objective

Bump `ProvenanceEntry` and `SynthesisManifest` from schema version "1" to "2". Add all mandatory Phase 7 fields to both models. Update the synthesis pipeline to populate these fields at write time. Update every fixture and test that touches these models.

This WP runs in **Lane B** in parallel with WP01 (Lane A: versioning registry). WP03 depends on both.

## Branch Strategy

- **Planning base branch**: `main`
- **Merge target**: `main`
- **Execution workspace**: allocated by `lanes.json` (Lane B); do not guess the worktree path

## Context

**Current state** (v1):
- `ProvenanceEntry` in `synthesize_pipeline.py`: `schema_version: Literal["1"]`, `corpus_snapshot_id: str | None = None` (optional), no `synthesizer_version`, no `source_input_ids`, no `produced_at`, no `synthesis_run_id`
- `SynthesisManifest` in `manifest.py`: `schema_version: Literal["1"]`, no `synthesizer_version`, no `manifest_hash`

**Target state** (v2):
- `ProvenanceEntry`: `schema_version: Literal["2"]`, `corpus_snapshot_id: str` (mandatory, `"(none)"` sentinel), plus `synthesizer_version: str`, `source_input_ids: list[str]`, `produced_at: str`, `synthesis_run_id: str`
- `SynthesisManifest`: `schema_version: Literal["2"]`, `synthesizer_version: str` (minLength=1), `manifest_hash: str` (64-char SHA-256 hex)

**Critical constraints**:
1. `ProvenanceEntry` uses `ConfigDict(frozen=True)` — `produced_at` cannot be set by a factory default. The caller (`write_pipeline.promote()`) must pass `produced_at=datetime.now(UTC).isoformat()` at the moment of writing.
2. `manifest_hash` = `sha256(canonical_yaml({all manifest fields except manifest_hash})).hexdigest()`. Because `SynthesisManifest` is frozen, compute via `model_dump(mode="python")`, pop `"manifest_hash"`, hash, then construct the final manifest with `manifest_hash` set.
3. `canonical_yaml()` already exists in `synthesize_pipeline.py` — use it everywhere for consistency (NFR-004 byte-stability).
4. `corpus_snapshot_id` must be `corpus_id or "(none)"` — never `None` — at every construction site.
5. Do NOT change `evidence_bundle_hash` — it stays `str | None = None` (optional).

**Working directory**: `src/` (run `cd src && mypy --strict charter/synthesizer/synthesize_pipeline.py charter/synthesizer/manifest.py`).

## Subtask Guidance

### T008 — Bump ProvenanceEntry to v2

**File**: `src/charter/synthesizer/synthesize_pipeline.py`

Read the full file first. Locate `ProvenanceEntry`. Apply these changes:

1. Change `schema_version: Literal["1"] = "1"` → `schema_version: Literal["2"] = "2"`
2. Promote `corpus_snapshot_id: str | None = None` → `corpus_snapshot_id: str` (required, no default)
3. Add required fields (no defaults — validation must fail if absent):
   ```python
   synthesizer_version: str = Field(..., min_length=1)
   source_input_ids: list[str]
   produced_at: str
   synthesis_run_id: str = Field(..., min_length=1)
   ```
4. Keep all existing fields in their original positions; add new fields after `generated_at`.
5. Keep `evidence_bundle_hash: str | None = None` and `adapter_notes: str | None = None` as-is.

**Field order in final model** (reference only):
```
schema_version, artifact_urn, artifact_kind, artifact_slug,
artifact_content_hash, inputs_hash, adapter_id, adapter_version,
synthesizer_version, source_section, source_urns, source_input_ids,
generated_at, produced_at, corpus_snapshot_id, synthesis_run_id,
evidence_bundle_hash, adapter_notes
```

Validation check (Pydantic v2):
- `synthesizer_version: str = Field(..., min_length=1)` — empty string raises `ValidationError`
- `synthesis_run_id: str = Field(..., min_length=1)` — same
- `corpus_snapshot_id: str` with no default — `None` raises `ValidationError`

Run `mypy --strict src/charter/synthesizer/synthesize_pipeline.py` after.

### T009 — Bump SynthesisManifest to v2

**File**: `src/charter/synthesizer/manifest.py`

Read the full file first. Locate `SynthesisManifest`. Apply:

1. Change `schema_version: Literal["1"] = "1"` → `schema_version: Literal["2"] = "2"`
2. Add required fields:
   ```python
   synthesizer_version: str = Field(..., min_length=1)
   manifest_hash: str = Field(..., min_length=64, max_length=64)
   ```
3. Keep all existing fields; add new fields after `adapter_version`.

Validate: `SynthesisManifest(synthesizer_version="", ...)` must raise `ValidationError`.

Run `mypy --strict src/charter/synthesizer/manifest.py` after.

### T010 — Update `provenance.py` to stamp `produced_at` at write time

**File**: `src/charter/synthesizer/provenance.py`

Read the full file. Find `dump_yaml()` (or whatever function writes the provenance sidecar to disk).

`produced_at` is set by the **caller** before passing the `ProvenanceEntry` to this function — the model is frozen and can't be mutated. However, if the current design is that `dump_yaml()` receives a `ProvenanceEntry` instance and writes it directly, the construction happens upstream in `write_pipeline.py`.

Check whether `provenance.py` receives a fully-constructed `ProvenanceEntry` or constructs it internally. If it constructs it: move `produced_at=datetime.now(UTC).isoformat()` to the construction call (the instant before `dump_yaml` is called). If `dump_yaml()` just serializes a pre-constructed entry: verify that `produced_at` is already set by the caller (write_pipeline.py, T011).

Ensure the YAML output for a provenance sidecar includes `produced_at` as a top-level key.

### T011 — Update `write_pipeline.py` `promote()`

**File**: `src/charter/synthesizer/write_pipeline.py`

Read the full file. Find all locations where `ProvenanceEntry(...)` is constructed (the `promote()` function, or equivalent). Update each construction site:

```python
import specify_cli  # for __version__
from datetime import datetime, timezone

# In promote() or equivalent:
entry = ProvenanceEntry(
    schema_version="2",
    artifact_urn=...,
    artifact_kind=...,
    artifact_slug=...,
    artifact_content_hash=...,
    inputs_hash=...,
    adapter_id=...,
    adapter_version=...,
    synthesizer_version=specify_cli.__version__,        # NEW
    source_section=...,
    source_urns=...,
    source_input_ids=list(source.source_urns),          # NEW (mirror of source_urns for Phase 7)
    generated_at=...,
    produced_at=datetime.now(timezone.utc).isoformat(), # NEW — stamped at write time
    corpus_snapshot_id=corpus_id or "(none)",            # PROMOTED (str not Optional)
    synthesis_run_id=staging_dir.run_id,                 # NEW
    evidence_bundle_hash=...,
    adapter_notes=...,
)
```

Also update `SynthesisManifest(...)` construction to pass `synthesizer_version` and compute `manifest_hash`:

```python
import hashlib
from charter.synthesizer.synthesize_pipeline import canonical_yaml  # adjust import path

# Build manifest without hash first:
manifest_data = dict(
    schema_version="2",
    mission_id=...,
    created_at=...,
    run_id=...,
    adapter_id=...,
    adapter_version=...,
    synthesizer_version=specify_cli.__version__,
    artifacts=[...],
    manifest_hash="",  # placeholder
)
manifest_data.pop("manifest_hash")
hash_input = canonical_yaml(manifest_data).encode()
manifest_hash = hashlib.sha256(hash_input).hexdigest()  # 64 hex chars

manifest = SynthesisManifest(
    **manifest_data,
    manifest_hash=manifest_hash,
)
```

Run `mypy --strict src/charter/synthesizer/write_pipeline.py` after.

### T012 — Update `resynthesize_pipeline.py`

**File**: `src/charter/synthesizer/resynthesize_pipeline.py`

Apply the same `ProvenanceEntry` v2 construction changes as T011. The `resynthesize_pipeline` reads an existing bundle and re-synthesizes selected artifacts; it constructs new provenance entries for re-synthesized artifacts.

Check:
- Does `resynthesize_pipeline.py` have access to `staging_dir.run_id`? It must — `synthesis_run_id` is mandatory. If not, trace how the staging directory is threaded through.
- Use `list(source.source_urns)` for `source_input_ids` (same as write_pipeline).
- Use `corpus_id or "(none)"` for `corpus_snapshot_id`.

Run `mypy --strict src/charter/synthesizer/resynthesize_pipeline.py` after.

### T013 — Update YAML sidecar fixtures

**Directory**: `tests/charter/fixtures/synthesizer/`

List all `.yaml` files in this directory. For each provenance sidecar YAML (files with `schema_version: "1"` and provenance fields):

1. Change `schema_version: "1"` → `schema_version: "2"`
2. Add the new mandatory fields with realistic test values:
   ```yaml
   synthesizer_version: "3.2.0a5"
   source_input_ids:
     - "urn:sk:charter:section:directives"
   produced_at: "2026-01-01T00:00:00+00:00"
   corpus_snapshot_id: "(none)"
   synthesis_run_id: "01HTEST00000000000000TEST01"
   ```
3. If `corpus_snapshot_id` is currently `null` or absent, set it to `"(none)"`.

Also update `synthesis-manifest.yaml` fixtures (if present) to v2:
```yaml
schema_version: "2"
synthesizer_version: "3.2.0a5"
manifest_hash: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"  # 64-char placeholder
```

**Important**: The `manifest_hash` in fixtures does NOT need to be cryptographically valid (it's a test fixture). Use a 64-char hex string placeholder. Tests that verify hash correctness should compute the hash dynamically, not compare to a fixture value.

Also check `tests/charter/synthesizer/conftest.py` for any `ProvenanceEntry` factory functions and update them to include v2 fields.

### T014 — Update test files for v2

**Files**:
- `tests/charter/synthesizer/test_provenance.py`
- `tests/charter/synthesizer/test_manifest.py`
- `tests/charter/synthesizer/test_adapter_contract.py`

Read each file fully. Update assertions that reference `schema_version: "1"` → `"2"`. Add assertions for the new v2 fields.

**test_provenance.py additions**:
```python
def test_provenance_entry_v2_corpus_snapshot_id_required():
    # corpus_snapshot_id=None must raise ValidationError
    with pytest.raises(ValidationError):
        ProvenanceEntry(**{**VALID_V2_FIELDS, "corpus_snapshot_id": None})

def test_provenance_entry_v2_synthesizer_version_empty_raises():
    with pytest.raises(ValidationError):
        ProvenanceEntry(**{**VALID_V2_FIELDS, "synthesizer_version": ""})

def test_provenance_entry_v1_schema_version_raises():
    with pytest.raises(ValidationError):
        ProvenanceEntry(**{**VALID_V2_FIELDS, "schema_version": "1"})
```

**test_manifest.py additions**:
```python
def test_manifest_hash_validates():
    # build manifest without hash, compute hash, verify stored matches
    manifest = build_test_manifest_v2()
    fields_without_hash = manifest.model_dump(mode="python")
    fields_without_hash.pop("manifest_hash")
    computed = hashlib.sha256(canonical_yaml(fields_without_hash).encode()).hexdigest()
    assert computed == manifest.manifest_hash
```

After all changes, run:
```bash
cd src && pytest ../tests/charter/synthesizer/test_provenance.py ../tests/charter/synthesizer/test_manifest.py ../tests/charter/synthesizer/test_adapter_contract.py -v
```

Also verify the byte-stability regression test still passes:
```bash
cd src && pytest ../tests/charter/synthesizer/test_synthesize_path_parity.py -v
```

## Definition of Done

- [ ] `ProvenanceEntry.schema_version` is `Literal["2"]`; all 5 new/promoted fields are mandatory
- [ ] `SynthesisManifest.schema_version` is `Literal["2"]`; `synthesizer_version` and `manifest_hash` present
- [ ] `write_pipeline.py` passes all 5 new fields; computes `manifest_hash` correctly
- [ ] `resynthesize_pipeline.py` passes all 5 new fields
- [ ] All YAML fixture sidecars updated to v2; conftest.py updated
- [ ] `test_provenance.py`, `test_manifest.py`, `test_adapter_contract.py` pass with v2 assertions
- [ ] `test_synthesize_path_parity.py` passes (no byte-stability regression)
- [ ] `mypy --strict` passes on all 5 modified source files
- [ ] No changes to any file outside `owned_files`

## Risks

- **`produced_at` on frozen model**: The model cannot be mutated after construction. The construction call in `write_pipeline.promote()` must stamp `produced_at=datetime.now(timezone.utc).isoformat()` before calling `dump_yaml()`. Do not try to set it in `dump_yaml()`.
- **`manifest_hash` circular construction**: Build the dict without `manifest_hash`, hash it, then construct the `SynthesisManifest` with `manifest_hash` included. Do not use `model_copy()` or validators for this.
- **`corpus_snapshot_id` promotion breaks existing calls**: Search for every `ProvenanceEntry(` call with `corpus_snapshot_id=None` or missing `corpus_snapshot_id`. All must be updated to `corpus_snapshot_id=corpus_id or "(none)"`.
- **Fixture hash values**: Set the manifest_hash in fixtures to any 64-char hex string; do not try to compute a valid hash for fixture files.
- **`test_synthesize_path_parity.py`**: This test verifies byte-for-byte determinism of serialized sidecars. Adding new fields may break it if the field order or serialization changes. Run it early to detect breakage.
