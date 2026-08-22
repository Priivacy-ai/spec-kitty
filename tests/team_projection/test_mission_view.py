"""Tests for specify_cli.team_projection.mission_view (D1-T1).

Covers §4 N1 (byte determinism), N7/N8 (no orchestration-state laundering /
closed WP allowlist), and C1 (reuse of status.reducer.materialize_snapshot,
not reimplementation).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.utils import write_wp

pytestmark = [pytest.mark.unit, pytest.mark.git_repo]


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=True
    )


def _commit_all(repo: Path, message: str = "wp fixture") -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


def test_build_team_mission_snapshot_shape(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    feature_dir = temp_repo / "kitty-specs" / slug
    snap = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    assert snap.schema_ == "team_mission_snapshot/v1"
    assert snap.provenance.tree_clean is True
    assert snap.content_sha256.startswith("sha256:")
    assert len(snap.content_sha256) == len("sha256:") + 64
    assert "WP01" in snap.mission["work_packages"]


def test_content_sha256_covers_mission_body_only(temp_repo: Path) -> None:
    """The digest must be stable under an envelope-only schema bump — i.e. it
    hashes ``mission``, never ``provenance`` (§3.3)."""
    import hashlib

    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    snap = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    canonical = json.dumps(snap.mission, sort_keys=True, separators=(",", ":"))
    expected = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()  # noqa: TID251
    assert snap.content_sha256 == expected


# --- N1: byte determinism ----------------------------------------------------


def test_byte_determinism_two_builds_same_commit(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    snap_a = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)
    snap_b = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    json_a = snap_a.model_dump_json(by_alias=True)
    json_b = snap_b.model_dump_json(by_alias=True)
    assert json_a == json_b


def test_raw_model_dump_json_is_NOT_hashseed_stable(temp_repo: Path) -> None:
    """Documents WHY N1's guarantee must be scoped to the on-disk artifact,
    not to arbitrary serialization of the Pydantic model (Renata D1-T1
    review, LOW finding — this is the concrete regression the review warned
    about, reproduced): ``TeamMissionSnapshot.model_dump_json()`` does NOT
    sort keys, so ``work_packages.WP01``'s field order (built from a dict
    comprehension over ``TEAM_WP_ALLOWED_FIELDS``, a frozenset whose
    iteration order is PYTHONHASHSEED-dependent) genuinely differs between
    two fresh interpreters. This is why ``write.py``'s
    ``_atomic_write_json`` — the ONLY sanctioned path to disk (§3.2 docstring)
    — always re-serializes through ``json.dumps(..., sort_keys=True)``
    rather than writing ``model_dump_json()`` output verbatim; see
    :func:`test_byte_determinism_of_published_artifact_across_processes`
    below for the guarantee that actually matters (the file on disk).
    """
    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    script = (
        "from pathlib import Path\n"
        "from specify_cli.team_projection.mission_view import build_team_mission_snapshot\n"
        f"feature_dir = Path({str(temp_repo / 'kitty-specs' / slug)!r})\n"
        f"project_dir = Path({str(temp_repo)!r})\n"
        "snap = build_team_mission_snapshot(feature_dir, project_dir, require_clean=True)\n"
        "print(snap.model_dump_json(by_alias=True), end='')\n"
    )

    def _run_with_seed(seed: str) -> str:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )
        return result.stdout

    output_seed_a = _run_with_seed("12345")
    output_seed_b = _run_with_seed("999999")

    assert output_seed_a, "subprocess produced no output"
    assert json.loads(output_seed_a)["schema"] == "team_mission_snapshot/v1"
    # Both are valid, semantically-identical documents (same key/value set)...
    assert json.loads(output_seed_a) == json.loads(output_seed_b)
    # ...but NOT byte-identical: raw model_dump_json() does not canonicalize
    # dict order, so it is NOT a hashseed-stable serialization on its own.
    assert output_seed_a != output_seed_b, (
        "model_dump_json() output was unexpectedly hashseed-stable in this "
        "run -- if this starts failing, the underlying instability this test "
        "documents may have been fixed upstream (e.g. pydantic added key "
        "sorting); if so, delete this test, it has served its purpose."
    )


def test_byte_determinism_of_published_artifact_across_processes(temp_repo: Path) -> None:
    """N1's real requirement — proven via TWO SEPARATE PROCESS invocations
    (fresh interpreter, different ``PYTHONHASHSEED`` each time), matching
    the wording of D1.md §4 N1 exactly, and matching what Renata's review
    verified by hand: the ARTIFACT THAT ACTUALLY REACHES DISK
    (``.kittify/derived/<slug>/team-snapshot.json``, written by
    ``write_team_projection`` through ``_atomic_write_json``'s
    ``json.dumps(..., sort_keys=True)`` funnel) is byte-identical across
    runs, even though raw ``model_dump_json()`` is provably NOT (see the
    test immediately above) — because the write boundary, not the model's
    default serialization, is what supplies the canonicalization.
    """
    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)

    script = (
        "from pathlib import Path\n"
        "from specify_cli.team_projection.write import write_team_projection\n"
        f"write_team_projection(Path({str(temp_repo)!r}))\n"
    )

    def _run_with_seed(seed: str) -> None:
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = seed
        subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )

    derived = temp_repo / ".kittify" / "derived"

    _run_with_seed("12345")
    files_seed_a = {
        path.relative_to(derived): path.read_bytes() for path in derived.rglob("*") if path.is_file()
    }
    assert files_seed_a, "no files were written under .kittify/derived"

    _run_with_seed("999999")
    files_seed_b = {
        path.relative_to(derived): path.read_bytes() for path in derived.rglob("*") if path.is_file()
    }

    assert files_seed_a.keys() == files_seed_b.keys()
    for relative_path, content_a in files_seed_a.items():
        assert content_a == files_seed_b[relative_path], (
            f"{relative_path} differed byte-for-byte across PYTHONHASHSEED runs"
        )


# --- N7: no orchestration-state laundering (shell_pid / shell_pid_created_at) ----


def test_shell_pid_present_locally_absent_from_team_snapshot(temp_repo: Path) -> None:
    from specify_cli.status.reducer import materialize
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    # write_wp seeds shell_pid=1234 via an InnerStateChanged annotation.
    write_wp(temp_repo, slug, "planned", "WP01", shell_pid="4242")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    local_snapshot = materialize(feature_dir)
    assert local_snapshot.work_packages["WP01"].get("shell_pid") == 4242

    snap = build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)
    rendered = snap.model_dump_json(by_alias=True)
    assert "shell_pid" not in rendered
    assert "notes" not in rendered
    assert "shell_pid" not in snap.mission["work_packages"]["WP01"]


# --- N8: closed WP filter raises on an unrecognized key ----------------------


def test_unknown_wp_state_key_raises(temp_repo: Path, monkeypatch) -> None:
    from specify_cli.status import reducer as reducer_mod
    from specify_cli.team_projection import mission_view as mission_view_mod

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    real_materialize_snapshot = reducer_mod.materialize_snapshot

    def _poisoned(feature_dir_arg: Path):  # noqa: ANN001, ANN202
        snapshot = real_materialize_snapshot(feature_dir_arg)
        snapshot.work_packages["WP01"]["totally_new_future_slot"] = "surprise"
        return snapshot

    monkeypatch.setattr(mission_view_mod, "materialize_snapshot", _poisoned)

    with pytest.raises(mission_view_mod.UnknownWPStateFieldError):
        mission_view_mod.build_team_mission_snapshot(
            feature_dir, temp_repo, require_clean=True
        )


# --- C1: reuse, not reimplementation -----------------------------------------


def test_reuses_materialize_snapshot_exactly_once(temp_repo: Path, monkeypatch) -> None:
    from specify_cli.status import reducer as reducer_mod
    from specify_cli.team_projection import mission_view as mission_view_mod

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    calls = {"n": 0}
    real_materialize_snapshot = reducer_mod.materialize_snapshot

    def _spy(feature_dir_arg: Path):  # noqa: ANN001, ANN202
        calls["n"] += 1
        return real_materialize_snapshot(feature_dir_arg)

    monkeypatch.setattr(mission_view_mod, "materialize_snapshot", _spy)

    mission_view_mod.build_team_mission_snapshot(feature_dir, temp_repo, require_clean=True)

    assert calls["n"] == 1


# --- Local/dashboard mode (require_clean=False default) ---------------------


def test_local_mode_default_require_clean_false(temp_repo: Path) -> None:
    from specify_cli.team_projection.mission_view import build_team_mission_snapshot

    slug = "001-demo-feature"
    write_wp(temp_repo, slug, "planned", "WP01")
    _commit_all(temp_repo)
    feature_dir = temp_repo / "kitty-specs" / slug

    (feature_dir / "untracked.txt").write_text("x", encoding="utf-8")

    snap = build_team_mission_snapshot(feature_dir, temp_repo)
    assert snap.provenance.tree_clean is False
