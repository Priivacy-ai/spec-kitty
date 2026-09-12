"""Explicit checkout ownership reaches real authoring and context readers."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import app as charter_app

pytestmark = [pytest.mark.integration, pytest.mark.git_repo]
runner = CliRunner()


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _policy(root: Path, name: str) -> None:
    charter = root / ".kittify/charter"
    charter.mkdir(parents=True, exist_ok=True)
    (charter / "charter.md").write_text(f"# Project Charter\n\n## Policy Summary\n\n- {name} policy.\n\n## Code Review Checklist\n\n- {name} policy.\n")
    (charter / "charter.yaml").write_text(
        f"directives:\n  directives:\n    - id: PROJECT_{name}\n      title: {name} policy\n      description: Only {name} governs this checkout.\n"
    )
    (root / ".kittify/config.yaml").write_text("mission_type_activations:\n  - software-dev\n")


@pytest.fixture
def checkouts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    primary = (tmp_path / "primary").resolve()
    primary.mkdir()
    _git(primary, "init", "--quiet", "--initial-branch=main")
    _git(primary, "config", "user.email", "checkout@example.invalid")
    _git(primary, "config", "user.name", "Checkout Test")
    _policy(primary, "PRIMARY")
    _git(primary, "add", ".kittify")
    _git(primary, "commit", "--quiet", "-m", "Seed primary policy")
    lane = (tmp_path / "lane").resolve()
    _git(primary, "worktree", "add", "--quiet", "-b", "codex/policy", str(lane))
    _policy(lane, "OWNED")
    nested = lane / "nested"
    nested.mkdir()
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.chdir(nested)
    return primary, lane


def _snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes() for p in (root / ".kittify").rglob("*") if p.is_file()}


def test_owned_new_writes_only_selected_checkout(checkouts: tuple[Path, Path]) -> None:
    primary, lane = checkouts
    before = _snapshot(primary)
    result = runner.invoke(charter_app, ["new", "directive", "OWNED_NEW", "--owned-checkout", str(lane)])
    assert result.exit_code == 0, result.output
    target = Path(".kittify/doctrine/directive/OWNED_NEW.directive.yaml")
    assert (lane / target).is_file()
    assert not (primary / target).exists()
    assert _snapshot(primary) == before


@pytest.mark.parametrize("mode", ["text", "json", "include"])
def test_owned_context_reads_selected_policy_without_primary_writes(checkouts: tuple[Path, Path], mode: str) -> None:
    primary, lane = checkouts
    before = _snapshot(primary)
    args = ["context", "--owned-checkout", str(lane), "--no-mark-loaded"]
    if mode == "include":
        args += ["--include", "section:code-review-checklist"]
    else:
        args += ["--action", "implement"]
        if mode == "json":
            args.append("--json")
    result = runner.invoke(charter_app, args)
    assert result.exit_code == 0, result.output
    if mode == "json":
        payload = json.loads(result.output)
        assert any(item["id"] == "PROJECT_OWNED" for item in payload["all_directives"])
        assert all(item["id"] != "PROJECT_PRIMARY" for item in payload["all_directives"])
    else:
        assert "OWNED policy" in result.output
        assert "PRIMARY policy" not in result.output
    assert _snapshot(primary) == before


@pytest.mark.parametrize("command", ["new", "context"])
@pytest.mark.parametrize("invalid", ["foreign", "nested", "missing"])
def test_invalid_owned_checkout_refuses_without_writes(checkouts: tuple[Path, Path], tmp_path: Path, command: str, invalid: str) -> None:
    primary, lane = checkouts
    target = tmp_path / invalid
    if invalid == "foreign":
        target.mkdir()
        _git(target, "init", "--quiet")
    elif invalid == "nested":
        target = lane / "nested"
    before = _snapshot(primary), _snapshot(lane)
    args = ["new", "directive", "REFUSED"] if command == "new" else ["context", "--action", "implement"]
    result = runner.invoke(charter_app, [*args, "--owned-checkout", str(target)])
    assert result.exit_code != 0
    assert (_snapshot(primary), _snapshot(lane)) == before


def test_owned_new_refuses_symlink_escape(checkouts: tuple[Path, Path], tmp_path: Path) -> None:
    primary, lane = checkouts
    outside = tmp_path / "outside"
    outside.mkdir()
    (lane / ".kittify/doctrine").symlink_to(outside, target_is_directory=True)
    result = runner.invoke(charter_app, ["new", "directive", "ESCAPE", "--owned-checkout", str(lane)])
    assert result.exit_code != 0
    assert not list(outside.iterdir())
    assert not (primary / ".kittify/doctrine/directive/ESCAPE.directive.yaml").exists()


def test_default_context_after_owned_call_retains_primary_policy(checkouts: tuple[Path, Path]) -> None:
    _primary, lane = checkouts
    owned = runner.invoke(charter_app, ["context", "--owned-checkout", str(lane), "--include", "section:code-review-checklist"])
    assert owned.exit_code == 0
    default = runner.invoke(charter_app, ["context", "--include", "section:code-review-checklist"])
    assert default.exit_code == 0
    assert "PRIMARY policy" in default.output
    assert "OWNED policy" not in default.output


def test_scoped_reads_refuse_escape_and_restore_after_error(checkouts: tuple[Path, Path]) -> None:
    from charter.activation.checkout_scope import charter_checkout_scope, selected_charter_checkout

    primary, lane = checkouts
    with pytest.raises(ValueError, match="escapes"), charter_checkout_scope(lane):
        assert selected_charter_checkout(lane / "nested") == lane
        selected_charter_checkout(primary)
    assert selected_charter_checkout(primary) is None


def test_nested_scopes_restore_and_refuse_foreign_repository(checkouts: tuple[Path, Path], tmp_path: Path) -> None:
    from charter.activation.checkout_scope import charter_checkout_scope, selected_charter_checkout

    primary, lane = checkouts
    foreign = tmp_path / "foreign-scope"
    foreign.mkdir()
    _git(foreign, "init", "--quiet")
    with charter_checkout_scope(lane):
        with charter_checkout_scope(primary):
            assert selected_charter_checkout(primary) == primary
        assert selected_charter_checkout(lane) == lane
        with pytest.raises(ValueError, match="another repository"), charter_checkout_scope(foreign):
            pytest.fail("Foreign checkout scope must not open")
        assert selected_charter_checkout(lane) == lane
    assert selected_charter_checkout(primary) is None
    with pytest.raises(ValueError, match="checkout root"), charter_checkout_scope(lane / "nested"):
        pytest.fail("Nested directory must not become checkout root")


def test_concurrent_checkout_scopes_are_isolated(checkouts: tuple[Path, Path]) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from charter.activation.checkout_scope import charter_checkout_scope, selected_charter_checkout

    primary, lane = checkouts
    barrier = Barrier(2)

    def read(root: Path) -> Path | None:
        with charter_checkout_scope(root):
            barrier.wait(timeout=10)
            return selected_charter_checkout(root)

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(read, [primary, lane])) == [primary, lane]
    assert selected_charter_checkout(primary) is None
