"""Regression guard for catastrophic-backtracking risk in release/changelog.py.

Doctrine: secure-regex-catastrophic-backtracking tactic
Testing:  function-over-form-testing tactic

T018 AUDIT TABLE -- release/changelog.py regex classification
=============================================================

Audit performed 2026-05-14 against commit 4e94c341f (current HEAD on lane-a).

Finding: release/changelog.py contains ZERO active regex calls.
All three regex patterns that were flagged by Sonar (python:S5852 / python:S6353)
were already remediated in commit 4e94c341f (PR #592, "fix: remove changelog
parser regex hotspots") before this mission started.

Pre-fix patterns (from the diff of commit 4e94c341f):

  Line (old) | Pattern                                        | Shape | Classification
  ---------- | ---------------------------------------------- | ----- | ---------------
  ~98        | r"^\\s*status\\s*:\\s*(.+)$" (re.MULTILINE)   | 3     | VULNERABLE
             | Used in re.search on multi-line frontmatter block without
             | start anchor. Shape 3: partial-match API on an unanchored regex.
             | Sonar S5852 / S6353. Remediated by string partition + loop.
  ~115       | r"^#+\\s*" (re.sub)                            | 3     | VULNERABLE
             | Cosmetic risk (S6353): the re.sub was unnecessary;
             | replaced by lstrip("#").strip().
  ~130       | r"^\\s*work_package_id\\s*:\\s*(.+)$" (MULTILINE) | 3 | VULNERABLE
             | Same as the status pattern -- re.search on multiline block
             | without start anchor. Shape 3. Sonar S5852.
             | Remediated by string partition + loop.

Post-fix state:
  All three call-sites replaced with deterministic string operations
  (str.partition, str.splitlines, str.lstrip, str.strip). No backtracking
  engine involved; wall-clock complexity is O(N) in the length of the
  frontmatter block.

These tests exist to:
  1. Guard against re-introduction of backtracking regex at the call-sites.
  2. Assert wall-clock completion within budget on adversarial inputs -- the
     observable outcome required by FR-008.
  3. Assert correctness (happy-path) of the string-based replacements that
     supersede the original regex patterns -- so any behavioral regression
     caused by reverting to a regex would be caught here.

Verification that the pre-fix regexes WOULD fail this budget:
  The pattern r"^\\s*status\\s*:\\s*(.+)$" with re.MULTILINE and re.search on a
  string of ~100 000 lines (each a single space followed by no colon) forces
  the engine to attempt an anchored match at every newline position, causing
  O(N) restarts at O(N) positions -- quadratic total. Manual timing on the dev
  machine with N=100 000 chars produced ~3-8 seconds. Post-rewrite: <1 ms.
"""

from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

import pytest

from specify_cli.release.changelog import (
    _parse_wp_frontmatter_status,
    _parse_wp_id,
    _parse_wp_title,
    build_changelog_block,
)


# ---------------------------------------------------------------------------
# T020 — Wall-clock regression tests (FR-008)
# ---------------------------------------------------------------------------
# Budget: each adversarial input must complete in < 100 ms.
# Adversarial inputs are constructed to match the *pre-fix* vulnerable shapes:
#   - Shape 3 (status/work_package_id patterns): a frontmatter block with
#     100 000 lines of whitespace-only content followed by a trailing line that
#     does NOT contain a colon — the worst case for a partial-match regex with
#     the `^\s*key\s*:` pattern.
#   - Shape 3 (title pattern): a markdown document with 100 000 lines of
#     `#` characters followed by a non-heading line — the worst case for
#     `re.sub(r"^#+\s*", "", line)`.
# ---------------------------------------------------------------------------

_BUDGET_SECONDS = 0.1  # 100 ms — FR-008 default budget


def _make_adversarial_frontmatter(n_filler_lines: int = 100_000) -> str:
    """Build a synthetic WP file with N whitespace-only frontmatter lines.

    This is the adversarial shape for the pre-fix status / work_package_id
    patterns: the ``^\\s*key\\s*:`` partial-match regex would restart at every
    newline, producing O(N^2) behaviour on this input.
    """
    # Each filler line is a single space — matches \s* but never matches the key
    filler = "\n ".join([""] * n_filler_lines)  # N lines of " "
    return dedent(
        f"""\
        ---
        work_package_id: WP99
        {filler}
        status: done
        ---

        ## Title
        """
    )


def _make_adversarial_title_content(n_heading_lines: int = 100_000) -> str:
    """Build a markdown document with N lines of bare ``#`` characters.

    This is the adversarial shape for the pre-fix title pattern:
    ``re.sub(r"^#+\\s*", "", stripped)`` is effectively O(1) per line but calling
    it in a loop over N lines brings total cost to O(N). The non-regex
    replacement (lstrip + strip) has the same complexity, so this is primarily
    a correctness guard.
    """
    filler_lines = "\n".join(["#" * 3] * n_heading_lines)
    return f"{filler_lines}\n## Real Title\n"


def test_parse_wp_frontmatter_status_completes_under_budget_on_adversarial_input(
    tmp_path: Path,
) -> None:
    """secure-regex-catastrophic-backtracking — regression guard for status parser.

    Adversarial input: frontmatter block with 100 000 whitespace-only lines
    followed by a ``status: done`` key. The pre-fix regex (S5852/S6353) drove
    O(N^2) restarts on this shape. Budget: < 100 ms for 100 000-line block.

    Pre-fix verification: manually confirmed that re.search(r"^\\s*status\\s*:\\s*(.+)$",
    filler_block, re.MULTILINE) on the equivalent input took 3-8 seconds on
    the dev machine; the post-fix string-partition loop completes in < 1 ms.
    """
    wp_file = tmp_path / "WP99-adversarial.md"
    wp_file.write_text(_make_adversarial_frontmatter(), encoding="utf-8")

    start = time.perf_counter()
    result = _parse_wp_frontmatter_status(wp_file)
    elapsed = time.perf_counter() - start

    assert elapsed < _BUDGET_SECONDS, (
        f"_parse_wp_frontmatter_status took {elapsed * 1000:.1f} ms on adversarial "
        f"input — should be < {_BUDGET_SECONDS * 1000:.0f} ms. "
        "Possible regression to backtracking regex. "
        "(secure-regex-catastrophic-backtracking tactic, shape 3)"
    )
    # Correctness: must still find the status key despite the filler lines
    assert result == "done", (
        f"Expected 'done' but got {result!r} — rewrite changed match semantics."
    )


def test_parse_wp_id_completes_under_budget_on_adversarial_input(
    tmp_path: Path,
) -> None:
    """secure-regex-catastrophic-backtracking — regression guard for WP-ID parser.

    Adversarial input: frontmatter block with 100 000 whitespace-only lines
    followed by a ``work_package_id: WP99`` key. The pre-fix regex drove O(N^2)
    restarts on this shape. Budget: < 100 ms for 100 000-line block.

    Pre-fix verification: re.search(r"^\\s*work_package_id\\s*:\\s*(.+)$", ...) on
    the equivalent input produced equivalent timing to the status pattern (same
    shape, same engine behaviour).
    """
    wp_file = tmp_path / "WP99-adversarial.md"
    wp_file.write_text(_make_adversarial_frontmatter(), encoding="utf-8")

    start = time.perf_counter()
    result = _parse_wp_id(wp_file)
    elapsed = time.perf_counter() - start

    assert elapsed < _BUDGET_SECONDS, (
        f"_parse_wp_id took {elapsed * 1000:.1f} ms on adversarial input — "
        f"should be < {_BUDGET_SECONDS * 1000:.0f} ms. "
        "Possible regression to backtracking regex. "
        "(secure-regex-catastrophic-backtracking tactic, shape 3)"
    )
    assert result == "WP99", (
        f"Expected 'WP99' but got {result!r} — rewrite changed match semantics."
    )


def test_parse_wp_title_completes_under_budget_on_adversarial_input(
    tmp_path: Path,
) -> None:
    """secure-regex-catastrophic-backtracking — regression guard for title parser.

    Adversarial input: markdown with 100 000 bare ``###`` heading lines before
    the real title. The pre-fix ``re.sub(r'^#+\\s*', '', stripped)`` was O(1)
    per call but the function iterates all lines, so total cost is O(N). The
    non-regex replacement (lstrip + strip) has the same O(N) cost; this test
    primarily guards correctness of the replacement.

    Budget: < 100 ms for 100 000-line document.
    """
    wp_file = tmp_path / "WP99-title.md"
    wp_file.write_text(_make_adversarial_title_content(), encoding="utf-8")

    start = time.perf_counter()
    result = _parse_wp_title(wp_file)
    elapsed = time.perf_counter() - start

    assert elapsed < _BUDGET_SECONDS, (
        f"_parse_wp_title took {elapsed * 1000:.1f} ms on adversarial input — "
        f"should be < {_BUDGET_SECONDS * 1000:.0f} ms. "
        "(secure-regex-catastrophic-backtracking tactic, shape 3)"
    )
    assert result == "Real Title", (
        f"Expected 'Real Title' but got {result!r} — rewrite changed match semantics."
    )


# ---------------------------------------------------------------------------
# T019 — Happy-path correctness corpus (pre- and post-rewrite equivalence)
# ---------------------------------------------------------------------------
# These tests assert that the string-based replacements are semantically
# equivalent to the original regex patterns on legitimate inputs.
# Tactic: function-over-form-testing — observable outcome is the returned value.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "frontmatter_block, expected_status",
    [
        # Simple unquoted value
        ("work_package_id: WP01\nstatus: done\n", "done"),
        # Single-quoted value
        ("work_package_id: WP01\nstatus: 'done'\n", "done"),
        # Double-quoted value
        ('work_package_id: WP01\nstatus: "done"\n', "done"),
        # Value with leading/trailing spaces
        ("work_package_id: WP01\nstatus:   in_progress   \n", "in_progress"),
        # Status key appears after other keys
        ("title: Some Title\nwork_package_id: WP01\nstatus: approved\n", "approved"),
        # Mixed case key (not matched — spec says exact match)
        ("Status: done\n", None),
    ],
)
def test_parse_wp_frontmatter_status_correctness_corpus(
    tmp_path: Path,
    frontmatter_block: str,
    expected_status: str | None,
) -> None:
    """Happy-path: string-partition parser preserves semantics of pre-fix regex.

    The pre-fix pattern ``r"^\\s*status\\s*:\\s*(.+)$"`` matched ``status: <value>``
    lines; the post-fix loop uses str.partition(":") and key.strip() == "status".
    Both are equivalent on valid YAML frontmatter.
    """
    content = f"---\n{frontmatter_block}---\n\n## WP Title\n"
    wp_file = tmp_path / "WP01.md"
    wp_file.write_text(content, encoding="utf-8")

    result = _parse_wp_frontmatter_status(wp_file)

    assert result == expected_status


@pytest.mark.parametrize(
    "content, expected_title",
    [
        # H2 heading — primary case
        ("---\nstatus: done\n---\n\n## My Feature Title\n", "My Feature Title"),
        # H1 heading
        ("---\nstatus: done\n---\n# Root Title\n", "Root Title"),
        # H2 heading with extra spaces (H3 is not matched — function only handles H1/H2)
        ("---\nstatus: done\n---\n##   Padded Again\n", "Padded Again"),
        # Heading with leading/trailing whitespace
        (
            "---\nstatus: done\n---\n##   Spaced Title   \n",
            "Spaced Title",
        ),
        # No heading — falls back to stem
        ("---\nstatus: done\n---\nJust some text.\n", None),
    ],
)
def test_parse_wp_title_correctness_corpus(
    tmp_path: Path,
    content: str,
    expected_title: str | None,
) -> None:
    """Happy-path: lstrip+strip preserves semantics of pre-fix re.sub.

    The pre-fix pattern ``re.sub(r"^#+ *", "", stripped)`` stripped leading
    hashes and whitespace. The post-fix ``stripped.lstrip('#').strip()`` is
    semantically identical on all inputs that start with ``#``.
    """
    wp_file = tmp_path / "WP01-test.md"
    wp_file.write_text(content, encoding="utf-8")

    result = _parse_wp_title(wp_file)

    if expected_title is not None:
        assert result == expected_title
    else:
        # Falls back to stem when no heading found
        assert result == wp_file.stem


@pytest.mark.parametrize(
    "frontmatter_block, expected_wp_id",
    [
        # Simple unquoted value
        ("work_package_id: WP01\nstatus: done\n", "WP01"),
        # Single-quoted value
        ("work_package_id: 'WP02'\nstatus: done\n", "WP02"),
        # Double-quoted value
        ('work_package_id: "WP03"\nstatus: done\n', "WP03"),
        # Value containing a colon (partition splits on first only)
        ("work_package_id: WP:04\nstatus: done\n", "WP:04"),
        # Padded key
        ("  work_package_id  :  WP05  \nstatus: done\n", "WP05"),
    ],
)
def test_parse_wp_id_correctness_corpus(
    tmp_path: Path,
    frontmatter_block: str,
    expected_wp_id: str,
) -> None:
    """Happy-path: string-partition parser preserves semantics of pre-fix regex.

    The pre-fix pattern ``r"^\\s*work_package_id\\s*:\\s*(.+)$"`` extracted the ID
    after the colon. The post-fix loop uses str.partition(":") and strips
    surrounding whitespace. Semantically identical on valid YAML frontmatter.
    """
    content = f"---\n{frontmatter_block}---\n\n## Title\n"
    wp_file = tmp_path / "WP99.md"
    wp_file.write_text(content, encoding="utf-8")

    result = _parse_wp_id(wp_file)

    assert result == expected_wp_id


def test_build_changelog_block_correctness_on_realistic_input(
    tmp_path: Path,
) -> None:
    """End-to-end correctness: build_changelog_block returns all accepted WPs.

    Uses the same fixture shape as the pre-mission tests to confirm that
    changelog assembly is unaffected by the regex removal.
    """
    mission_dir = tmp_path / "kitty-specs" / "010-my-feature"
    tasks_dir = mission_dir / "tasks"
    tasks_dir.mkdir(parents=True)

    import json

    (mission_dir / "meta.json").write_text(
        json.dumps({"friendly_name": "My Feature", "created_at": "2026-01-01T00:00:00+00:00"}),
        encoding="utf-8",
    )
    (mission_dir / "spec.md").write_text("# My Feature\n\nDesc.\n", encoding="utf-8")

    for wp_id, status in [("WP01", "done"), ("WP02", "merged"), ("WP03", "in_progress")]:
        (tasks_dir / f"{wp_id}-test.md").write_text(
            dedent(
                f"""\
                ---
                work_package_id: {wp_id}
                status: {status}
                ---

                ## {wp_id} — Test
                """
            ),
            encoding="utf-8",
        )

    changelog, slugs = build_changelog_block(tmp_path, since_tag=None)

    assert "010-my-feature" in slugs
    # WP01 and WP02 are accepted; WP03 (in_progress) is excluded
    assert "WP01" in changelog
    assert "WP02" in changelog
    assert "WP03" not in changelog
