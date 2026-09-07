"""Public upgrade contracts, using the ordinary executable and independent oracle."""

from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema
import pytest

from tests.upgrade.preview_support.fixtures import prepare_case
from tests.upgrade.preview_support.snapshot import assert_unchanged, net_delta

pytestmark = pytest.mark.integration
CHECKOUT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("target", "message"),
    [
        ("3.2.6", "Refusing to downgrade project metadata from 3.2.7rc1 to 3.2.6"),
        ("not-a-version", "Invalid upgrade target version: not-a-version"),
    ],
    ids=["downgrade", "malformed"],
)
def test_project_json_downgrade_refuses_without_dry_run(tmp_path: Path, target: str, message: str) -> None:
    """Implicit preview must reject a lower target semantically and by process."""
    case = prepare_case(tmp_path / "case", CHECKOUT)
    before = case.observe()
    result = case.run("upgrade", "--project", "--json", f"--target={target}", "--no-worktrees")
    after = case.observe()
    evidence = Path(os.environ.get("WP10_EVIDENCE_ROOT", str(tmp_path / "evidence")))
    case.retain(evidence / ("project-json-" + target), result, before, after)

    payload = result.json()
    schema_path = CHECKOUT / ("kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json")
    jsonschema.Draft202012Validator(json.loads(schema_path.read_text())).validate(payload)
    assert payload["project"]["state"] == "compatible", payload
    assert payload["decision"] == "BLOCK_INCOMPATIBLE_FLAGS", payload
    assert payload["case"] == "none", payload
    assert payload["exit_code"] == 2, payload
    assert payload["pending_migrations"] == [], payload
    assert payload["rendered_human"] == message
    assert result.returncode == 2, result
    assert_unchanged(before, after)


@pytest.mark.parametrize(
    "hidden",
    [("--agent-check",), ("--agent-choice", "skip"), ("--agent-latest", "9.0.0")],
    ids=["check", "choice", "latest"],
)
def test_implicit_project_preview_rejects_hidden_operations(tmp_path: Path, hidden: tuple[str, ...]) -> None:
    """Effective preview wins before hidden dispatch or cold-home startup."""
    case = prepare_case(tmp_path / "case", CHECKOUT, global_state="G0")
    before = case.observe()
    result = case.run("upgrade", "--project", "--json", "--no-worktrees", *hidden)
    after = case.observe()
    evidence = Path(os.environ.get("WP10_EVIDENCE_ROOT", str(tmp_path / "evidence")))
    case.retain(evidence / ("implicit-hidden-" + hidden[0].removeprefix("--")), result, before, after)
    payload = result.json()
    schema_path = CHECKOUT / "kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json"
    jsonschema.Draft202012Validator(json.loads(schema_path.read_text())).validate(payload)
    assert payload["decision"] == "BLOCK_INCOMPATIBLE_FLAGS"
    assert payload["case"] == "none"
    assert payload["exit_code"] == result.returncode == 2
    assert payload["pending_migrations"] == []
    assert "Hidden agent operations" in payload["rendered_human"]
    assert_unchanged(before, after)


def test_cold_preview_and_valid_actual_apply_share_complete_preparation(tmp_path: Path) -> None:
    """Pure healthy preview cannot be delivered by merely disabling bootstrap."""
    case = prepare_case(tmp_path / "case", CHECKOUT, global_state="G0")
    before = case.observe()
    preview = case.run("upgrade", "--dry-run", "--json", "--no-worktrees")
    after_preview = case.observe()
    evidence = Path(os.environ.get("WP10_EVIDENCE_ROOT", str(tmp_path / "evidence")))
    case.retain(evidence / "cold-preview", preview, before, after_preview)
    assert preview.returncode == 0, preview
    assert preview.json()["decision"] in {"ALLOW", "ALLOW_WITH_NAG"}
    assert_unchanged(before, after_preview)

    applied = case.run("upgrade", "--json", "--yes", "--no-worktrees")
    after_apply = case.observe()
    case.retain(evidence / "cold-apply", applied, after_preview, after_apply)
    assert applied.returncode == 0, applied
    assert applied.json()["success"] is True
    assert any(effect.root == "home" for effect in net_delta(after_preview, after_apply))
    for marker in ("version.lock", "agent-skills.lock", "agent-commands.lock"):
        assert list(Path(case.env["HOME"]).rglob(marker)), marker

    repeated = case.run("upgrade", "--json", "--yes", "--no-worktrees")
    after_repeat = case.observe()
    case.retain(evidence / "cold-repeat", repeated, after_apply, after_repeat)
    assert repeated.returncode == 0, repeated
    assert_unchanged(after_apply, after_repeat)
