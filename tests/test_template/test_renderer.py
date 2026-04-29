from __future__ import annotations

from pathlib import Path

from specify_cli.template.renderer import (
    parse_frontmatter,
    render_template,
    render_template_text,
    rewrite_paths,
)


def test_parse_frontmatter_returns_metadata_body_and_raw() -> None:
    content = """---
description: Demo
scripts:
  sh: echo hi
---
Hello world
"""
    metadata, body, raw = parse_frontmatter(content)

    assert metadata["description"] == "Demo"
    assert metadata["scripts"]["sh"] == "echo hi"
    assert body.strip() == "Hello world"
    assert "scripts:" in raw


def test_render_template_applies_callable_variables_and_rewrites_paths(tmp_path: Path) -> None:
    template_path = tmp_path / "cmd.md"
    template_path.write_text(
        """---
description: Replace tokens
scripts:
  sh: ./scripts/run.sh
---
Use {SCRIPT} for __AGENT__ via templates/commands/demo.md.
""",
        encoding="utf-8",
    )

    metadata, rendered, raw = render_template(
        template_path,
        lambda meta: {"{SCRIPT}": meta["scripts"]["sh"], "__AGENT__": "codex"},
    )

    assert metadata["description"] == "Replace tokens"
    assert "Use ./.kittify/scripts/run.sh for codex" in rendered
    assert ".kittify/templates/commands/demo.md" in rendered
    assert "scripts:" in raw


def test_render_template_text_uses_supplied_text_instead_of_rereading_path(tmp_path: Path) -> None:
    template_path = tmp_path / "cmd.md"
    template_path.write_text(
        """---
description: Original
scripts:
  sh: echo original
---
Original body
""",
        encoding="utf-8",
    )

    metadata, rendered, _raw = render_template_text(
        """---
description: Processed
scripts:
  sh: echo processed
---
Run {SCRIPT}
""",
        lambda meta: {"{SCRIPT}": meta["scripts"]["sh"]},
        template_path=template_path,
    )

    assert metadata["description"] == "Processed"
    assert "Run echo processed" in rendered
    assert "Original body" not in rendered


def test_rewrite_paths_accepts_custom_patterns() -> None:
    result = rewrite_paths("Use foo/path", {"foo/path": "bar/path"})
    assert result == "Use bar/path"


def test_rewrite_paths_keeps_source_template_paths() -> None:
    source_path = "src/specify_cli/missions/software-dev/templates/spec-template.md"
    assert rewrite_paths(source_path) == source_path
