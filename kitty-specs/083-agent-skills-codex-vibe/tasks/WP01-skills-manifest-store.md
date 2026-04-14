---
work_package_id: WP01
title: Skills Manifest Store and Schema Plumbing
lane: "done"
dependencies: []
base_branch: main
base_commit: 18378e6761899dffe69c92e849d6b4140d19b2a3
created_at: '2026-04-14T09:48:35.942061+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "opus"
shell_pid: '3815'
reviewed_by: "unknown"
review_status: "approved"
history:
- at: '2026-04-14T00:00:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/skills/
branch_strategy: lane-worktree
execution_mode: code_change
merge_target_branch: main
owned_files:
- src/specify_cli/skills/manifest_store.py
- src/specify_cli/skills/manifest_errors.py
- src/specify_cli/skills/data/skills-manifest.schema.json
- tests/specify_cli/skills/test_manifest_store.py
planning_base_branch: main
requirement_refs:
- FR-007
---

# WP01 — Skills Manifest Store and Schema Plumbing

## Objective

Deliver a pure, well-tested persistence layer for `.kittify/skills-manifest.json`. This is the foundation that WP03 (installer) and WP06 (migration) depend on. It must be completable and verifiable in isolation — no renderer, no installer, no CLI wiring.

## Context

The mission introduces an ownership manifest for Spec Kitty's contributions to `.agents/skills/`. The full design is in `kitty-specs/083-agent-skills-codex-vibe/plan.md` and `data-model.md`; the schema is frozen at `kitty-specs/083-agent-skills-codex-vibe/contracts/skills-manifest.schema.json`.

Key invariants this WP must enforce:
- The on-disk file format is JSON with `schema_version: 1`, sorted keys, 2-space indent, and a trailing newline.
- Entries are sorted by `path` so diffs are deterministic.
- Unknown future top-level fields are tolerated with a warning (forward-compatible), but known fields are strictly typed.
- Loading a malformed manifest raises a structured `ManifestError` with a code the CLI can format.
- Writes are atomic (write to temp file, `os.replace`) so a crash mid-write cannot leave a corrupt file.

This WP does not yet *use* the manifest for anything — it just guarantees the API is correct and the persistence is trustworthy.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per lane from `lanes.json` after `finalize-tasks` runs. Likely lane A given this is foundation work.

## Implementation

### Subtask T001 — Create `manifest_store.py` with dataclasses and `ManifestError`

Create `src/specify_cli/skills/manifest_store.py`. Define:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SCHEMA_VERSION = 1

@dataclass(frozen=True)
class ManifestEntry:
    path: str                      # POSIX-style, relative to repo root
    content_hash: str              # 64-char lowercase hex SHA-256
    agents: tuple[str, ...]        # sorted, no duplicates
    installed_at: str              # ISO-8601 UTC
    spec_kitty_version: str

    def with_agent_added(self, agent_key: str) -> "ManifestEntry": ...
    def with_agent_removed(self, agent_key: str) -> "ManifestEntry": ...

@dataclass
class SkillsManifest:
    schema_version: int = SCHEMA_VERSION
    entries: list[ManifestEntry] = field(default_factory=list)

    def find(self, path: str) -> ManifestEntry | None: ...
    def upsert(self, entry: ManifestEntry) -> None: ...
    def remove_path(self, path: str) -> None: ...
```

Put the exception type in a sibling file `src/specify_cli/skills/manifest_errors.py` so other modules (installer, migration, doctor) can import it without pulling the whole manifest store API:

```python
class ManifestError(Exception):
    def __init__(self, code: str, **context):
        self.code = code
        self.context = context
        super().__init__(f"{code}: {context}")
```

Codes to support: `"unsupported_schema_version"`, `"schema_validation_failed"`, `"corrupt_json"`, `"duplicate_path"`.

### Subtask T002 — Implement schema validation on `load()`

Ship a copy of `contracts/skills-manifest.schema.json` at `src/specify_cli/skills/data/skills-manifest.schema.json` so the running CLI has it in its package resources. Load it with `importlib.resources`. Use the existing `jsonschema` dependency if it's already in `pyproject.toml`; if not, use a small hand-rolled validator keyed on the specific fields in the schema (prefer adding `jsonschema` as a dep only if nothing else in the repo already provides validation — grep for `jsonschema` before adding).

`load(repo_root: Path) -> SkillsManifest`:
- If `.kittify/skills-manifest.json` does not exist, return `SkillsManifest(schema_version=1, entries=[])`.
- Read and parse JSON. On `json.JSONDecodeError`, raise `ManifestError("corrupt_json", path=..., detail=...)`.
- Reject `schema_version != 1` with `ManifestError("unsupported_schema_version", found=...)`.
- Validate against the JSON schema. On failure, raise `ManifestError("schema_validation_failed", errors=[...])` with a list of human-readable messages.
- Deserialize into `ManifestEntry` records (coerce `agents` list → tuple).
- Detect duplicate `path` values and raise `ManifestError("duplicate_path", path=...)`.
- Return the `SkillsManifest`.

### Subtask T003 — Implement atomic save with deterministic formatting

`save(repo_root: Path, manifest: SkillsManifest) -> None`:
- Validate the manifest against the schema before writing. If invalid, raise — do not write a bad file.
- Sort `manifest.entries` by `path` ascending before serialization.
- Serialize with `json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)`. Append `"\n"`.
- Write to `<path>.tmp` in the same directory, `os.fsync` it, then `os.replace(tmp, final)`.
- Ensure `.kittify/` exists (create with `parents=True, exist_ok=True`).

### Subtask T004 — Implement `fingerprint()` SHA-256 helper [P]

`fingerprint(content: bytes) -> str` returns the lowercase hex digest of the SHA-256 of the input bytes. Kept as a module-level helper so the installer, renderer snapshot tests, and migration can all share the exact same hashing routine.

Also export a convenience `fingerprint_file(path: Path) -> str` that reads bytes and hashes them. Do not follow symlinks outside the repo root.

### Subtask T005 — Unit tests

Create `tests/specify_cli/skills/test_manifest_store.py`:

- **Round-trip identity**: build a `SkillsManifest` with three entries in an arbitrary order, `save`, re-`load`, assert equality (entries sorted by path).
- **Absent file**: `load()` on a repo with no `.kittify/` returns an empty manifest.
- **Schema version mismatch**: craft a JSON file with `schema_version: 2`, assert `ManifestError("unsupported_schema_version")`.
- **Schema validation**: craft a JSON file missing required field `content_hash`, assert `ManifestError("schema_validation_failed")` with a message referencing that field.
- **Duplicate path**: craft a JSON file with two entries sharing the same path, assert `ManifestError("duplicate_path", path=...)`.
- **Atomic save durability**: monkeypatch `os.replace` to raise after `os.fsync`, assert that the pre-existing manifest file (if any) is unchanged and that the `.tmp` file is cleaned up on failure. (If cleanup is hard to guarantee atomically, acceptable fallback is asserting the final file stays intact.)
- **Fingerprint stability**: `fingerprint(b"hello")` equals the known SHA-256 digest of `"hello"`. Running it twice on the same bytes returns the same value.
- **Forward-compatibility**: a JSON file with an unknown top-level field (e.g. `"comment": "hi"`) loads successfully, and a subsequent save drops the unknown field (document this behavior in the function docstring).

All tests must run without network, without `jsonschema` installed if we chose the hand-rolled path (adjust test skip markers accordingly).

## Definition of Done

- [ ] `src/specify_cli/skills/manifest_store.py` and `src/specify_cli/skills/manifest_errors.py` exist with the API described above.
- [ ] `src/specify_cli/skills/data/skills-manifest.schema.json` is present and bit-for-bit equal to `contracts/skills-manifest.schema.json`.
- [ ] `pytest tests/specify_cli/skills/test_manifest_store.py` passes.
- [ ] `ruff check src/specify_cli/skills/` passes.
- [ ] No new third-party dependency introduced unless already present (document the choice in the module docstring).
- [ ] Module docstring lists the invariants from §Context.
- [ ] No changes to files outside `owned_files`.

## Risks

- **JSON schema library choice.** If `jsonschema` is not already a dep, a hand-rolled validator is acceptable — but it must cover every constraint in the schema (types, enum, pattern, `additionalProperties: false`, `required`). Under-validating breaks the trust model of the manifest.
- **Atomic save on Windows.** `os.replace` is atomic on POSIX and Windows NTFS, but the temp file must live in the same directory as the target. The implementation must not drop the temp in `/tmp`.
- **Tuple vs list for `agents`.** `ManifestEntry` is frozen with a tuple for hashability; the JSON representation is a list. The load/save boundary must consistently coerce between the two.

## Reviewer Guidance

- Confirm the schema file in `data/` matches the one in `contracts/` byte-for-byte.
- Confirm the atomic-save test actually exercises the failure path, not a happy path in disguise.
- Confirm that `SkillsManifest.upsert` replaces entries by path rather than appending duplicates.
- Look for accidental mutation of a loaded manifest — `ManifestEntry` should be frozen; mutations happen via the `with_*` helpers returning new records.

## Command to run implementation

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Activity Log

- 2026-04-14T10:04:21Z – claude – shell_pid=3815 – lane=for_review – Implementation complete; ready for review
- 2026-04-14T10:06:05Z – opus – shell_pid=3815 – lane=done – Review passed: schema byte-identical to contract, 37 tests pass including atomic-save failure and forward-compat warnings, ruff clean on owned files, ManifestEntry is frozen with with_* helpers, atomic save uses os.replace with fsync + tmp cleanup, entries sorted by path on save, fingerprint/fingerprint_file share hashlib.sha256.
