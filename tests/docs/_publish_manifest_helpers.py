"""Shared primitives for the PR-time docsite publish-integrity gates.

Both gates in ``test_publish_manifest_coherence.py`` (#2357, #2360) reduce to
the same question, asked of two different inputs (a committed baseline URL, a
``docs/toc.yml`` href): *is this site-relative published-URL path resolvable
WITHOUT a DocFX build?* "Resolvable" means one of:

* **DERIVED** — the page still exists in the source tree, so
  ``capture_baseline_urls.derive_urls_from_source`` would (re-)produce it, or
* **REDIRECT-COVERED** — the URL is a key in the committed
  ``redirect_map.yaml`` **and** its redirect TARGET itself resolves (is
  DERIVED or a documented build-time-generated shape). This mirrors
  ``redirect_stub_generator.check_coverage``'s real, build-time invariant
  exactly: a stub is only real coverage when ``target_live`` holds —
  ``generate()`` refuses to emit a stub pointing at a 404 (the no-404
  invariant) and reports it as a ``dead_targets`` entry instead. A redirect
  whose target does not resolve is NOT coverage; the source path is reported
  uncovered, same as ``check_coverage`` would (post-build) via a missing
  stub.

This is a **static-tree approximation** of ``check_coverage``: the real gate
checks file presence inside an emitted ``_site``; DocFX/.NET is CI-only (see
``redirect_stub_generator`` module docstring), so PR-time cannot build one.
The approximation trades that live-build fidelity for running in every PR.
There is no known divergence left between this approximation's notion of
"covered" and ``check_coverage``'s: both require the redirect target to
resolve, not merely that the source is a mapped key.

Known model limit (documented in ``derive_urls_from_source``'s own docstring):
pages generated at build time from a non-static source — today, exactly
``kitty-specs/**/*.html``, emitted by ``generate_kitty_specs_docs.py`` from the
top-level ``kitty-specs/`` mission-spec tree, per the ``resource`` block in
``docs/docfx.json`` — are absent from a plain source-tree walk. Both gates
allowlist *only* that one documented shape (:func:`is_generated_at_build`);
anything else that is neither derived nor redirect-covered is a real gap.
This allowlist also applies when resolving a redirect TARGET (a redirect
could in principle point at a kitty-specs generated page), keeping the two
checks symmetric.

Separately documented known-limit (not a divergence from ``check_coverage``,
since ``docfx.json``'s ``overwrite`` block is not a publish source at all):
the ``overwrite`` block (``apidoc/**.md``) is not modeled by
``derive_urls_from_source`` and therefore not by this approximation either,
because ``docs/apidoc/`` is currently empty/inert — a future apidoc
population would need this revisited.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

# Mirrors capture_baseline_urls.SITE_URL / redirect_stub_generator.SITE_URL —
# duplicated here (both source modules already duplicate the same literal)
# rather than importing a private constant across an internal/test boundary.
SITE_URL = "https://docs.spec-kitty.ai/"

MD_SUFFIX = ".md"
HTML_SUFFIX = ".html"

# The ONLY documented build-time generator whose output is absent from a
# static source-tree walk (see module docstring above). Narrow by
# construction: matches exactly the resource-block shape docfx.json declares
# (``kitty-specs/**/*.html``) — a prefix-and-suffix pair, nothing broader (no
# bare-prefix or bare-suffix match that could swallow an unrelated real gap).
_GENERATED_AT_BUILD_PREFIX = "kitty-specs/"


def is_generated_at_build(url_path: str) -> bool:
    """True only for the one documented non-static generator output.

    ``url_path`` is site-relative (no ``SITE_URL`` prefix), e.g.
    ``"kitty-specs/index.html"``.
    """
    return url_path.startswith(_GENERATED_AT_BUILD_PREFIX) and url_path.endswith(
        HTML_SUFFIX
    )


def strip_site(url: str, site_url: str = SITE_URL) -> str:
    """Strip the site-URL prefix, mirroring ``redirect_stub_generator._strip_site``."""
    return url[len(site_url) :] if url.startswith(site_url) else url


def uncovered_urls(
    candidate_paths: list[str],
    derived_paths: set[str],
    redirect_map: dict[str, str],
) -> list[str]:
    """Return the ``candidate_paths`` that are neither DERIVED nor REDIRECT-COVERED.

    Shared by both gates: gate 1 passes the committed baseline URLs as
    ``candidate_paths``; gate 2 passes the resolved ``docs/toc.yml`` href
    targets. ``derived_paths`` and ``redirect_map`` keys/values must already
    be site-relative (no ``SITE_URL`` prefix). The one documented build-time
    generator shape (:func:`is_generated_at_build`) is excluded narrowly —
    every other miss is a real, reportable gap.

    REDIRECT-COVERED requires the redirect's TARGET to resolve too (mirrors
    ``redirect_stub_generator.check_coverage``'s ``target_live`` requirement):
    a path that is merely a ``redirect_map`` key is not sufficient — if its
    target is not itself DERIVED (or the documented generated-at-build shape),
    the stub would point at a 404 and ``generate()`` would refuse to emit it
    (a ``dead_targets`` entry), so the source path is reported uncovered.
    """
    uncovered: list[str] = []
    for path in candidate_paths:
        if is_generated_at_build(path):
            continue
        if path in derived_paths:
            continue
        target = redirect_map.get(path)
        if target is not None and (
            target in derived_paths or is_generated_at_build(target)
        ):
            continue
        uncovered.append(path)
    return sorted(uncovered)


def iter_toc_hrefs(toc_path: Path) -> list[str]:
    """Flatten every ``href`` in a DocFX ``toc.yml``, including nested ``items``."""
    data: Any = yaml.safe_load(toc_path.read_text(encoding="utf-8")) or []
    hrefs: list[str] = []

    def _walk(nodes: Any) -> None:
        for node in nodes or []:
            href = node.get("href")
            if href:
                hrefs.append(str(href))
            _walk(node.get("items"))

    _walk(data)
    return hrefs


def href_to_url_path(href: str) -> str | None:
    """Resolve a root ``toc.yml`` href to its site-relative published-URL path.

    ``docs/toc.yml`` hrefs are relative to the docs root for the top-level nav
    this gate covers. A directory reference (trailing ``/``) resolves to that
    directory's ``index.html`` (DocFX's own convention, also relied on by
    ``redirect_map.yaml``'s ``archive/1x/index.html`` etc. entries); a
    ``*.md`` reference resolves like DocFX's content mapping (``*.html``);
    anything else (already ``*.html``) passes through unchanged. External
    links (``http://``/``https://``) are out of scope for publish-coherence
    and resolve to ``None`` so callers can skip them.
    """
    if href.startswith(("http://", "https://")):
        return None
    if href.endswith("/"):
        return f"{href}index.html"
    if href.endswith(MD_SUFFIX):
        return f"{href[: -len(MD_SUFFIX)]}{HTML_SUFFIX}"
    return href
