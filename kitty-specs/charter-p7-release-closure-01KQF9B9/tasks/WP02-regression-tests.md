---
work_package_id: WP02
title: Add Public-CLI Regression Tests
dependencies:
- WP01
requirement_refs:
- FR-008
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-charter-p7-release-closure-01KQF9B9
base_commit: 67dc0ec540b9b7f1af664d5570770a1b4f9ed630
created_at: '2026-04-30T14:37:43.818341+00:00'
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
agent: "claude"
shell_pid: "63309"
history:
- event: created
  at: '2026-04-30T13:57:24Z'
agent_profile: python-pedro
authoritative_surface: tests/charter/
execution_mode: code_change
owned_files:
- tests/charter/test_bundle_validate_cli.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile:

```
/ad-hoc-profile-load python-pedro
```

Then return here and continue.

---

## Objective

Add regression tests to `tests/charter/test_bundle_validate_cli.py` that exercise every new failure mode through the public CLI surface — not by calling internal helpers directly.

The tests prove that after WP01:
1. Synthesis-state failures are surfaced by the public `charter bundle validate` command (not just by the internal `validate_synthesis_state()` helper).
2. `charter bundle validate --json` stdout is valid JSON on every path — success, failure, and legacy bundles.
3. The new `synthesis_state` key is present and correct in the JSON output.

**Prerequisite**: WP01 must be merged or available in the lane worktree before these tests can pass.

---

## Context

**Files to read before starting**:
- `tests/charter/test_bundle_validate_cli.py` — full read; understand existing fixtures and test structure
- `src/charter/bundle.py` lines 137–200 — understand what `validate_synthesis_state()` checks so fixtures trigger the right conditions
- `kitty-specs/charter-p7-release-closure-01KQF9B9/contracts/validate-json-output.md` — the expected JSON shape

**Existing test structure**:
- `runner = CliRunner()` at module level
- `compliant_repo` fixture: git-inited repo with compliant charter bundle (`charter.md` tracked, derived files present, `.gitignore` correct, `metadata.yaml` contains `bundle_schema_version: 2`)
- `_git_init(tmp_path)`, `_write_compliant_bundle(tmp_path)` helpers — reuse these for synthesis state tests
- `_invoke_validate_json()` helper → `runner.invoke(charter_bundle.app, ["validate", "--json"])`

**What conditions trigger synthesis-state failures** (from `src/charter/bundle.py`):
- **Missing sidecar** (FR-001): file under `.kittify/doctrine/` but no matching sidecar under `.kittify/charter/provenance/`
- **Missing artifact reference** (FR-002): file under `.kittify/charter/provenance/` references a file that doesn't exist under `.kittify/doctrine/`
- **Manifest hash mismatch** (FR-003): `.kittify/charter/synthesis-manifest.yaml` exists and lists an artifact with a `content_hash` that doesn't match the file on disk

**What does NOT trigger failures** (backward compat, C-012):
- No `.kittify/doctrine/` directory at all → `synthesis_state_present=False`, passes
- `.kittify/doctrine/` exists but empty → `synthesis_state_present=False`, passes

---

## Subtask T007 — Add Fixture Helpers

**Purpose**: Write three helper functions for constructing synthesis state in test repos. Place them above the existing `@pytest.fixture` definitions in `test_bundle_validate_cli.py`.

```python
import hashlib


def _add_doctrine_artifact(repo_root: Path, rel_path: str, content: str = "# artifact\n") -> Path:
    """Write a doctrine artifact under .kittify/doctrine/."""
    full = repo_root / ".kittify" / "doctrine" / rel_path
    full.parent.mkdir(parents=True, exist_ok=True)
    full.write_text(content, encoding="utf-8")
    return full


def _add_provenance_sidecar(
    repo_root: Path,
    kind: str,
    slug: str,
    content_hash: str | None = None,
) -> Path:
    """Write a valid ProvenanceEntry v2 sidecar under .kittify/charter/provenance/.

    Filename is always '{kind}-{slug}.yaml' — this is the convention that
    _check_artifacts_have_provenance and _check_provenance_have_artifacts both rely on.
    kind+slug are derived from the sidecar filename (stem.split('-', 1)), not from YAML content.
    """
    prov_dir = repo_root / ".kittify" / "charter" / "provenance"
    prov_dir.mkdir(parents=True, exist_ok=True)
    sidecar = prov_dir / f"{kind}-{slug}.yaml"
    if content_hash is None:
        content_hash = "a" * 64
    sidecar.write_text(
        f"schema_version: '2'\n"
        f"artifact_urn: '{kind}:{slug}'\n"
        f"artifact_kind: {kind}\n"
        f"artifact_slug: {slug}\n"
        f"artifact_content_hash: {content_hash}\n"
        f"inputs_hash: {'b' * 64}\n"
        f"adapter_id: fixture\n"
        f"adapter_version: 1.0.0\n"
        f"synthesizer_version: '3.2.0a5'\n"
        f"source_urns:\n- directive:DIRECTIVE_003\n"
        f"source_input_ids:\n- directive:DIRECTIVE_003\n"
        f"generated_at: '2026-04-30T00:00:00+00:00'\n"
        f"produced_at: '2026-01-01T00:00:00+00:00'\n"
        f"corpus_snapshot_id: '(none)'\n"
        f"synthesis_run_id: '01HTEST00000000000000TEST01'\n",
        encoding="utf-8",
    )
    return sidecar


def _add_synthesis_manifest(
    repo_root: Path,
    artifact_rel: str,
    content: str,
    corrupt_hash: bool = False,
) -> Path:
    """Write .kittify/charter/synthesis-manifest.yaml referencing one artifact.

    Uses charter.synthesizer.manifest (SynthesisManifest + dump_manifest) so the
    format matches what load_yaml/verify_manifest expect. See _make_v2_manifest() in
    tests/charter/synthesizer/test_bundle_validate_extension.py for the exact pattern.

    When corrupt_hash=True, tampers with the stored content_hash after dumping so that
    verify_manifest raises on the per-artifact content_hash mismatch (FR-003).

    NOTE: validate_synthesis_state() → _check_manifest_integrity() → verify_manifest()
    only checks per-artifact content_hash values. The manifest self-hash field
    (manifest_hash) is NOT verified by the current implementation. T010 therefore tests
    per-artifact content_hash mismatch only; manifest self-hash verification is out of
    scope for this mission.
    """
    from charter.synthesizer.manifest import SynthesisManifest, dump_manifest  # noqa: PLC0415

    artifact_full_rel = f".kittify/doctrine/{artifact_rel}"
    real_hash = hashlib.sha256(content.encode()).hexdigest()
    # Build the manifest with the correct hash, then optionally corrupt it.
    sm = SynthesisManifest(
        artifacts={artifact_full_rel: {"content_hash": real_hash}},
    )
    manifest_path = repo_root / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    dump_manifest(sm, manifest_path)

    if corrupt_hash:
        # Re-write just the content_hash to a known-bad value so verify_manifest fails.
        raw = manifest_path.read_text(encoding="utf-8")
        raw = raw.replace(real_hash, "deadbeef" * 8)
        manifest_path.write_text(raw, encoding="utf-8")

    return manifest_path
```

**Note on `_add_synthesis_manifest`**: The import inside the function body avoids adding a module-level import that could fail in environments where `charter.synthesizer` is not on the path. If `SynthesisManifest` or `dump_manifest` have different names in the actual module, check `src/charter/synthesizer/manifest.py` and mirror the call pattern from `_make_v2_manifest()` in `tests/charter/synthesizer/test_bundle_validate_extension.py`.

**Validation**:
- [ ] The three helpers are defined above the fixture definitions
- [ ] `hashlib` is imported at the top of the test file
- [ ] `_add_provenance_sidecar` creates a file named `{kind}-{slug}.yaml` (not the artifact filename)
- [ ] `_add_synthesis_manifest` uses `SynthesisManifest + dump_manifest` (not raw string YAML)

---

## Subtask T008 — Test: Missing Sidecar → Exits 1

**Purpose**: Doctrine artifact exists, no matching provenance sidecar → validation fails.

```python
def test_validate_fails_when_doctrine_artifact_has_no_sidecar(
    compliant_repo: Path,
) -> None:
    """FR-001: synthesized artifact without a provenance sidecar must fail validation."""
    _add_doctrine_artifact(compliant_repo, "directives/001-foo.directive.yaml")
    # No sidecar written. Expected sidecar name would be 'directive-foo.yaml'.

    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    ss = payload["synthesis_state"]
    assert ss["present"] is True
    assert ss["passed"] is False
    # Error message references the artifact or expected sidecar path.
    assert any("foo" in e for e in ss["errors"]), ss["errors"]
    # Mirrored into top-level errors with synthesis_state: prefix.
    assert any("synthesis_state:" in e for e in payload["errors"]), payload["errors"]
```

**Validation**:
- [ ] Test passes with WP01 implemented
- [ ] `json.loads(result.stdout)` does not raise
- [ ] `result.exit_code == 1`

---

## Subtask T009 — Test: Sidecar Referencing Absent Artifact → Exits 1

**Purpose**: Provenance sidecar exists but the artifact it references is gone → validation fails (FR-002).

```python
def test_validate_fails_when_sidecar_references_missing_artifact(
    compliant_repo: Path,
) -> None:
    """FR-002: provenance sidecar must reference an existing artifact file."""
    # Create .kittify/doctrine/ so validate_synthesis_state() doesn't early-return.
    # (It returns synthesis_state_present=False if doctrine/ is absent.)
    (compliant_repo / ".kittify" / "doctrine").mkdir(parents=True, exist_ok=True)
    # Write sidecar directive-bar.yaml but NOT the corresponding doctrine artifact.
    # _check_provenance_have_artifacts derives kind=directive, slug=bar from the filename
    # and looks for any *directive.yaml with slug "bar" in doctrine/ — finds nothing.
    _add_provenance_sidecar(compliant_repo, kind="directive", slug="bar")

    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert payload["synthesis_state"]["passed"] is False
```

**Validation**:
- [ ] Test passes with WP01 implemented
- [ ] `json.loads(result.stdout)` does not raise
- [ ] Exit code is 1

---

## Subtask T010 — Test: Manifest with Bad Per-Artifact Content Hash → Exits 1

**Purpose**: Synthesis manifest exists with a per-artifact `content_hash` that does not match on-disk bytes → validation fails (FR-003).

**Scope note**: `validate_synthesis_state()` → `_check_manifest_integrity()` → `verify_manifest()` checks **per-artifact `content_hash` values only**. The manifest self-hash field (`manifest_hash`) is not verified by the current implementation. This test covers the per-artifact content_hash mismatch path; manifest self-hash verification is explicitly out of scope for this mission.

```python
def test_validate_fails_on_manifest_content_hash_mismatch(
    compliant_repo: Path,
) -> None:
    """FR-003: mismatched synthesis manifest per-artifact content_hash must fail."""
    artifact_content = "# directive content\n"
    _add_doctrine_artifact(
        compliant_repo,
        "directives/002-baz.directive.yaml",
        content=artifact_content,
    )
    # Sidecar: directive-baz.yaml (kind=directive, slug=baz from _kind_and_slug_from_artifact).
    _add_provenance_sidecar(compliant_repo, kind="directive", slug="baz")
    _add_synthesis_manifest(
        compliant_repo,
        "directives/002-baz.directive.yaml",
        content=artifact_content,
        corrupt_hash=True,  # Forces per-artifact content_hash mismatch.
    )

    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 1, result.output
    payload = json.loads(result.stdout)
    assert payload["passed"] is False
    assert payload["synthesis_state"]["passed"] is False
```

**Validation**:
- [ ] Test passes with WP01 implemented
- [ ] `json.loads(result.stdout)` does not raise
- [ ] Exit code is 1

---

## Subtask T011 — Test: `--json` Strict JSON for Each Failure Type

**Purpose**: Assert that `--json` stdout is valid JSON (parseable) for every failure scenario introduced by this mission.

```python
def test_validate_json_is_strict_on_missing_sidecar(compliant_repo: Path) -> None:
    """FR-005/FR-006: --json stdout must parse even on synthesis failure."""
    _add_doctrine_artifact(compliant_repo, "directives/003-strict.directive.yaml")
    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 1
    # This must not raise — strict JSON contract.
    payload = json.loads(result.stdout)
    assert "synthesis_state" in payload
    assert "errors" in payload
    assert payload["passed"] is False


def test_validate_json_is_strict_on_manifest_mismatch(compliant_repo: Path) -> None:
    """FR-005/FR-006: --json stdout must parse on manifest hash failure."""
    content = "# artifact\n"
    _add_doctrine_artifact(compliant_repo, "directives/004-manifest.directive.yaml", content)
    _add_provenance_sidecar(compliant_repo, kind="directive", slug="manifest")
    _add_synthesis_manifest(compliant_repo, "directives/004-manifest.directive.yaml", content, corrupt_hash=True)
    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)  # must not raise
    assert payload["synthesis_state"]["passed"] is False
```

**Validation**:
- [ ] `json.loads(result.stdout)` does not raise in either test
- [ ] Both tests have `result.exit_code == 1`
- [ ] `"synthesis_state"` and `"errors"` keys present in payload

---

## Subtask T012 — Test: Legacy Bundle (No Synthesis State) → Exits 0

**Purpose**: Project with a valid charter bundle but no synthesis state passes validation, and `synthesis_state.present` is False (FR-004, backward compat C-012).

```python
def test_validate_passes_legacy_bundle_without_synthesis_state(
    compliant_repo: Path,
) -> None:
    """FR-004 / C-012: legacy bundles with no synthesis state must still pass."""
    # compliant_repo has no .kittify/doctrine/, no provenance sidecars, no manifest.
    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    ss = payload["synthesis_state"]
    assert ss["present"] is False
    assert ss["passed"] is True
    assert ss["errors"] == []
```

**Validation**:
- [ ] Test passes
- [ ] `result.exit_code == 0`
- [ ] `synthesis_state.present` is False
- [ ] `synthesis_state.passed` is True

---

## Subtask T013 — Test: Complete v2 Bundle Passes

**Purpose**: Bundle with valid doctrine artifact, matching sidecar, and valid manifest exits 0 (FR-009 regression guard).

```python
def test_validate_passes_complete_v2_bundle(compliant_repo: Path) -> None:
    """FR-009 regression: a complete v2 bundle with synthesis state must still pass."""
    artifact_content = "# complete directive\n"
    _add_doctrine_artifact(
        compliant_repo, "directives/005-complete.directive.yaml", artifact_content
    )
    # Sidecar: directive-complete.yaml (kind=directive, slug=complete).
    _add_provenance_sidecar(compliant_repo, kind="directive", slug="complete")
    _add_synthesis_manifest(
        compliant_repo,
        "directives/005-complete.directive.yaml",
        content=artifact_content,
        corrupt_hash=False,  # Correct hash.
    )

    result = runner.invoke(charter_bundle.app, ["validate", "--json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.stdout)
    assert payload["passed"] is True
    ss = payload["synthesis_state"]
    assert ss["present"] is True
    assert ss["passed"] is True
    assert ss["errors"] == []
    assert payload["errors"] == []
```

**Validation**:
- [ ] Test passes
- [ ] `result.exit_code == 0`
- [ ] `synthesis_state.present` True, `synthesis_state.passed` True, `errors` empty

---

## Subtask T014 — Update `test_validate_json_shape_matches_contract`

**Purpose**: The existing contract test asserts required keys; add `synthesis_state` and `errors` to the required set.

**Find the existing test** (around line 239):
```python
required_keys = {
    "result",
    "canonical_root",
    "manifest_schema_version",
    "bundle_compliant",
    "tracked_files",
    "derived_files",
    "gitignore",
    "out_of_scope_files",
    "warnings",
}
```

**Update to**:
```python
required_keys = {
    "result",
    "canonical_root",
    "manifest_schema_version",
    "bundle_compliant",
    "passed",         # New: overall gate
    "errors",         # New: mirrored error list
    "tracked_files",
    "derived_files",
    "gitignore",
    "out_of_scope_files",
    "warnings",
    "synthesis_state",  # New: synthesis state block
}
assert required_keys <= set(payload.keys())

# Assert synthesis_state shape.
ss = payload["synthesis_state"]
assert {"present", "passed", "errors", "warnings"} <= set(ss.keys())
assert isinstance(ss["present"], bool)
assert isinstance(ss["passed"], bool)
assert isinstance(ss["errors"], list)
assert isinstance(ss["warnings"], list)
```

**Validation**:
- [ ] Test passes
- [ ] No existing assertions removed

---

## Run the Full Suite

After all test additions:

```bash
uv run pytest tests/charter/test_bundle_validate_cli.py -q
uv run pytest tests/charter/synthesizer/test_bundle_validate_extension.py -q
uv run pytest tests/specify_cli/cli/commands/test_charter_status_provenance.py -q
uv run pytest tests/doctrine/test_versioning.py tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py -q
uv run ruff check tests/charter/test_bundle_validate_cli.py
```

All must pass green before committing.

**Definition of Done for WP02**:
- [ ] 8 new tests added (T007 helpers + T008–T014 test functions); all pass
- [ ] `test_validate_json_shape_matches_contract` updated and passes
- [ ] All 8 existing tests in `test_bundle_validate_cli.py` continue to pass
- [ ] Phase 7 guard tests (provenance, versioning, migration) pass
- [ ] `ruff check` passes on the test file
- [ ] `json.loads(result.stdout)` succeeds for every new `--json` test

---

## Branch Strategy

**Planning base branch**: `main`
**Final merge target**: `main`

Enter the implementation workspace via:

```bash
spec-kitty agent action implement WP02 --agent claude
```

WP02 shares the same lane as WP01 if they are sequenced. Do not implement WP02 until WP01 is complete — the test fixtures depend on WP01's changes being in place.

---

## Reviewer Guidance

- Every new test invokes the CLI through `runner.invoke(charter_bundle.app, ...)` — not by calling `validate_synthesis_state()` directly.
- Every `--json` test calls `json.loads(result.stdout)` without a try/except — a parse error IS the failure signal.
- The `_add_synthesis_manifest` helper: confirm `corrupt_hash=True` actually produces a non-matching hash (i.e., content is written to disk before the manifest is created, and the manifest stores a different hash). Fixture order matters: write artifact → write sidecar → write manifest (so the manifest can reference real content and compute the correct hash for the non-corrupt case).
- T012 (legacy bundle): the `compliant_repo` fixture has no `.kittify/doctrine/` directory. Confirm the test does not accidentally create one.

## Activity Log

- 2026-04-30T14:46:59Z – claude – shell_pid=57391 – 87 tests pass; ruff clean; all T007-T014 implemented
- 2026-04-30T14:47:25Z – claude – shell_pid=63309 – Started review via action command
