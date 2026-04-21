---
work_package_id: WP01
title: 'Executor Core: Package Foundation + profiles list'
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-006
- FR-008
- FR-009
- FR-012
- FR-013
- FR-014
- FR-017
- FR-018
- FR-019
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
history:
- date: '2026-04-21'
  event: created
  actor: claude
authoritative_surface: src/specify_cli/invocation/
execution_mode: code_change
owned_files:
- src/specify_cli/invocation/__init__.py
- src/specify_cli/invocation/errors.py
- src/specify_cli/invocation/registry.py
- src/specify_cli/invocation/writer.py
- src/specify_cli/invocation/executor.py
- src/specify_cli/cli/commands/profiles_cmd.py
- tests/specify_cli/invocation/__init__.py
- tests/specify_cli/invocation/test_executor.py
- tests/specify_cli/invocation/test_registry.py
- tests/specify_cli/invocation/test_writer.py
- tests/specify_cli/invocation/cli/__init__.py
- tests/specify_cli/invocation/cli/test_profiles.py
- tests/specify_cli/invocation/fixtures/**
tags: []
---

# WP01 — Executor Core: Package Foundation + `profiles list`

## Objective

Stand up the `src/specify_cli/invocation/` package with its core primitives:
`ProfileInvocationExecutor`, `InvocationRecord`, `ProfileRegistry`, `InvocationWriter`,
structured error types, and the `spec-kitty profiles list` CLI command.

This WP is the dependency root — every other WP depends on the seams defined here.

**Implementation command**:
```bash
spec-kitty agent action implement WP01 --agent claude
```

## Branch Strategy

- Planning base: `main`
- Merge target: `main`
- Execution worktree: allocated by `lanes.json` after `finalize-tasks`

## Context

**ADR-3 entry gate**: The ADR-3 document at
`kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/adr-3-deterministic-action-router.md`
is already committed. Read it before implementing the executor's router slot.

**Key existing seams to import from** (read these files before starting):
- `src/charter/context.py::build_charter_context` — programmatic governance context API
- `src/doctrine/agent_profiles/repository.py::AgentProfileRepository` — profile loading
- `src/doctrine/agent_profiles/capabilities.py::DEFAULT_ROLE_CAPABILITIES` — canonical verbs
- `src/doctrine/agent_profiles/profile.py::AgentProfile` — profile model

**Charter policy**:
- `typer` for CLI, `rich` for output, `pydantic` v2 for models
- `mypy --strict` must pass
- ≥ 90% line coverage on new code
- Integration tests for CLI commands

---

## Subtask T001 — Package Scaffold

**Purpose**: Create the package directory structure and the `errors.py` error types used throughout the package.

**Steps**:

1. Create `src/specify_cli/invocation/__init__.py` (initially empty, expanded in T005/T006).

2. Create `src/specify_cli/invocation/errors.py`:
   ```python
   class InvocationError(Exception):
       """Base for all invocation errors."""

   class ProfileNotFoundError(InvocationError):
       def __init__(self, profile_id: str, available: list[str]) -> None:
           self.profile_id = profile_id
           self.available = available
           super().__init__(f"Profile '{profile_id}' not found. Available: {available}")

   class ContextUnavailableError(InvocationError):
       """Governance context could not be assembled (charter not synthesized)."""

   class InvocationWriteError(InvocationError):
       """JSONL write failed. Invocation not started."""

   class RouterAmbiguityError(InvocationError):
       def __init__(
           self,
           request_text: str,
           error_code: str,  # ROUTER_AMBIGUOUS | ROUTER_NO_MATCH | PROFILE_NOT_FOUND
           candidates: list[dict[str, str]],
           suggestion: str,
       ) -> None:
           self.request_text = request_text
           self.error_code = error_code
           self.candidates = candidates
           self.suggestion = suggestion
           super().__init__(f"{error_code}: {suggestion}")
   ```

3. Create test fixtures directory `tests/specify_cli/invocation/fixtures/profiles/`.

4. Create minimal fixture profile `tests/specify_cli/invocation/fixtures/profiles/implementer.agent.yaml`:
   ```yaml
   profile-id: implementer-fixture
   friendly-name: "Implementer (fixture)"
   role: implementer
   specialization:
     domain-keywords: [implement, build, code]
   ```

5. Create `tests/specify_cli/invocation/fixtures/profiles/reviewer.agent.yaml`:
   ```yaml
   profile-id: reviewer-fixture
   friendly-name: "Reviewer (fixture)"
   role: reviewer
   specialization:
     domain-keywords: [review, audit, assess]
   ```

**Files**:
- `src/specify_cli/invocation/__init__.py` (empty initially)
- `src/specify_cli/invocation/errors.py`
- `tests/specify_cli/invocation/__init__.py`
- `tests/specify_cli/invocation/cli/__init__.py`
- `tests/specify_cli/invocation/fixtures/profiles/implementer.agent.yaml`
- `tests/specify_cli/invocation/fixtures/profiles/reviewer.agent.yaml`

---

## Subtask T002 — `record.py`: InvocationRecord + Policy Stub

**Purpose**: Define `InvocationRecord` as the v1 Pydantic model and create a stub `MinimalViableTrailPolicy` (WP05 will finalize it).

**Steps**:

1. Create `src/specify_cli/invocation/record.py`:
   ```python
   from __future__ import annotations
   from typing import Literal
   from pydantic import BaseModel, Field
   import datetime

   class InvocationRecord(BaseModel):
       """v1 JSONL event record. Each invocation produces one file with two events."""
       event: Literal["started", "completed"]
       invocation_id: str                         # ULID
       profile_id: str
       action: str                                # canonical action token
       request_text: str = ""
       governance_context_hash: str = ""          # first 16 hex chars of SHA-256
       governance_context_available: bool = True
       actor: str = "unknown"                     # "claude" | "operator" | "unknown"
       router_confidence: str | None = None       # "exact" | "canonical_verb" | "domain_keyword"
       started_at: str = ""                       # ISO-8601 UTC
       # completed event fields (null until profile-invocation complete)
       completed_at: str | None = None
       outcome: Literal["done", "failed", "abandoned"] | None = None
       evidence_ref: str | None = None

       model_config = {"frozen": True}
   ```

2. Add `MINIMAL_VIABLE_TRAIL_POLICY` stub:
   ```python
   # Stub — WP05 finalizes the full frozen dataclass.
   # Other modules may import this symbol; WP05 replaces the value in-place.
   MINIMAL_VIABLE_TRAIL_POLICY: dict[str, object] = {
       "tier_1": {"name": "every_invocation", "mandatory": True},
       "tier_2": {"name": "evidence_artifact", "mandatory": False},
       "tier_3": {"name": "durable_project_state", "mandatory": False},
   }
   ```

**Validation rules** (document as comments in the file):
- `invocation_id` must be a valid ULID (26 chars)
- `started_at` must be ISO-8601 UTC
- `event` discriminator must be `"started"` or `"completed"`

**Files**: `src/specify_cli/invocation/record.py`

---

## Subtask T003 — `registry.py`: ProfileRegistry

**Purpose**: Thin wrapper over `AgentProfileRepository` that handles the project-local override path and provides a clean API for the executor.

**Steps**:

1. Create `src/specify_cli/invocation/registry.py`:
   ```python
   from __future__ import annotations
   from pathlib import Path
   from doctrine.agent_profiles.repository import AgentProfileRepository
   from doctrine.agent_profiles.profile import AgentProfile
   from specify_cli.invocation.errors import ProfileNotFoundError

   class ProfileRegistry:
       def __init__(self, repo_root: Path) -> None:
           project_profiles_dir = repo_root / ".kittify" / "profiles"
           self._repo = AgentProfileRepository(
               project_dir=project_profiles_dir if project_profiles_dir.exists() else None,
           )

       def list_all(self) -> list[AgentProfile]:
           return self._repo.list_all()

       def get(self, profile_id: str) -> AgentProfile | None:
           return self._repo.get(profile_id)

       def resolve(self, profile_id: str) -> AgentProfile:
           profile = self._repo.get(profile_id)
           if profile is None:
               available = [p.profile_id for p in self._repo.list_all()]
               raise ProfileNotFoundError(profile_id, available)
           return profile

       def has_profiles(self) -> bool:
           return len(self._repo.list_all()) > 0
   ```

**Notes**:
- When `.kittify/profiles/` does not exist, `project_dir=None` causes the repo to fall back to shipped profiles gracefully (no exception).
- If shipped profiles also produce an empty list, `has_profiles()` returns False — the executor uses this to produce the "run charter synthesize" error message.

**Files**: `src/specify_cli/invocation/registry.py`

---

## Subtask T004 — `writer.py`: InvocationWriter

**Purpose**: Append-only JSONL writer. Creates the per-invocation file on `write_started`, appends the completed event on `write_completed`. Raises `InvocationWriteError` on filesystem failure.

**Steps**:

1. Create `src/specify_cli/invocation/writer.py`:
   ```python
   from __future__ import annotations
   import json
   from pathlib import Path
   import datetime
   from specify_cli.invocation.record import InvocationRecord
   from specify_cli.invocation.errors import InvocationWriteError

   EVENTS_DIR = ".kittify/events/profile-invocations"

   class InvocationWriter:
       def __init__(self, repo_root: Path) -> None:
           self._dir = repo_root / EVENTS_DIR

       def _ensure_dir(self) -> None:
           self._dir.mkdir(parents=True, exist_ok=True)

       def invocation_path(self, profile_id: str, invocation_id: str) -> Path:
           return self._dir / f"{profile_id}-{invocation_id}.jsonl"

       def write_started(self, record: InvocationRecord) -> Path:
           """Write the `started` event. Returns the JSONL file path."""
           self._ensure_dir()
           path = self.invocation_path(record.profile_id, record.invocation_id)
           try:
               # Use "x" mode (exclusive create) to detect ULID collision (extremely rare).
               # On collision, caller should retry with a new ULID.
               with path.open("x", encoding="utf-8") as f:
                   f.write(json.dumps(record.model_dump()) + "\n")
           except FileExistsError:
               raise InvocationWriteError(
                   f"ULID collision on {path} — retry with a new invocation_id"
               )
           except OSError as e:
               raise InvocationWriteError(f"Failed to write invocation record: {e}") from e
           return path

       def write_completed(
           self,
           invocation_id: str,
           profile_id: str,
           repo_root: Path,
           *,
           outcome: str | None = None,
           evidence_ref: str | None = None,
       ) -> InvocationRecord:
           """Append the `completed` event to an existing invocation file."""
           path = self.invocation_path(profile_id, invocation_id)
           if not path.exists():
               from specify_cli.invocation.errors import InvocationError
               raise InvocationError(f"Invocation record not found: {invocation_id}")
           completed = InvocationRecord(
               event="completed",
               invocation_id=invocation_id,
               profile_id=profile_id,
               action="",  # not re-stated in completed event
               completed_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               outcome=outcome,  # type: ignore[arg-type]
               evidence_ref=evidence_ref,
           )
           try:
               with path.open("a", encoding="utf-8") as f:
                   f.write(json.dumps(completed.model_dump(exclude_none=False)) + "\n")
           except OSError as e:
               raise InvocationWriteError(f"Failed to append completed event: {e}") from e
           return completed
   ```

2. **Append-only invariant**: The writer only uses `"x"` (exclusive create) for the started event and `"a"` (append) for the completed event. No existing line is ever mutated.

**Files**: `src/specify_cli/invocation/writer.py`

---

## Subtask T005 — `executor.py`: ProfileInvocationExecutor

**Purpose**: The single execution primitive. `invoke()` assembles governance context, generates the ULID, writes the started record, and returns `InvocationPayload`. Accepts an optional `router` parameter (set by CLI commands; None by default for tests without router).

**Steps**:

1. Create `src/specify_cli/invocation/executor.py`:
   ```python
   from __future__ import annotations
   import datetime
   import hashlib
   from pathlib import Path
   from ulid2 import generate_ulid_as_uuid  # or from ulid import ULID — check existing imports

   from charter.context import build_charter_context
   from specify_cli.invocation.errors import ProfileNotFoundError, InvocationWriteError
   from specify_cli.invocation.record import InvocationRecord
   from specify_cli.invocation.registry import ProfileRegistry
   from specify_cli.invocation.writer import InvocationWriter

   # TYPE_CHECKING import for router (avoids circular; router.py created in WP02)
   from typing import TYPE_CHECKING, Protocol
   if TYPE_CHECKING:
       from specify_cli.invocation.router import ActionRouter

   class ActionRouterPlugin(Protocol):
       """No-op protocol stub — reserved for future hybrid routing extension."""
       # No methods in v1. Fill in WP02's ActionRouterPlugin slot here.

   class InvocationPayload:
       """Ephemeral response returned to CLI callers."""
       __slots__ = (
           "invocation_id", "profile_id", "profile_friendly_name",
           "action", "governance_context_text", "governance_context_hash",
           "governance_context_available", "router_confidence",
       )
       def __init__(self, **kwargs: object) -> None:
           for k, v in kwargs.items():
               setattr(self, k, v)

       def to_dict(self) -> dict[str, object]:
           return {s: getattr(self, s) for s in self.__slots__}

   class ProfileInvocationExecutor:
       """Single execution primitive for all profile-governed invocations."""

       def __init__(
           self,
           repo_root: Path,
           router: "ActionRouter | None" = None,
       ) -> None:
           self._repo_root = repo_root
           self._registry = ProfileRegistry(repo_root)
           self._writer = InvocationWriter(repo_root)
           self._router = router

       def invoke(
           self,
           request_text: str,
           profile_hint: str | None = None,
           actor: str = "unknown",
       ) -> InvocationPayload:
           """
           Route the request, load governance context, write started record, return payload.

           IMPORTANT: Does NOT spawn any LLM call. Returns synchronously.
           mark_loaded=False ensures first-load state for specify/plan/implement/review
           is NOT poisoned by invocation calls.
           """
           from ulid2 import generate_ulid_as_uuid as _gen_ulid  # noqa: F401
           import ulid2  # confirm import style matches existing codebase
           invocation_id = str(ulid2.generate_ulid_as_uuid())  # adapt to actual import

           # 1. Resolve (profile_id, action)
           if profile_hint is not None:
               profile = self._registry.resolve(profile_hint)  # raises ProfileNotFoundError
               action = self._derive_action_from_request(request_text, profile.role)
               router_confidence = None  # caller supplied explicit hint
           elif self._router is not None:
               from specify_cli.invocation.router import RouterDecision
               result = self._router.route(request_text)
               if isinstance(result, RouterDecision):
                   profile = self._registry.resolve(result.profile_id)
                   action = result.action
                   router_confidence = result.confidence
               else:
                   raise result  # RouterAmbiguityError — let CLI handle
           else:
               raise RuntimeError(
                   "No profile_hint and no router configured. "
                   "Use 'spec-kitty ask <profile>' or supply a router."
               )

           # 2. Assemble governance context (mark_loaded=False — critical)
           ctx_result = build_charter_context(
               self._repo_root,
               profile=profile.profile_id,
               action=action,
               mark_loaded=False,
           )
           ctx_hash = hashlib.sha256(ctx_result.text.encode()).hexdigest()[:16]
           ctx_available = ctx_result.mode != "missing"

           # 3. Write started record (raises InvocationWriteError on fs failure)
           started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
           record = InvocationRecord(
               event="started",
               invocation_id=invocation_id,
               profile_id=profile.profile_id,
               action=action,
               request_text=request_text,
               governance_context_hash=ctx_hash,
               governance_context_available=ctx_available,
               actor=actor,
               router_confidence=router_confidence,
               started_at=started_at,
           )
           self._writer.write_started(record)  # raises InvocationWriteError → non-zero exit

           return InvocationPayload(
               invocation_id=invocation_id,
               profile_id=profile.profile_id,
               profile_friendly_name=getattr(profile, "friendly_name", profile.profile_id),
               action=action,
               governance_context_text=ctx_result.text,
               governance_context_hash=ctx_hash,
               governance_context_available=ctx_available,
               router_confidence=router_confidence,
           )

       def _derive_action_from_request(self, request_text: str, role: object) -> str:
           """Derive canonical action token from role when profile_hint is explicit."""
           from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
           from doctrine.agent_profiles.profile import Role
           caps = DEFAULT_ROLE_CAPABILITIES.get(role) if isinstance(role, Role) else None
           if caps and caps.canonical_verbs:
               return caps.canonical_verbs[0]
           return "advise"  # default fallback
   ```

2. **ULID import**: Check `src/specify_cli/status/models.py` for the exact ULID import style used in the codebase and match it.

3. **`mark_loaded=False` is critical**: Add a module-level docstring comment explaining why. Failing to pass this flag would corrupt `context-state.json` and break the `specify`/`plan` first-load detection.

**Files**: `src/specify_cli/invocation/executor.py`

---

## Subtask T006 — `profiles_cmd.py` + main.py registration

**Purpose**: The `spec-kitty profiles list [--json]` command. Returns a JSON array or rich table of available profiles.

**Steps**:

1. Create `src/specify_cli/cli/commands/profiles_cmd.py`:
   ```python
   from __future__ import annotations
   import json
   from pathlib import Path
   import typer
   from rich.console import Console
   from rich.table import Table
   from specify_cli.invocation.registry import ProfileRegistry

   app = typer.Typer(name="profiles", help="Manage and list agent profiles.")
   console = Console()

   @app.command("list")
   def list_profiles(
       json_output: bool = typer.Option(False, "--json", help="Output JSON array."),
   ) -> None:
       """List all available agent profiles."""
       repo_root = Path.cwd()  # resolved by context detection (adapt to existing pattern)
       registry = ProfileRegistry(repo_root)
       profiles = registry.list_all()

       if not profiles:
           if json_output:
               typer.echo("[]")
           else:
               console.print("[yellow]No profiles found.[/yellow] Run 'spec-kitty charter synthesize' to create project-local profiles.")
           raise typer.Exit(0)

       descriptors = []
       for p in profiles:
           from doctrine.agent_profiles.capabilities import DEFAULT_ROLE_CAPABILITIES
           caps = DEFAULT_ROLE_CAPABILITIES.get(p.role) if hasattr(p, "role") else None
           canonical_verbs = caps.canonical_verbs if caps else []
           domain_kws = getattr(getattr(p, "specialization", None), "domain_keywords", []) or []
           source = "project_local" if hasattr(p, "_source") and p._source == "project" else "shipped"
           descriptors.append({
               "profile_id": p.profile_id,
               "friendly_name": getattr(p, "friendly_name", p.profile_id),
               "role": str(p.role),
               "action_domains": list({*canonical_verbs, *domain_kws}),
               "source": source,
           })

       if json_output:
           typer.echo(json.dumps(descriptors, indent=2))
       else:
           table = Table(title="Agent Profiles")
           table.add_column("Profile ID")
           table.add_column("Friendly Name")
           table.add_column("Role")
           table.add_column("Source")
           for d in descriptors:
               table.add_row(d["profile_id"], d["friendly_name"], d["role"], d["source"])
           console.print(table)
   ```

2. **Register in `src/specify_cli/cli/main.py`**: Add:
   ```python
   from specify_cli.cli.commands.profiles_cmd import app as profiles_app
   app.add_typer(profiles_app, name="profiles")
   ```

3. **Repo root resolution**: Check how other commands (e.g., `charter.py`, `next_cmd.py`) resolve the repo root — use the same utility function (typically `find_repo_root()` or `get_repo_root()`). Do not use `Path.cwd()` directly if a utility exists.

**Files**:
- `src/specify_cli/cli/commands/profiles_cmd.py`
- `src/specify_cli/cli/main.py` (add registration)

---

## Subtask T007 — Tests

**Purpose**: Unit and integration tests covering the WP01 surfaces. Target ≥ 90% line coverage.

**Tests to write**:

### `tests/specify_cli/invocation/test_record.py`
- `test_invocation_record_started_fields` — all required fields present, correct types
- `test_invocation_record_frozen` — mutation raises TypeError
- `test_invocation_record_json_roundtrip` — `model_dump()` → `InvocationRecord(**data)` is lossless

### `tests/specify_cli/invocation/test_registry.py`
- `test_registry_lists_shipped_profiles` — fixtures dir exists; list_all returns ≥ 1 profile
- `test_registry_get_existing` — get known profile returns AgentProfile
- `test_registry_get_missing_returns_none` — get unknown returns None
- `test_registry_resolve_missing_raises` — resolve unknown raises ProfileNotFoundError
- `test_registry_fallback_no_project_dir` — tmp_path with no `.kittify/profiles/` — no exception

### `tests/specify_cli/invocation/test_writer.py`
- `test_write_started_creates_file` — file exists, contains valid JSON line
- `test_write_completed_appends_line` — two lines in file after complete
- `test_write_started_append_only` — opening a written file in append mode does not corrupt it
- `test_write_started_collision_raises` — create file before write_started → raises InvocationWriteError
- `test_invocation_path_format` — path matches `<profile_id>-<invocation_id>.jsonl`

### `tests/specify_cli/invocation/test_executor.py`
- `test_invoke_with_profile_hint` — passes profile_hint, returns InvocationPayload, creates JSONL
- `test_invoke_no_router_no_hint_raises` — RuntimeError
- `test_invoke_missing_profile_hint_raises` — ProfileNotFoundError
- `test_invoke_degraded_charter` — charter missing → governance_context_available=False, JSONL still written
- `test_invoke_mark_loaded_false` — context_state.json NOT modified after invoke (critical)
- `test_invoke_write_failure_raises` — mock writer raises InvocationWriteError → propagates

### `tests/specify_cli/invocation/cli/test_profiles.py` (integration, CliRunner)
- `test_profiles_list_json_output` — exits 0, valid JSON array
- `test_profiles_list_table_output` — exits 0, rich table rendered
- `test_profiles_list_no_profiles` — exits 0, empty array / helpful message

**Run tests**:
```bash
cd src && pytest tests/specify_cli/invocation/ -v --tb=short
cd src && mypy specify_cli/invocation/ --strict
```

**Acceptance**:
- [ ] All tests pass
- [ ] `mypy --strict` clean on `src/specify_cli/invocation/`
- [ ] `coverage report` shows ≥ 90% for invocation package
- [ ] `spec-kitty profiles list --json` returns valid JSON on a project with shipped profiles

---

## Definition of Done

- [ ] `src/specify_cli/invocation/` package exists with all 5 modules (+ `__init__.py`)
- [ ] `src/specify_cli/cli/commands/profiles_cmd.py` exists and is registered in `main.py`
- [ ] All T007 tests pass
- [ ] `mypy --strict` passes for all new files
- [ ] `spec-kitty profiles list --json` exits 0 and returns a JSON array

## Risks

- **ULID import style**: confirm exact import from `src/specify_cli/status/models.py` before implementing executor.
- **Repo root resolution**: use the project's existing utility — do not invent a new one.
- **`mark_loaded=False`**: if this flag is accidentally dropped during refactoring, first-load state for `specify`/`plan` will be corrupted. The test `test_invoke_mark_loaded_false` is the regression guard.

## Reviewer Guidance

1. Verify `mark_loaded=False` is passed in every `build_charter_context` call.
2. Verify `write_started` uses `"x"` mode (exclusive create), not `"w"` (overwrite).
3. Verify `ActionRouterPlugin` Protocol has no methods (it is a stub for WP02's extension).
4. Verify `spec-kitty profiles list --json` output has all 5 required fields per descriptor.
5. Verify no test makes a live charter context call (use fixture profiles only).
