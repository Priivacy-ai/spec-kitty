"""Redirect-stub generator + coverage gate (FR-006, NFR-002).

This is **WP07 / IC-05a** of the Common Docs Structural Move (mission B,
``common-docs-structural-move-01KW3SBK``). DocFX on GitHub Pages has **no native
redirect**, so every moved published URL is preserved by a generated
``<meta http-equiv="refresh">`` **stub page emitted at the old path** into the
built ``_site`` (Mission A's D4 mechanism). ``contracts/redirect-stub.md`` is the
authority.

Three concerns, kept single-writer and deterministic:

``redirect_map.yaml`` (single-writer, WP07-owned)
    ``{ old_url_path: new_url_path }`` derived **deterministically** from two
    committed, immutable inputs — WP02's pre-move baseline manifest
    (:data:`DEFAULT_BASELINE`) and the mission's ``occurrence_map.yaml`` ``moves:``
    spine. A baseline URL earns a redirect entry iff its source path falls under a
    move that relocates it *within the published tree*. The move WPs
    (WP03/WP04/WP06/WP10) do **not** hand-append to the map — they ensure their
    moves are represented in ``moves:``; WP07 re-derives. A regen is diff-stable.

    Only moves whose ``from`` is a **currently-published** ``docs/`` path can change
    a baseline (public) URL. Internal relocations that were *never* published —
    ``architecture/**`` folds, the ``architecture/adrs`` era-less ADRs, the
    ``CHANGELOG.md`` relocate-with-alias — have **no public URL to preserve** and so
    yield no redirect entry (verified against ``docs/docfx.json``'s content globs /
    the baseline). Their continuity is an *internal-link* concern handled by the
    move WPs' ``targeted_ref_updates``, not a ``<meta refresh>`` stub.

``generate(redirect_map, site_dir)``
    For each ``old -> new`` emit a stub at ``old`` inside ``_site`` pointing at
    ``new``. A stub is emitted **only** when ``new`` resolves to a live page — **no
    stub may point at a 404** (the no-404 invariant). Entries whose target is
    missing are returned as ``dead_targets`` and fail CI.

``check_coverage(baseline, redirect_map, site_dir)``
    A baseline URL is **covered** iff it resolves directly (page still present) OR a
    stub exists at that path pointing to a live target. Returns the ``uncovered``
    list; the contract is ``uncovered == []`` (NFR-002, 100%). The check is
    **non-vacuous**: it asserts the loaded baseline is non-empty, so it can never
    silently pass against an empty denominator.

**No live build locally.** DocFX/.NET is CI-only, so ``redirect_map.yaml`` is
derived structurally from the source tree + committed manifests (as WP02 did); the
real ``_site`` injection + coverage gate run in ``.github/workflows/docs-pages.yml``
between the ``Build documentation`` and ``Upload artifact`` steps.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# --- Canonical constants ----------------------------------------------------

# Published site root. Mirrors ``_siteUrl`` in ``docs/docfx.json`` and the
# ``site_url`` recorded in WP02's baseline manifest.
SITE_URL = "https://docs.spec-kitty.ai/"

MD_SUFFIX = ".md"
HTML_SUFFIX = ".html"
DOCS_PREFIX = "docs/"

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BASELINE = _REPO_ROOT / "scripts" / "docs" / "redirect_baseline_urls.json"
DEFAULT_REDIRECT_MAP = _REPO_ROOT / "scripts" / "docs" / "redirect_map.yaml"
DEFAULT_SITE_DIR = _REPO_ROOT / "docs" / "_site"

# This redirect map is specific to mission B's move spine; the derivation reads
# that mission's ``occurrence_map.yaml`` (override with ``--occurrence-map``).
MISSION_SLUG = "common-docs-structural-move-01KW3SBK"
DEFAULT_OCCURRENCE_MAP = (
    _REPO_ROOT / "kitty-specs" / MISSION_SLUG / "occurrence_map.yaml"
)

REDIRECT_MAP_HEADER = (
    "# Redirect map — DocFX has no native redirect; each old->new preserves a\n"
    "# moved published URL via a <meta http-equiv=\"refresh\"> stub (FR-006).\n"
    "#\n"
    "# SINGLE-WRITER (WP07-owned): DERIVED, do not hand-edit. Regenerate with\n"
    "#   python3 scripts/docs/redirect_stub_generator.py regenerate-map\n"
    "# from the committed baseline manifest + occurrence_map.yaml `moves:` spine.\n"
    "# Keys/values are site-relative published-URL paths.\n"
)

STUB_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Page moved</title>
<meta http-equiv="refresh" content="0; url={target}">
<link rel="canonical" href="{target}">
<meta name="robots" content="noindex">
</head>
<body>
<p>This page has moved. Redirecting to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


# --- Data structures --------------------------------------------------------


@dataclass(frozen=True)
class Move:
    """One ``occurrence_map.yaml`` ``moves:`` entry (``from`` paths -> ``to``)."""

    sources: tuple[str, ...]
    dest: str


@dataclass
class GenerateResult:
    """Outcome of :func:`generate`.

    ``emitted`` are the stub files written; ``dead_targets`` are ``(old, new)``
    pairs skipped because ``new`` is missing from the site (the no-404 invariant —
    no stub is written for them).
    """

    emitted: list[Path] = field(default_factory=list)
    dead_targets: list[tuple[str, str]] = field(default_factory=list)


# --- Input loading ----------------------------------------------------------


def load_baseline(manifest_path: Path) -> tuple[str, list[str]]:
    """Return ``(site_url, url_paths)`` from WP02's baseline manifest.

    ``url_paths`` are site-relative (the ``site_url`` prefix stripped), sorted and
    de-duplicated, so they line up with paths inside ``_site``.
    """
    data: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    site_url = str(data.get("site_url", SITE_URL))
    paths = {_strip_site(str(u), site_url) for u in data.get("urls", [])}
    return site_url, sorted(paths)


def load_moves(occurrence_map_path: Path) -> list[Move]:
    """Return the ``moves:`` spine from an ``occurrence_map.yaml``."""
    data: dict[str, Any] = yaml.safe_load(
        occurrence_map_path.read_text(encoding="utf-8")
    )
    moves: list[Move] = []
    for raw in data.get("moves", []) or []:
        sources = tuple(str(s) for s in raw.get("from", []))
        dest = str(raw.get("to", "")).rstrip("/")
        if sources and dest:
            moves.append(Move(sources=sources, dest=dest))
    return moves


def load_redirect_map(redirect_map_path: Path) -> dict[str, str]:
    """Load the committed redirect map (``{old_url_path: new_url_path}``)."""
    raw = yaml.safe_load(redirect_map_path.read_text(encoding="utf-8")) or {}
    return {str(k): str(v) for k, v in raw.items()}


def _strip_site(url: str, site_url: str) -> str:
    return url[len(site_url):] if url.startswith(site_url) else url


# --- Redirect-map derivation (single-writer) --------------------------------


def _url_path_to_repo_paths(url_path: str) -> tuple[str, ...]:
    """Map a published URL path back to its candidate ``docs/`` source path(s).

    Content pages publish ``docs/<rel>.md`` -> ``<rel>.html``; standalone
    resources (``1x``/``2x``/``assets``) publish ``docs/<rel>.html`` as-is. We
    return both candidate shapes so move-matching works for either.
    """
    repo_html = f"{DOCS_PREFIX}{url_path}"
    if repo_html.endswith(HTML_SUFFIX):
        repo_md = f"{repo_html[: -len(HTML_SUFFIX)]}{MD_SUFFIX}"
        return (repo_md, repo_html)
    return (repo_html,)


def _relocate(repo_path: str, moves: list[Move]) -> str | None:
    """Return the new repo path if a move relocates ``repo_path``, else ``None``."""
    for move in moves:
        for src in move.sources:
            if repo_path == src:
                return f"{move.dest}/{Path(src).name}"
            prefix = f"{src.rstrip('/')}/"
            if repo_path.startswith(prefix):
                return f"{move.dest}/{repo_path[len(prefix):]}"
    return None


def _repo_path_to_url_path(repo_path: str) -> str | None:
    """Convert a ``docs/`` source path to its published URL path, or ``None``.

    A source path that no longer lives under ``docs/`` has no published page to
    redirect to (it left the public tree), so it cannot back a stub.
    """
    if not repo_path.startswith(DOCS_PREFIX):
        return None
    rel = repo_path[len(DOCS_PREFIX):]
    if rel.endswith(MD_SUFFIX):
        rel = f"{rel[: -len(MD_SUFFIX)]}{HTML_SUFFIX}"
    return rel


def derive_redirect_map(
    baseline_url_paths: list[str],
    moves: list[Move],
) -> dict[str, str]:
    """Derive ``{old_url_path: new_url_path}`` from baseline URLs + the move spine.

    For each baseline (published) URL, find a move that relocates its source path
    *within the published tree* and record old->new when the URL actually changes.
    Driven purely by the two committed, immutable inputs, so the result is
    deterministic and diff-stable across the mission's timeline.
    """
    mapping: dict[str, str] = {}
    for url_path in baseline_url_paths:
        new_url = _resolve_new_url(url_path, moves)
        if new_url is not None and new_url != url_path:
            mapping[url_path] = new_url
    return dict(sorted(mapping.items()))


def _resolve_new_url(url_path: str, moves: list[Move]) -> str | None:
    for repo_path in _url_path_to_repo_paths(url_path):
        new_repo = _relocate(repo_path, moves)
        if new_repo is None:
            continue
        return _repo_path_to_url_path(new_repo)
    return None


def render_redirect_map(mapping: dict[str, str]) -> str:
    """Render the redirect map as deterministic, diff-stable YAML with a header."""
    body = yaml.safe_dump(
        dict(sorted(mapping.items())),
        default_flow_style=False,
        sort_keys=True,
        allow_unicode=True,
    )
    if not mapping:
        body = "{}\n"
    return f"{REDIRECT_MAP_HEADER}{body}"


def write_redirect_map(path: Path, mapping: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_redirect_map(mapping), encoding="utf-8")


# --- Stub emission + coverage -----------------------------------------------


def render_stub(new_url_path: str, site_url: str = SITE_URL) -> str:
    """Render the ``<meta refresh>`` stub HTML for ``new_url_path``."""
    target = f"{site_url}{new_url_path}"
    return STUB_TEMPLATE.format(target=target)


def generate(
    redirect_map: dict[str, str],
    site_dir: Path,
    site_url: str = SITE_URL,
) -> GenerateResult:
    """Emit ``<meta refresh>`` stubs at old paths inside ``site_dir``.

    A stub is written **only** when its ``new`` target resolves to a live page in
    ``site_dir`` — the no-404 invariant. Entries whose target is missing are
    reported in :attr:`GenerateResult.dead_targets` (and fail CI) rather than
    producing a stub that points at a 404.
    """
    result = GenerateResult()
    for old_path, new_path in sorted(redirect_map.items()):
        if not (site_dir / new_path).is_file():
            result.dead_targets.append((old_path, new_path))
            continue
        stub_path = site_dir / old_path
        stub_path.parent.mkdir(parents=True, exist_ok=True)
        stub_path.write_text(render_stub(new_path, site_url), encoding="utf-8")
        result.emitted.append(stub_path)
    return result


def check_coverage(
    baseline_url_paths: list[str],
    redirect_map: dict[str, str],
    site_dir: Path,
) -> list[str]:
    """Return the baseline URLs that are **not** covered post-move.

    Covered iff the URL resolves directly (page present) OR a stub exists at that
    path pointing to a live target. Caller is responsible for asserting the
    baseline is non-empty (see :func:`assert_non_vacuous`) so the gate never passes
    against an empty denominator.
    """
    uncovered: list[str] = []
    for url_path in baseline_url_paths:
        new_path = redirect_map.get(url_path)
        if new_path is None:
            if not (site_dir / url_path).is_file():
                uncovered.append(url_path)
            continue
        stub_present = (site_dir / url_path).is_file()
        target_live = (site_dir / new_path).is_file()
        if not (stub_present and target_live):
            uncovered.append(url_path)
    return uncovered


def assert_non_vacuous(baseline_url_paths: list[str]) -> None:
    """Guard against a false-green coverage check over an empty baseline."""
    if not baseline_url_paths:
        raise ValueError(
            "baseline URL set is empty — coverage check would be vacuous "
            "(NFR-002 denominator missing); refusing to report a false 100%."
        )


# --- CLI --------------------------------------------------------------------


def _default_occurrence_map() -> Path | None:
    """Resolve the mission's ``occurrence_map.yaml`` (the move spine source)."""
    return DEFAULT_OCCURRENCE_MAP if DEFAULT_OCCURRENCE_MAP.is_file() else None


def _cmd_regenerate_map(args: argparse.Namespace) -> int:
    occ = args.occurrence_map or _default_occurrence_map()
    if occ is None:
        print("ERROR: could not resolve occurrence_map.yaml; pass --occurrence-map")
        return 2
    _, baseline = load_baseline(args.baseline)
    mapping = derive_redirect_map(baseline, load_moves(occ))
    write_redirect_map(args.redirect_map, mapping)
    print(f"wrote {len(mapping)} redirect entries -> {args.redirect_map}")
    return 0


def _cmd_check_map(args: argparse.Namespace) -> int:
    occ = args.occurrence_map or _default_occurrence_map()
    if occ is None:
        print("ERROR: could not resolve occurrence_map.yaml; pass --occurrence-map")
        return 2
    _, baseline = load_baseline(args.baseline)
    derived = derive_redirect_map(baseline, load_moves(occ))
    committed = load_redirect_map(args.redirect_map)
    if derived != committed:
        print("ERROR: redirect_map.yaml is stale — re-run `regenerate-map`.")
        print(f"  derived={derived}")
        print(f"  committed={committed}")
        return 1
    print(f"redirect_map.yaml is fresh ({len(committed)} entries).")
    return 0


def _cmd_generate(args: argparse.Namespace) -> int:
    site_url, _ = load_baseline(args.baseline)
    redirect_map = load_redirect_map(args.redirect_map)
    result = generate(redirect_map, args.site_dir, site_url)
    print(f"emitted {len(result.emitted)} redirect stubs into {args.site_dir}")
    if result.dead_targets:
        print("ERROR: redirect stubs point at missing targets (no-404 invariant):")
        for old, new in result.dead_targets:
            print(f"  {old} -> {new} (target not in site)")
        return 1
    return 0


def _cmd_coverage(args: argparse.Namespace) -> int:
    _, baseline = load_baseline(args.baseline)
    assert_non_vacuous(baseline)
    redirect_map = load_redirect_map(args.redirect_map)
    uncovered = check_coverage(baseline, redirect_map, args.site_dir)
    print(
        f"coverage: {len(baseline) - len(uncovered)}/{len(baseline)} baseline URLs "
        f"covered ({len(redirect_map)} redirects)."
    )
    if uncovered:
        print("ERROR: uncovered baseline URLs (NFR-002 violation):")
        for url_path in uncovered:
            print(f"  {url_path}")
        return 1
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name, handler in (
        ("regenerate-map", _cmd_regenerate_map),
        ("check-map", _cmd_check_map),
        ("generate", _cmd_generate),
        ("coverage", _cmd_coverage),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
        sp.add_argument("--redirect-map", type=Path, default=DEFAULT_REDIRECT_MAP)
        sp.add_argument("--site-dir", type=Path, default=DEFAULT_SITE_DIR)
        sp.add_argument("--occurrence-map", type=Path, default=None)
        sp.set_defaults(handler=handler)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    handler: Any = args.handler
    return int(handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
