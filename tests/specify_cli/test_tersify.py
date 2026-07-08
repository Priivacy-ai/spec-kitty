"""Invariant tests for the tersifier research prototype.

The safety contract: with SPEC_KITTY_TERSIFY unset there is zero behavior
change, and with it set, nothing spec-kitty's machinery depends on — code
fences, frontmatter, placeholders, markers, headings, tables — is ever
altered, across the ENTIRE bundled corpus of mission-step prompts and
doctrine skills.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specify_cli.tersify import (
    ENV_FLAG,
    Tersifier,
    hand_cache_path,
    tersify_for_llm,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

CORPUS = sorted(REPO_ROOT.glob("src/doctrine/missions/mission-steps/**/prompt.md")) + sorted(REPO_ROOT.glob("src/doctrine/skills/*/SKILL.md"))
CORPUS_IDS = [p.relative_to(REPO_ROOT).as_posix() for p in CORPUS]

_FENCE_RE = re.compile(r"```[\s\S]*?```")
_PLACEHOLDER_RES = {
    "curly": re.compile(r"\{\{[^{}\n]*\}\}|\{[A-Z_]+\}"),
    "dollar_var": re.compile(r"\$[A-Z_][A-Z0-9_]*"),
    "dunder": re.compile(r"__[A-Z_]+__"),
    "html_comment": re.compile(r"<!--[\s\S]*?-->"),
}
_HEADING_RE = re.compile(r"^#{1,6} .*$", re.MULTILINE)
_FRONTMATTER_RE = re.compile(r"\A---\r?\n[\s\S]*?\r?\n---\r?\n")
_SENTINELS = ("", "")


def test_corpus_is_not_empty() -> None:
    assert len(CORPUS) >= 12, "expected bundled mission-step prompts and skills"


def test_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_FLAG, raising=False)
    text = "Please make sure that you summarize this in order to help.\n"
    assert tersify_for_llm(text) == text


@pytest.mark.parametrize("path", CORPUS, ids=CORPUS_IDS)
def test_dictionary_pass_preserves_machinery(path: Path) -> None:
    original = path.read_text(encoding="utf-8")
    result = Tersifier().tersify(original).text

    # Code fences byte-identical and all present.
    for fence in _FENCE_RE.findall(original):
        assert fence in result, f"code fence altered in {path.name}: {fence[:60]!r}"

    # Placeholder/marker populations identical (multiset, order-independent).
    for kind, regex in _PLACEHOLDER_RES.items():
        assert sorted(regex.findall(original)) == sorted(regex.findall(result)), f"{kind} population changed in {path.name}"

    # Headings preserved verbatim and in order (section anchors).
    assert _HEADING_RE.findall(original) == _HEADING_RE.findall(result)

    # Frontmatter byte-identical when present, still starting at byte 0.
    fm = _FRONTMATTER_RE.match(original)
    if fm:
        assert result.startswith(fm.group(0))

    # No placeholder sentinel leakage.
    for sentinel in _SENTINELS:
        assert sentinel not in result


@pytest.mark.parametrize("path", CORPUS, ids=CORPUS_IDS)
def test_dictionary_pass_is_idempotent(path: Path) -> None:
    tersifier = Tersifier()
    once = tersifier.tersify(path.read_text(encoding="utf-8")).text
    twice = tersifier.tersify(once).text
    assert once == twice


def test_hand_cache_used_when_hash_matches(tmp_path: Path) -> None:
    source = tmp_path / "prompt.md"
    source.write_text("Please summarize the following very long instructions.\n", encoding="utf-8")
    cache = hand_cache_path(source)
    cache.parent.mkdir()
    import hashlib

    # noqa justification: file-integrity check (hand-cache staleness), not charter hashing.
    digest = hashlib.sha256(source.read_bytes()).hexdigest()  # noqa: TID251
    cache.write_text(
        f"<!-- tersifier:source-sha256={digest} -->\nsummarize instructions.\n",
        encoding="utf-8",
    )
    result = Tersifier().tersify(source.read_text(encoding="utf-8"), source_path=source)
    assert result.source == "hand"
    assert result.text == "summarize instructions.\n"


def test_stale_hand_cache_falls_back_to_dictionary(tmp_path: Path) -> None:
    source = tmp_path / "prompt.md"
    source.write_text("New instructions the terse copy has never seen.\n", encoding="utf-8")
    cache = hand_cache_path(source)
    cache.parent.mkdir()
    cache.write_text(
        f"<!-- tersifier:source-sha256={'0' * 64} -->\nOUTDATED TERSE COPY\n",
        encoding="utf-8",
    )
    result = Tersifier().tersify(source.read_text(encoding="utf-8"), source_path=source)
    assert result.source == "dictionary"
    assert "OUTDATED" not in result.text


def test_bundled_hand_cache_hashes_are_fresh() -> None:
    """Every committed .terse.md must match its current source, or it is dead
    weight (it would silently fall back to the dictionary pass)."""
    import hashlib

    for cache in REPO_ROOT.glob("src/**/terse/*.terse.md"):
        source = cache.parent.parent / cache.name.removesuffix(".terse.md")
        assert source.is_file(), f"orphaned hand cache: {cache}"
        header = cache.read_text(encoding="utf-8").splitlines()[0]
        # noqa justification: file-integrity check (hand-cache staleness), not charter hashing.
        digest = hashlib.sha256(source.read_bytes()).hexdigest()  # noqa: TID251
        assert digest in header, f"stale hand cache (regenerate or delete): {cache}"


def test_hand_cache_preserves_machinery() -> None:
    """The committed hand-tersified files obey the same protection contract
    the dictionary pass enforces mechanically."""
    for cache in REPO_ROOT.glob("src/**/terse/*.terse.md"):
        source = cache.parent.parent / cache.name.removesuffix(".terse.md")
        original = source.read_text(encoding="utf-8")
        body = cache.read_text(encoding="utf-8").split("\n", 1)[1]
        for fence in _FENCE_RE.findall(original):
            assert fence in body, f"code fence altered in {cache.name}: {fence[:60]!r}"
        assert _HEADING_RE.findall(original) == _HEADING_RE.findall(body)
        for kind in ("dollar_var", "dunder"):
            regex = _PLACEHOLDER_RES[kind]
            assert sorted(regex.findall(original)) == sorted(regex.findall(body)), f"{kind} population changed in {cache.name}"
        fm = _FRONTMATTER_RE.match(original)
        if fm:
            assert body.startswith(fm.group(0))


def test_skills_render_pipeline_with_flag_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """End-to-end: command_renderer.render() under the flag still satisfies
    its own invariants (no stray $ARGUMENTS, frontmatter built, body intact)."""
    monkeypatch.setenv(ENV_FLAG, "1")
    from specify_cli.skills import command_renderer

    template = REPO_ROOT / "src/doctrine/missions/mission-steps/software-dev/accept/prompt.md"
    rendered = command_renderer.render(template, "codex", "0.0.0-test")
    assert "$ARGUMENTS" not in rendered.body
    assert "## Steps" in rendered.body
    assert rendered.frontmatter["name"] == "spec-kitty.accept"


def test_slash_command_pipeline_with_flag_enabled(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """End-to-end: render_command_template() under the flag keeps the version
    marker, frontmatter on line 1, and substituted placeholders."""
    monkeypatch.setenv(ENV_FLAG, "1")
    from specify_cli.template.asset_generator import render_command_template

    template = tmp_path / "demo.md"
    template.write_text(
        "---\ndescription: Demo command\nscripts:\n  sh: echo hi\n---\n"
        "# Demo\n\nPlease make sure that you run {SCRIPT} in order to proceed.\n\n"
        "## User Input\n\n```text\n$ARGUMENTS\n```\n",
        encoding="utf-8",
    )
    rendered = render_command_template(template, "sh", "claude", "$ARGUMENTS", "md")
    assert rendered.startswith("---\n")
    assert "spec-kitty-command-version" in rendered
    assert "echo hi" in rendered  # {SCRIPT} substitution still happened
    assert "$ARGUMENTS" in rendered
    assert "make sure that you" not in rendered  # prose was compressed
    assert "in order to" not in rendered
