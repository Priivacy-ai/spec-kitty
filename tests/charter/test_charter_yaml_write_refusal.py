"""A YAML writer must refuse interference before publishing completion proof."""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.activation import charter_yaml_io as yaml_io

pytestmark = pytest.mark.unit


def test_applied_receipt_rejects_corrupted_prepared_bytes(tmp_path: Path) -> None:
    target = tmp_path / "charter.yaml"
    desired = b"metadata: {owner: writer}\n"
    prepared = yaml_io.prepare_yaml_write(target, desired, section="metadata")
    assert yaml_io.apply_yaml_write(prepared)
    assert prepared.recheck_applied() == (target,)

    # Simulate corrupted preparation state on the same receipt-owning object;
    # a copied object would exercise only the separate receipt identity guard.
    object.__setattr__(prepared, "desired_bytes", b"metadata: {owner: corrupt}\n")
    with pytest.raises(ValueError, match="precondition_changed: prepared bytes"):
        prepared.recheck_applied()
    assert target.read_bytes() == desired


def test_apply_refuses_replaced_created_parent_without_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    parent = tmp_path / "new"
    target = parent / "charter.yaml"
    retired_parent = tmp_path / "writer-created"
    customized = b"operator-owned notes\n"
    prepared = yaml_io.prepare_yaml_write(target, b"metadata: {}\n", section="metadata")
    real_chmod = Path.chmod

    def replace_after_chmod(path: Path, mode: int, *, follow_symlinks: bool = True) -> None:
        real_chmod(path, mode, follow_symlinks=follow_symlinks)
        if path == parent:
            path.rename(retired_parent)
            path.mkdir()
            (path / "notes.txt").write_bytes(customized)

    monkeypatch.setattr(Path, "chmod", replace_after_chmod)
    with pytest.raises(ValueError, match="precondition_changed: YAML created parent"):
        yaml_io.apply_yaml_write(prepared)
    assert retired_parent.is_dir()
    assert (parent / "notes.txt").read_bytes() == customized
    assert not target.exists()
    with pytest.raises(ValueError, match="no completion receipt"):
        prepared.recheck_applied()


def test_apply_refuses_target_rewritten_during_readback_without_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "charter.yaml"
    customized = b"metadata: {owner: operator}\n"
    prepared = yaml_io.prepare_yaml_write(target, b"metadata: {owner: writer}\n", section="metadata")
    observe = yaml_io.observe_yaml_input
    interfered = []

    def rewrite_before_observation(path: Path) -> yaml_io._YamlInput:
        # The initial recheck sees an absent target. The first existing-target
        # read is the post-flush observation paired with the real fstat result.
        if path == target and target.exists() and not interfered:
            target.write_bytes(customized)
            interfered.append(path)
        return observe(path)

    monkeypatch.setattr(yaml_io, "observe_yaml_input", rewrite_before_observation)
    with pytest.raises(ValueError, match="precondition_changed: YAML written target"):
        yaml_io.apply_yaml_write(prepared)
    assert interfered == [target]
    assert target.read_bytes() == customized
    with pytest.raises(ValueError, match="no completion receipt"):
        prepared.recheck_applied()


def test_apply_refuses_changed_input_before_publishing_receipt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "source.yaml"
    source.write_bytes(b"choice: original\n")
    customized = b"choice: operator\n"
    target = tmp_path / "charter.yaml"
    desired = b"metadata: {owner: writer}\n"
    prepared = yaml_io.prepare_yaml_write(target, desired, section="metadata", inputs=(yaml_io.observe_yaml_input(source),))
    observe = yaml_io.observe_yaml_input
    interfered = []

    def rewrite_input_after_target_observation(path: Path) -> yaml_io._YamlInput:
        result = observe(path)
        if path == target and result.content == desired and not interfered:
            source.write_bytes(customized)
            interfered.append(source)
        return result

    monkeypatch.setattr(yaml_io, "observe_yaml_input", rewrite_input_after_target_observation)
    with pytest.raises(ValueError, match="precondition_changed: .*source.yaml"):
        yaml_io.apply_yaml_write(prepared)
    assert interfered == [source]
    assert source.read_bytes() == customized
    assert target.read_bytes() == desired  # A completed write is not a completed proof.
    with pytest.raises(ValueError, match="no completion receipt"):
        prepared.recheck_applied()
