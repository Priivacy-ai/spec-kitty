"""Command-Skill Installer for shared-root command-skill agents.

This module owns all mutations under ``.agents/skills/`` for agents that consume
Spec Kitty slash commands as Agent Skills.  It wraps
:mod:`specify_cli.skills.manifest_store` (WP01) and
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
from pathlib import Path
from typing import Any

from specify_cli.skills import manifest_store
from specify_cli.skills.manifest_store import ManifestEntry
from specify_cli.skills import command_renderer
from specify_cli.skills._agent_roster import SUPPORTED_AGENTS as SUPPORTED_AGENTS
from specify_cli.agent_upgrade_prompt import prepend_agent_upgrade_check
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.shims.registry import CONSUMER_SKILLS

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Re-exported from the leaf authority :data:`specify_cli.skills._agent_roster`
#: so historical ``command_installer.SUPPORTED_AGENTS`` references keep working
#: while the roster has exactly one definition (#1941).

#: Commands installed as full prompt-backed Agent Skills.  These match the
#: step directories under ``src/doctrine/missions/mission-steps/software-dev/``.
#: ``checklist`` was retired in 3.2.0a5 (FR-003 / FR-004 / #815).
PROMPT_BACKED_COMMANDS: tuple[str, ...] = (
    "accept",
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

#: Commands installed as thin Agent Skills that delegate to the canonical CLI.
CLI_WRAPPER_COMMANDS: tuple[str, ...] = (
    "dashboard",
    "merge",
    "status",
)

#: The full consumer-facing command-skill set.
CANONICAL_COMMANDS: tuple[str, ...] = tuple(
    sorted((*PROMPT_BACKED_COMMANDS, *CLI_WRAPPER_COMMANDS))
)

assert set(CANONICAL_COMMANDS) == set(CONSUMER_SKILLS), (
    "Command-skill installer must cover every consumer command"
)

_CLI_WRAPPER_DESCRIPTIONS: dict[str, str] = {
    "dashboard": "Open the mission dashboard",
    "merge": "Merge an accepted mission",
    "status": "Show mission and work package status",
}

_CLI_WRAPPER_COMMANDS: dict[str, str] = {
    "dashboard": "spec-kitty dashboard",
    "merge": "spec-kitty merge",
    "status": "spec-kitty agent tasks status",
}

def _package_templates_dir(mission_type: str = "software-dev") -> Path:
    """Return the directory containing canonical command step directories inside
    the installed ``doctrine`` package.

    Templates ship as regular files inside the doctrine package under
    ``missions/mission-steps/<mission_type>/``.  Deriving the path from
    ``doctrine.__file__`` yields a real :class:`pathlib.Path` that works
    identically in editable and wheel installs.

    Parameters
    ----------
    mission_type:
        The mission type sub-directory to resolve (defaults to
        ``"software-dev"``).
    """
    import doctrine  # noqa: PLC0415 — deferred to avoid import-time side effects

    return (
        Path(doctrine.__file__).parent
        / "missions"
        / "mission-steps"
        / mission_type
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
        * ``"unsafe_path"`` — a managed path resolves outside ``repo_root``.
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
    stale:
        Manifest entries for command skills that are no longer canonical.
    unsafe:
        Manifest entries or orphan candidates that resolve outside
        ``repo_root`` through symlinks.
    """

    drift: list[str] = field(default_factory=list)
    orphans: list[str] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    unsafe: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_template(repo_root: Path, command: str) -> Path:
    """Return the absolute path to the command prompt template for *command*.

    Templates live inside the installed ``doctrine`` package (not under the
    user's project root). ``repo_root`` is retained in the signature for
    call-site symmetry but is intentionally unused — the template location is
    package state, not project state.

    New doctrine layout:
    ``doctrine/missions/mission-steps/<mission_type>/<step_id>/prompt.md``
    """
    del repo_root  # not used; kept for call-site consistency
    return _package_templates_dir() / command / "prompt.md"


def _render_command_skill(repo_root: Path, command: str, agent_key: str, version: str) -> bytes:
    """Return serialized SKILL.md bytes for a command skill."""
    if command in PROMPT_BACKED_COMMANDS:
        template = _resolve_template(repo_root, command)
        rendered = command_renderer.render(
            template, agent_key, version, repo_root=repo_root
        )
        return rendered.to_skill_md().encode("utf-8")

    if command not in CLI_WRAPPER_COMMANDS:
        raise InstallerError("unknown_command", command=command)

    description = _CLI_WRAPPER_DESCRIPTIONS[command]
    cli_command = _CLI_WRAPPER_COMMANDS[command]
    body = (
        f"# /spec-kitty.{command} - {description}\n\n"
        "## Purpose\n\n"
        "Run the canonical Spec Kitty CLI command for this workflow and treat "
        "its output as authoritative.\n\n"
        "Do not rediscover mission context from branches, files, prompt "
        "contents, or separate charter loads. If mission selection is required, "
        "pass `--mission <handle>` where `<handle>` is a mission_id, mid8, or "
        "mission_slug.\n\n"
        "## User Input\n\n"
        "The content of the user's message that invoked this skill is the User "
        "Input. Consider it before proceeding. If it contains CLI arguments, "
        "append them to the command below.\n\n"
        "## Steps\n\n"
        "Run this command from the repository root:\n\n"
        "```bash\n"
        f"{cli_command} <user-provided-args-if-any>\n"
        "```\n\n"
        "Report the command output and follow any next-step instructions it "
        "prints.\n"
    )
    body = prepend_agent_upgrade_check(body)
    skill_md = (
        "---\n"
        f"name: spec-kitty.{command}\n"
        f"description: {description}\n"
        "user-invocable: true\n"
        "---\n"
        f"{body if body.startswith(chr(10)) else chr(10) + body}"
    )
    return skill_md.encode("utf-8")


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


def _ensure_project_confined(repo_root: Path, rel_path: str, abs_path: Path) -> None:
    """Reject managed paths that escape the project root through symlinks."""
    repo_resolved = repo_root.resolve()
    try:
        resolved_target = abs_path.resolve(strict=False)
    except OSError as exc:
        raise InstallerError("unsafe_path", path=rel_path, detail=str(exc)) from exc

    if not resolved_target.is_relative_to(repo_resolved):
        raise InstallerError(
            "unsafe_path",
            path=rel_path,
            resolved=str(resolved_target),
            repo_root=str(repo_resolved),
        )


def _command_from_rel_path(rel_path: str) -> str | None:
    prefix = ".agents/skills/spec-kitty."
    suffix = "/SKILL.md"
    if not rel_path.startswith(prefix) or not rel_path.endswith(suffix):
        return None
    return rel_path[len(prefix) : -len(suffix)]


def _is_canonical_rel_path(rel_path: str) -> bool:
    command = _command_from_rel_path(rel_path)
    return command in CANONICAL_COMMANDS


def _remove_empty_parent(path: Path) -> None:
    parent = path.parent
    try:
        if parent.exists() and not any(parent.iterdir()):
            parent.rmdir()
    except OSError:
        pass


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
        One of :data:`SUPPORTED_AGENTS`.

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
        skill_md_bytes = _render_command_skill(repo_root, command, agent_key, version)
        rel_path = f".agents/skills/spec-kitty.{command}/SKILL.md"
        abs_path = repo_root / rel_path
        _ensure_project_confined(repo_root, rel_path, abs_path)

        existing = manifest.find(rel_path)

        if existing is not None:
            # Drift check: if the file exists, its hash must match the
            # manifest record. A missing managed file is a repairable gap.
            file_exists = abs_path.exists()
            on_disk_hash = (
                manifest_store.fingerprint_file(abs_path)
                if file_exists
                else None
            )
            if file_exists and on_disk_hash != existing.content_hash:
                raise InstallerError("unexpected_collision", path=rel_path)

            # Compute the hash we *would* write.
            would_write_hash = manifest_store.fingerprint(skill_md_bytes)

            if file_exists and existing.content_hash == would_write_hash:
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
            would_write_hash = manifest_store.fingerprint(skill_md_bytes)
            if abs_path.exists():
                on_disk_hash = manifest_store.fingerprint_file(abs_path)
                if on_disk_hash != would_write_hash:
                    raise InstallerError("unexpected_collision", path=rel_path)
                manifest.upsert(
                    ManifestEntry(
                        path=rel_path,
                        content_hash=would_write_hash,
                        agents=(agent_key,),
                        installed_at=now_utc_iso(),
                        spec_kitty_version=version,
                    )
                )
                report.reused_shared.append(rel_path)
                continue

            abs_path.parent.mkdir(parents=True, exist_ok=True)
            _atomic_write(abs_path, skill_md_bytes)
            manifest.upsert(
                ManifestEntry(
                    path=rel_path,
                    content_hash=would_write_hash,
                    agents=(agent_key,),
                    installed_at=now_utc_iso(),
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
        The supported command-skill agent to remove.

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

    for entry in manifest.entries:
        if agent_key not in entry.agents:
            continue

        abs_path = repo_root / entry.path
        _ensure_project_confined(repo_root, entry.path, abs_path)

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
            _remove_empty_parent(abs_path)

            manifest.remove_path(entry.path)
            report.deref.append(entry.path)
            report.deleted.append(entry.path)

    manifest_store.save(repo_root, manifest)
    return report


def prune_stale(repo_root: Path) -> list[str]:
    """Remove manifest entries whose command is no longer canonical.

    Stale files are deleted only when their on-disk bytes still match the
    manifest hash. Edited files fail closed.
    """
    try:
        manifest = manifest_store.load(repo_root)
    except Exception as exc:
        raise InstallerError("manifest_parse_failed", detail=str(exc)) from exc

    pruned: list[str] = []
    for entry in manifest.entries.copy():
        if _is_canonical_rel_path(entry.path):
            continue

        abs_path = repo_root / entry.path
        _ensure_project_confined(repo_root, entry.path, abs_path)
        if abs_path.exists():
            on_disk_hash = manifest_store.fingerprint_file(abs_path)
            if on_disk_hash != entry.content_hash:
                raise InstallerError("file_mutation_detected", path=entry.path)
            abs_path.unlink()
            _remove_empty_parent(abs_path)

        manifest.remove_path(entry.path)
        pruned.append(entry.path)

    if pruned:
        manifest_store.save(repo_root, manifest)
    return pruned


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
        try:
            _ensure_project_confined(repo_root, entry.path, abs_path)
        except InstallerError:
            report.unsafe.append(entry.path)
            continue
        if not _is_canonical_rel_path(entry.path):
            report.stale.append(entry.path)
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
                try:
                    _ensure_project_confined(repo_root, rel, file)
                except InstallerError:
                    report.unsafe.append(rel)
                    continue
                if rel not in manifest_paths:
                    report.orphans.append(rel)

    return report
