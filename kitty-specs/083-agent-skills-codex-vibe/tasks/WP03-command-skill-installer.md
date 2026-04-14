---
work_package_id: WP03
title: Command-Skill Installer (additive, reference-counted)
lane: "for_review"
dependencies:
- WP01
- WP02
base_branch: main
base_commit: d1d0857f1ac74e6f1715fb7139ed7a4b5a5a8e5b
created_at: '2026-04-14T10:07:03.376981+00:00'
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
shell_pid: '9377'
agent: "claude"
history:
- at: '2026-04-14T00:00:00+00:00'
  actor: planner
  event: created
authoritative_surface: src/specify_cli/skills/command_installer.py
branch_strategy: lane-worktree
execution_mode: code_change
merge_target_branch: main
owned_files:
- src/specify_cli/skills/command_installer.py
- tests/specify_cli/skills/test_command_installer.py
planning_base_branch: main
requirement_refs:
- FR-006
- FR-008
- NFR-002
---

# WP03 — Command-Skill Installer

## Objective

Deliver the installer that owns the mutations of `.agents/skills/` for Codex and Vibe. Install is additive and idempotent; remove is reference-counted; verify surfaces drift, orphans, and gaps. Third-party subdirectories under `.agents/skills/` must remain byte-identical through any install or remove operation.

## Context

This is the load-bearing module for NFR-002 (shared-root coexistence across three-plus agents) and FR-008 (selective remove). The contract is frozen at `kitty-specs/083-agent-skills-codex-vibe/contracts/skill-renderer.contract.md` (§Module: `command_installer`). Read it before starting.

Inputs:
- `command_renderer.render()` from WP02 — returns a `RenderedSkill` with frontmatter + body.
- `manifest_store.load/save/fingerprint()` from WP01 — provides persistence and hashing.

Output:
- Files written under `<repo>/.agents/skills/spec-kitty.<command>/SKILL.md`.
- Updated `<repo>/.kittify/skills-manifest.json`.

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution worktree: allocated per lane from `lanes.json` after `finalize-tasks`. Expected to follow WP01+WP02 into the same or an adjacent lane; `finalize-tasks` will compute.

## Implementation

### Subtask T012 — Create `command_installer.py` with report dataclasses

Create `src/specify_cli/skills/command_installer.py`:

```python
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

SUPPORTED_AGENTS = ("codex", "vibe")
CANONICAL_COMMANDS = (
    "specify", "plan", "tasks", "tasks-outline", "tasks-packages",
    "tasks-finalize", "implement", "review", "accept", "merge",
    "analyze", "research", "checklist", "status", "dashboard", "charter",
)

@dataclass
class InstallReport:
    added: list[str] = field(default_factory=list)
    already_installed: list[str] = field(default_factory=list)
    reused_shared: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

@dataclass
class RemoveReport:
    deref: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)

@dataclass
class VerifyReport:
    drift: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)

class InstallerError(Exception):
    def __init__(self, code: str, **context): ...
```

Error codes: `manifest_parse_failed`, `unexpected_collision`, `manifest_entry_not_found`, `file_mutation_detected`.

### Subtask T013 — Implement `install(repo_root, agent_key)`

Pseudo-code (see §Module: `command_installer` in the contract for authoritative behavior):

```python
def install(repo_root: Path, agent_key: str) -> InstallReport:
    if agent_key not in SUPPORTED_AGENTS:
        raise InstallerError("unsupported_agent", agent_key=agent_key)

    manifest = manifest_store.load(repo_root)
    report = InstallReport()

    for command in CANONICAL_COMMANDS:
        template = _resolve_template(repo_root, command)   # mission-dir resolution
        rendered = command_renderer.render(template, agent_key, VERSION)
        skill_md_bytes = rendered.to_skill_md().encode("utf-8")
        rel_path = f".agents/skills/spec-kitty.{command}/SKILL.md"
        abs_path = repo_root / rel_path

        existing = manifest.find(rel_path)

        if existing is not None:
            # Drift check: if the file on disk doesn't match the manifest hash, error.
            on_disk_hash = manifest_store.fingerprint_file(abs_path) if abs_path.exists() else None
            if on_disk_hash != existing.content_hash:
                raise InstallerError("unexpected_collision", path=rel_path)
            # Idempotent: same bytes we'd write?
            would_write_hash = manifest_store.fingerprint(skill_md_bytes)
            if existing.content_hash == would_write_hash:
                if agent_key in existing.agents:
                    report.already_installed.append(rel_path)
                else:
                    manifest.upsert(existing.with_agent_added(agent_key))
                    report.reused_shared.append(rel_path)
                continue
            # Content changed (template updated this release): rewrite the file.
            _atomic_write(abs_path, skill_md_bytes)
            manifest.upsert(ManifestEntry(
                path=rel_path,
                content_hash=would_write_hash,
                agents=tuple(sorted(set(existing.agents) | {agent_key})),
                installed_at=existing.installed_at,
                spec_kitty_version=VERSION,
            ))
            report.added.append(rel_path)  # content update counts as "added"
        else:
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(abs_path, skill_md_bytes)
            content_hash = manifest_store.fingerprint(skill_md_bytes)
            manifest.upsert(ManifestEntry(
                path=rel_path,
                content_hash=content_hash,
                agents=(agent_key,),
                installed_at=_now_utc_iso(),
                spec_kitty_version=VERSION,
            ))
            report.added.append(rel_path)

    manifest_store.save(repo_root, manifest)
    return report
```

`_atomic_write(path, bytes)`: temp file in same dir, `os.fsync`, `os.replace`.

### Subtask T014 — Implement `remove(repo_root, agent_key)`

```python
def remove(repo_root: Path, agent_key: str) -> RemoveReport:
    manifest = manifest_store.load(repo_root)
    report = RemoveReport()

    for entry in list(manifest.entries):
        if agent_key not in entry.agents:
            continue
        new_agents = tuple(a for a in entry.agents if a != agent_key)
        abs_path = repo_root / entry.path

        # Drift check before mutating disk.
        if abs_path.exists():
            on_disk_hash = manifest_store.fingerprint_file(abs_path)
            if on_disk_hash != entry.content_hash:
                raise InstallerError("file_mutation_detected", path=entry.path)

        if new_agents:
            manifest.upsert(entry.with_agent_removed(agent_key))
            report.deref.append(entry.path)
            report.kept.append(entry.path)
        else:
            # Physically remove the file. Remove the parent dir only if empty
            # AFTER the file is gone — that preserves third-party co-tenants.
            if abs_path.exists():
                abs_path.unlink()
            parent = abs_path.parent
            if parent.exists() and not any(parent.iterdir()):
                parent.rmdir()
            manifest.remove_path(entry.path)
            report.deref.append(entry.path)
            report.deleted.append(entry.path)

    manifest_store.save(repo_root, manifest)
    return report
```

### Subtask T015 — Implement `verify(repo_root)` [P]

Read-only. Never mutate:

```python
def verify(repo_root: Path) -> VerifyReport:
    manifest = manifest_store.load(repo_root)
    report = VerifyReport()

    manifest_paths = {e.path for e in manifest.entries}

    for entry in manifest.entries:
        abs_path = repo_root / entry.path
        if not abs_path.exists():
            report.gaps.append(entry.path)
            continue
        on_disk = manifest_store.fingerprint_file(abs_path)
        if on_disk != entry.content_hash:
            report.drift.append(entry.path)

    # Orphan scan: only under `.agents/skills/spec-kitty.*/`
    skills_root = repo_root / ".agents" / "skills"
    if skills_root.exists():
        for subdir in skills_root.iterdir():
            if not subdir.is_dir() or not subdir.name.startswith("spec-kitty."):
                continue
            for file in subdir.rglob("*"):
                if not file.is_file():
                    continue
                rel = str(file.relative_to(repo_root)).replace("\\", "/")
                if rel not in manifest_paths:
                    report.orphans.append(rel)

    return report
```

### Subtask T016 — Coexistence tests

Create `tests/specify_cli/skills/test_command_installer.py`. Key tests:

- **Happy path install**: fresh tmpdir, run `install("vibe")`, assert 16 `SKILL.md` files exist, manifest has 16 entries, each entry's `agents == ("vibe",)`.
- **Idempotent install**: run `install("vibe")` twice; second call's `InstallReport.already_installed` has 16 entries and nothing else was modified on disk (compare mtimes or byte contents).
- **Reused-shared add**: `install("codex")`, then `install("vibe")`; assert 16 entries with `agents == ("codex", "vibe")` (sorted); files on disk are unchanged bytes (SHA-256 stable).
- **Three-tenant coexistence**: before any install, seed `.agents/skills/` with three third-party directories:
  - `.agents/skills/handwritten-review/SKILL.md` with contents `"# handwritten review\n"`
  - `.agents/skills/another-tool.lint/SKILL.md`
  - `.agents/skills/my-stuff/other-file.txt`

  Hash each file. Run `install("codex")` + `install("vibe")` + `remove("codex")` + `remove("vibe")`. After each step, re-hash the three seed files and assert byte-identity. Assert Spec Kitty's manifest is empty at the end and `.agents/skills/spec-kitty.*/` is gone.
- **Parent-dir preservation**: in a test where the canonical skill dir contains a third-party file (e.g., `.agents/skills/spec-kitty.specify/extra.txt` that the user authored), `remove()` must delete `SKILL.md` (if `agents` emptied) but leave `extra.txt` and the parent dir. This is a defensive test — in practice we don't expect tenants inside our own skill dirs — but the installer's parent-dir logic must handle it.
- **Collision error**: seed a stale manifest entry whose on-disk hash does not match; `install()` raises `InstallerError("unexpected_collision", path=...)`.
- **File mutation on remove**: install, then edit the installed file by hand; `remove()` raises `InstallerError("file_mutation_detected", path=...)` and the manifest is unchanged.

### Subtask T017 — Drift integration test

Add to the same test file or a sibling `test_command_installer_verify.py`:

- Install, mutate `SKILL.md` on disk, run `verify()`, assert `VerifyReport.drift == [<path>]` and `orphans == []` and `gaps == []`.
- Install, delete `SKILL.md` on disk, run `verify()`, assert `gaps == [<path>]`.
- Write a Spec-Kitty-named file not in the manifest (e.g., `.agents/skills/spec-kitty.unknown/SKILL.md`), run `verify()`, assert `orphans` contains it.

## Definition of Done

- [ ] `src/specify_cli/skills/command_installer.py` exists with `install`, `remove`, `verify`, `InstallerError`, and the three report dataclasses.
- [ ] `pytest tests/specify_cli/skills/test_command_installer.py` passes.
- [ ] The three-tenant coexistence test specifically asserts byte-identity via SHA-256, not just `st_mtime` or file existence.
- [ ] `ruff check src/specify_cli/skills/` passes.
- [ ] No new third-party dependencies.
- [ ] No changes to files outside `owned_files`.
- [ ] Every pathway that could touch disk uses atomic write or single-file unlink; no bulk `shutil.rmtree` under `.agents/skills/` anywhere.

## Risks

- **Parent-dir cleanup race.** Between the file unlink and the `rmdir`, another process could drop a file into our directory. The `rmdir` only succeeds on an empty dir, so the worst case is a benign failure we ignore — code the `rmdir` inside a `try: ... except OSError: pass`.
- **Hash-based collision detection on first install.** On a completely fresh project the file does not exist; no drift check is needed. On a re-install after manifest corruption, the collision path must surface a clear error rather than silently overwriting.
- **POSIX vs Windows path normalization.** Manifest paths are always POSIX (`/`-separated). When building `rel` for orphan detection, use `str(path.relative_to(repo_root)).replace("\\", "/")` on Windows.

## Reviewer Guidance

- Audit every `unlink()`, `rmtree()`, and `rmdir()` call. The installer must never call `rmtree` under `.agents/skills/`. The *only* directory it deletes is a specific `spec-kitty.<command>/` path, and only after confirming that directory is empty.
- Audit the idempotency path: two back-to-back `install("vibe")` calls produce zero file writes the second time.
- Confirm the coexistence test seeds *real* third-party file content (not just empty files) and uses SHA-256 to compare.

## Command to run implementation

```bash
spec-kitty agent action implement WP03 --agent <name>
```

## Activity Log

- 2026-04-14T10:14:23Z – claude – shell_pid=9377 – lane=for_review – Installer complete; coexistence test green
