"""Lock the canonical requirements-checklist artifact contract (C-003).

The deprecated `/spec-kitty.checklist` slash-command surface was retired
in WP04 (FR-003 / FR-004 / #815). The canonical
`kitty-specs/<mission>/checklists/requirements.md` artifact MUST keep
working — it is created by `/spec-kitty.specify` during spec authoring
and is the gate that the planning flow checks before advancing.

This test locks two layers so future cleanup never accidentally removes
the artifact:

1. The `software-dev` mission's `specify.md` source template still
   contains an explicit instruction to create the file at
   `feature_dir/checklists/requirements.md`.
2. The `software-dev` mission's `mission.yaml` still declares
   `checklists/` as an optional artifact directory.

Both checks are static (no subprocess, no filesystem mutation) so the
test is fast and deterministic.
"""

from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]

SOFTWARE_DEV_DIR = (
    REPO_ROOT / "src" / "specify_cli" / "missions" / "software-dev"
)
SPECIFY_TEMPLATE = SOFTWARE_DEV_DIR / "command-templates" / "specify.md"
MISSION_YAML = SOFTWARE_DEV_DIR / "mission.yaml"


def test_specify_template_creates_requirements_checklist() -> None:
    """`specify.md` must instruct creation of `checklists/requirements.md`.

    This is the canonical artifact contract C-003. If a future template
    edit drops this instruction, the `/spec-kitty.specify` flow would
    silently stop creating the requirements checklist — breaking the
    quality gate the planning flow depends on.
    """
    assert SPECIFY_TEMPLATE.exists(), (
        f"Source template missing: {SPECIFY_TEMPLATE}.\n"
        "The software-dev /spec-kitty.specify template is the canonical "
        "owner of the requirements-checklist artifact."
    )
    text = SPECIFY_TEMPLATE.read_text(encoding="utf-8")
    assert "checklists/requirements.md" in text, (
        "specify.md no longer references `checklists/requirements.md`. "
        "The canonical requirements checklist artifact (C-003) must be "
        "created by /spec-kitty.specify; do not remove that instruction "
        "without an explicit migration plan."
    )


def test_software_dev_mission_declares_checklists_directory() -> None:
    """`mission.yaml` must list `checklists/` as an optional artifact.

    The mission contract enumerates the artifact directories produced by
    each phase. `checklists/` is the home of the canonical requirements
    checklist (and any user-added domain checklists); removing it from
    the artifact list would weaken the contract.
    """
    assert MISSION_YAML.exists(), f"mission.yaml missing: {MISSION_YAML}"
    data = yaml.safe_load(MISSION_YAML.read_text(encoding="utf-8"))
    artifacts = data.get("artifacts", {}) or {}
    optional = artifacts.get("optional", []) or []
    assert "checklists/" in optional, (
        "software-dev/mission.yaml no longer declares `checklists/` as "
        "an optional artifact directory. The canonical requirements "
        "checklist lives there; do not remove without a migration plan."
    )
