"""Tests for the redirect-stub generator + coverage gate (FR-006, NFR-002).

Covers the three contract guarantees from ``contracts/redirect-stub.md``:

* **derivation** — the redirect map is derived single-writer from the baseline +
  ``moves:`` spine and matches the committed ``redirect_map.yaml`` (diff-stable);
* **emit + no-404** — ``generate`` writes ``<meta refresh>`` stubs at the old paths
  and refuses to emit a stub whose target is a 404;
* **coverage goes RED on a gap** — a baseline URL with neither a live page nor a
  live-target stub appears in ``uncovered`` (the NFR-002 gate has teeth), and the
  check is non-vacuous against an empty baseline.

Fixtures use realistic published-URL shapes (``3x/index.html``,
``context/charter-overview.html``, ``tutorials/getting-started.html``).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from scripts.docs.redirect_stub_generator import (
    DEFAULT_BASELINE,
    DEFAULT_OCCURRENCE_MAP,
    DEFAULT_REDIRECT_MAP,
    SITE_URL,
    Move,
    assert_non_vacuous,
    check_coverage,
    derive_redirect_map,
    generate,
    load_baseline,
    load_moves,
    load_redirect_map,
    render_redirect_map,
)

# Pure generator unit tests (no git/subprocess) — fast developer-loop shard.
pytestmark = pytest.mark.fast

# The docs-published move that relocates a baseline URL: WP10 distils the
# ``docs/3x`` charter shadow tree into ``docs/context`` (so ``3x/*.html`` ->
# ``context/*.html``). Source != dest, so it produces real redirect entries.
_MOVE_3X = Move(sources=("docs/3x",), dest="docs/context")

# Realistic published-URL paths.
_DIRECT_URL = "tutorials/getting-started.html"
_MOVED_URL = "3x/charter-overview.html"
_MOVED_TARGET = "context/charter-overview.html"


def _make_site(tmp_path: Path, pages: list[str]) -> Path:
    """Stage a minimal ``_site`` containing ``pages`` (site-relative paths)."""
    site = tmp_path / "_site"
    for rel in pages:
        page = site / rel
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(f"<html><body>{rel}</body></html>", encoding="utf-8")
    return site


# --- derivation -------------------------------------------------------------


def test_derive_maps_published_move_to_new_url() -> None:
    baseline = [_DIRECT_URL, _MOVED_URL, "3x/index.html"]
    mapping = derive_redirect_map(baseline, [_MOVE_3X])
    assert mapping == {
        "3x/charter-overview.html": "context/charter-overview.html",
        "3x/index.html": "context/index.html",
    }
    # A page whose source did not move has no redirect (it resolves directly).
    assert _DIRECT_URL not in mapping


def test_derive_ignores_never_published_internal_moves() -> None:
    # architecture/** + CHANGELOG.md were never published URLs, so a baseline-driven
    # derivation yields no public-URL redirect for them (their source is not docs/).
    arch_move = Move(sources=("docs/adr/2.x",), dest="docs/adr/2.x")
    changelog_move = Move(sources=("CHANGELOG.md",), dest="docs/changelog")
    mapping = derive_redirect_map(
        [_DIRECT_URL, _MOVED_URL], [arch_move, changelog_move]
    )
    assert mapping == {}


def test_committed_redirect_map_is_diff_stable() -> None:
    """Re-deriving from the committed inputs reproduces the committed map."""
    _, baseline = load_baseline(DEFAULT_BASELINE)
    occ = _resolve_occurrence_map()
    derived = derive_redirect_map(baseline, load_moves(occ))
    committed = load_redirect_map(DEFAULT_REDIRECT_MAP)
    assert derived == committed
    # And the rendered form round-trips (the on-disk YAML body is canonical).
    rendered = render_redirect_map(derived)
    assert yaml.safe_load(rendered) == committed


# The shadow-tree redirects WP10 must preserve (FR-008): the ``docs/<v>x`` trees.
# These are the *teeth* of this gate — every one must be present and correct in
# the committed map. The committed map is a strict superset (WP08/WP18 added the
# Divio re-section redirects, e.g. ``explanation/* -> architecture/*``); the
# exact, diff-stable identity of the full map is pinned separately by
# ``test_committed_redirect_map_is_diff_stable``.
_SHADOW_TREE_REDIRECTS = {
    # docs/1x snapshot -> pre-existing archive/1x twin
    "1x/artifacts-and-commands.html": "archive/1x/artifacts-and-commands.html",
    "1x/branches-and-workspaces.html": "archive/1x/branches-and-workspaces.html",
    "1x/index.html": "archive/1x/index.html",
    "1x/orchestration-and-api.html": "archive/1x/orchestration-and-api.html",
    "1x/workflow.html": "archive/1x/workflow.html",
    # docs/2x snapshot -> pre-existing archive/2x twin
    "2x/adr-coverage.html": "archive/2x/adr-coverage.html",
    "2x/doctrine-and-charter.html": "archive/2x/doctrine-and-charter.html",
    "2x/glossary-system.html": "archive/2x/glossary-system.html",
    "2x/index.html": "archive/2x/index.html",
    "2x/model-discipline-routing.html": "archive/2x/model-discipline-routing.html",
    "2x/model-to-task_type.html": "archive/2x/model-to-task_type.html",
    "2x/orchestration-and-api.html": "archive/2x/orchestration-and-api.html",
    "2x/runtime-and-missions.html": "archive/2x/runtime-and-missions.html",
    # docs/context live charter content -> distilled into context/
    "3x/charter-overview.html": "context/charter-overview.html",
    "3x/governance-files.html": "context/governance-files.html",
    "3x/index.html": "context/index.html",
}


def test_committed_map_covers_the_shadow_tree_redirects() -> None:
    """The committed map covers every deleted/moved shadow-tree URL (FR-008).

    WP10 resolves the three ``docs/<v>x`` shadow trees: ``docs/1x`` + ``docs/2x``
    (true HTML snapshots) are DELETED and each baseline URL redirects to its
    pre-existing canonical archive twin (``archive/<v>x/*``); ``docs/context`` (live
    charter content) is distilled + moved into ``context/`` and redirected there.
    The committed map grew to a full-coverage map (WP18 re-section redirects
    folded in), so this gate asserts the shadow-tree redirects are a **subset**
    — drop or corrupt any one and it reds — while the full map's exact identity
    is pinned by ``test_committed_redirect_map_is_diff_stable``.
    """
    committed = load_redirect_map(DEFAULT_REDIRECT_MAP)
    missing = {
        old: new
        for old, new in _SHADOW_TREE_REDIRECTS.items()
        if committed.get(old) != new
    }
    assert missing == {}, f"shadow-tree redirects missing/wrong in committed map: {missing}"


# --- emit + no-404 ----------------------------------------------------------


def test_generate_emits_meta_refresh_stub_at_old_path(tmp_path: Path) -> None:
    site = _make_site(tmp_path, [_DIRECT_URL, _MOVED_TARGET])
    result = generate({_MOVED_URL: _MOVED_TARGET}, site)

    stub = site / _MOVED_URL
    assert stub.is_file()
    assert [p.name for p in result.emitted] == [stub.name]
    assert not result.dead_targets

    html = stub.read_text(encoding="utf-8")
    target = f"{SITE_URL}{_MOVED_TARGET}"
    assert f'http-equiv="refresh" content="0; url={target}"' in html
    assert f'<link rel="canonical" href="{target}">' in html


def test_generate_flags_dead_target_and_writes_no_stub(tmp_path: Path) -> None:
    # Target page is absent -> the stub would be a dead link (404).
    site = _make_site(tmp_path, [_DIRECT_URL])
    result = generate({_MOVED_URL: "context/missing.html"}, site)

    assert result.emitted == []
    assert result.dead_targets == [(_MOVED_URL, "context/missing.html")]
    # No 404-pointing stub was written.
    assert not (site / _MOVED_URL).exists()


# --- coverage (RED on a gap) ------------------------------------------------


def test_coverage_green_after_generate(tmp_path: Path) -> None:
    site = _make_site(tmp_path, [_DIRECT_URL, _MOVED_TARGET])
    redirect_map = {_MOVED_URL: _MOVED_TARGET}
    generate(redirect_map, site)
    uncovered = check_coverage([_DIRECT_URL, _MOVED_URL], redirect_map, site)
    assert uncovered == []


def test_coverage_red_when_redirect_removed(tmp_path: Path) -> None:
    """Drop the redirect for a moved page -> its baseline URL goes uncovered."""
    site = _make_site(tmp_path, [_DIRECT_URL, _MOVED_TARGET])
    # Old page is gone (moved) and there is no redirect entry for it.
    uncovered = check_coverage([_DIRECT_URL, _MOVED_URL], redirect_map={}, site_dir=site)
    assert uncovered == [_MOVED_URL]


def test_coverage_red_when_stub_points_at_dead_target(tmp_path: Path) -> None:
    # Map exists but target is a 404 -> not covered (stub would be a dead link).
    site = _make_site(tmp_path, [_DIRECT_URL])
    redirect_map = {_MOVED_URL: "context/missing.html"}
    generate(redirect_map, site)  # writes nothing (dead target)
    uncovered = check_coverage([_DIRECT_URL, _MOVED_URL], redirect_map, site)
    assert uncovered == [_MOVED_URL]


def test_assert_non_vacuous_rejects_empty_baseline() -> None:
    with pytest.raises(ValueError, match="empty"):
        assert_non_vacuous([])
    # A populated baseline passes silently.
    assert_non_vacuous([_DIRECT_URL])


def test_real_baseline_is_non_empty_and_normalised() -> None:
    site_url, baseline = load_baseline(DEFAULT_BASELINE)
    raw = json.loads(DEFAULT_BASELINE.read_text(encoding="utf-8"))
    assert site_url == raw["site_url"]
    assert len(baseline) == raw["url_count"]
    assert baseline  # non-vacuous denominator
    assert all(not p.startswith("http") for p in baseline)


def _resolve_occurrence_map() -> Path:
    assert DEFAULT_OCCURRENCE_MAP.is_file(), DEFAULT_OCCURRENCE_MAP
    return DEFAULT_OCCURRENCE_MAP
