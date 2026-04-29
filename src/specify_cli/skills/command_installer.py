"""Command-Skill Installer for Codex and Vibe.

This module owns all mutations under ``.agents/skills/`` for the Codex and Vibe
agents.  It wraps :mod:`specify_cli.skills.manifest_store` (WP01) and
:mod:`specify_cli.skills.command_renderer` (WP02) to provide three public
operations:

* :func:`install` — additive, idempotent, reference-counted.
* :func:`remove` — reference-counted; physical delete only when ``agents``
  list empties.
* :func:`verify` — read-only drift / orphan / gap scanner.

NFR-002 (shared-root coexistence)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Third-party directories and files under ``.agents/skills/`` are **never**
touched.  The installer only creates or deletes paths that appear in the
manifest, and the manifest only ever references files in
``spec-kitty.<command>/SKILL.md`` subdirectories.

No call to :func:`shutil.rmtree` or any recursive deletion exists in this
module.  The only directory removal is a targeted
``parent.rmdir()`` — which succeeds only on an empty directory.
"""

from __future__ import annotations

import contextlib
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from specify_cli.skills import manifest_store
from specify_cli.skills.manifest_store import ManifestEntry
from specify_cli.skills import command_renderer

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_AGENTS: tuple[str, ...] = ("codex", "vibe")

#: The canonical command templates that exist in the current codebase.
#: Matches the files under
#: ``src/specify_cli/missions/software-dev/command-templates/``.
#: ``checklist`` was retired in 3.2.0a5 (FR-003 / FR-004 / #815).
CANONICAL_COMMANDS: tuple[str, ...] = (
    "analyze",
    "charter",
    "implement",
    "plan",
    "research",
    "review",
    "specify",
    "tasks",
    "tasks-finalize",
    "tasks-outline",
    "tasks-packages",
)

def _package_templates_dir() -> Path:
    """Return the directory containing canonical command templates inside the
    installed ``specify_cli`` package.

    Templates ship as regular files inside the package directory (not inside a
    zipapp), so deriving their path from ``specify_cli.__file__`` yields a real
    :class:`pathlib.Path` that works identically in editable and wheel installs.
    """
    import specify_cli  # noqa: PLC0415 — deferred to avoid import-time side effects

    return (
        Path(specify_cli.__file__).parent
        / "missions"
        / "software-dev"
        / "command-templates"
    )


# ---------------------------------------------------------------------------
# Error type
# ---------------------------------------------------------------------------


class InstallerError(Exception):
    """Raised when an install, remove, or verify operation cannot complete safely.

    Attributes
    ----------
    code:
        Machine-readable error code.  One of:

        * ``"manifest_parse_failed"`` — manifest is corrupt; operator must
          resolve before retrying.
        * ``"unexpected_collision"`` — on-disk hash does not match the manifest
          entry hash during install.  Drift detected.
        * ``"manifest_entry_not_found"`` — ``remove()`` called for an agent
          with no matching manifest entries.
        * ``"file_mutation_detected"`` — on-disk hash does not match the
          manifest entry hash during remove.  Abort to preserve integrity.
        * ``"unsupported_agent"`` — ``agent_key`` not in
          :data:`SUPPORTED_AGENTS`.
    context:
        Additional diagnostic keyword arguments (path, agent_key, etc.).
    """

    def __init__(self, code: str, **context: Any) -> None:
        self.code = code
        self.context = context
        super().__init__(f"{code}: {context}")


# ---------------------------------------------------------------------------
# Report dataclasses
# ---------------------------------------------------------------------------


@dataclass
class InstallReport:
    """Summary of an :func:`install` operation.

    Attributes
    ----------
    added:
        Paths of files that were written to disk for the first time (or
        rewritten due to a template update).
    already_installed:
        Paths already in the manifest for this agent with matching hashes —
        no disk write occurred.
    reused_shared:
        Paths already on disk (installed by another agent) whose manifest
        entry gained *agent_key* in its ``agents`` tuple.
    errors:
        Human-readable error strings for non-fatal issues (empty unless a
        caller uses the error-collection path, which is reserved for future
        use).
    """

    added: list[str] = field(default_factory=list)
    already_installed: list[str] = field(default_factory=list)
    reused_shared: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class RemoveReport:
    """Summary of a :func:`remove` operation.

    Attributes
    ----------
    deref:
        Paths for which *agent_key* was removed from ``agents`` (covers both
        ``kept`` and ``deleted`` cases).
    deleted:
        Subset of ``deref`` whose ``agents`` list became empty — the file was
        physically deleted.
    kept:
        Subset of ``deref`` whose ``agents`` list is still non-empty — the
        file remains on disk, owned by the remaining agents.
    """

    deref: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)


@dataclass
class VerifyReport:
    """Summary of a :func:`verify` operation.

    Attributes
    ----------
    drift:
        Paths whose on-disk SHA-256 no longer matches the stored hash.
    orphans:
        Files under ``.agents/skills/spec-kitty.*/`` that are not in the
        manifest.
    gaps:
        Manifest entries whose files are missing from disk.
    """

    drift: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_template(repo_root: Path, command: str) -> Path:
    """Return the absolute path to the command template for *command*.

    Templates live inside the installed ``specify_cli`` package (not under the
    user's project root). ``repo_root`` is retained in the signature for call-site
    symmetry but is intentionally unused — the template location is package
    state, not project state.
    """
    del repo_root  # not used; kept for call-site consistency
    return _package_templates_dir() / f"{command}.md"


def _atomic_write(path: Path, content: bytes) -> None:
    """Write *content* to *path* atomically (temp-file + rename).

    Guarantees that a crashed write leaves at most a stale ``.tmp`` file
    behind, never a partially-written target.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        raise


def _now_utc_iso() -> str:
    """Return the current UTC time as an ISO-8601 string (with ``+00:00``)."""
    return datetime.now(tz=UTC).isoformat()


def _get_version() -> str:
    """Return the current Spec Kitty CLI version, or a dev fallback."""
    try:
        import specify_cli as _sk  # noqa: PLC0415

        return getattr(_sk, "__version__", "0.0.0-dev")
    except Exception:  # pragma: no cover
        return "0.0.0-dev"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def install(repo_root: Path, agent_key: str) -> InstallReport:
    """Install all canonical command skills for *agent_key*.

    This function is **idempotent**: running it twice for the same
    ``agent_key`` produces identical on-disk state and an identical manifest.

    It is also **additive**: third-party files under ``.agents/skills/`` are
    never modified, renamed, or deleted.

    Parameters
    ----------
    repo_root:
        Absolute path to the project root (the directory that contains
        ``.kittify/`` and ``.agents/``).
    agent_key:
        One of :data:`SUPPORTED_AGENTS` (``"codex"`` or ``"vibe"``).

    Returns
    -------
    InstallReport
        Breakdown of added / already_installed / reused_shared paths.

    Raises
    ------
    InstallerError("unsupported_agent")
        *agent_key* is not in :data:`SUPPORTED_AGENTS`.
    InstallerError("unexpected_collision")
        A manifest entry's on-disk hash does not match the stored hash (drift
        detected before we could safely proceed).
    InstallerError("manifest_parse_failed")
        The manifest file is corrupt and cannot be loaded.
    command_renderer.SkillRenderError
        Propagated from the renderer if a template is malformed or missing.
    """
    if agent_key not in SUPPORTED_AGENTS:
        raise InstallerError("unsupported_agent", agent_key=agent_key)

    try:
        manifest = manifest_store.load(repo_root)
    except Exception as exc:
        raise InstallerError("manifest_parse_failed", detail=str(exc)) from exc

    version = _get_version()
    report = InstallReport()

    for command in CANONICAL_COMMANDS:
        template = _resolve_template(repo_root, command)
        rendered = command_renderer.render(
            template, agent_key, version, repo_root=repo_root
        )
        skill_md_bytes = rendered.to_skill_md().encode("utf-8")
        rel_path = f".agents/skills/spec-kitty.{command}/SKILL.md"
        abs_path = repo_root / rel_path

        existing = manifest.find(rel_path)

        if existing is not None:
            # Drift check: on-disk hash must match the manifest record.
            on_disk_hash = (
                manifest_store.fingerprint_file(abs_path)
                if abs_path.exists()
                else None
            )
            if on_disk_hash != existing.content_hash:
                raise InstallerError("unexpected_collision", path=rel_path)

            # Compute the hash we *would* write.
            would_write_hash = manifest_store.fingerprint(skill_md_bytes)

            if existing.content_hash == would_write_hash:
                # Same bytes — either already claimed by this agent or shared.
                if agent_key in existing.agents:
                    report.already_installed.append(rel_path)
                else:
                    manifest.upsert(existing.with_agent_added(agent_key))
                    report.reused_shared.append(rel_path)
                continue

            # Template was updated this release — rewrite the file.
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(abs_path, skill_md_bytes)
            manifest.upsert(
                ManifestEntry(
                    path=rel_path,
                    content_hash=would_write_hash,
                    agents=tuple(sorted(set(existing.agents) | {agent_key})),
                    installed_at=existing.installed_at,
                    spec_kitty_version=version,
                )
            )
            report.added.append(rel_path)
        else:
            # New installation.
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(abs_path, skill_md_bytes)
            content_hash = manifest_store.fingerprint(skill_md_bytes)
            manifest.upsert(
                ManifestEntry(
                    path=rel_path,
                    content_hash=content_hash,
                    agents=(agent_key,),
                    installed_at=_now_utc_iso(),
                    spec_kitty_version=version,
                )
            )
            report.added.append(rel_path)

    manifest_store.save(repo_root, manifest)
    return report


def remove(repo_root: Path, agent_key: str) -> RemoveReport:
    """Remove *agent_key* from all manifest entries it owns.

    Physical file deletion occurs only when the entry's ``agents`` list
    becomes empty.  Files co-owned by other agents are left byte-identical
    on disk; only the ``agents`` list in the manifest is updated.

    The parent ``spec-kitty.<command>/`` directory is removed **only** when
    it is empty after the file deletion, preserving any third-party files the
    user may have placed there.

    Parameters
    ----------
    repo_root:
        Absolute path to the project root.
    agent_key:
        The agent to remove (``"codex"`` or ``"vibe"``).

    Returns
    -------
    RemoveReport
        Breakdown of deref / deleted / kept paths.

    Raises
    ------
    InstallerError("manifest_parse_failed")
        The manifest file is corrupt.
    InstallerError("file_mutation_detected")
        A file's on-disk hash differs from the manifest hash.  Removal is
        aborted for safety; the caller should run ``spec-kitty doctor`` to
        resolve.
    """
    try:
        manifest = manifest_store.load(repo_root)
    except Exception as exc:
        raise InstallerError("manifest_parse_failed", detail=str(exc)) from exc

    report = RemoveReport()

    for entry in list(manifest.entries):
        if agent_key not in entry.agents:
            continue

        abs_path = repo_root / entry.path

        # Drift check before mutating disk.
        if abs_path.exists():
            on_disk_hash = manifest_store.fingerprint_file(abs_path)
            if on_disk_hash != entry.content_hash:
                raise InstallerError(
                    "file_mutation_detected", path=entry.path
                )

        new_agents = tuple(a for a in entry.agents if a != agent_key)

        if new_agents:
            # Other agents still need this file — only update the manifest.
            manifest.upsert(entry.with_agent_removed(agent_key))
            report.deref.append(entry.path)
            report.kept.append(entry.path)
        else:
            # We are the last agent — physically remove the file.
            if abs_path.exists():
                abs_path.unlink()

            # Remove the parent dir only if it is empty after our deletion.
            # This preserves any third-party files the user placed in the dir.
            parent = abs_path.parent
            try:
                if parent.exists() and not any(parent.iterdir()):
                    parent.rmdir()
            except OSError:
                # Benign: another process wrote to the dir between our unlink
                # and the iterdir() check.  Leave the dir in place.
                pass

            manifest.remove_path(entry.path)
            report.deref.append(entry.path)
            report.deleted.append(entry.path)

    manifest_store.save(repo_root, manifest)
    return report


def verify(repo_root: Path) -> VerifyReport:
    """Scan for drift, orphans, and gaps without mutating anything.

    This function is read-only.  It never writes to the manifest or to the
    filesystem.

    Parameters
    ----------
    repo_root:
        Absolute path to the project root.

    Returns
    -------
    VerifyReport
        * ``drift``: entries whose on-disk SHA-256 no longer matches the
          stored hash.
        * ``orphans``: files under ``.agents/skills/spec-kitty.*/`` that are
          not recorded in the manifest.
        * ``gaps``: manifest entries whose files are absent from disk.

    Raises
    ------
    InstallerError("manifest_parse_failed")
        The manifest file is corrupt.
    """
    try:
        manifest = manifest_store.load(repo_root)
    except Exception as exc:
        raise InstallerError("manifest_parse_failed", detail=str(exc)) from exc

    report = VerifyReport()
    manifest_paths = {e.path for e in manifest.entries}

    # --- Drift and gaps -------------------------------------------------------
    for entry in manifest.entries:
        abs_path = repo_root / entry.path
        if not abs_path.exists():
            report.gaps.append(entry.path)
            continue
        on_disk = manifest_store.fingerprint_file(abs_path)
        if on_disk != entry.content_hash:
            report.drift.append(entry.path)

    # --- Orphan scan ----------------------------------------------------------
    # Only examine spec-kitty.* subdirectories under .agents/skills/.
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
