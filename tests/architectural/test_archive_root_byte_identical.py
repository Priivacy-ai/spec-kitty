"""Historical preservation gate (M1 NFR-002, WP12 FR-007-011).

The four fixed exclusion roots (``DM-01M0P6C8C7Q6SPBT412V39RPN0``) are immutable
historical-record surfaces:

* ``kitty-specs/`` — archived mission dossiers,
* ``.kittify/migrations/mission-state/quarantine/`` — quarantined migration state,
* ``kitty-ops/`` — repo-ops history,
* ``.kittify/missions/`` — mission-state history.

M1's editorial freeze endures; its operator decision also permits runtime
appends. Only the exact lifecycle log may extend a preserved byte prefix.
Unsigned suffix validation establishes format, not cryptographic authenticity.
WP11's independently reviewed recovery has exact Git provenance, output pins
AND current read-only canonical replay. It is not a general snapshot exception.
Both index and working tree are checked against merge-base(HEAD, origin/main).
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import stat
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from specify_cli.invocation.lifecycle import LIFECYCLE_LOG_RELATIVE_PATH
from specify_cli.invocation.record import ProfileInvocationRecord
from specify_cli.status.reducer import materialize_snapshot, materialize_to_json

REPO_ROOT = Path(__file__).resolve().parents[2]

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
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "SPEC_KITTY_ENABLE_SAAS_SYNC": "0"},
    )


def _git_bytes(*args: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        check=False,
        env={**os.environ, "GIT_NO_REPLACE_OBJECTS": "1", "GIT_OPTIONAL_LOCKS": "0", "SPEC_KITTY_ENABLE_SAAS_SYNC": "0"},
    )
    assert result.returncode == 0, f"Git preservation read failed {args!r}: {result.stderr!r}"
    return result.stdout


@dataclass(frozen=True)
class Blob:
    mode: str
    oid: str

    def read(self) -> bytes:
        return _git_bytes("cat-file", "blob", self.oid)


def _tree(rev: str, *paths: str) -> dict[str, Blob]:
    result: dict[str, Blob] = {}
    for row in _git_bytes("ls-tree", "-rz", rev, "--", *paths).split(b"\0"):
        if row:
            header, path = row.split(b"\t", 1)
            mode, kind, oid = header.decode("ascii").split()
            assert kind == "blob", f"{os.fsdecode(path)}: non-blob historical entry"
            result[os.fsdecode(path)] = Blob(mode, oid)
    return result


def _index() -> dict[str, Blob]:
    result: dict[str, Blob] = {}
    for row in _git_bytes("ls-files", "--stage", "-z").split(b"\0"):
        if row:
            header, path = row.split(b"\t", 1)
            mode, oid, stage = header.decode("ascii").split()
            assert stage == "0", f"{os.fsdecode(path)}: unmerged index"
            result[os.fsdecode(path)] = Blob(mode, oid)
    return result


def _confined(path: str) -> Path:
    relative = Path(path)
    assert not relative.is_absolute() and ".." not in relative.parts, f"{path}: unsafe path"
    current = REPO_ROOT
    for part in relative.parts[:-1]:
        current = current / part
        assert current.is_dir() and not current.is_symlink(), f"{path}: unsafe parent {current}"
    return current / relative.name


def _disk(path: str, mode: str) -> bytes:
    candidate = _confined(path)
    assert candidate.exists() or candidate.is_symlink(), f"{path}: missing file"
    observed = candidate.lstat()
    assert stat.S_ISREG(observed.st_mode), f"{path}: regular-file kind required"
    actual_mode = "100755" if observed.st_mode & stat.S_IXUSR else "100644"
    assert mode in {"100644", "100755"} and actual_mode == mode, f"{path}: mode changed"
    return candidate.read_bytes()


def _changes(base: str, *, cached: bool = False) -> list[tuple[str, tuple[str, ...]]]:
    """Unscoped NUL view: retain both endpoints, regardless of rename detection."""
    args = ["diff", "--name-status", "-z", "--no-ext-diff"]
    if cached:
        args.append("--cached")
    rows = iter(_git_bytes(*args, base, "--").split(b"\0"))
    changes = []
    for row in rows:
        if row:
            status = row.decode("ascii")
            count = 2 if status.startswith(("R", "C")) else 1
            paths = tuple(os.fsdecode(next(rows)) for _ in range(count))
            changes.append((status, paths))
    return changes


def _lifecycle_prefix(path: str, before: bytes, after: bytes) -> None:
    if after == before:
        return
    assert after.startswith(before), f"{path}: historical byte prefix changed"
    assert not before or before.endswith(b"\n"), f"{path}: unterminated historical boundary"
    suffix = after[len(before) :]
    assert suffix.endswith(b"\n"), f"{path}: incomplete suffix record"
    for number, row in enumerate(suffix[:-1].split(b"\n"), 1):
        try:
            data = json.loads(row.decode("utf-8"))
            assert isinstance(data, dict), "record must be an object"
            ProfileInvocationRecord.from_dict(data)
        except (UnicodeError, ValueError, KeyError, TypeError, AssertionError) as error:
            raise AssertionError(f"{path}: invalid suffix row {number}: {error}") from error


def _check_lifecycle(baseline: dict[str, Blob], index: dict[str, Blob]) -> None:
    path = LIFECYCLE_LOG_RELATIVE_PATH.as_posix()
    if path not in baseline:
        return
    old = baseline[path]
    assert path in index, f"{path}: deleted or renamed in index"
    assert index[path].mode == old.mode, f"{path}: index mode changed"
    before = old.read()
    _lifecycle_prefix(path, before, index[path].read())
    _lifecycle_prefix(path, before, _disk(path, old.mode))


# WP11 independent review, persisted by parent event 01M1VMFHA7K9XJAK0Y2MJR6NRV.
# These commits and this digest are trust inputs, never taken from the candidate.
ORIGINAL = "c0054153b9bce0778cf41a85d11ecd4e9650031d"
SOURCE = "3442ca1afc20b1b83b27a7bc64fd7014050b12a1"
CONVERGENCE = "2554bd13adc289d3457681308645fe52619bca0e"
RED_RECEIPT = "13e75ffd06434e02b0ddd578b7047f22506bc917"
RESTORED = "3cb4af0ccce9a3b8db73e03fb37149d62bf3ef53"
RECOVERED = "8e2d40bc0cbf607eea3af97ae9a80e82f18ee8f4"
RECEIPT = "docs/archive/program-evidence/upgrade-preview-mission-health-01M1V6E1/recovery-receipt.json"
RECEIPT_SHA256 = "f320ada834fbabcddd7186147d606551dcecf066dad4c4eef182eafcf0a7f4b8"
CYCLIC = "kitty-specs/reject-cyclic-lane-graphs-01M0QCK4"
CYCLIC_FILES = frozenset(
    {
        ".kittify/dossiers/reject-cyclic-lane-graphs-01M0QCK4/snapshot-latest.json",
        "acceptance-matrix.json",
        "adversarial-review.md",
        "analysis-report.md",
        "checklists/requirements.md",
        "contracts/lane-dependency-cycle.schema.json",
        "data-model.md",
        "decisions/DM-01M0QCNTD5CM0SE0HKQ79C9NF6.md",
        "decisions/DM-01M0QDJWKXD5JHSVHV0NWSJDWM.md",
        "decisions/DM-01M0QEAKZVM8QAVZPF9AE6D1N8.md",
        "decisions/index.json",
        "issue-matrix.json",
        "lanes.json",
        "meta.json",
        "mission-review.md",
        "plan.md",
        "pr-summary.md",
        "quickstart.md",
        "research.md",
        "retrospective.yaml",
        "spec.md",
        "status.events.jsonl",
        "status.json",
        "tasks.md",
        "tasks/.gitkeep",
        "tasks/README.md",
        "tasks/WP01-authoritative-domain-cycle-gate.md",
        "tasks/WP01-authoritative-domain-cycle-gate/review-cycle-1.md",
        "tasks/WP01-authoritative-domain-cycle-gate/review-cycle-2.md",
        "tasks/WP01-authoritative-domain-cycle-gate/review-feedback-1.md",
        "tasks/WP02-finalization-diagnostics-and-persistence.md",
        "tasks/WP03-determinism-performance-and-regression.md",
    }
)
OLD_BUNDLE = "kitty-specs/R2-T1-local-legacy-removal"
NEW_BUNDLE = "docs/archive/program-evidence/R2-T1-local-legacy-removal"
SPINE = "kitty-specs/common-docs-convergence-01KZMTR9/occurrence_map.yaml"
SNAPSHOTS = (
    "kitty-specs/doctrine-drg-silent-drop-boundary-01M0PE7E/status.json",
    "kitty-specs/symbolkey-source-module-01M0B0SF/status.json",
    CYCLIC + "/status.json",
)
MOVES = tuple(
    (f"{OLD_BUNDLE}/{name}", f"{NEW_BUNDLE}/{name}")
    for name in (
        "deletion-manifest.md",
        "commit-history-notes.md",
    )
)


def _reviewed_receipt() -> dict[str, Any]:
    raw = _git_bytes("show", f"{RECOVERED}:{RECEIPT}")
    assert _sha256(raw) == RECEIPT_SHA256, f"{RECEIPT}: reviewed receipt pin"
    result: dict[str, Any] = json.loads(raw)
    return result


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()  # noqa: TID251 - exact file-integrity digest, not charter semantic hashing


def _exact_candidate(path: str, expected: Blob, index: dict[str, Blob]) -> bytes:
    assert index.get(path) == expected, f"{path}: tracked index blob/mode differs from reviewed proof"
    raw = _disk(path, expected.mode)
    assert raw == expected.read(), f"{path}: reviewed bytes changed"
    return raw


def _recovery_present(baseline: dict[str, Blob], index: dict[str, Blob]) -> bool:
    if RECEIPT in baseline or RECEIPT in index or (REPO_ROOT / RECEIPT).is_symlink():
        return True
    # Deleting all outputs together must not erase the admission's obligations.
    return _run_git(["merge-base", "--is-ancestor", RECOVERED, "HEAD"]).returncode == 0


def _historical_restoration(receipt: dict[str, Any]) -> dict[str, Blob]:
    source = _tree(SOURCE, CYCLIC)
    assert source.keys() == {f"{CYCLIC}/{name}" for name in CYCLIC_FILES}, f"{CYCLIC}: historical path membership"
    assert source == _tree(CONVERGENCE + "^1", CYCLIC), f"{CYCLIC}: convergence source history"
    schema = CYCLIC + "/contracts/lane-dependency-cycle.schema.json"
    assert _tree(CONVERGENCE, CYCLIC) == {schema: source[schema]}, f"{CYCLIC}: convergence deletion proof"
    assert _tree(ORIGINAL, CYCLIC) == {schema: source[schema]}, f"{CYCLIC}: retained schema proof"
    assert source[schema].oid == "26cb3b8bafde72894f0d1ec0a9c1701cd511f497"
    assert source == _tree(RESTORED, CYCLIC), f"{CYCLIC}: restoration before replay differs"
    entries = receipt["restores"]
    assert sorted(entry["path"] for entry in entries) == sorted(source.keys() - {schema})
    for entry in [*entries, receipt["retained_schema"]]:
        old = source[entry["path"]]
        assert (old.oid, old.mode, _sha256(old.read())) == (
            entry["blob"],
            entry["mode"],
            entry["sha256"],
        ), f"{entry['path']}: historical receipt provenance"
    assert _tree(RED_RECEIPT, CYCLIC) == {schema: source[schema]}, f"{CYCLIC}: RED chronology"
    return source


def _check_snapshot(path: str, index: dict[str, Blob], receipt: dict[str, Any]) -> None:
    source = SOURCE if path == SNAPSHOTS[2] else ORIGINAL
    directory = path.rsplit("/", 1)[0]
    before = _tree(source, directory)
    reviewed = _tree(RECOVERED, directory)
    # Every historical input, including annotations and metadata, stays exact.
    assert before.keys() == reviewed.keys(), f"{path}: reviewed input membership"
    for name, old in before.items():
        if name != path:
            assert reviewed[name] == old, f"{name}: reviewed history changed"
            _exact_candidate(name, old, index)
    candidate = _exact_candidate(path, reviewed[path], index)
    entry = receipt["restored_mission_replay"] if source == SOURCE else next(entry for entry in receipt["replays"] if entry["path"] == path)
    assert before[path].oid == entry["before_blob"], f"{path}: original snapshot OID"
    assert _sha256(candidate) == entry["after_sha256"], f"{path}: reviewed output hash"
    # Read-only owner composition; never materialize/save/repair the candidate.
    canonical = materialize_to_json(materialize_snapshot(REPO_ROOT / directory)).encode("utf-8")
    assert canonical == candidate, f"{path}: canonical replay differs from reviewed output"
    old_snapshot = json.loads(before[path].read())
    snapshot = json.loads(candidate)
    assert snapshot["work_packages"].keys() == old_snapshot["work_packages"].keys()
    for wp, old_state in old_snapshot["work_packages"].items():
        state = snapshot["work_packages"][wp]
        for key in ("review_result", "lane", "force_count", "last_event_id", "last_transition_at", "actor", "agent"):
            assert state.get(key) == old_state.get(key), f"{path}: {wp} historical {key} changed"
        assert state["lane"] == "done" and state["review_result"]["verdict"] == "approved"


def _check_relocations(index: dict[str, Blob], receipt: dict[str, Any]) -> None:
    assert sorted((entry["from"], entry["to"]) for entry in receipt["relocations"]) == sorted(MOVES)
    for old, new in MOVES:
        source = _tree(ORIGINAL, old)[old]
        entry = next(entry for entry in receipt["relocations"] if entry["from"] == old)
        assert entry["to"] == new and source.oid == entry["blob"], f"{old}: relocation provenance"
        assert _tree(entry["introduction_commit"], old)[old] == source, f"{old}: introduction proof"
        assert old not in index, f"{old}: relocation source still tracked"
        assert not (REPO_ROOT / old).exists(), f"{old}: relocation source still present"
        _exact_candidate(new, source, index)
    assert not (REPO_ROOT / OLD_BUNDLE).exists() and not (REPO_ROOT / OLD_BUNDLE).is_symlink(), f"{OLD_BUNDLE}: residual source directory or alias"


def _check_recovery(index: dict[str, Blob]) -> set[str]:
    receipt = _reviewed_receipt()
    trusted = _tree(RECOVERED, RECEIPT, NEW_BUNDLE, SPINE, CYCLIC, *SNAPSHOTS)
    _exact_candidate(RECEIPT, trusted[RECEIPT], index)
    source = _historical_restoration(receipt)
    assert {p for p in index if p.startswith(CYCLIC + "/")} == source.keys(), f"{CYCLIC}: index inventory differs"
    disk_paths = {str(p.relative_to(REPO_ROOT)) for p in (REPO_ROOT / CYCLIC).rglob("*") if not p.is_dir()}
    assert disk_paths == source.keys(), f"{CYCLIC}: disk inventory differs: {sorted(disk_paths ^ source.keys())}"
    for path, old in source.items():
        expected = trusted[path] if path == SNAPSHOTS[2] else old
        _exact_candidate(path, expected, index)
    for path in SNAPSHOTS:
        _check_snapshot(path, index, receipt)
    _check_relocations(index, receipt)
    _exact_candidate(NEW_BUNDLE + "/README.md", trusted[NEW_BUNDLE + "/README.md"], index)
    # Preserve the reviewed prefix/rows while retaining the separate spine policy
    # for subsequent additions. No candidate-controlled receipt can change it.
    prefix = trusted[SPINE].read()
    assert prefix == _git_bytes("show", f"{ORIGINAL}:{SPINE}") + receipt["occurrence_map"]["append_only_delta"].encode()
    assert SPINE in index and index[SPINE].mode == trusted[SPINE].mode, f"{SPINE}: tracked mode changed"
    assert index[SPINE].read().startswith(prefix), f"{SPINE}: reviewed navigation prefix changed in index"
    assert _disk(SPINE, trusted[SPINE].mode).startswith(prefix), f"{SPINE}: reviewed navigation prefix changed"
    return {*SNAPSHOTS, *(old for old, _ in MOVES)}


def _files_under_roots_at(rev: str) -> set[str]:
    """Every tracked file under an archive root at ``rev``."""
    return {path for path in _tree(rev) if any(path.startswith(root) for root in _ARCHIVE_ROOTS)}


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


def test_no_preexisting_archived_file_was_modified() -> None:
    """Default freeze plus evidence-bound lifecycle and recovery operations."""
    port_base_rev = _require_port_base_rev()
    baseline = _tree(port_base_rev)
    assert any(path.startswith(_ARCHIVE_ROOTS) for path in baseline), "empty archive baseline"
    index = _index()
    _check_lifecycle(baseline, index)
    admitted = _check_recovery(index) if _recovery_present(baseline, index) else set()
    violations: list[str] = []
    for status, paths in [*_changes(port_base_rev), *_changes(port_base_rev, cached=True)]:
        for path in paths:
            if not path.startswith(_ARCHIVE_ROOTS) or path in _APPEND_ONLY_SPINE_EXCEPTIONS:
                continue
            if path == LIFECYCLE_LOG_RELATIVE_PATH.as_posix() and status == "M":
                continue
            if path in admitted:
                continue
            if status == "A" and path not in baseline:
                continue
            violations.append(f"{status}\t{path}: ordinary archive history changed")
    assert not violations, "Historical preservation violation under the four archive roots:\n  " + "\n  ".join(sorted(set(violations)))


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
    assert guarded_nodes.keys() == guarded, "protected gate function missing"
    assert all(
        not any(
            isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "skipif" for decorator in node.decorator_list
        )
        for node in guarded_nodes.values()
    )
