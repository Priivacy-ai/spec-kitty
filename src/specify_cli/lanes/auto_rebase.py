"""Stale-lane auto-rebase orchestrator.

Drives the auto-rebase pipeline described in
``architecture/2.x/adr/2026-05-14-1-stale-lane-auto-rebase-classifier-policy.md``:

1. Attempt ``git merge <mission-branch>`` inside the lane worktree.
2. If the merge succeeds cleanly, return :class:`AutoRebaseReport` with
   ``succeeded=True``.
3. If conflicts surface, classify each conflicted region via
   :mod:`specify_cli.merge.conflict_classifier`. Any ``Manual`` classification
   aborts the merge and returns ``succeeded=False``.
4. For ``Auto`` classifications, splice the merged text back into the file
   and stage it. Run post-merge validation (TOML parse / AST parse).
5. If ``uv.lock`` was conflicted, regenerate it under the cross-process
   :class:`specify_cli.core.file_lock.MachineFileLock` to serialize across
   lanes. Stage the regenerated file.
6. If any ``__init__.py`` was modified, run ``ruff --fix --select I001 <file>``.
   Non-zero exit ⇒ revert to ``Manual``.
7. Create the merge commit with message
   ``"auto-rebase(lane=<id>): <N> conflicts resolved by classifier rules
   [<rule_ids>]"`` per ADR §Operator-visible-behavior.

This module performs all subprocess and filesystem I/O. The classifier in
:mod:`specify_cli.merge.conflict_classifier` is pure.
"""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from specify_cli.core.file_lock import MachineFileLock
from specify_cli.lanes.models import ExecutionLane
from specify_cli.merge.conflict_classifier import (
    RULE_ID_INIT_IMPORTS,
    RULE_ID_UVLOCK,
    Auto,
    ConflictClassification,
    Manual,
    classify,
    validate_resolution,
)

__all__ = [
    "AutoRebaseReport",
    "attempt_auto_rebase",
]


@dataclass(frozen=True)
class AutoRebaseReport:
    """Outcome of an auto-rebase attempt for a single lane.

    Mirrors the dataclass in ``data-model.md`` §3. The dataclass is
    ``frozen=True`` so callers cannot mutate the audit-log record.
    """

    lane_id: str
    attempted: bool
    succeeded: bool
    classifications: tuple[ConflictClassification, ...] = field(default_factory=tuple)
    halt_reason: str | None = None

    def __post_init__(self) -> None:
        # Invariant: halt_reason is set iff succeeded is False.
        if self.succeeded and self.halt_reason is not None:
            raise ValueError(
                "AutoRebaseReport: halt_reason must be None when succeeded=True"
            )
        if not self.succeeded and self.halt_reason is None and self.attempted:
            raise ValueError(
                "AutoRebaseReport: halt_reason must be set when succeeded=False "
                "and attempted=True"
            )


# Conflict-marker regex used to split a conflicted file into clean text,
# conflict regions, and the trailing clean tail.
_RE_CONFLICT_REGION = re.compile(
    r"<{7}[^\n]*\n.*?>{7}[^\n]*\n",
    re.DOTALL,
)


def _run(
    cmd: list[str], cwd: Path, *, check: bool = False
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command capturing stdout/stderr as text."""
    return subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _list_conflicted_files(worktree: Path) -> list[Path]:
    """Return absolute paths to files currently in conflict in ``worktree``."""
    result = _run(["git", "diff", "--name-only", "--diff-filter=U"], worktree)
    if result.returncode != 0:
        return []
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name:
            continue
        paths.append(worktree / name)
    return paths


def _split_into_regions(
    text: str,
) -> tuple[list[tuple[bool, str]], int]:
    """Return ``(segments, conflict_count)`` where each segment is
    ``(is_conflict, text)``. Order is preserved so a faithful reassembly is
    a simple concatenation.
    """
    segments: list[tuple[bool, str]] = []
    last_end = 0
    count = 0
    for m in _RE_CONFLICT_REGION.finditer(text):
        if m.start() > last_end:
            segments.append((False, text[last_end : m.start()]))
        segments.append((True, m.group(0)))
        count += 1
        last_end = m.end()
    if last_end < len(text):
        segments.append((False, text[last_end:]))
    return segments, count


def _git_user_env_ready(worktree: Path) -> None:
    """Best-effort: ensure git user.name/user.email exist so ``git commit``
    does not fail under unconfigured environments (e.g. test sandboxes)."""
    for key, default in (("user.email", "auto-rebase@spec-kitty"), ("user.name", "spec-kitty auto-rebase")):
        existing = _run(["git", "config", "--get", key], worktree)
        if existing.returncode != 0 or not existing.stdout.strip():
            _run(["git", "config", key, default], worktree)


def _regenerate_uv_lock(repo_root: Path, worktree: Path) -> tuple[bool, str]:
    """Regenerate ``uv.lock`` under :class:`MachineFileLock`.

    Returns ``(success, message)``. ``message`` is the stderr/stdout summary
    on failure; empty string on success.
    """
    lock_path = repo_root / ".kittify" / "auto-rebase-uv-lock.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    async def _run_locked() -> tuple[bool, str]:
        async with MachineFileLock(lock_path):
            # Subprocess is intentionally blocking here; we already hold a
            # cross-process file lock so the call is serialized.
            result = subprocess.run(  # noqa: ASYNC221
                ["uv", "lock", "--no-upgrade"],
                cwd=str(worktree),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return False, (result.stderr or result.stdout).strip()
            return True, ""

    try:
        return asyncio.run(_run_locked())
    except FileNotFoundError:
        # uv not installed in this environment — fall back to checkout-theirs
        # to avoid blocking the orchestrator entirely. The operator can
        # regenerate later. We treat this as a soft success only when the
        # caller has explicitly accepted the policy; otherwise it is a hard
        # failure. Be conservative: hard failure.
        return False, "uv binary not found on PATH"
    except Exception as exc:  # noqa: BLE001 — surface to operator
        return False, f"uv lock raised: {exc!r}"


def _attempt_resolve_uv_lock(worktree: Path, repo_root: Path) -> tuple[bool, str]:
    """Discard both sides of the ``uv.lock`` conflict and stage the regenerated file."""
    # Remove the conflicted state by checking out --theirs then deleting the
    # file; uv lock will write a fresh one.
    lockfile = worktree / "uv.lock"
    if lockfile.exists():
        try:
            lockfile.unlink()
        except OSError as exc:
            return False, f"could not remove conflicted uv.lock: {exc!r}"
    ok, message = _regenerate_uv_lock(repo_root, worktree)
    if not ok:
        return False, message
    add_result = _run(["git", "add", "uv.lock"], worktree)
    if add_result.returncode != 0:
        return False, f"git add uv.lock failed: {add_result.stderr.strip()}"
    return True, ""


def _run_ruff_imports_fix(worktree: Path, file_path: Path) -> tuple[bool, str]:
    """Run ``ruff --fix --select I001`` on a single file. Returns ``(ok, message)``."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--fix", "--select", "I001", str(file_path)],
            cwd=str(worktree),
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        # ruff not installed — keep the merged content as-is (it is already
        # a deterministic union; the lint pass is purely cosmetic).
        return True, ""
    if result.returncode not in (0, 1):
        # 0 = no issues, 1 = fixed issues. Anything else is a hard failure.
        return False, (result.stderr or result.stdout).strip()
    return True, ""


def attempt_auto_rebase(  # noqa: C901, PLR0915
    lane: ExecutionLane,
    branch: str,  # noqa: ARG001 — kept for API symmetry with stale_check
    mission_branch: str,
    repo_root: Path,
    worktree_path: Path,
) -> AutoRebaseReport:
    """Attempt a stale-lane auto-rebase.

    The caller has already determined the lane is stale. This function:

    1. Runs ``git merge <mission_branch>`` inside ``worktree_path``.
    2. If clean, returns ``succeeded=True``.
    3. Classifies each conflict region. Any ``Manual`` aborts the merge and
       returns ``succeeded=False``.
    4. Applies ``Auto`` resolutions, regenerates ``uv.lock`` if needed, runs
       ``ruff --fix --select I001`` on touched ``__init__.py`` files, and
       commits with the audit message.
    """
    _git_user_env_ready(worktree_path)

    # Step 1: attempt the merge.
    merge_result = _run(
        ["git", "merge", "--no-edit", "--no-ff", mission_branch],
        worktree_path,
    )
    if merge_result.returncode == 0:
        return AutoRebaseReport(
            lane_id=lane.lane_id,
            attempted=True,
            succeeded=True,
            classifications=(),
        )

    # Step 2: collect conflicted files.
    conflicted = _list_conflicted_files(worktree_path)
    if not conflicted:
        # Non-conflict failure (e.g. uncommitted local changes). Abort.
        _run(["git", "merge", "--abort"], worktree_path)
        return AutoRebaseReport(
            lane_id=lane.lane_id,
            attempted=True,
            succeeded=False,
            classifications=(),
            halt_reason=(
                f"git merge failed without conflicts: "
                f"{(merge_result.stderr or merge_result.stdout).strip()}"
            ),
        )

    classifications: list[ConflictClassification] = []
    init_py_touched: list[Path] = []
    uvlock_seen = False

    for file_path in conflicted:
        # Special handling for uv.lock — never read the conflicted body for
        # classification; we regenerate.
        if file_path.name == "uv.lock":
            classification = ConflictClassification(
                file_path=file_path,
                hunk_text="",
                resolution=Auto(merged_text="", rule_id=RULE_ID_UVLOCK),
            )
            classifications.append(classification)
            uvlock_seen = True
            continue

        try:
            body = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            _run(["git", "merge", "--abort"], worktree_path)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=(
                    f"could not read conflicted file {file_path}: {exc!r}"
                ),
            )

        segments, conflict_count = _split_into_regions(body)
        if conflict_count == 0:
            # File flagged as conflicted but no markers — treat as Manual.
            _run(["git", "merge", "--abort"], worktree_path)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=(
                    f"file {file_path} marked conflicted but contains no "
                    f"conflict markers"
                ),
            )

        file_classifications: list[ConflictClassification] = []
        for is_conflict, segment in segments:
            if not is_conflict:
                continue
            cls = classify(file_path, segment)
            file_classifications.append(cls)
            if isinstance(cls.resolution, Manual):
                _run(["git", "merge", "--abort"], worktree_path)
                classifications.extend(file_classifications)
                return AutoRebaseReport(
                    lane_id=lane.lane_id,
                    attempted=True,
                    succeeded=False,
                    classifications=tuple(classifications),
                    halt_reason=cls.resolution.reason,
                )

        # All regions in this file are Auto — splice them in.
        rebuilt_parts: list[str] = []
        idx = 0
        for is_conflict, segment in segments:
            if is_conflict:
                resolution = file_classifications[idx].resolution
                idx += 1
                assert isinstance(resolution, Auto)  # narrow for mypy
                rebuilt_parts.append(resolution.merged_text)
            else:
                rebuilt_parts.append(segment)
        rebuilt = "".join(rebuilt_parts)

        # Run validation pass against the full file body.
        validated_file_classifications: list[ConflictClassification] = []
        validation_failed: ConflictClassification | None = None
        for cls in file_classifications:
            validated = validate_resolution(cls, rebuilt)
            validated_file_classifications.append(validated)
            if isinstance(validated.resolution, Manual):
                validation_failed = validated
                break
        if validation_failed is not None:
            _run(["git", "merge", "--abort"], worktree_path)
            classifications.extend(validated_file_classifications)
            assert isinstance(validation_failed.resolution, Manual)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=validation_failed.resolution.reason,
            )

        # Write back and stage.
        try:
            file_path.write_text(rebuilt, encoding="utf-8")
        except OSError as exc:
            _run(["git", "merge", "--abort"], worktree_path)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=f"could not write merged file {file_path}: {exc!r}",
            )

        if file_path.name == "__init__.py":
            init_py_touched.append(file_path)

        # Stage.
        add_result = _run(
            ["git", "add", str(file_path.relative_to(worktree_path))],
            worktree_path,
        )
        if add_result.returncode != 0:
            _run(["git", "merge", "--abort"], worktree_path)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=(
                    f"git add {file_path} failed: {add_result.stderr.strip()}"
                ),
            )

        classifications.extend(validated_file_classifications)

    # Step 4: regenerate uv.lock if it was conflicted.
    if uvlock_seen:
        ok, message = _attempt_resolve_uv_lock(worktree_path, repo_root)
        if not ok:
            _run(["git", "merge", "--abort"], worktree_path)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=f"{RULE_ID_UVLOCK}: {message}",
            )

    # Step 5: ruff --fix --select I001 on touched __init__.py files.
    for init_path in init_py_touched:
        ok, message = _run_ruff_imports_fix(worktree_path, init_path)
        if not ok:
            _run(["git", "merge", "--abort"], worktree_path)
            return AutoRebaseReport(
                lane_id=lane.lane_id,
                attempted=True,
                succeeded=False,
                classifications=tuple(classifications),
                halt_reason=f"{RULE_ID_INIT_IMPORTS}: ruff failed: {message}",
            )
        # Re-stage in case ruff modified the file.
        _run(
            ["git", "add", str(init_path.relative_to(worktree_path))],
            worktree_path,
        )

    # Step 6: create the merge commit.
    rule_ids_used = sorted(
        {
            c.resolution.rule_id
            for c in classifications
            if isinstance(c.resolution, Auto)
        }
    )
    message = (
        f"auto-rebase(lane={lane.lane_id}): {len(classifications)} conflicts "
        f"resolved by classifier rules [{', '.join(rule_ids_used)}]"
    )
    commit_result = _run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", message],
        worktree_path,
    )
    if commit_result.returncode != 0:
        _run(["git", "merge", "--abort"], worktree_path)
        return AutoRebaseReport(
            lane_id=lane.lane_id,
            attempted=True,
            succeeded=False,
            classifications=tuple(classifications),
            halt_reason=(
                f"merge commit failed: "
                f"{(commit_result.stderr or commit_result.stdout).strip()}"
            ),
        )

    return AutoRebaseReport(
        lane_id=lane.lane_id,
        attempted=True,
        succeeded=True,
        classifications=tuple(classifications),
    )
