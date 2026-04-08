---
work_package_id: WP04
title: Tracker Bind Build-Id and Contract Provenance Tests
dependencies:
- WP03
requirement_refs:
- FR-009
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T025
- T026
- T027
- T028
history:
- date: '2026-04-08'
  actor: planner
  action: created
authoritative_surface: src/specify_cli/tracker/
execution_mode: code_change
mission_slug: 075-mission-build-identity-contract-cutover
owned_files:
- src/specify_cli/tracker/origin.py
- src/specify_cli/tracker/saas_client.py
- src/specify_cli/tracker/origin_models.py
- tests/specify_cli/tracker/test_origin_bind.py
- tests/specify_cli/core/test_contract_gate.py
tags: []
---

# WP04 — Tracker Bind Build-Id and Contract Provenance Tests

## Branch Strategy

- **Planning base**: `main`
- **Merge target**: `main`
- **Workspace**: allocated by `spec-kitty implement WP04` (lane-based worktree, same lane as WP03)
- **Command**: `spec-kitty implement WP04 --mission 075-mission-build-identity-contract-cutover`
- **PREREQUISITE**: WP03 must be merged to `main` before starting WP04. The tracker bind must use the per-worktree `build_id` from `ensure_identity()` — not the stale value from `config.yaml`.

## Objective

1. **FR-009**: Add `build_id` to the `bind_mission_origin` SaaS call. Currently `bind_mission_origin` sends `mission_slug`, `external_issue_id`, etc., but no `build_id`. After this WP it also sends `build_id` loaded from `ProjectIdentity`.

2. **FR-015 (test only)**: The `upstream_contract.json` already carries `_schema_version: "3.0.0"` and `_source_events_commit: "5b8e6dc"`. Write the Scenario 4 acceptance test that asserts these fields are present and correct.

## Context

### Tracker bind anatomy

`bind_mission_origin` in `src/specify_cli/tracker/origin.py` (line ~175):
1. Loads `meta.json` to get `mission_slug`
2. Resolves `repo_root` via `_resolve_repo_root(feature_dir)`
3. Loads `tracker_config` to get `project_slug`
4. Calls `actual_client.bind_mission_origin(provider, project_slug, mission_slug=..., ...)`
5. Writes to local `meta.json` (local-second)
6. Emits `MissionOriginBound` event

`repo_root` is already resolved at step 2. `ProjectIdentity` can be loaded from `repo_root` using `ensure_identity(repo_root)`.

`SaaSTrackerClient.bind_mission_origin()` is at `src/specify_cli/tracker/saas_client.py` line ~437. Its current signature does not include `build_id`. This must be extended.

### Contract provenance

`_load_contract()` in `src/specify_cli/core/contract_gate.py` loads `upstream_contract.json` via `importlib.resources`. The file already has:
```json
{
  "_schema_version": "3.0.0",
  "_source_events_commit": "5b8e6dc",
  "_source_saas_commit": "3a0e4af",
  ...
}
```
No content change needed. T028 writes a test asserting these fields.

## Subtask Guidance

### T025 — Extend SaaSTrackerClient.bind_mission_origin() to accept build_id

**File**: `src/specify_cli/tracker/saas_client.py`

Locate `bind_mission_origin` (~line 437). Add `build_id: str` to its parameter list:

```python
def bind_mission_origin(
    self,
    provider: str,
    project_slug: str,
    *,
    mission_slug: str,
    build_id: str,           # NEW
    external_issue_id: str,
    external_issue_key: str,
    external_issue_url: str,
    title: str,
    external_status: str,
) -> None:
```

Include `build_id` in the outbound payload dict sent to the SaaS endpoint. The exact payload structure depends on the existing implementation — add `"build_id": build_id` alongside `"mission_slug"` in the request body.

**Audit**: Search for any other callers of `SaaSTrackerClient.bind_mission_origin()` beyond `origin.py`. Update all call sites to pass `build_id=""` or the real value as appropriate (may include test files).

Run `mypy --strict src/specify_cli/tracker/saas_client.py` — must pass.

---

### T026 — Load ProjectIdentity in bind_mission_origin(); pass build_id to client

**File**: `src/specify_cli/tracker/origin.py`

In `bind_mission_origin()` (line ~175), after step 2 (`repo_root = _resolve_repo_root(feature_dir)`), add:

```python
from specify_cli.sync.project_identity import ensure_identity

# Load per-worktree project identity to get build_id
project_identity = ensure_identity(repo_root)
build_id = project_identity.build_id or ""
```

Then pass `build_id` to the client call:

```python
actual_client.bind_mission_origin(
    provider,
    project_slug,
    mission_slug=mission_slug,
    build_id=build_id,          # NEW
    external_issue_id=candidate.external_issue_id,
    external_issue_key=candidate.external_issue_key,
    external_issue_url=candidate.url,
    title=candidate.title,
    external_status=candidate.status,
)
```

**Important**: The import of `ensure_identity` should be a top-level import in `origin.py`, not inline. Move it to the imports section if you write it inline first.

Run `mypy --strict src/specify_cli/tracker/origin.py` — must pass.

---

### T027 — Write test: captured bind call payload contains build_id (Scenario 3)

**File**: `tests/specify_cli/tracker/test_origin_bind.py`

Write a test that mocks `SaaSTrackerClient.bind_mission_origin` and asserts `build_id` is present in the captured call:

```python
from unittest.mock import MagicMock, patch
from pathlib import Path
from specify_cli.tracker.origin import bind_mission_origin
from specify_cli.tracker.origin_models import OriginCandidate

def test_bind_mission_origin_includes_build_id(tmp_path):
    """bind_mission_origin must send build_id in the SaaS call payload (FR-009, Scenario 3)."""
    # Set up minimal fixture
    feature_dir = tmp_path / "kitty-specs" / "075-test"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text('{"mission_slug": "075-test"}')

    # Minimal .kittify config
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "project:\n  uuid: test-uuid\n  slug: test-slug\n  node_id: abc123\n"
    )
    (kittify / "tracker.yaml").write_text(
        "provider: linear\nproject_slug: test-slug\n"
    )

    # Mock the SaaS client
    mock_client = MagicMock()
    candidate = OriginCandidate(
        external_issue_id="LIN-123",
        external_issue_key="LIN-123",
        url="https://linear.app/test/LIN-123",
        title="Test Issue",
        status="Todo",
    )

    with patch(
        "specify_cli.sync.project_identity._build_id_path",
        return_value=tmp_path / ".git" / "spec-kitty-build-id",
    ):
        # Create the build-id file
        (tmp_path / ".git").mkdir(exist_ok=True)
        (tmp_path / ".git" / "spec-kitty-build-id").write_text("test-build-id-uuid\n")

        bind_mission_origin(
            feature_dir=feature_dir,
            candidate=candidate,
            provider="linear",
            resource_type="linear_team",
            resource_id="team-123",
            client=mock_client,
        )

    # Assert build_id was sent
    call_kwargs = mock_client.bind_mission_origin.call_args.kwargs
    assert "build_id" in call_kwargs, f"build_id missing from bind call kwargs: {call_kwargs}"
    assert call_kwargs["build_id"] == "test-build-id-uuid"
```

Adjust the fixture structure to match how existing tests create the minimal project directory.

---

### T028 — Write test: _load_contract() provenance fields (Scenario 4)

**File**: `tests/specify_cli/core/test_contract_gate.py`

Add a test asserting the provenance fields in `upstream_contract.json`:

```python
from specify_cli.core.contract_gate import _load_contract

def test_upstream_contract_carries_provenance_fields():
    """upstream_contract.json must carry _schema_version and _source_events_commit (FR-015, Scenario 4)."""
    contract = _load_contract()

    assert contract.get("_schema_version") == "3.0.0", (
        f"Expected _schema_version='3.0.0', got {contract.get('_schema_version')!r}"
    )
    assert contract.get("_source_events_commit") == "5b8e6dc", (
        f"Expected _source_events_commit='5b8e6dc', got {contract.get('_source_events_commit')!r}"
    )
    assert contract.get("_source_saas_commit") == "3a0e4af", (
        f"Expected _source_saas_commit='3a0e4af', got {contract.get('_source_saas_commit')!r}"
    )
```

This test requires no production changes — it documents and locks the existing state (FR-015 is already implemented).

## Definition of Done

- [ ] `SaaSTrackerClient.bind_mission_origin()` accepts `build_id: str` parameter
- [ ] `bind_mission_origin` in `origin.py` loads `ProjectIdentity` and passes `build_id` to the client
- [ ] Test asserts captured bind call kwargs contain `build_id` with the expected value (Scenario 3)
- [ ] Test asserts `_load_contract()["_schema_version"] == "3.0.0"` and `_source_events_commit == "5b8e6dc"` (Scenario 4)
- [ ] `mypy --strict` passes on all modified files
- [ ] All tests in `tests/specify_cli/tracker/` and `tests/specify_cli/core/test_contract_gate.py` green

## Risks

| Risk | Mitigation |
|------|-----------|
| `SaaSTrackerClient.bind_mission_origin()` has additional call sites not in `origin.py` | `grep -r "\.bind_mission_origin(" src/ tests/` before changing the signature; update all call sites |
| `_load_contract()` is private — test imports it directly | This is acceptable for a targeted contract test; `_load_contract` is stable internal API |

## Reviewer Guidance

- Confirm `bind_mission_origin` SaaS call in `origin.py` passes `build_id=` to the client
- Confirm `SaaSTrackerClient.bind_mission_origin()` signature includes `build_id: str` (keyword-only after `*`)
- Confirm T028 test asserts all three provenance fields (`_schema_version`, `_source_events_commit`, `_source_saas_commit`)
- Run `pytest tests/specify_cli/tracker/test_origin_bind.py tests/specify_cli/core/test_contract_gate.py -v` — all green
