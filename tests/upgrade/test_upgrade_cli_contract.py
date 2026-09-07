"""Public upgrade contracts, using the ordinary executable and independent oracle."""

from __future__ import annotations

import json
import os
from pathlib import Path

import jsonschema
import pytest

from tests.upgrade.preview_support.fixtures import prepare_case
from tests.upgrade.preview_support.snapshot import assert_unchanged

pytestmark = pytest.mark.integration
CHECKOUT = Path(__file__).resolve().parents[2]


def test_project_json_downgrade_refuses_without_dry_run(tmp_path: Path) -> None:
    """Implicit preview must reject a lower target semantically and by process."""
    case = prepare_case(tmp_path / "case", CHECKOUT)
    before = case.observe()
    result = case.run("upgrade", "--project", "--json", "--target=3.2.6", "--no-worktrees")
    after = case.observe()
    evidence = Path(os.environ.get("WP10_EVIDENCE_ROOT", str(tmp_path / "evidence")))
    case.retain(evidence / "project-json-downgrade", result, before, after)

    payload = result.json()
    schema_path = CHECKOUT / (
        "kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/"
        "contracts/compat-planner.json"
    )
    jsonschema.Draft202012Validator(json.loads(schema_path.read_text())).validate(payload)
    assert payload["project"]["state"] == "compatible", payload
    assert payload["decision"] == "BLOCK_INCOMPATIBLE_FLAGS", payload
    assert payload["case"] == "none", payload
    assert payload["exit_code"] == 2, payload
    assert payload["pending_migrations"] == [], payload
    assert payload["rendered_human"] == (
        "Refusing to downgrade project metadata from 3.2.7rc1 to 3.2.6"
    )
    assert result.returncode == 2, result
    assert_unchanged(before, after)
