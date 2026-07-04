"""PR-time docsite publish-integrity gates (#2357, #2360).

Two "no PR-time gate saw it" defect classes, closed by construction
(DIRECTIVE_043):

* **Gate 1 (#2357)** — a moved-away page can leave a committed baseline URL
  with neither a live page nor a redirect stub. The real NFR-002 invariant
  (``redirect_stub_generator.check_coverage``) only runs post-build in CI
  (DocFX is CI-only); this is its PR-time, build-free approximation: every
  baseline URL must be DERIVED (still resolvable from the source tree, see
  ``capture_baseline_urls.derive_urls_from_source``) or REDIRECT-COVERED (a
  key in the committed ``redirect_map.yaml``). This is exactly the class that
  broke the docsite deploy for a week on 2026-07-04 — an incomplete
  migration-runbook move left a baseline URL uncovered, caught only
  post-merge by the build-time gate.

* **Gate 2 (#2360)** — a ``docs/toc.yml`` nav entry can point at an
  unpublished path and ship a 404. In cluster 2, a "Release Goals" nav entry
  pointing at an unpublished path was caught only by adversarial review, not
  by any PR-time gate. This asserts every toc href resolves to a DERIVED or
  REDIRECT-COVERED published URL — the same "covered" test as gate 1, applied
  to the nav instead of the baseline.

Both gates share the static-tree "covered" primitive in
``tests/docs/_publish_manifest_helpers.py`` (``uncovered_urls`` +
``is_generated_at_build``'s narrow allowlist for the one documented
build-time-only generator, ``kitty-specs/**/*.html``).

Scope (intentionally tight): toc **href** coherence only — the witnessed
defect shape. Body-link publish-coverage (asserting every in-page markdown
link that targets another *published* page actually resolves) is a plausible
follow-on but is NOT covered here: distinguishing "link to a published page"
from "intentional cross-reference to an unpublished file" (e.g. a link to
this repo's own ``CONTRIBUTING.md``, a kitty-specs mission doc, or an
``architecture/adr`` symlink target) needs scoping work to avoid false
positives on the current tree, and that scoping was not attempted here. Left
as an explicit follow-up.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.docs.capture_baseline_urls import derive_urls_from_source
from scripts.docs.redirect_stub_generator import (
    DEFAULT_BASELINE,
    DEFAULT_REDIRECT_MAP,
    load_baseline,
    load_redirect_map,
)
from tests.docs._publish_manifest_helpers import (
    SITE_URL,
    href_to_url_path,
    is_generated_at_build,
    iter_toc_hrefs,
    strip_site,
    uncovered_urls,
)

# tests/docs runs in the dedicated `fast-tests-docs` CI job under
# `-m "not windows_ci"` (no `fast` marker required there — see
# .github/workflows/ci-quality.yml's fast-tests-docs job comment). No special
# marker needed to be collected by that job; `fast` is added anyway so this
# file also participates in the broader fast-tests-core-misc sweep like its
# siblings (test_capture_baseline_urls.py, test_redirect_stub_generator.py).
pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCS_DIR = _REPO_ROOT / "docs"
DEFAULT_DOCFX_JSON = DEFAULT_DOCS_DIR / "docfx.json"
DEFAULT_TOC = DEFAULT_DOCS_DIR / "toc.yml"


def _write(path: Path, text: str = "x") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _stage_docs_tree(root: Path) -> tuple[Path, Path]:
    """Stage a tiny published docs tree: two live pages, one content block."""
    docs = root / "docs"
    _write(docs / "index.md")
    _write(docs / "how-to" / "create-plan.md")
    docfx = docs / "docfx.json"
    docfx.write_text(
        json.dumps(
            {
                "build": {
                    "content": [{"files": ["index.md", "how-to/*.md"]}],
                    "resource": [],
                }
            }
        ),
        encoding="utf-8",
    )
    return docs, docfx


def _derived_paths(docs: Path, docfx: Path) -> set[str]:
    return {
        strip_site(u, SITE_URL)
        for u in derive_urls_from_source(docs, docfx, site_url=SITE_URL)
    }


# --- Gate 1 (#2357): baseline coverage ---------------------------------------


def test_gate1_fixture_has_teeth_on_moved_away_page(tmp_path: Path) -> None:
    """A baseline URL for a page that moved away with no stub is reported.

    This is the exact pre-#2313 defect shape: the migration-runbook page moved,
    its old baseline URL was neither still-derivable nor redirect-covered, and
    nothing caught it until the post-build NFR-002 gate — a week after the
    docsite had already been broken. Pinned here as a permanent regression
    test (mirrors ``test_redirect_stub_generator.test_coverage_red_when_
    redirect_removed``'s pattern of asserting the exact uncovered output).
    """
    docs, docfx = _stage_docs_tree(tmp_path)
    derived = _derived_paths(docs, docfx)
    baseline_paths = sorted(derived | {"how-to/retired-runbook.html"})

    uncovered = uncovered_urls(baseline_paths, derived, redirect_map={})

    assert uncovered == ["how-to/retired-runbook.html"]


def test_gate1_fixture_green_once_redirect_covers_the_move(tmp_path: Path) -> None:
    """The same moved-away page is covered once a redirect stub maps it forward."""
    docs, docfx = _stage_docs_tree(tmp_path)
    derived = _derived_paths(docs, docfx)
    baseline_paths = sorted(derived | {"how-to/retired-runbook.html"})
    redirect_map = {"how-to/retired-runbook.html": "how-to/create-plan.html"}

    uncovered = uncovered_urls(baseline_paths, derived, redirect_map)

    assert uncovered == []


def test_gate1_fixture_excludes_only_the_documented_generated_shape(
    tmp_path: Path,
) -> None:
    """The kitty-specs build-time allowlist is narrow — it must not mask a real gap.

    ``kitty-specs/index.html`` is absent from the static source tree (it is
    generated by ``generate_kitty_specs_docs.py`` at build time) and must be
    excluded rather than flagged. A same-shaped-looking but genuinely missing
    page OUTSIDE ``kitty-specs/`` must still be reported — proving the
    allowlist matches by the documented prefix, not by "absent from source"
    in general (which would silently swallow the very defect class #2357
    exists to catch).
    """
    docs, docfx = _stage_docs_tree(tmp_path)
    derived = _derived_paths(docs, docfx)
    baseline_paths = sorted(
        derived | {"kitty-specs/index.html", "how-to/also-missing.html"}
    )

    uncovered = uncovered_urls(baseline_paths, derived, redirect_map={})

    assert uncovered == ["how-to/also-missing.html"]
    assert "kitty-specs/index.html" not in uncovered


def test_gate1_fixture_red_when_redirect_target_is_dead(tmp_path: Path) -> None:
    """A redirect whose TARGET does not resolve is not real coverage.

    Mirrors ``redirect_stub_generator.check_coverage``'s ``target_live``
    requirement (a stub is only real coverage when ``new_path`` resolves to a
    live page — ``generate()``'s no-404 invariant refuses to emit a stub
    pointing at a 404 and reports it as a ``dead_targets`` entry instead).
    Treating "path is a redirect_map key" as sufficient (the pre-fold
    behaviour) is false confidence: a redirect to a dead page is NOT real
    coverage, and the SOURCE must still be reported uncovered.
    """
    docs, docfx = _stage_docs_tree(tmp_path)
    derived = _derived_paths(docs, docfx)
    baseline_paths = sorted(derived | {"how-to/retired-runbook.html"})
    redirect_map = {"how-to/retired-runbook.html": "how-to/nonexistent-target.html"}

    uncovered = uncovered_urls(baseline_paths, derived, redirect_map)

    assert uncovered == ["how-to/retired-runbook.html"]


def test_gate1_live_baseline_is_fully_covered() -> None:
    """The real gate: every committed baseline URL is derived or redirect-covered.

    No live DocFX ``_site`` build (CI-only) — this is the static-tree
    approximation described in the module docstring. A RED here on the current
    tree is a real, reportable NFR-002-adjacent gap, not a test to loosen.
    """
    _, baseline_paths = load_baseline(DEFAULT_BASELINE)
    derived = _derived_paths(DEFAULT_DOCS_DIR, DEFAULT_DOCFX_JSON)
    redirect_map = load_redirect_map(DEFAULT_REDIRECT_MAP)

    uncovered = uncovered_urls(baseline_paths, derived, redirect_map)

    assert uncovered == []


# --- Gate 2 (#2360): nav <-> publish-manifest coherence ----------------------


def test_gate2_fixture_has_teeth_on_unpublished_toc_href(tmp_path: Path) -> None:
    """A toc.yml href pointing at an unpublished page is reported.

    This is the exact cluster-2 "Release Goals" shape: a nav entry added
    pointing at a path that was never in the published set — it would have
    shipped a 404 and was only caught by adversarial review. Pinned as a
    permanent regression test.
    """
    docs, docfx = _stage_docs_tree(tmp_path)
    toc = docs / "toc.yml"
    toc.write_text(
        "- name: Home\n  href: index.md\n"
        "- name: Release Goals\n  href: release-goals/index.md\n",
        encoding="utf-8",
    )
    derived = _derived_paths(docs, docfx)
    hrefs = iter_toc_hrefs(toc)
    resolved = [p for h in hrefs if (p := href_to_url_path(h)) is not None]

    uncovered = uncovered_urls(resolved, derived, redirect_map={})

    assert uncovered == ["release-goals/index.html"]


def test_gate2_fixture_green_once_toc_href_targets_a_published_page(
    tmp_path: Path,
) -> None:
    docs, docfx = _stage_docs_tree(tmp_path)
    toc = docs / "toc.yml"
    toc.write_text(
        "- name: Home\n  href: index.md\n"
        "- name: How-To\n  href: how-to/create-plan.md\n",
        encoding="utf-8",
    )
    derived = _derived_paths(docs, docfx)
    hrefs = iter_toc_hrefs(toc)
    resolved = [p for h in hrefs if (p := href_to_url_path(h)) is not None]

    uncovered = uncovered_urls(resolved, derived, redirect_map={})

    assert uncovered == []


def test_gate2_fixture_excludes_only_the_documented_generated_shape(
    tmp_path: Path,
) -> None:
    """A ``kitty-specs/*.html`` nav href is allowlisted narrowly, like gate 1."""
    docs, docfx = _stage_docs_tree(tmp_path)
    toc = docs / "toc.yml"
    toc.write_text(
        "- name: Home\n  href: index.md\n"
        "- name: Mission Runs\n  href: kitty-specs/index.html\n"
        "- name: Ghost\n  href: how-to/ghost.md\n",
        encoding="utf-8",
    )
    derived = _derived_paths(docs, docfx)
    hrefs = iter_toc_hrefs(toc)
    resolved = [p for h in hrefs if (p := href_to_url_path(h)) is not None]

    uncovered = uncovered_urls(resolved, derived, redirect_map={})

    assert uncovered == ["how-to/ghost.html"]
    assert "kitty-specs/index.html" not in uncovered


def test_gate2_href_resolution_handles_directories_and_external_links() -> None:
    """Directory hrefs resolve to their index; external links are out of scope."""
    assert href_to_url_path("archive/") == "archive/index.html"
    assert href_to_url_path("archive/2x/") == "archive/2x/index.html"
    assert href_to_url_path("guides/index.md") == "guides/index.html"
    assert href_to_url_path("kitty-specs/index.html") == "kitty-specs/index.html"
    assert href_to_url_path("https://example.com/") is None
    assert href_to_url_path("http://example.com/") is None


def test_gate2_live_toc_hrefs_all_resolve_to_published_or_redirected_urls() -> None:
    """The real gate: every ``docs/toc.yml`` href targets a published/covered path.

    This is the check that would have caught the cluster-2 "Release Goals"
    404 pre-fix. A RED here means a live nav entry currently 404s and must be
    reported, not suppressed.
    """
    derived = _derived_paths(DEFAULT_DOCS_DIR, DEFAULT_DOCFX_JSON)
    redirect_map = load_redirect_map(DEFAULT_REDIRECT_MAP)
    hrefs = iter_toc_hrefs(DEFAULT_TOC)
    resolved = [p for h in hrefs if (p := href_to_url_path(h)) is not None]

    uncovered = uncovered_urls(resolved, derived, redirect_map)

    assert uncovered == []


# --- Shared allowlist narrowness -----------------------------------------


def test_generated_at_build_allowlist_matches_only_kitty_specs_html() -> None:
    """``is_generated_at_build`` must not over-match beyond the documented shape."""
    assert is_generated_at_build("kitty-specs/index.html")
    assert is_generated_at_build("kitty-specs/nested/mission.html")
    # Same prefix, wrong suffix (not an html page) -> not excluded.
    assert not is_generated_at_build("kitty-specs/toc.yml")
    # Same suffix, wrong/no prefix -> not excluded (a real page, or a real gap).
    assert not is_generated_at_build("how-to/kitty-specs-guide.html")
    assert not is_generated_at_build("index.html")
