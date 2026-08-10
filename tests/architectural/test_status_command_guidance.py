"""Keep #2983's scoped guidance aligned with the compiled Click/Typer command tree.

Mission ``annoying-bugs-sweep-01KYHQ9F`` / WP04 removed concrete examples of the
nonexistent top-level ``spec-kitty status`` command from the canonical
plain-language styleguide and four published documentation pages. This guard
prevents the recurrence.

Two properties matter, and both are enforced below:

1. **Only concrete invocations are extracted.** A command is extracted only when
   it stands in *command position* inside a fenced code block or an inline code
   span. Narrative prose such as "spec-kitty prints a single banner before
   normal output" is not an invocation and must never be scanned as one.
2. **Resolution happens against the compiled Click command tree.** Typer
   normalizes callback names when it builds the Click parser
   (``verify_setup`` -> ``verify-setup``), so raw registration metadata is *not*
   an authority for what the CLI accepts. This guard resolves through
   ``typer.main.get_command()`` -- the same object ``spec-kitty`` dispatches on.

Both a source denominator and an invocation denominator are asserted so that
deleting a scoped file, or silently dropping the examples, cannot green the
gate. ``test_guard_reddens_on_a_planted_phantom_command`` mutates a real scoped
source and pushes it through the identical extraction + resolution path,
proving the gate is non-vacuous.
"""

from __future__ import annotations

import functools
import os
import re
import sys
from collections.abc import Iterable, Iterator
from pathlib import Path

import click
import pytest
import typer
import typer.main

# SPEC_KITTY_ENABLE_SAAS_SYNC is set collection-wide in tests/conftest.py
# pytest_configure (#3213), not per-module.
os.environ.setdefault("SPEC_KITTY_NO_UPGRADE_CHECK", "1")

#: ``architectural`` is what the always-on ``arch-adversarial`` CI pole selects
#: (``-m '<arch_shard_N> and not windows_ci and (git_repo or integration or
#: architectural) and not timing'``); without it the ``arch_shard_N`` marker the
#: hash-bucket fallback applies is not enough and every test here is deselected.
#: ``docs_scoped`` additionally keeps the guard in the pole's docs-only trim
#: (``-m '<arch_shard_N> and docs_scoped and not windows_ci'``) -- four of the
#: five scoped sources are Markdown pages, so a docs-only PR is exactly when
#: this guard most needs to fire.
pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]

_REPO_ROOT = Path(__file__).resolve().parents[2]

#: The exact #2983 source set WP04 owns. Asserted as a denominator so that a
#: deleted or renamed file fails the gate instead of shrinking it to nothing.
_SCOPED_SOURCE_FILES = (
    Path("packs/built-in/styleguides/plain-language.styleguide.yaml"),
    Path("docs/api/environment-variables.md"),
    Path("docs/api/upgrade-lifecycle.md"),
    Path("docs/architecture/launch-readiness-future.md"),
    Path("docs/guides/how-to/installation/install-and-upgrade.md"),
)
_SCOPED_SOURCE_DENOMINATOR = 5

#: Concrete invocations currently extracted from the scoped sources. Bump this
#: deliberately when guidance gains or loses an example; drift fails the gate.
#:
#: 79 -> 82 (2026-07-30, #3030 WP09). The machine-global env-var warning added
#: exactly three invocations to docs/api/environment-variables.md (lines 126/131/137):
#: `spec-kitty sync opt-in`, `SPEC_KITTY_ENABLE_SAAS_SYNC=1 spec-kitty sync now`,
#: `spec-kitty sync doctor`. All three resolve in the live Click tree, so the gate's
#: substantive contract — guidance never names a command the CLI does not expose —
#: still holds; only the count moved. Verified per-source: the other four scoped
#: files are unchanged at 3/21/12/27, and the merge-base measured 16 for this file
#: against 19 now.
#:
#: Bumped rather than reworded: shedding three legitimate, resolving CLI examples to
#: satisfy a counter would weaken the guidance to reach green. The doc is correct and
#: the ratchet was stale.
_SCOPED_INVOCATION_DENOMINATOR = 82

_CLI_NAME = "spec-kitty"

#: Markdown/CommonMark fence toggles (``` and ~~~), opening or closing.
_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
#: Inline code spans. Non-greedy so two spans on one line stay separate.
_INLINE_SPAN_RE = re.compile(r"`+([^`\n]+?)`+")
#: Shell separators that start a fresh command position on the same line.
_SHELL_SEPARATOR_RE = re.compile(r"\|\||&&|[|;]")
#: ``FOO=bar`` prefixes that may precede the executable in command position.
_ENV_ASSIGNMENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=\S*$")
#: A Click/Typer subcommand name. Flags, placeholders, and arguments stop the walk.
_SUBCOMMAND_RE = re.compile(r"^[a-z][a-z0-9-]*$")
#: Interactive prompt markers that may precede the executable.
_PROMPT_TOKENS = frozenset({"$", ">", "%"})


class Invocation:
    """One concrete ``spec-kitty`` invocation found in a scoped source."""

    __slots__ = ("line_number", "path", "source", "text")

    def __init__(
        self, source: Path, line_number: int, path: tuple[str, ...], text: str
    ) -> None:
        self.source = source
        self.line_number = line_number
        self.path = path
        self.text = text

    def __repr__(self) -> str:
        return f"{self.source.name}:{self.line_number}: {self.text}"


# --------------------------------------------------------------------------- #
# Extraction: concrete invocations only
# --------------------------------------------------------------------------- #


def command_position_path(segment: str) -> tuple[str, ...] | None:
    """Return the subcommand path if ``segment`` opens a ``spec-kitty`` call.

    Returns ``None`` when ``spec-kitty`` is not in command position, which is
    what keeps narrative prose ("... spec-kitty prints a banner ...") and
    package references (``pipx upgrade spec-kitty-cli``) out of the inventory.
    """
    tokens = segment.split()
    index = 0
    while index < len(tokens) and (
        tokens[index] in _PROMPT_TOKENS or _ENV_ASSIGNMENT_RE.match(tokens[index])
    ):
        index += 1
    if index >= len(tokens) or tokens[index] != _CLI_NAME:
        return None
    path: list[str] = []
    for token in tokens[index + 1 :]:
        if not _SUBCOMMAND_RE.match(token):
            break
        path.append(token)
    return tuple(path)


def code_segments(text: str) -> Iterator[tuple[int, str]]:
    """Yield ``(line_number, segment)`` for every code-context shell segment.

    Code context is a fenced code-block line or the body of an inline code
    span. Everything else in the document is prose and is skipped.
    """
    in_fence = False
    for line_number, line in enumerate(text.splitlines(), 1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        code_chunks = (
            [line]
            if in_fence
            else [match.group(1) for match in _INLINE_SPAN_RE.finditer(line)]
        )
        for chunk in code_chunks:
            for segment in _SHELL_SEPARATOR_RE.split(chunk):
                yield line_number, segment


def extract_invocations(source: Path) -> list[Invocation]:
    """Extract every concrete ``spec-kitty`` invocation from ``source``."""
    found: list[Invocation] = []
    for line_number, segment in code_segments(source.read_text(encoding="utf-8")):
        path = command_position_path(segment)
        if path is None:
            continue
        found.append(Invocation(source, line_number, path, segment.strip()))
    return found


# --------------------------------------------------------------------------- #
# Resolution: the compiled Click command tree
# --------------------------------------------------------------------------- #


def _build_live_app() -> typer.Typer:
    """Build the full CLI tree without the startup-sensitive ``next`` shortcut."""
    from specify_cli import app
    from specify_cli.cli.commands import register_commands

    saved_argv = sys.argv[:]
    sys.argv = [_CLI_NAME, "--help"]
    try:
        register_commands(app)
    finally:
        sys.argv = saved_argv
    assert isinstance(app, typer.Typer), "specify_cli.app must be a Typer instance"
    return app


@functools.lru_cache(maxsize=1)
def compiled_command_tree() -> click.Command:
    """Return the Click command the ``spec-kitty`` entry point actually parses.

    This is the authority for command names. Typer rewrites callback names on
    the way in (``verify_setup`` -> ``verify-setup``), so anything derived from
    the Python callback would produce false verdicts.
    """
    return typer.main.get_command(_build_live_app())


def resolves_in_command_tree(path: tuple[str, ...]) -> bool:
    """Return ``True`` if ``path`` addresses a real command in the Click tree.

    Trailing segments consumed by a leaf command (positional arguments such as
    ``spec-kitty init my-project``) are accepted once the leaf is reached.
    """
    node: click.Command = compiled_command_tree()
    for segment in path:
        if not isinstance(node, click.Group):
            # A leaf command was already reached; the rest are its arguments.
            return True
        context = click.Context(node, info_name=node.name)
        child = node.get_command(context, segment)
        if child is None:
            return False
        node = child
    return True


def unresolved_invocations(sources: Iterable[Path]) -> list[Invocation]:
    """Return every extracted invocation that the live CLI would reject."""
    return [
        invocation
        for source in sources
        for invocation in extract_invocations(source)
        if not resolves_in_command_tree(invocation.path)
    ]


def _scoped_sources() -> tuple[Path, ...]:
    return tuple(_REPO_ROOT / relative for relative in _SCOPED_SOURCE_FILES)


def _render(failures: Iterable[Invocation]) -> str:
    return "\n".join(f"  - {failure!r}" for failure in failures)


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


def test_scoped_guidance_only_names_real_commands() -> None:
    """Every concrete invocation in the #2983 source set resolves in the CLI."""
    assert len(_SCOPED_SOURCE_FILES) == _SCOPED_SOURCE_DENOMINATOR
    sources = _scoped_sources()
    missing = [str(source) for source in sources if not source.is_file()]
    assert not missing, f"Scoped #2983 source inventory drifted: {missing}"

    invocations = [
        invocation for source in sources for invocation in extract_invocations(source)
    ]
    assert len(invocations) == _SCOPED_INVOCATION_DENOMINATOR, (
        "Scoped #2983 invocation inventory drifted: expected "
        f"{_SCOPED_INVOCATION_DENOMINATOR}, found {len(invocations)}."
    )

    failures = [
        invocation
        for invocation in invocations
        if not resolves_in_command_tree(invocation.path)
    ]
    assert not failures, (
        "#2983 scoped guidance names a command the CLI does not expose:\n"
        + _render(failures)
    )


def test_top_level_status_command_is_still_absent() -> None:
    """The replacement targets are real and ``spec-kitty status`` is not.

    Without this pin the guard could be greened by adding the very command the
    mission decided not to add.
    """
    assert not resolves_in_command_tree(("status",))
    assert resolves_in_command_tree(("agent", "tasks", "status"))
    assert resolves_in_command_tree(("upgrade",))


def test_resolution_uses_click_names_not_callback_names() -> None:
    """Regression pin for the cycle-1 defect.

    ``verify-setup`` is backed by a callback named ``verify_setup``. Resolving
    against callback-derived names reported that real, shipped command as
    missing. The compiled Click tree is the only correct authority.
    """
    assert resolves_in_command_tree(("verify-setup",))
    assert not resolves_in_command_tree(("verify_setup",))


def test_extraction_ignores_prose_and_package_names() -> None:
    """Narrative prose and ``spec-kitty-cli`` references are not invocations."""
    corpus = (
        "When a newer CLI is available, spec-kitty prints a single banner "
        "before normal output.\n"
        "The `spec-kitty-cli` package lives on PATH; install it with "
        "`pipx upgrade spec-kitty-cli`.\n"
        "Config lives in `~/.config/spec-kitty/upgrade.yaml`.\n"
        "```bash\n"
        "SPEC_KITTY_NO_NAG=1 spec-kitty upgrade --cli   # real invocation\n"
        "```\n"
        "Inline: run `spec-kitty agent tasks status` to inspect work packages.\n"
    )
    paths = [
        path
        for _, segment in code_segments(corpus)
        if (path := command_position_path(segment)) is not None
    ]
    assert paths == [("upgrade",), ("agent", "tasks", "status")]


def test_guard_reddens_on_a_planted_phantom_command(tmp_path: Path) -> None:
    """Mutation proof over a real scoped source, on the identical scan path.

    The styleguide's ``good_example`` is reverted to the exact defect #2983
    reported (``spec-kitty status``) and pushed back through
    :func:`unresolved_invocations` -- the same function the shipping gate calls.
    """
    styleguide = _REPO_ROOT / _SCOPED_SOURCE_FILES[0]
    original = styleguide.read_text(encoding="utf-8")
    assert "`spec-kitty agent tasks status`" in original, (
        "Mutation fixture is stale: the styleguide no longer carries the "
        "corrected invocation this proof mutates."
    )

    # Unmutated copy: the same path stays green, so the proof is not trivially red.
    clean = tmp_path / f"clean-{styleguide.name}"
    clean.write_text(original, encoding="utf-8")
    assert unresolved_invocations((clean,)) == []

    mutated = tmp_path / styleguide.name
    mutated.write_text(
        original.replace("`spec-kitty agent tasks status`", "`spec-kitty status`"),
        encoding="utf-8",
    )
    failures = unresolved_invocations((mutated,))
    assert [failure.path for failure in failures] == [("status",)], _render(failures)
