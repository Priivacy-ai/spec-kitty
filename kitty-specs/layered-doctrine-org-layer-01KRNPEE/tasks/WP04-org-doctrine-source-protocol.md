---
work_package_id: WP04
title: OrgDoctrineSource Protocol and Implementations
dependencies:
- WP01
- WP03
requirement_refs:
- C-001
- C-002
- C-005
- FR-007
- FR-008
- FR-009
- FR-010
- FR-011
- FR-020
- FR-021
- NFR-001
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
- T021
agent: "claude:opus-4-7:python-pedro:implementer"
shell_pid: "572399"
history:
- date: '2026-05-15'
  event: created
agent_profile: architect-alphonso
authoritative_surface: src/specify_cli/doctrine/sources/
execution_mode: code_change
owned_files:
- src/specify_cli/doctrine/__init__.py
- src/specify_cli/doctrine/sources/__init__.py
- src/specify_cli/doctrine/sources/protocol.py
- src/specify_cli/doctrine/sources/git_source.py
- src/specify_cli/doctrine/sources/https_source.py
- src/specify_cli/doctrine/sources/api_source.py
- src/specify_cli/doctrine/snapshot.py
- tests/specify_cli/doctrine/__init__.py
- tests/specify_cli/doctrine/test_sources.py
- tests/specify_cli/doctrine/test_snapshot.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load architect-alphonso
```

This WP involves defining the extensible fetch-source protocol. The architect profile helps
ensure the interface design is clean and forward-compatible.

---

## Objective

Create the `src/specify_cli/doctrine/` package with:
- `OrgDoctrineSource` Protocol and `FetchResult` dataclass
- Three concrete source implementations: `GitSource`, `HttpsBundleSource`, `ApiSource`
- `snapshot.py` with atomic write and `pack-manifest.yaml` generation

All fetch operations write to a local snapshot directory and terminate the network call
before returning. Resolution reads only from the local snapshot.

---

## Context

This WP creates a new Python package `src/specify_cli/doctrine/` — the home for all
doctrine fetch/pack tooling. It has no dependencies on WP01–WP03 (which modify the
`doctrine/` and `charter/` packages) and can proceed in parallel.

The `OrgDoctrineSource` is a structural `typing.Protocol` (not an ABC). Any object with
a `fetch(target_dir: Path) -> FetchResult` method satisfies it. This design enables
third-party source implementations without inheritance.

See `contracts/org-doctrine-source-api-contract.md` for the HTTP API protocol that
`ApiSource` must implement.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Implement command**: `spec-kitty agent action implement WP04 --agent claude:sonnet-4-6`

---

## Subtask T016 — Define `OrgDoctrineSource` Protocol and `FetchResult`

**File**: `src/specify_cli/doctrine/sources/protocol.py`

```python
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

@dataclass
class FetchResult:
    ok: bool
    artifacts_written: int
    pack_version: str | None
    errors: list[str] = field(default_factory=list)

@runtime_checkable
class OrgDoctrineSource(Protocol):
    """Fetch-time source adapter for org doctrine packs.

    Implementations pull governance artifacts from a remote location and
    write a validated snapshot to *target_dir*. No network calls are made
    after this method returns.
    """
    def fetch(self, target_dir: Path) -> FetchResult: ...
```

Also create `src/specify_cli/doctrine/__init__.py` and
`src/specify_cli/doctrine/sources/__init__.py` (empty or with minimal exports).

---

## Subtask T017 — Implement `GitSource`

**File**: `src/specify_cli/doctrine/sources/git_source.py`

```python
class GitSource:
    def __init__(self, url: str, ref: str | None = None): ...
    def fetch(self, target_dir: Path) -> FetchResult: ...
```

**`GitSource` is a persistent clone manager, not a one-shot copier.** The `.git/` directory
is preserved; `target_dir` IS the working repository. The atomic write pattern in
`snapshot.py` does NOT apply to git sources — git provides its own consistency.

**Implementation steps**:

*First install* (`target_dir` does not contain `.git/`):
1. Run `git clone <url> <target_dir>` via `subprocess.run()`.
2. If `ref` is set: run `git -C <target_dir> checkout <ref>`.
3. On non-zero exit: remove `target_dir` if partially created; return `FetchResult(ok=False, errors=[stderr])`.

*Subsequent update* (`(target_dir / ".git").exists()`):
1. Run `git -C <target_dir> fetch --tags origin`.
2. Run `git -C <target_dir> reset --hard <ref>` if `ref` set, else `git reset --hard origin/HEAD`.
3. On non-zero exit: do NOT modify `target_dir`; return `FetchResult(ok=False, errors=[stderr])`. The existing clone remains usable.

**Authentication**: SSH keys and git credential helpers via the system git config. If
`GIT_TOKEN` env var is set and the URL is HTTPS, inject via
`url.replace("https://", f"https://oauth2:{token}@")` before the git call.

**Pack version**: `git -C <target_dir> describe --tags --always` after a successful clone
or reset. This is the canonical version string — no separate `pack-manifest.yaml` is written
for git sources.

**`artifacts_written`**: count of `*.yaml` files under `target_dir` (excluding `.git/`).

---

## Subtask T018 — Implement `HttpsBundleSource`

**File**: `src/specify_cli/doctrine/sources/https_source.py`

```python
class HttpsBundleSource:
    def __init__(self, url: str, ref: str | None = None): ...
    def fetch(self, target_dir: Path) -> FetchResult: ...
```

**Implementation steps**:
1. Build the request: `GET <url>` with `Authorization: Bearer <SPEC_KITTY_ORG_TOKEN>` if
   the env var is set.
2. Stream response to a temp file (`NamedTemporaryFile`).
3. Detect format from `Content-Type` or URL suffix: `.tar.gz` → `tarfile`, `.zip` → `zipfile`.
4. Extract to `target_dir`.
5. Return `FetchResult` with `pack_version` from `ref` or response `ETag` header.

**Error handling**: 401/403 → `FetchResult(ok=False, errors=["Authentication failed. Set SPEC_KITTY_ORG_TOKEN."])`.
4xx (other) → include status code in error. 5xx → retry once after 2s; fail with error.

---

## Subtask T019 — Implement `ApiSource`

**File**: `src/specify_cli/doctrine/sources/api_source.py`

Follows `contracts/org-doctrine-source-api-contract.md` exactly.

```python
class ApiSource:
    def __init__(self, url: str, ref: str | None = None): ...
    def fetch(self, target_dir: Path) -> FetchResult: ...
```

**Implementation steps**:
1. Build auth header: `Authorization: Bearer <SPEC_KITTY_ORG_TOKEN>` or
   use `SPEC_KITTY_ORG_AUTH_HEADER` verbatim if set.
2. `GET /artifact-types` → list of artifact type names. 404 → use hardcoded default list
   (all 8 types).
3. For each artifact type: `GET /artifacts/{artifact_type}` → write each item's `content`
   to `target_dir/<artifact_type>/<filename>`.
4. `GET /drg-extensions` → write each fragment to `target_dir/drg/<filename>`. 404 → skip.
5. `GET /version` → capture as `pack_version`. 404 → use response date.
6. Create all required parent directories before writing files.
7. Return `FetchResult(ok=True, ...)` with total artifact count and pack_version.

**Error handling**: Per `contracts/org-doctrine-source-api-contract.md` §Error handling.
401/403 → `ok=False` with credential error and remediation hint.
429 → retry once after `Retry-After` seconds.
5xx / network error → `ok=False` with error detail.

---

## Subtask T020 — Implement `snapshot.py`

**File**: `src/specify_cli/doctrine/snapshot.py`

Two responsibilities (for non-git sources only — `GitSource` manages its own target_dir):
1. **Atomic write**: write to a temp dir, validate, rename to `local_path`.
2. **Pack manifest**: write `pack-manifest.yaml` to `local_path` after atomic rename.

`GitSource` does NOT use `write_snapshot`. It manages `target_dir` directly via git
subprocess calls (see T017). `snapshot.py` is used by `HttpsBundleSource` and `ApiSource`.

```python
def write_snapshot(
    source: OrgDoctrineSource,
    local_path: Path,
) -> FetchResult:
    """Fetch from *source* into a temp dir, validate, atomically move to *local_path*."""
    ...

def write_pack_manifest(local_path: Path, result: FetchResult, source_url: str) -> None:
    """Write pack-manifest.yaml into *local_path* after a successful fetch."""
    ...
```

**Atomic write pattern**:
1. Create `tmp_dir = local_path.parent / f".tmp-{uuid4()}"`.
2. Call `source.fetch(tmp_dir)` → `FetchResult`.
3. If `result.ok` is False: `shutil.rmtree(tmp_dir, ignore_errors=True)`, return result.
4. Run basic validation: check that at least one recognized artifact directory exists. If
   not: rmtree tmp_dir, return `FetchResult(ok=False, errors=["No artifact directories found"])`.
5. If existing `local_path` exists: `shutil.rmtree(local_path)`.
6. `shutil.move(str(tmp_dir), str(local_path))`.
7. Call `write_pack_manifest(local_path, result, source_url)`.
8. Return result.

**`pack-manifest.yaml` format**:
```yaml
pack_version: "v1.2.0"
fetched_at: "2026-05-15T11:30:00Z"
source_type: git
source_url: "git@example.com:org/doctrine.git"
artifact_counts:
  directives: 12
  agent_profiles: 8
```
`source_url` strips credentials before writing.

---

## Subtask T021 — Unit tests for sources and snapshot

**Files**: `tests/specify_cli/doctrine/test_sources.py`, `test_snapshot.py`

**`test_sources.py`**:

| Test | Approach | Expected |
|---|---|---|
| `test_git_source_first_install` | `target_dir` has no `.git/`; mock `git clone` success | `FetchResult.ok=True`; `target_dir/.git/` present |
| `test_git_source_update` | `target_dir` has `.git/`; mock `git fetch + reset` success | `FetchResult.ok=True`; runs fetch+reset not clone |
| `test_git_source_failure_first_install` | Mock `git clone` non-0 exit | `FetchResult.ok=False`; `target_dir` cleaned up |
| `test_git_source_failure_update` | Mock `git fetch` non-0 exit | `FetchResult.ok=False`; existing clone unchanged |
| `test_git_source_token_injected` | Set `GIT_TOKEN` env var; HTTPS URL | URL transformed before subprocess call |
| `test_git_source_version_from_describe` | Mock `git describe` output | `FetchResult.pack_version` matches describe output |
| `test_https_source_tar_gz` | Mock `requests.get`; provide tar.gz fixture | Files extracted to target_dir |
| `test_https_source_401` | Mock 401 response | `FetchResult.ok=False` with auth error |
| `test_https_source_429_retry` | Mock 429 then 200 | Retries once and succeeds |
| `test_api_source_full_flow` | Mock all API endpoints | All artifact types written; drg/ written |
| `test_api_source_no_drg` | Mock `/drg-extensions` returning 404 | No drg/ dir; `ok=True` |
| `test_api_source_auth_header` | Set `SPEC_KITTY_ORG_AUTH_HEADER` | Custom header used in requests |

**`test_snapshot.py`**:

| Test | Expected |
|---|---|
| `test_atomic_write_success` | `local_path` exists after success; tmp_dir removed |
| `test_atomic_write_fetch_failure` | `local_path` unchanged; tmp_dir removed |
| `test_atomic_write_replaces_existing` | Old `local_path` replaced atomically |
| `test_pack_manifest_written` | `pack-manifest.yaml` exists in `local_path`; contains pack_version |

---

## Definition of Done

- [ ] `OrgDoctrineSource` Protocol defined with `runtime_checkable`
- [ ] `FetchResult` dataclass defined with all fields
- [ ] `GitSource`, `HttpsBundleSource`, `ApiSource` all implement `OrgDoctrineSource` Protocol
- [ ] `snapshot.py` provides `write_snapshot()` with atomic write guarantee
- [ ] All tests in `test_sources.py` and `test_snapshot.py` pass
- [ ] `isinstance(git_source, OrgDoctrineSource)` returns `True` (runtime_checkable)

## Risks

- `GitSource` subprocess invocation must handle stdout/stderr correctly (git may write to
  stderr even on success). Use `capture_output=True` and check `returncode`.
- Tarball extraction must handle both `tar.gz` (which may have a top-level directory) and
  `zip` (which may not). Normalize by always extracting contents to `target_dir` directly.
- `ApiSource` must create subdirectories before writing artifact files; `GET /artifacts/directives`
  may return 0 items for some types — handle empty lists gracefully.

## Reviewer Guidance

1. Verify `isinstance()` check works for all three concrete implementations.
2. Confirm atomic write: simulate a `fetch()` failure midway through and verify `local_path`
   is unchanged.
3. Confirm `SPEC_KITTY_ORG_TOKEN` is not logged or written anywhere (security).

## Activity Log

- 2026-05-15T13:31:54Z – claude:opus-4-7:python-pedro:implementer – shell_pid=572399 – Started implementation via action command
