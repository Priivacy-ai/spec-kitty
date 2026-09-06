"""WP01 harness controls; product acceptance remains a separate red suite."""

from __future__ import annotations

import json
import os
from dataclasses import replace
from pathlib import Path

import pytest

from tests.upgrade.preview_support.process import child_environment, run_process
from tests.upgrade.preview_support.provenance import identify_source
from tests.upgrade.preview_support.snapshot import assert_unchanged, net_delta, snapshot

pytestmark = pytest.mark.integration
LANE = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("mutation", ["ignored", "mkdir", "rmdir", "unlink", "retarget", "chmod", "mtime"])
def test_observations_and_omission_controls(tmp_path: Path, mutation: str) -> None:
    """Each required observation catches its own otherwise invisible mutation."""
    root = tmp_path / "root"
    root.mkdir()
    (root / ".gitignore").write_text("ignored\n")
    regular = root / "ignored"
    regular.write_bytes(b"before")
    empty = root / "empty"
    empty.mkdir()
    link = root / "link"
    link.symlink_to("missing")
    before = snapshot({"project": root})
    if mutation == "ignored":
        regular.write_bytes(b"after")
    elif mutation == "mkdir":
        (root / "new").mkdir()
    elif mutation == "rmdir":
        empty.rmdir()
    elif mutation == "unlink":
        link.unlink()
    elif mutation == "retarget":
        link.unlink()
        link.symlink_to("other-missing")
    elif mutation == "chmod":
        regular.chmod(0o700)
    else:
        old = regular.stat().st_mtime_ns
        regular.write_bytes(b"before")
        os.utime(regular, ns=(old, old + 1_000_000_000))
    after = snapshot({"project": root})
    with pytest.raises(AssertionError, match="Filesystem changed"):
        assert_unchanged(before, after)
    key = ("project", {"mkdir": "new", "rmdir": "empty", "unlink": "link", "retarget": "link"}.get(mutation, "ignored"))
    # A blinded observer loses this witness even when incidental parent mtimes
    # are restored. This control does not modify the real raw snapshots.
    blinded = dict(after)
    for path, node in before.items():
        if path in blinded and node.kind == "directory":
            blinded[path] = replace(blinded[path], mtime_ns=node.mtime_ns)
    if key in before:
        blinded[key] = before[key]
    else:
        del blinded[key]
    assert_unchanged(before, blinded)
    if mutation != "mtime":
        expected = {"ignored": "update", "mkdir": "create", "rmdir": "delete", "unlink": "delete", "retarget": "retarget", "chmod": "chmod"}[mutation]
        assert [(effect.path, effect.action) for effect in net_delta(before, after)] == [(key[1], expected)]


def test_absent_roots_and_creation_mode_are_not_lost(tmp_path: Path) -> None:
    root = tmp_path / "absent"
    before = snapshot({"home": root})
    assert before[("home", ".")].kind == "absent"
    root.mkdir(mode=0o700)
    (root / "executable").write_bytes(b"data")
    (root / "executable").chmod(0o755)
    after = snapshot({"home": root})
    assert [(e.path, e.action) for e in net_delta(before, after)] == [(".", "create"), ("executable", "create")]
    assert after[("home", "executable")].mode == 0o755


def test_symlinks_are_not_followed_and_type_changes_are_replacements(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    target = tmp_path / "target"
    target.mkdir()
    (target / "sentinel").write_bytes(b"untouched")
    link = root / "link"
    link.symlink_to(target)
    before = snapshot({"project": root})
    assert ("project", "link/sentinel") not in before
    link.unlink()
    link.write_bytes(b"copy")
    assert [(e.path, e.action) for e in net_delta(before, snapshot({"project": root}))] == [("link", "replace")]
    assert (target / "sentinel").read_bytes() == b"untouched"


def test_child_environment_seals_fixture_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GH_TOKEN", "not-a-real-token")
    monkeypatch.setenv("PYTHONPATH", "/wrong/source")
    monkeypatch.setenv("SPEC_KITTY_TEMPLATE_ROOT", "/wrong/templates")
    env = child_environment(tmp_path, {"SPEC_KITTY_ENABLE_SAAS_SYNC": "1", "HOME": "/wrong/home"})
    assert env["SPEC_KITTY_ENABLE_SAAS_SYNC"] == "0"
    assert "GH_TOKEN" not in env and "PYTHONPATH" not in env
    assert "SPEC_KITTY_TEMPLATE_ROOT" not in env
    roots = ["HOME", "USERPROFILE", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "XDG_STATE_HOME", "APPDATA", "LOCALAPPDATA", "SPEC_KITTY_HOME", "TMPDIR", "TMP", "TEMP"]
    assert all(Path(env[key]).is_relative_to(tmp_path) for key in roots)
    assert not (tmp_path / "home").exists()
    result = run_process([str(LANE / ".venv/bin/python"), "-c", "import json, os; print(json.dumps(dict(os.environ)))"], tmp_path, env)
    assert result.json()["HOME"] == env["HOME"]


def test_provenance_rejects_other_checkout(tmp_path: Path) -> None:
    env = child_environment(tmp_path)
    identity = identify_source(LANE / ".venv/bin/spec-kitty", LANE, env)
    assert Path(identity.module).is_relative_to(LANE.resolve() / "src")
    assert identity.version and identity.commit and identity.interpreter
    other = tmp_path / "other-checkout"
    other.mkdir()
    with pytest.raises(AssertionError, match="Source mismatch"):
        identify_source(LANE / ".venv/bin/spec-kitty", other, env)


@pytest.mark.parametrize("output", ["", "banner\n{}", "{}\n{}"])
def test_machine_output_must_be_one_complete_value(tmp_path: Path, output: str) -> None:
    result = run_process([str(LANE / ".venv/bin/python"), "-c", f"print({output!r})"], tmp_path, child_environment(tmp_path))
    with pytest.raises((AssertionError, json.JSONDecodeError)):
        result.json()


def test_startup_failure_cannot_pass_purity(tmp_path: Path) -> None:
    result = run_process([str(LANE / ".venv/bin/python"), "-c", "raise RuntimeError('startup control')"], tmp_path, child_environment(tmp_path))
    with pytest.raises(AssertionError, match="Command failed"):
        result.require_success()
