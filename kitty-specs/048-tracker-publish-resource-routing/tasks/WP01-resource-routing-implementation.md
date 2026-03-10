---
work_package_id: WP01
title: Resource Routing Implementation and Tests
lane: "for_review"
dependencies: []
base_branch: 2.x
base_commit: cbae93b2edf7e9ef4460f944e676a884b2130957
created_at: '2026-03-10T10:12:11.293482+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
phase: Phase 1 - Core Implementation
assignee: ''
agent: claude
shell_pid: '42429'
review_status: ''
reviewed_by: ''
history:
- timestamp: '2026-03-10T09:49:14Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs: [FR-001, FR-002, FR-003, FR-004, FR-005, FR-006, FR-007, FR-008, FR-011, FR-012]
---

# Work Package Prompt: WP01 – Resource Routing Implementation and Tests

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes.

*[This section is empty initially.]*

---

## Objectives & Success Criteria

- Add `external_resource_type` and `external_resource_id` to the tracker snapshot publish payload.
- Jira publishes `("jira_project", credentials["project_key"])`.
- Linear publishes `("linear_team", credentials["team_id"])`.
- Unsupported providers and missing credentials yield `(null, null)`.
- All 10 test cases in the test matrix pass (8 derivation + 1 empty-creds-present + 1 idempotency rebind).
- The idempotency key includes `external_resource_type` and `external_resource_id` so rebind-then-publish is not deduplicated.
- Existing `sync_publish()` behavior unchanged for all other payload fields.

**Implementation command** (no dependencies):
```bash
spec-kitty implement WP01
```

## Context & Constraints

- **Spec**: `kitty-specs/048-tracker-publish-resource-routing/spec.md`
- **Plan**: `kitty-specs/048-tracker-publish-resource-routing/plan.md`
- **Data model**: `kitty-specs/048-tracker-publish-resource-routing/data-model.md`
- **Contract**: `kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md`
- **Source file**: `src/specify_cli/tracker/service.py` (lines 182-243 contain `sync_publish()`)
- **Credential shapes**: Jira stores `project_key`, Linear stores `team_id` in `~/.spec-kitty/credentials` (see `src/specify_cli/tracker/factory.py` lines 76-92)

**Constraints**:
- Do NOT modify the Git event envelope (15 fields in `EventEmitter._emit()`).
- Do NOT modify `TrackerProjectConfig`, `TrackerCredentialStore`, or `factory.py`.
- Do NOT add new dependencies — this is a pure dict-lookup, no network calls.
- The `external_resource_type` values `"jira_project"` and `"linear_team"` are **canonical wire values** — stable contract strings, not display labels.

## Subtasks & Detailed Guidance

### Subtask T001 – Add RESOURCE_ROUTING_MAP module-level constant

**Purpose**: Define the static mapping from normalized provider name to `(resource_type, credential_key)` pairs. This constant is the single source of truth for which providers support routing and which credential key holds the resource identifier.

**Steps**:
1. Open `src/specify_cli/tracker/service.py`.
2. Add the following constant after the existing imports, before the `TrackerServiceError` class:

```python
# Canonical wire values for tracker resource routing.
# Keys: normalized provider name (from normalize_provider()).
# Values: (external_resource_type, credential_key_for_resource_id).
# These are stable contract strings — not display labels.
RESOURCE_ROUTING_MAP: dict[str, tuple[str, str]] = {
    "jira": ("jira_project", "project_key"),
    "linear": ("linear_team", "team_id"),
}
```

**Files**: `src/specify_cli/tracker/service.py`
**Parallel?**: No — T002 and T003 depend on this constant.
**Notes**: Future providers (e.g., Azure DevOps) add one dict entry here. No other code changes needed.

---

### Subtask T002 – Add _resolve_resource_routing() static method

**Purpose**: Encapsulate the derivation logic as a pure function. Takes `(provider, credentials)` and returns `(external_resource_type, external_resource_id)` or `(None, None)`.

**Steps**:
1. Add the following static method to `TrackerService`, after the existing `_project_identity()` method (around line 342):

```python
@staticmethod
def _resolve_resource_routing(
    provider: str,
    credentials: dict[str, Any],
) -> tuple[str | None, str | None]:
    """Derive resource routing fields from provider and credentials.

    Returns (external_resource_type, external_resource_id) if the provider
    has a routing mapping and the required credential key is present and
    non-empty. Otherwise returns (None, None).
    """
    entry = RESOURCE_ROUTING_MAP.get(provider)
    if entry is None:
        return None, None
    resource_type, credential_key = entry
    resource_id = credentials.get(credential_key)
    if resource_id is None or not str(resource_id).strip():
        return None, None
    return resource_type, str(resource_id).strip()
```

**Files**: `src/specify_cli/tracker/service.py`
**Parallel?**: No — T003 calls this method.
**Notes**:
- The method is `@staticmethod` because it has no `self` dependencies — it's a pure function of its arguments.
- Empty string and whitespace-only values are treated as missing (both fields return `None`).
- Both fields are always atomically null or atomically populated — never one null and one populated.

---

### Subtask T003 – Integrate routing fields into sync_publish() payload

**Purpose**: Call `_resolve_resource_routing()` inside `sync_publish()` and add the two new fields to the payload dict.

**Steps**:
1. In `sync_publish()` (line ~191), after the `project_identity = self._project_identity()` call, add:

```python
resource_type, resource_id = self._resolve_resource_routing(provider, credentials)
```

2. Add the two fields to the `payload` dict (after `"project_slug"`):

```python
payload = {
    "provider": provider,
    "workspace": workspace,
    "external_resource_type": resource_type,
    "external_resource_id": resource_id,
    "doctrine_mode": config.doctrine_mode,
    # ... rest of existing fields unchanged ...
}
```

3. Update the idempotency key hash (line ~215) to include routing fields:

```python
idempotency_key = hashlib.sha256(
    f"{provider}|{workspace}|{resource_type}|{resource_id}|{len(issues)}|{len(mappings)}|{payload['checkpoint']['cursor']}".encode("utf-8")
).hexdigest()
```

This ensures that rebinding to a different `project_key` (Jira) or `team_id` (Linear) produces a different idempotency key even when the issue/mapping/cursor state is unchanged. `resource_type` and `resource_id` may be `None` — `str(None)` is stable.

**Files**: `src/specify_cli/tracker/service.py` (modify `sync_publish()` method, lines 182-243)
**Parallel?**: No — depends on T001 and T002.
**Notes**:
- Insert the new fields right after `"workspace"` and before `"doctrine_mode"` to match the contract document's field order.
- Do NOT change any existing fields or their sources.
- The `provider` and `credentials` variables are already available at this point in the method (line 191-192).
- The idempotency key must use `resource_type` and `resource_id` (the resolved values), not raw credential keys.

---

### Subtask T004 – Create derivation unit tests (10 test cases)

**Purpose**: Test `_resolve_resource_routing()` in isolation against all cases from the plan's test matrix, plus verify idempotency key changes on rebind.

**Steps**:
1. Create `tests/specify_cli/tracker/test_service_publish.py`.
2. Import `TrackerService` and `RESOURCE_ROUTING_MAP` from `specify_cli.tracker.service`.
3. Write parameterized tests covering:

```python
import pytest
from specify_cli.tracker.service import TrackerService, RESOURCE_ROUTING_MAP


class TestResolveResourceRouting:
    """Unit tests for TrackerService._resolve_resource_routing()."""

    def test_jira_happy_path(self):
        result = TrackerService._resolve_resource_routing(
            "jira", {"project_key": "ACME", "base_url": "https://x.atlassian.net"}
        )
        assert result == ("jira_project", "ACME")

    def test_linear_happy_path(self):
        result = TrackerService._resolve_resource_routing(
            "linear", {"team_id": "abc-123", "api_key": "tok"}
        )
        assert result == ("linear_team", "abc-123")

    def test_jira_missing_project_key(self):
        result = TrackerService._resolve_resource_routing(
            "jira", {"base_url": "https://x.atlassian.net"}
        )
        assert result == (None, None)

    def test_linear_missing_team_id(self):
        result = TrackerService._resolve_resource_routing(
            "linear", {"api_key": "tok"}
        )
        assert result == (None, None)

    def test_jira_empty_string_project_key(self):
        result = TrackerService._resolve_resource_routing(
            "jira", {"project_key": ""}
        )
        assert result == (None, None)

    def test_jira_whitespace_only_project_key(self):
        result = TrackerService._resolve_resource_routing(
            "jira", {"project_key": "   "}
        )
        assert result == (None, None)

    def test_unsupported_provider(self):
        result = TrackerService._resolve_resource_routing(
            "beads", {"command": "bd"}
        )
        assert result == (None, None)

    def test_unknown_provider(self):
        result = TrackerService._resolve_resource_routing(
            "notion", {"api_key": "tok"}
        )
        assert result == (None, None)

    def test_jira_creds_present_but_no_routing_key(self):
        """Credentials dict is non-empty but lacks project_key.
        This is the path where _load_runtime() succeeds but routing is unavailable.
        """
        result = TrackerService._resolve_resource_routing(
            "jira", {"base_url": "https://x.atlassian.net", "email": "a@b.com", "api_token": "tok"}
        )
        assert result == (None, None)


class TestResourceRoutingMap:
    """Verify canonical wire values are stable."""

    def test_jira_wire_value(self):
        assert RESOURCE_ROUTING_MAP["jira"] == ("jira_project", "project_key")

    def test_linear_wire_value(self):
        assert RESOURCE_ROUTING_MAP["linear"] == ("linear_team", "team_id")

    def test_only_jira_and_linear(self):
        assert set(RESOURCE_ROUTING_MAP.keys()) == {"jira", "linear"}
```

**Files**: `tests/specify_cli/tracker/test_service_publish.py` (new file)
**Parallel?**: Yes — the method signature and return type are defined in T002. Tests can be written simultaneously.
**Notes**: These tests call the static method directly — no mocking needed, no external dependencies.

---

### Subtask T005 – Add payload integration test

**Purpose**: Verify that `sync_publish()` includes both routing fields in the HTTP request body sent to the SaaS.

**Steps**:
1. In the same `tests/specify_cli/tracker/test_service_publish.py`, add an integration test class.
2. Mock `TrackerService._load_runtime()` to return controlled config/credentials/store.
3. Mock `TrackerService._project_identity()` to return a known project identity.
4. Use `respx` or `unittest.mock.patch` on `httpx.Client.post` to capture the outgoing payload.
5. Assert the payload contains `external_resource_type` and `external_resource_id` with expected values.

```python
from unittest.mock import MagicMock, patch, PropertyMock
from pathlib import Path

from specify_cli.tracker.config import TrackerProjectConfig
from specify_cli.tracker.service import TrackerService


class TestSyncPublishPayload:
    """Integration test: sync_publish() sends routing fields in HTTP body."""

    def test_jira_publish_includes_routing_fields(self):
        config = TrackerProjectConfig(
            provider="jira",
            workspace="acme.atlassian.net",
            doctrine_mode="external_authoritative",
        )
        credentials = {
            "base_url": "https://acme.atlassian.net",
            "email": "a@b.com",
            "api_token": "tok",
            "project_key": "ACME",
        }
        store = MagicMock()
        store.list_issues = MagicMock(return_value=MagicMock())
        store.list_mappings = MagicMock(return_value=[])
        store.get_checkpoint = MagicMock(return_value=None)

        # Make list_issues async-compatible
        import asyncio

        async def mock_list_issues(system=None):
            return []

        store.list_issues = mock_list_issues

        service = TrackerService(Path("/tmp/fake-repo"))

        with patch.object(
            TrackerService, "_load_runtime", return_value=(config, credentials, store)
        ), patch.object(
            TrackerService, "_project_identity", return_value={"uuid": "test-uuid", "slug": "test-proj"}
        ), patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"status": "ok"}
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_client_cls.return_value.__enter__.return_value.post = MagicMock(return_value=mock_response)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = service.sync_publish(
                server_url="https://example.com",
                auth_token="test-token",
            )

            # Extract the payload sent to httpx
            post_call = mock_client_cls.return_value.__enter__.return_value.post
            assert post_call.called
            sent_payload = post_call.call_args[1]["json"]

            assert sent_payload["external_resource_type"] == "jira_project"
            assert sent_payload["external_resource_id"] == "ACME"
            # Verify existing fields are still present
            assert sent_payload["provider"] == "jira"
            assert sent_payload["workspace"] == "acme.atlassian.net"

    def test_unsupported_provider_publishes_null_routing(self):
        config = TrackerProjectConfig(
            provider="beads",
            workspace="my-workspace",
            doctrine_mode="external_authoritative",
        )
        credentials = {"command": "bd"}
        store = MagicMock()
        store.list_mappings = MagicMock(return_value=[])
        store.get_checkpoint = MagicMock(return_value=None)

        import asyncio

        async def mock_list_issues(system=None):
            return []

        store.list_issues = mock_list_issues

        service = TrackerService(Path("/tmp/fake-repo"))

        with patch.object(
            TrackerService, "_load_runtime", return_value=(config, credentials, store)
        ), patch.object(
            TrackerService, "_project_identity", return_value={"uuid": None, "slug": None}
        ), patch("httpx.Client") as mock_client_cls:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.is_success = True
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {"status": "ok"}
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_client_cls.return_value.__enter__.return_value.post = MagicMock(return_value=mock_response)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = service.sync_publish(
                server_url="https://example.com",
                auth_token="test-token",
            )

            post_call = mock_client_cls.return_value.__enter__.return_value.post
            sent_payload = post_call.call_args[1]["json"]

            assert sent_payload["external_resource_type"] is None
            assert sent_payload["external_resource_id"] is None

    def test_idempotency_key_changes_on_rebind(self):
        """Rebinding to a different project_key must produce a different idempotency key,
        even when issue/mapping/cursor state is identical."""
        store = MagicMock()
        store.list_mappings = MagicMock(return_value=[])
        store.get_checkpoint = MagicMock(return_value=None)

        async def mock_list_issues(system=None):
            return []
        store.list_issues = mock_list_issues

        service = TrackerService(Path("/tmp/fake-repo"))
        keys = []

        for project_key in ("ACME", "BETA"):
            config = TrackerProjectConfig(
                provider="jira",
                workspace="acme.atlassian.net",
                doctrine_mode="external_authoritative",
            )
            credentials = {
                "base_url": "https://acme.atlassian.net",
                "email": "a@b.com",
                "api_token": "tok",
                "project_key": project_key,
            }

            with patch.object(
                TrackerService, "_load_runtime", return_value=(config, credentials, store)
            ), patch.object(
                TrackerService, "_project_identity", return_value={"uuid": "test-uuid", "slug": "test-proj"}
            ), patch("httpx.Client") as mock_client_cls:
                mock_response = MagicMock()
                mock_response.status_code = 200
                mock_response.is_success = True
                mock_response.headers = {"content-type": "application/json"}
                mock_response.json.return_value = {"status": "ok"}
                mock_client_cls.return_value.__enter__ = MagicMock(return_value=MagicMock())
                mock_client_cls.return_value.__enter__.return_value.post = MagicMock(return_value=mock_response)
                mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

                result = service.sync_publish(
                    server_url="https://example.com",
                    auth_token="test-token",
                )
                keys.append(result["idempotency_key"])

        assert keys[0] != keys[1], "Rebind to different project_key must change idempotency key"
```

**Files**: `tests/specify_cli/tracker/test_service_publish.py` (same file as T004)
**Parallel?**: No — depends on T001-T003 being implemented.
**Notes**:
- The integration test is heavier due to mocking the HTTP client, but it proves the full `sync_publish()` path works.
- If the mocking approach is too brittle, an acceptable alternative is to extract the payload-building logic into a testable helper and test that directly. But the mock approach is preferred since it tests the actual HTTP call path.
- The idempotency rebind test is critical — without it, the P1 finding about deduplicated routing changes would regress silently.

## Test Strategy

Run all tests with:
```bash
python -m pytest tests/specify_cli/tracker/test_service_publish.py -v
```

Verify no regressions in adjacent test files:
```bash
python -m pytest tests/specify_cli/tracker/ -v
```

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `spec-kitty-tracker` import error in test environment | Medium | Blocks integration tests | Mock `_load_runtime()` to avoid the import entirely |
| Existing sync_publish tests break | Low | Must update tests | Search for existing tests first; update if needed |
| Payload field order matters to SaaS | Low | SaaS rejects payload | JSON field order is not significant; SaaS should accept any order |

## Review Guidance

- Verify `RESOURCE_ROUTING_MAP` contains exactly `"jira"` and `"linear"` entries.
- Verify wire values are `"jira_project"` and `"linear_team"` (not provider names, not display labels).
- Verify `_resolve_resource_routing()` is `@staticmethod` with no side effects.
- Verify both fields are atomically null or atomically populated.
- Verify `sync_publish()` payload includes both new fields without removing or modifying existing fields.
- Verify the idempotency key hash includes `resource_type` and `resource_id` — rebind must produce a different key.
- Verify all 10 test cases from the plan's test matrix are covered (8 derivation + empty-creds-present + idempotency rebind).
- Verify the empty-creds-present test covers the real `_load_runtime()` path where credentials are `{}` (not the spec's incorrect claim that it raises).

## Activity Log

- 2026-03-10T09:49:14Z – system – lane=planned – Prompt created.
- 2026-03-10T10:12:11Z – claude – shell_pid=42429 – lane=doing – Assigned agent via workflow command
- 2026-03-10T10:14:18Z – claude – shell_pid=42429 – lane=for_review – Ready for review: resource routing fields added to sync_publish() with 16 passing tests
