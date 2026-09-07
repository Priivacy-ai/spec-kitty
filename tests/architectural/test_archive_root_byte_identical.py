"""Preserve archived proof while active missions record their lifecycle.

The original charter-authority-flip M1 gate froze every pre-existing file in
four exclusion roots. ``kitty-specs`` also holds active missions: their birth
may land on main before acceptance and implementation history. That existence
alone is not evidence of archival.

Everything remains byte-frozen except two bounded updates to a mission proven
active in the Git baseline: append-only status events and additive completion
metadata. Baseline identity must match its MissionCreated record, completion
metadata must be absent, and the canonical archive registry must not contain
it. Proof files and all other roots remain immutable. Working-tree edits cannot
change baseline eligibility; malformed evidence fails closed.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.utils import REPO_ROOT
from specify_cli.missions._archive import ARCHIVE_REGISTRY_RELPATH

pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

# The convergence-port base ref. The upstream mission base is not an ancestor of
# this repository's main, so comparing it directly would blame pre-existing fork
# deletions on M1. The merge-base with main is the exact pre-port EXP tree.
_PORT_BASE_REF = "origin/main"

# The four fixed exclusion / immutable-archive roots.
_ARCHIVE_ROOTS: tuple[str, ...] = (
    "kitty-specs/",
    ".kittify/migrations/mission-state/quarantine/",
    "kitty-ops/",
    ".kittify/missions/",
)

# Append-only exceptions carved out of the immutable-archive freeze
# (2026-08-28, mission charter-authority-flip-01M14RB3 landing pass, #3664):
# the canonical rename-reconcile spine (``scripts/docs/rename_reconcile.py``'s
# ``DEFAULT_OCCURRENCE_MAP``) lives under ``kitty-specs/`` but is a *living*
# cross-mission registry, NOT a frozen proof artifact — every doc-rename
# mission is REQUIRED to append its move here or the ``build`` job's
# rename-reconcile gate reds (see main's own ``docs(landing): declare docs/plans
# curation moves on the reconcile spine`` and ``docs(plans): register the
# domains/ plan moves on the canonical rename-reconcile spine``). Appending a
# new move line is this file's designed use, not the "editing an archived
# artifact to fix a stale line" that NFR-002 forbids, so it is exempt from the
# byte-freeze while every other pre-existing archived file stays frozen.
# NOTE: the exemption is a whole-path carve-out (any mutation of this one file
# passes, not strictly an append) -- its content integrity is independently
# policed by the build job's rename-reconcile gate, so a destructive rewrite
# here would red there, not slip through silently.
_APPEND_ONLY_SPINE_EXCEPTIONS: frozenset[str] = frozenset({"kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml"})


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _files_under_roots_at(rev: str) -> set[str]:
    """Every tracked file under an archive root at ``rev``."""
    result = _run_git(["ls-tree", "-r", "--name-only", rev])
    if result.returncode != 0:
        raise RuntimeError(f"git ls-tree failed for {rev!r}: {result.stderr!r}")
    return {path for path in result.stdout.splitlines() if any(path.startswith(root) for root in _ARCHIVE_ROOTS)}


def _port_base_rev() -> str | None:
    result = _run_git(["merge-base", "HEAD", _PORT_BASE_REF])
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _require_port_base_rev() -> str:
    """Return the EXP port base, failing closed under CI when it is absent."""
    port_base_rev = _port_base_rev()
    if port_base_rev is not None:
        return port_base_rev
    message = f"EXP port base (merge-base HEAD {_PORT_BASE_REF!r}) is not reachable; archive freeze cannot run"
    if os.environ.get("CI") == "true":
        pytest.fail(message)
    pytest.skip(message)


# Canonical lifecycle writers: mission_metadata.record_acceptance,
# set_vcs_lock/record_merge, upgrade status-phase and merge-baseline capture.
# Only NEW keys may be added; no prior identity/config/history value may change.
_COMPLETION_METADATA_KEYS = frozenset(
    {
        "accepted_at",
        "accepted_by",
        "acceptance_mode",
        "accepted_from_commit",
        "accept_commit",
        "acceptance_history",
        "merged_at",
        "merged_by",
        "merged_into",
        "merged_strategy",
        "merged_push",
        "merged_commit",
        "merge_history",
        "baseline_merge_commit",
        "status_phase",
        "vcs",
        "vcs_locked_at",
    }
)


def _baseline_bytes(rev: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "-C", str(REPO_ROOT), "show", f"{rev}:{path}"], capture_output=True, check=False)
    if result.returncode == 0:
        return result.stdout
    # A missing registry is legitimate; an unreadable tracked blob is not.
    exists = _run_git(["ls-tree", rev, "--", path])
    if exists.returncode != 0 or exists.stdout:
        raise RuntimeError(f"Cannot read baseline blob {rev}:{path}: {result.stderr!r}")
    return None


def _baseline_text(rev: str, path: str) -> str | None:
    data = _baseline_bytes(rev, path)
    return data.decode("utf-8") if data is not None else None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json_object(text: str) -> dict[str, object]:
    result = json.loads(text, object_pairs_hook=_unique_object)
    if not isinstance(result, dict):
        raise ValueError("expected JSON object")
    return result


def _active_at_base(rev: str, mission_dir: str) -> bool:
    """Positive baseline evidence only; absence/corruption never unfreezes proof."""
    try:
        meta = _json_object(_baseline_text(rev, f"{mission_dir}/meta.json") or "")
        mission_id = meta.get("mission_id")
        completed_keys = {key for key in _COMPLETION_METADATA_KEYS if key.startswith(("accept", "merge"))}
        if not isinstance(mission_id, str) or not mission_id or completed_keys.intersection(meta):
            return False
        rows = [_json_object(line) for line in (_baseline_text(rev, f"{mission_dir}/status.events.jsonl") or "").splitlines()]
        born = any(
            row.get("event_type") == "MissionCreated" and isinstance(row.get("payload"), dict) and row["payload"].get("mission_id") == mission_id for row in rows
        )
        registry = _baseline_text(rev, ARCHIVE_REGISTRY_RELPATH.as_posix())
        archived = [_json_object(line) for line in registry.splitlines()] if registry is not None else []
        return born and all(isinstance(record.get("mission_id"), str) and record["mission_id"] and record["mission_id"] != mission_id for record in archived)
    except (ValueError, TypeError):
        return False


def _active_lifecycle_update(rev: str, path: str) -> bool:
    parts = Path(path).parts
    if len(parts) != 3 or parts[0] != "kitty-specs" or parts[2] not in {"meta.json", "status.events.jsonl"}:
        return False
    if not _active_at_base(rev, Path(*parts[:2]).as_posix()):
        return False
    before = _baseline_bytes(rev, path)
    try:
        # read_bytes preserves newlines: CRLF conversion is a history rewrite.
        after = (REPO_ROOT / path).read_bytes()
        if before is None:
            return False
        if parts[2] == "status.events.jsonl":
            prefix = before
            if not prefix.endswith(b"\n") or not after.startswith(prefix) or not after.endswith(b"\n"):
                return False
            suffix = after[len(prefix) :]
            return bool(suffix) and all(_json_object(line) for line in suffix.decode("utf-8").splitlines())
        original = _json_object(before.decode("utf-8"))
        updated = _json_object(after.decode("utf-8"))
        added = updated.keys() - original.keys()
        return (
            bool(added)
            and added <= _COMPLETION_METADATA_KEYS
            and all(key in updated and json.dumps(updated[key], sort_keys=True) == json.dumps(value, sort_keys=True) for key, value in original.items())
        )
    except (OSError, ValueError, TypeError):
        return False


def test_no_preexisting_archived_file_was_modified() -> None:
    """Freeze proof and archived files; permit bounded active lifecycle additions."""
    port_base_rev = _require_port_base_rev()
    baseline_files = _files_under_roots_at(port_base_rev)

    diff = _run_git(["diff", "--no-renames", "--name-status", port_base_rev, "--", *_ARCHIVE_ROOTS])
    if diff.returncode != 0:
        raise RuntimeError(f"git diff failed: {diff.stderr!r}")

    violations: list[str] = []
    for line in diff.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        status, path = parts[0], parts[-1]
        # The append-only rename-reconcile spine is exempt: appending a move
        # line to it is a required repo-wide contract, not an archive edit.
        if path in _APPEND_ONLY_SPINE_EXCEPTIONS:
            continue
        # An ADD of a path that did not exist at the base is M1's own new
        # content and is allowed. Anything else touching a pre-existing file
        # (Modify, Delete, Rename source) is a violation.
        if status.startswith("A") and path not in baseline_files:
            continue
        if status == "M" and _active_lifecycle_update(port_base_rev, path):
            continue
        if path in baseline_files:
            violations.append(f"{status}\t{path}")
        else:
            # A non-add status on a path absent from the base (e.g. a rename
            # into a root) is also unexpected under an immutable archive.
            violations.append(f"{status}\t{path} (unexpected non-add on new path)")

    assert not violations, (
        "Modified/deleted pre-existing archived file(s) under the four "
        "immutable exclusion roots (NFR-002 violation). Archive artifacts are "
        "byte-frozen; corrections belong in the live mission dossier, not the "
        "archive:\n  " + "\n  ".join(sorted(violations))
    )


def test_archive_baseline_is_non_empty() -> None:
    """Anti-vacuity floor: the archive roots are non-empty at the base, so the
    byte-identity assertion above is scanning real content, not nothing."""
    assert _files_under_roots_at(_require_port_base_rev()), (
        "no tracked files found under the archive roots at the EXP port base — the byte-identity gate would pass vacuously"
    )


def test_archive_freeze_gate_uses_the_exp_port_base_without_import_time_skip() -> None:
    """NFR-002 must execute in an EXP checkout instead of silently skipping.

    This is deliberately structural: decorators are evaluated while this module
    imports, before a test body could exercise the guard's runtime fallback.
    """
    module = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    assigned_names = {target.id for node in module.body if isinstance(node, ast.Assign) for target in node.targets if isinstance(target, ast.Name)}
    guarded = {"test_no_preexisting_archived_file_was_modified", "test_archive_baseline_is_non_empty"}
    guarded_nodes = {node.name: node for node in module.body if isinstance(node, ast.FunctionDef) and node.name in guarded}

    assert "_MISSION" + "_BASE_REV" not in assigned_names
    assert all(
        not any(
            isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "skipif" for decorator in node.decorator_list
        )
        for node in guarded_nodes.values()
    )


@pytest.fixture
def active_dossier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Real Git baseline: a born, unfinished mission plus immutable proof."""
    monkeypatch.setattr(sys.modules[__name__], "REPO_ROOT", tmp_path)
    dossier = tmp_path / "kitty-specs" / "live-mission"
    dossier.mkdir(parents=True)
    meta = {"mission_id": "01M1TZV64BPYQBCST251ECBZ4Z", "mission_slug": "live-mission", "mission_number": 1}
    (dossier / "meta.json").write_text(json.dumps(meta) + "\n", encoding="utf-8")
    birth = {"event_type": "MissionCreated", "payload": {"mission_id": meta["mission_id"]}}
    (dossier / "status.events.jsonl").write_text(json.dumps(birth) + "\n", encoding="utf-8")
    (dossier / "spec.md").write_text("immutable proof\n", encoding="utf-8")
    for args in (
        ["init", "-q"],
        ["add", "."],
        ["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "baseline"],
    ):
        assert _run_git(args).returncode == 0
    base = _run_git(["rev-parse", "HEAD"]).stdout.strip()
    monkeypatch.setattr(sys.modules[__name__], "_PORT_BASE_REF", base)
    return dossier


def test_active_dossier_can_record_completion(active_dossier: Path) -> None:
    meta_path = active_dossier / "meta.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    meta.update({"accepted_at": "2026-09-07T00:00:00Z", "accepted_by": "reviewer", "acceptance_history": [{"accepted_by": "reviewer"}]})
    meta_path.write_text(json.dumps(meta) + "\n", encoding="utf-8")
    with (active_dossier / "status.events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write('{"event_type":"TasksCompleted"}\n')
    test_no_preexisting_archived_file_was_modified()


@pytest.mark.parametrize(
    "mutation",
    ["event-rewrite", "event-delete", "event-invalid", "metadata-change", "metadata-delete", "metadata-unknown", "proof-rewrite", "proof-delete", "proof-rename"],
)
def test_active_dossier_exemption_rejects_history_mutations(active_dossier: Path, mutation: str) -> None:
    if mutation.startswith("event"):
        path = active_dossier / "status.events.jsonl"
        if mutation == "event-delete":
            path.unlink()
        elif mutation == "event-invalid":
            path.write_text(path.read_text(encoding="utf-8") + "not json\n", encoding="utf-8")
        else:
            path.write_text('{"event_type":"replacement"}\n', encoding="utf-8")
    elif mutation.startswith("metadata"):
        path = active_dossier / "meta.json"
        meta = json.loads(path.read_text(encoding="utf-8"))
        if mutation == "metadata-delete":
            del meta["mission_id"]
        elif mutation == "metadata-type-change":
            meta["mission_number"] = True
            meta["accepted_at"] = "2026-09-07T00:00:00Z"
        elif mutation == "metadata-unknown":
            meta["arbitrary_rewrite_permission"] = True
        else:
            meta["mission_id"] = "different-mission"
        path.write_text(json.dumps(meta), encoding="utf-8")
    else:
        path = active_dossier / "spec.md"
        if mutation == "proof-delete":
            path.unlink()
        elif mutation == "proof-rename":
            path.rename(active_dossier / "renamed.md")
        else:
            path.write_text("rewritten", encoding="utf-8")
    with pytest.raises(AssertionError, match="byte-frozen"):
        test_no_preexisting_archived_file_was_modified()


@pytest.mark.parametrize(
    "closed_by",
    [
        "archive-registry",
        "accepted",
        "accepted-null",
        "completion-history",
        "no-birth",
        "wrong-birth",
        "malformed-registry",
        "duplicate-registry-key",
        "registry-no-identity",
    ],
)
def test_baseline_closed_dossier_stays_frozen(active_dossier: Path, monkeypatch: pytest.MonkeyPatch, closed_by: str) -> None:
    if "registry" in closed_by:
        registry = REPO_ROOT / ".kittify" / "archive" / "archived-missions.jsonl"
        registry.parent.mkdir(parents=True)
        records = {
            "archive-registry": '{"mission_id":"01M1TZV64BPYQBCST251ECBZ4Z"}\n',
            "malformed-registry": "not json\n",
            "duplicate-registry-key": '{"mission_id":"01M1TZV64BPYQBCST251ECBZ4Z","mission_id":"other"}\n',
            "registry-no-identity": "{}\n",
        }
        registry.write_text(records[closed_by], encoding="utf-8")
    elif closed_by in {"accepted", "accepted-null", "completion-history"}:
        meta_path = active_dossier / "meta.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if closed_by == "completion-history":
            meta["acceptance_history"] = []
        else:
            meta["accepted_at"] = None if closed_by == "accepted-null" else "2026-09-06T00:00:00Z"
        meta_path.write_text(json.dumps(meta), encoding="utf-8")
    else:
        event = {"event_type": "MissionCreated", "payload": {"mission_id": "different-mission"}} if closed_by == "wrong-birth" else {"event_type": "historical"}
        (active_dossier / "status.events.jsonl").write_text(json.dumps(event) + "\n", encoding="utf-8")
    assert _run_git(["add", "."]).returncode == 0
    assert (
        _run_git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "closed baseline"]).returncode
        == 0
    )
    monkeypatch.setattr(sys.modules[__name__], "_PORT_BASE_REF", _run_git(["rev-parse", "HEAD"]).stdout.strip())
    if closed_by == "archive-registry":
        registry.unlink()  # Working-tree tampering cannot unfreeze an archived baseline.
    with (active_dossier / "status.events.jsonl").open("a", encoding="utf-8") as stream:
        stream.write('{"event_type":"TasksCompleted"}\n')
    with pytest.raises(AssertionError, match="byte-frozen"):
        test_no_preexisting_archived_file_was_modified()


def test_event_prefix_compares_exact_baseline_bytes(active_dossier: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = active_dossier / "status.events.jsonl"
    path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))
    assert _run_git(["add", "."]).returncode == 0
    assert (
        _run_git(["-c", "user.name=Test", "-c", "user.email=test@example.invalid", "-c", "commit.gpgsign=false", "commit", "-qm", "CRLF baseline"]).returncode == 0
    )
    monkeypatch.setattr(sys.modules[__name__], "_PORT_BASE_REF", _run_git(["rev-parse", "HEAD"]).stdout.strip())
    path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n") + b'{"event_type":"TasksCompleted"}\n')
    with pytest.raises(AssertionError, match="byte-frozen"):
        test_no_preexisting_archived_file_was_modified()
