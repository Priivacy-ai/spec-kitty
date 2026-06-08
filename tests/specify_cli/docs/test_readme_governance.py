"""WP03 — README Governance layer subsection regression tests."""
import re
from pathlib import Path


import pytest

pytestmark = [pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[3]
README = REPO_ROOT / "README.md"


def test_readme_has_governance_layer_section() -> None:
    content = README.read_text()
    assert "## Governance layer" in content, (
        "README.md must contain a '## Governance layer' subsection "
        "(WP03 / FR-005)."
    )


def test_governance_section_links_to_trail_model() -> None:
    content = README.read_text()
    gov_idx = content.index("## Governance layer")
    # Next top-level section or EOF
    next_h2 = content.find("\n## ", gov_idx + 1)
    section = content[gov_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "docs/trail-model.md" in section, (
        "Governance layer subsection must link to docs/trail-model.md."
    )


def test_governance_section_links_to_host_surface_parity() -> None:
    content = README.read_text()
    gov_idx = content.index("## Governance layer")
    next_h2 = content.find("\n## ", gov_idx + 1)
    section = content[gov_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "docs/host-surface-parity.md" in section, (
        "Governance layer subsection must link to docs/host-surface-parity.md."
    )


def test_governance_section_mentions_advise_ask_do() -> None:
    content = README.read_text()
    gov_idx = content.index("## Governance layer")
    next_h2 = content.find("\n## ", gov_idx + 1)
    section = content[gov_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "spec-kitty advise" in section
    assert "spec-kitty ask" in section
    assert "spec-kitty do" in section


def test_runtime_next_skill_references_resolve() -> None:
    skill = REPO_ROOT / "src/doctrine/skills/spec-kitty-runtime-next/SKILL.md"
    content = skill.read_text()
    links = re.findall(r"\]\(([^)#]+\.md)\)", content)
    for link in links:
        if link.startswith("/") or link.startswith("http"):
            continue
        target = (skill.parent / link).resolve()
        assert target.exists(), f"Broken link in runtime-next/SKILL.md: {link}"


def test_runtime_next_skill_documents_omitted_result_as_query_mode() -> None:
    skill = REPO_ROOT / "src/doctrine/skills/spec-kitty-runtime-next/SKILL.md"
    content = skill.read_text()

    assert "Defaults to `success` if omitted." not in content
    assert (
        "If omitted, `spec-kitty next` returns current state without advancing "
        "(query mode)."
    ) in content
