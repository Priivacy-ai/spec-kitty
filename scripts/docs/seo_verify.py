"""Built-output SEO verifier (IC-03).

Asserts metadata correctness against the **rendered** ``docs/_site`` tree, which
is the only layer that can observe a render-path defect. Source-level checks read
frontmatter; frontmatter can be perfectly correct while the emitted HTML omits
the tag entirely — exactly the state this mission repairs, where 147 pages had
correct-looking pipelines and zero ``<meta name="description">`` tags shipped.

Usage::

    python3 scripts/docs/seo_verify.py --site-dir docs/_site [--strict] [--json REPORT]

Exit contract mirrors :mod:`scripts.docs.description_length_check`: report-only
exits ``0``; ``--strict`` exits non-zero when any violation is found.

Two properties are load-bearing and deliberately non-obvious:

* **No second definition of "indexable" (I-08).** Classification calls
  :func:`scripts.docs.seo_postprocess.should_index` — the existing, working
  authority. Re-deriving the predicate here would reintroduce the very
  two-authorities bug the mission exists to repair, one module over.
* **Strictly read-only (C-B6).** Every file is opened for reading. A tool that
  can fix what it checks can pass itself, so ``_site`` is never mutated; the
  ``--json`` report is refused if it would be written inside the site tree.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Final

# ``scripts`` is not a package on ``sys.path`` when this file is run directly.
# Anchor the repo root so the indexability predicate and the shared metadata
# extractors resolve to the canonical seo_postprocess module rather than a
# forked copy — mirrors the sys.path bootstrap in ``glossary_linker.py``.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs.seo_postprocess import (  # noqa: E402  (sys.path bootstrap above)
    DEFAULT_BASE_URL,
    DEFAULT_TITLE,
    FALLBACK_DESCRIPTION,
    canonical_url,
    find_description,
    find_title,
    should_index,
)

__all__ = [
    "DEFAULT_SITE_DIR",
    "STALE_URL_FINDINGS",
    "AuditRecord",
    "PageClass",
    "RenderedPage",
    "StaleUrlFinding",
    "Violation",
    "build_parser",
    "classify",
    "main",
    "read_page",
    "verify_site",
]

DEFAULT_SITE_DIR: Final[str] = "docs/_site"

CANONICAL_RE: Final = re.compile(r'<link\s+rel="canonical"\s+href="(.*?)"\s*/?>', re.IGNORECASE | re.DOTALL)
OG_TITLE_RE: Final = re.compile(r'<meta\s+property="og:title"\s+content="(.*?)"\s*/?>', re.IGNORECASE | re.DOTALL)
OG_DESCRIPTION_RE: Final = re.compile(
    r'<meta\s+property="og:description"\s+content="(.*?)"\s*/?>', re.IGNORECASE | re.DOTALL
)
ROBOTS_RE: Final = re.compile(r'<meta\s+name="robots"\s+content="([^"]*)"', re.IGNORECASE)
SITEMAP_LOC_RE: Final = re.compile(r"<loc>(.*?)</loc>", re.IGNORECASE | re.DOTALL)

_REFRESH_MARKER: Final[str] = 'http-equiv="refresh"'
_SITEMAP_NAME: Final[str] = "sitemap.xml"

# Rule identifiers, as named in data-model.md / contracts/built-output-verifier.md.
_RULE_DESCRIPTION_PRESENT: Final[str] = "V-06"
_RULE_DESCRIPTION_NOT_BOILERPLATE: Final[str] = "V-07"
_RULE_CANONICAL: Final[str] = "V-08"
_RULE_OPEN_GRAPH: Final[str] = "V-09"
_RULE_DESCRIPTION_UNIQUE: Final[str] = "V-10"
_RULE_TITLE: Final[str] = "NFR-001"
_RULE_STUB: Final[str] = "I-09"
_RULE_SITEMAP: Final[str] = "C-B6"


class PageClass(StrEnum):
    """Exactly one class per built page; only ``INDEXABLE`` gets the rules.

    ``NOINDEX`` is the residual bucket: a page that :func:`should_index` rejects
    for a reason that is not "asset", "toc", or "redirect stub" — i.e. it carries
    an explicit ``robots: noindex`` directive. Naming it rather than folding it
    into a neighbouring class keeps the classification honest; silently calling
    such a page a ``TOC_PAGE`` would hide a real misconfiguration.
    """

    ASSET = "ASSET"
    TOC_PAGE = "TOC_PAGE"
    REDIRECT_STUB = "REDIRECT_STUB"
    NOINDEX = "NOINDEX"
    INDEXABLE = "INDEXABLE"


@dataclass(frozen=True, slots=True)
class RenderedPage:
    """Metadata observed in one built HTML file (``data-model.md``)."""

    relative_path: str
    classification: PageClass
    title: str | None
    description: str | None
    canonical: str | None
    og_title: str | None
    og_description: str | None
    robots: str | None

    @property
    def effective_title(self) -> str:
        """The title the emitter would have used for social metadata."""
        return self.title or DEFAULT_TITLE

    @property
    def effective_description(self) -> str:
        """The description the emitter would have used for social metadata."""
        return self.description or FALLBACK_DESCRIPTION

    def as_dict(self) -> dict[str, object]:
        """Serialize for the audit record."""
        return {
            "canonical": self.canonical,
            "classification": self.classification.value,
            "description": self.description,
            "og_description": self.og_description,
            "og_title": self.og_title,
            "relative_path": self.relative_path,
            "robots": self.robots,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class Violation:
    """A single rule failure, attributable to one page."""

    path: str
    rule: str
    detail: str | None = None
    peer: str | None = None

    def sort_key(self) -> tuple[str, str, str, str]:
        return (self.path, self.rule, self.detail or "", self.peer or "")

    def as_dict(self) -> dict[str, object]:
        return {"detail": self.detail, "path": self.path, "peer": self.peer, "rule": self.rule}


@dataclass(frozen=True, slots=True)
class StaleUrlFinding:
    """Evidence that an address reported in an issue is a pre-move address."""

    issue_url: str
    reported_address: str
    current_address: str


#: FR-011 / C-B8. The two addresses named in issue #1652 are pre-move addresses
#: now served as redirect stubs; the live pages carry correct metadata. Recording
#: this in the audit record is what lets the issue be closed on evidence.
STALE_URL_FINDINGS: Final[tuple[StaleUrlFinding, ...]] = (
    StaleUrlFinding(
        issue_url="https://github.com/Priivacy-ai/spec-kitty/issues/1652",
        reported_address="how-to/install-spec-kitty.html",
        current_address="guides/install-spec-kitty.html",
    ),
    StaleUrlFinding(
        issue_url="https://github.com/Priivacy-ai/spec-kitty/issues/1652",
        reported_address="reference/slash-commands.html",
        current_address="api/slash-commands.html",
    ),
)

_ABSENT: Final[str] = "ABSENT"
_NOTE_CONFIRMED: Final[str] = (
    "Confirmed in this build: the reported address is a redirect stub and the current "
    "address is an indexable page carrying its own description and canonical."
)
_NOTE_NOT_OBSERVED: Final[str] = (
    "Not observed in this build: one or both addresses are absent from the site tree."
)
_NOTE_UNEXPECTED: Final[str] = (
    "Both addresses are present but do not match the expected stub/live-page shape."
)


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """The reproducible evidence artifact (FR-001, FR-010)."""

    pages: tuple[RenderedPage, ...]
    violations: tuple[Violation, ...]
    findings: tuple[dict[str, object], ...]

    @property
    def counts(self) -> dict[str, int]:
        tally = Counter(page.classification.value for page in self.pages)
        return {member.value: tally.get(member.value, 0) for member in PageClass}

    def as_dict(self) -> dict[str, object]:
        return {
            "counts": self.counts,
            "findings": list(self.findings),
            "pages": [page.as_dict() for page in self.pages],
            "violations": [violation.as_dict() for violation in self.violations],
        }

    def to_json(self) -> str:
        """Deterministic serialization (I-06): sorted keys, sorted violations."""
        return json.dumps(self.as_dict(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


# --- Classification ---------------------------------------------------------


def classify(relative_path: str, markup: str) -> PageClass:
    """Classify one built page.

    ``should_index`` is the authority for the indexable/non-indexable split
    (I-08). The branches below only *explain* a negative verdict; they never
    override it, so this module cannot drift from the emitter's notion of what
    gets metadata.
    """
    if should_index(relative_path, markup):
        return PageClass.INDEXABLE
    rel = relative_path.replace("\\", "/")
    if rel.startswith("assets/"):
        return PageClass.ASSET
    if rel == "toc.html" or rel.endswith("/toc.html"):
        return PageClass.TOC_PAGE
    if _REFRESH_MARKER in markup.lower():
        return PageClass.REDIRECT_STUB
    return PageClass.NOINDEX


def _attribute(pattern: re.Pattern[str], markup: str) -> str | None:
    """Return the first captured attribute value, unescaped, or ``None``."""
    match = pattern.search(markup)
    if not match:
        return None
    return html.unescape(re.sub(r"\s+", " ", match.group(1))).strip() or None


def read_page(site_dir: Path, path: Path) -> RenderedPage:
    """Read one built page. Read-only: the file is never reopened for writing."""
    relative_path = path.relative_to(site_dir).as_posix()
    markup = path.read_text(encoding="utf-8")
    return RenderedPage(
        relative_path=relative_path,
        classification=classify(relative_path, markup),
        title=find_title(markup),
        description=find_description(markup),
        canonical=_attribute(CANONICAL_RE, markup),
        og_title=_attribute(OG_TITLE_RE, markup),
        og_description=_attribute(OG_DESCRIPTION_RE, markup),
        robots=_attribute(ROBOTS_RE, markup),
    )


# --- Rules V-06 … V-10 + NFR-001 -------------------------------------------


def _check_title(page: RenderedPage) -> list[Violation]:
    """NFR-001: a title must exist and must not be the bare site default."""
    if page.title is None:
        return [Violation(page.relative_path, _RULE_TITLE, "title missing or empty")]
    if page.title == DEFAULT_TITLE:
        return [Violation(page.relative_path, _RULE_TITLE, f"title is the site default: {page.title!r}")]
    return []


def _check_description(page: RenderedPage) -> list[Violation]:
    """V-06 / V-07: a description must be present and not the boilerplate."""
    if page.description is None:
        return [Violation(page.relative_path, _RULE_DESCRIPTION_PRESENT, 'no <meta name="description"> tag')]
    if page.description == FALLBACK_DESCRIPTION:
        return [
            Violation(
                page.relative_path,
                _RULE_DESCRIPTION_NOT_BOILERPLATE,
                "description is the boilerplate fallback",
            )
        ]
    return []


def _check_canonical(page: RenderedPage, base_url: str) -> list[Violation]:
    """V-08: the canonical link must address this very page."""
    expected = canonical_url(base_url, page.relative_path)
    if page.canonical == expected:
        return []
    observed = "missing" if page.canonical is None else page.canonical
    return [
        Violation(
            page.relative_path,
            _RULE_CANONICAL,
            f"canonical is {observed!r}, expected {expected!r}",
        )
    ]


def _check_open_graph(page: RenderedPage) -> list[Violation]:
    """V-09: Open Graph values must agree with the page's own title/description."""
    violations: list[Violation] = []
    if page.og_title != page.effective_title:
        violations.append(
            Violation(
                page.relative_path,
                _RULE_OPEN_GRAPH,
                f"og:title is {page.og_title!r}, expected {page.effective_title!r}",
            )
        )
    if page.og_description != page.effective_description:
        violations.append(
            Violation(
                page.relative_path,
                _RULE_OPEN_GRAPH,
                f"og:description is {page.og_description!r}, expected {page.effective_description!r}",
            )
        )
    return violations


def _check_duplicate_descriptions(indexable: list[RenderedPage]) -> list[Violation]:
    """V-10: descriptions must be unique, and a collision names both peers (I-07)."""
    by_description: dict[str, list[str]] = defaultdict(list)
    for page in indexable:
        if page.description is not None:
            by_description[page.description].append(page.relative_path)

    violations: list[Violation] = []
    for description, paths in by_description.items():
        if len(paths) < 2:
            continue
        for path in paths:
            peers = ", ".join(other for other in sorted(paths) if other != path)
            violations.append(
                Violation(
                    path,
                    _RULE_DESCRIPTION_UNIQUE,
                    f"description shared with {len(paths) - 1} other page(s): {description!r}",
                    peer=peers,
                )
            )
    return violations


def _check_stubs(stubs: list[RenderedPage], sitemap_urls: set[str], base_url: str) -> list[Violation]:
    """I-09 / FR-012: stubs stay noindex and stay out of the sitemap."""
    violations: list[Violation] = []
    for stub in stubs:
        if stub.robots is None or "noindex" not in stub.robots.lower():
            violations.append(
                Violation(stub.relative_path, _RULE_STUB, f"redirect stub robots is {stub.robots!r}, expected noindex")
            )
        address = canonical_url(base_url, stub.relative_path)
        if address in sitemap_urls:
            violations.append(
                Violation(stub.relative_path, _RULE_STUB, f"redirect stub address present in sitemap.xml: {address}")
            )
    return violations


def _check_sitemap(indexable: list[RenderedPage], sitemap_urls: set[str], base_url: str) -> list[Violation]:
    """C-B6: the sitemap's entry set equals the indexable page set."""
    expected = {canonical_url(base_url, page.relative_path): page.relative_path for page in indexable}
    violations = [
        Violation(relative_path, _RULE_SITEMAP, f"indexable page absent from sitemap.xml: {address}")
        for address, relative_path in expected.items()
        if address not in sitemap_urls
    ]
    violations += [
        Violation(_SITEMAP_NAME, _RULE_SITEMAP, f"sitemap entry has no indexable page: {address}")
        for address in sitemap_urls - set(expected)
    ]
    return violations


def _read_sitemap_urls(site_dir: Path) -> set[str]:
    """Return the ``<loc>`` set from ``sitemap.xml`` (empty when absent)."""
    sitemap = site_dir / _SITEMAP_NAME
    if not sitemap.is_file():
        return set()
    return {html.unescape(loc.strip()) for loc in SITEMAP_LOC_RE.findall(sitemap.read_text(encoding="utf-8"))}


# --- Audit ------------------------------------------------------------------


def _page_rules(page: RenderedPage, base_url: str) -> list[Violation]:
    """Per-page rules. Applied only to ``INDEXABLE`` pages (C-B5)."""
    return (
        _check_title(page)
        + _check_description(page)
        + _check_canonical(page, base_url)
        + _check_open_graph(page)
    )


def _finding_note(reported: RenderedPage | None, current: RenderedPage | None) -> str:
    """Describe what was *observed*, never more.

    The audit exists so issue #1652 can be closed on evidence. A fixed note
    asserting "the pre-move address is a stub" would still read as confirmation
    on a build where neither address is present — which is an assertion, not
    evidence. So the note states the observation that was actually made.
    """
    if reported is None or current is None:
        return _NOTE_NOT_OBSERVED
    confirmed = (
        reported.classification is PageClass.REDIRECT_STUB
        and current.classification is PageClass.INDEXABLE
        and current.description is not None
        and current.canonical is not None
    )
    return _NOTE_CONFIRMED if confirmed else _NOTE_UNEXPECTED


def _stale_url_findings(by_path: dict[str, RenderedPage]) -> tuple[dict[str, object], ...]:
    """Resolve :data:`STALE_URL_FINDINGS` against the built tree (FR-011)."""
    findings: list[dict[str, object]] = []
    for finding in STALE_URL_FINDINGS:
        reported = by_path.get(finding.reported_address)
        current = by_path.get(finding.current_address)
        findings.append(
            {
                "current_address": finding.current_address,
                "current_classification": _ABSENT if current is None else current.classification.value,
                "current_has_canonical": current is not None and current.canonical is not None,
                "current_has_description": current is not None and current.description is not None,
                "issue_url": finding.issue_url,
                "note": _finding_note(reported, current),
                "reported_address": finding.reported_address,
                "reported_classification": _ABSENT if reported is None else reported.classification.value,
            }
        )
    return tuple(findings)


def verify_site(*, site_dir: Path, base_url: str = DEFAULT_BASE_URL) -> AuditRecord:
    """Walk ``site_dir`` and apply every rule. Never writes to ``site_dir``."""
    pages = [read_page(site_dir, path) for path in sorted(site_dir.rglob("*.html"))]
    indexable = [page for page in pages if page.classification is PageClass.INDEXABLE]
    stubs = [page for page in pages if page.classification is PageClass.REDIRECT_STUB]
    sitemap_urls = _read_sitemap_urls(site_dir)

    violations: list[Violation] = []
    for page in indexable:
        violations += _page_rules(page, base_url)
    violations += _check_duplicate_descriptions(indexable)
    violations += _check_stubs(stubs, sitemap_urls, base_url)
    violations += _check_sitemap(indexable, sitemap_urls, base_url)
    violations.sort(key=Violation.sort_key)

    by_path = {page.relative_path: page for page in pages}
    return AuditRecord(
        pages=tuple(sorted(pages, key=lambda page: page.relative_path)),
        violations=tuple(violations),
        findings=_stale_url_findings(by_path),
    )


# --- CLI --------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """Build the verifier CLI parser."""
    parser = argparse.ArgumentParser(
        prog="seo_verify",
        description=(
            "Verify SEO metadata in the built docs site. Report-only (exit 0) "
            "unless --strict is passed."
        ),
    )
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=Path(DEFAULT_SITE_DIR),
        help=f"Built site directory to inspect (default: {DEFAULT_SITE_DIR}).",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"Canonical base URL the site publishes under (default: {DEFAULT_BASE_URL}).",
    )
    parser.add_argument(
        "--json",
        type=Path,
        default=None,
        metavar="REPORT",
        help="Write the audit record to REPORT (must be outside --site-dir).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero when any violation is found.",
    )
    return parser


def _resolve_report_path(report: Path, site_dir: Path) -> Path:
    """Refuse a report path inside the site tree — the verifier is read-only."""
    resolved = report.resolve()
    if resolved.is_relative_to(site_dir):
        raise SystemExit(f"--json must not write inside --site-dir (read-only): {resolved}")
    return resolved


def _emit_summary(record: AuditRecord) -> None:
    """Print a human-readable summary to stdout."""
    counts = record.counts
    sys.stdout.write(
        f"seo_verify: {len(record.pages)} built page(s) "
        f"({counts[PageClass.INDEXABLE.value]} indexable, "
        f"{counts[PageClass.REDIRECT_STUB.value]} redirect stub(s)); "
        f"{len(record.violations)} violation(s).\n"
    )
    for violation in record.violations:
        peer = f" [peer: {violation.peer}]" if violation.peer else ""
        sys.stdout.write(f"  {violation.rule} {violation.path}: {violation.detail}{peer}\n")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point. Returns the process exit code."""
    args = build_parser().parse_args(argv)
    site_dir = args.site_dir.resolve()
    if not site_dir.is_dir():
        raise SystemExit(f"Site directory not found: {site_dir}")

    report_path = None if args.json is None else _resolve_report_path(args.json, site_dir)
    record = verify_site(site_dir=site_dir, base_url=args.base_url)
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(record.to_json(), encoding="utf-8")
    _emit_summary(record)
    return 1 if (args.strict and record.violations) else 0


if __name__ == "__main__":  # pragma: no cover - module-level CLI guard
    raise SystemExit(main())
