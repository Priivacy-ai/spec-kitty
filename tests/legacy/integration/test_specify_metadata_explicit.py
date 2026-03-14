from __future__ import annotations

from tests.integration.test_specify_metadata_explicit import REPO_ROOT


def test_template_fix_applies_to_all_agents() -> None:
    """Template fix should remain visible across legacy agent templates."""
    source_template = REPO_ROOT / "src/specify_cli/missions/software-dev/command-templates/specify.md"

    assert source_template.exists(), "Source template should exist"

    content = source_template.read_text()

    assert '"target_branch":' in content, "Template should include target_branch in meta.json schema"
    assert '"vcs":' in content, "Template should include vcs in meta.json schema"
    assert "target_branch" in content, "Template should document target_branch"
    assert "vcs" in content or "VCS" in content, "Template should document vcs"
