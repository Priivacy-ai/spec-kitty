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

_UV_LOCK_FILENAME = "uv.lock"


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
            # Async subprocess so the event loop is not blocked while uv lock
            # runs (S7487). The cross-process MachineFileLock above still
            # serializes lock regeneration across parallel lane workers.
            proc = await asyncio.create_subprocess_exec(
                "uv",
                "lock",
                "--no-upgrade",
                cwd=str(worktree),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_bytes, stderr_bytes = await proc.communicate()
            if proc.returncode != 0:
                summary = (
                    stderr_bytes.decode("utf-8", errors="replace")
                    or stdout_bytes.decode("utf-8", errors="replace")
                ).strip()
                return False, summary
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
    lockfile = worktree / _UV_LOCK_FILENAME
    if lockfile.exists():
        try:
            lockfile.unlink()
        except OSError as exc:
            return False, f"could not remove conflicted uv.lock: {exc!r}"
    ok, message = _regenerate_uv_lock(repo_root, worktree)
    if not ok:
        return False, message
    add_result = _run(["git", "add", _UV_LOCK_FILENAME], worktree)
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


def _abort_with_failure(
    worktree_path: Path,
    lane_id: str,
    classifications: list[ConflictClassification],
    halt_reason: str,
) -> AutoRebaseReport:
    """Run ``git merge --abort`` and return a failure ``AutoRebaseReport``."""
    _run(["git", "merge", "--abort"], worktree_path)
    return AutoRebaseReport(
        lane_id=lane_id,
        attempted=True,
        succeeded=False,
        classifications=tuple(classifications),
        halt_reason=halt_reason,
    )


def _classify_file_regions(
    file_path: Path,
    segments: list[tuple[bool, str]],
) -> tuple[list[ConflictClassification], ConflictClassification | None]:
    """Classify each conflict region in a file's segments.

    Returns ``(classifications, manual_hit)``. When ``manual_hit`` is not None,
    classification was aborted at the first ``Manual`` result.
    """
    file_classifications: list[ConflictClassification] = []
    for is_conflict, segment in segments:
        if not is_conflict:
            continue
        cls = classify(file_path, segment)
        file_classifications.append(cls)
        if isinstance(cls.resolution, Manual):
            return file_classifications, cls
    return file_classifications, None


def _splice_resolutions(
    segments: list[tuple[bool, str]],
    file_classifications: list[ConflictClassification],
) -> str:
    """Concatenate clean segments with the merged_text of Auto resolutions."""
    rebuilt_parts: list[str] = []
    idx = 0
    for is_conflict, segment in segments:
        if is_conflict:
            resolution = file_classifications[idx].resolution
            idx += 1
            assert isinstance(resolution, Auto)
            rebuilt_parts.append(resolution.merged_text)
        else:
            rebuilt_parts.append(segment)
    return "".join(rebuilt_parts)


def _validate_file_classifications(
    file_classifications: list[ConflictClassification],
    rebuilt: str,
) -> tuple[list[ConflictClassification], ConflictClassification | None]:
    """Validate Auto resolutions against the rebuilt file body."""
    validated: list[ConflictClassification] = []
    for cls in file_classifications:
        v = validate_resolution(cls, rebuilt)
        validated.append(v)
        if isinstance(v.resolution, Manual):
            return validated, v
    return validated, None


def _process_conflicted_file(
    file_path: Path,
    worktree_path: Path,
) -> tuple[list[ConflictClassification], bool, str | None]:
    """Classify, splice, validate, write, and stage one conflicted file.

    Returns ``(classifications, is_init_py, halt_reason)``. When
    ``halt_reason`` is not None, the caller should abort. ``classifications``
    is always the partial list to surface for audit.
    """
    try:
        body = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [], False, f"could not read conflicted file {file_path}: {exc!r}"

    segments, conflict_count = _split_into_regions(body)
    if conflict_count == 0:
        return [], False, (
            f"file {file_path} marked conflicted but contains no conflict markers"
        )

    file_classifications, manual_hit = _classify_file_regions(file_path, segments)
    if manual_hit is not None:
        assert isinstance(manual_hit.resolution, Manual)
        return file_classifications, False, manual_hit.resolution.reason

    rebuilt = _splice_resolutions(segments, file_classifications)

    validated, validation_failed = _validate_file_classifications(
        file_classifications, rebuilt
    )
    if validation_failed is not None:
        assert isinstance(validation_failed.resolution, Manual)
        return validated, False, validation_failed.resolution.reason

    try:
        file_path.write_text(rebuilt, encoding="utf-8")
    except OSError as exc:
        return validated, False, f"could not write merged file {file_path}: {exc!r}"

    add_result = _run(
        ["git", "add", str(file_path.relative_to(worktree_path))],
        worktree_path,
    )
    if add_result.returncode != 0:
        return validated, False, (
            f"git add {file_path} failed: {add_result.stderr.strip()}"
        )

    return validated, file_path.name == "__init__.py", None


def _finalize_auto_rebase(
    lane_id: str,
    worktree_path: Path,
    repo_root: Path,
    classifications: list[ConflictClassification],
    init_py_touched: list[Path],
    uvlock_seen: bool,
) -> AutoRebaseReport:
    """Run post-resolution steps: uv.lock regen, ruff fix, commit."""
    if uvlock_seen:
        ok, message = _attempt_resolve_uv_lock(worktree_path, repo_root)
        if not ok:
            return _abort_with_failure(
                worktree_path, lane_id, classifications,
                f"{RULE_ID_UVLOCK}: {message}",
            )

    for init_path in init_py_touched:
        ok, message = _run_ruff_imports_fix(worktree_path, init_path)
        if not ok:
            return _abort_with_failure(
                worktree_path, lane_id, classifications,
                f"{RULE_ID_INIT_IMPORTS}: ruff failed: {message}",
            )
        _run(
            ["git", "add", str(init_path.relative_to(worktree_path))],
            worktree_path,
        )

    rule_ids_used = sorted(
        {
            c.resolution.rule_id
            for c in classifications
            if isinstance(c.resolution, Auto)
        }
    )
    message = (
        f"auto-rebase(lane={lane_id}): {len(classifications)} conflicts "
        f"resolved by classifier rules [{', '.join(rule_ids_used)}]"
    )
    commit_result = _run(
        ["git", "-c", "commit.gpgsign=false", "commit", "-m", message],
        worktree_path,
    )
    if commit_result.returncode != 0:
        return _abort_with_failure(
            worktree_path, lane_id, classifications,
            f"merge commit failed: "
            f"{(commit_result.stderr or commit_result.stdout).strip()}",
        )

    return AutoRebaseReport(
        lane_id=lane_id,
        attempted=True,
        succeeded=True,
        classifications=tuple(classifications),
    )


def attempt_auto_rebase(
    lane: ExecutionLane,
    branch: str,  # noqa: ARG001 — kept for API symmetry with check_lane_staleness  # NOSONAR(python:S1172)
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

    conflicted = _list_conflicted_files(worktree_path)
    if not conflicted:
        return _abort_with_failure(
            worktree_path, lane.lane_id, [],
            f"git merge failed without conflicts: "
            f"{(merge_result.stderr or merge_result.stdout).strip()}",
        )

    classifications: list[ConflictClassification] = []
    init_py_touched: list[Path] = []
    uvlock_seen = False

    for file_path in conflicted:
        if file_path.name == _UV_LOCK_FILENAME:
            classifications.append(ConflictClassification(
                file_path=file_path,
                hunk_text="",
                resolution=Auto(merged_text="", rule_id=RULE_ID_UVLOCK),
            ))
            uvlock_seen = True
            continue

        file_classifications, is_init, halt_reason = _process_conflicted_file(
            file_path, worktree_path,
        )
        classifications.extend(file_classifications)
        if halt_reason is not None:
            return _abort_with_failure(
                worktree_path, lane.lane_id, classifications, halt_reason,
            )
        if is_init:
            init_py_touched.append(file_path)

    return _finalize_auto_rebase(
        lane.lane_id, worktree_path, repo_root,
        classifications, init_py_touched, uvlock_seen,
    )
