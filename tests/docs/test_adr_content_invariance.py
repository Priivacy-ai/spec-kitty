"""Post-move content-invariance + census gate for the 117 unique ADRs (WP06).

WP06 ran WP05's extended converter over the live tree, moving the **117
realpath-unique** ADRs to ``docs/adr/<era>/`` with bare-``status`` frontmatter and
dropping the 71 back-compat symlinks. This module is the **merge-blocker** CI
gate for that move (C-002 / NFR-001):

* :class:`TestCensus` — exactly **117** ADR files live under ``docs/adr/<era>/``
  (a count ``< 117`` is a *lost* ADR; ``> 117`` is a leaked duplicate or an
  undropped mirror). No dangling back-compat symlink survives.
* :class:`TestContentInvariance` — for every one of the 117, the decision body
  is **byte-identical** to its pre-move original. The pre-image is recovered from
  git at the merge-base with the planning base (the originals are gone from the
  working tree after the move), reusing WP05's :func:`invariant` — **not** a
  forked comparator and **not** a re-render. The proof is **non-vacuous**: it
  asserts it compared exactly **117** files, and fails loudly (never skips) if
  the pre-image base cannot be resolved — a silent 0-file run is the precise
  false-green this gate exists to catch.

The reconciliation-ADR self-amendment (FR-013) is WP15's sanctioned prose edit:
the ``2026-06-27-1-common-docs-reconciliation.md`` decision body is mutated on
purpose (its "install as peer skills" Neutral note now records the three doctrine
tactics that shipped). C-002's no-content-mutation protects ADR decision-records
being *moved* — **not** this one sanctioned self-amendment — so this single file
is excluded from the byte-identity comparison (it still counts in the 117-file
census; it just isn't held byte-invariant). Every *other* ADR is a pure move and
stays byte-invariant.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Final

import pytest

# ``conftest.py`` puts the repo root on sys.path so ``scripts.docs`` imports.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs._inventory import parse_frontmatter  # noqa: E402
from scripts.docs.adr_converter import (  # noqa: E402
    AdrParseError,
    MADR_STATUSES,
    convert,
    invariant,
)

_DOCS_ADR: Final[Path] = _REPO_ROOT / "docs" / "adr"
_ERAS: Final[tuple[str, ...]] = ("1.x", "2.x", "3.x")
_DATE_PREFIX: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_EXPECTED_CENSUS: Final[int] = 117

#: The one ADR sanctioned to be self-amended in Mission B (FR-013): its Neutral
#: note is rewritten to record the three doctrine tactics that shipped. It is
#: excluded from the byte-identity comparison (but still counted in the census),
#: so the invariance proof compares ``_EXPECTED_CENSUS - 1`` files.
_SANCTIONED_SELF_AMENDMENT: Final[str] = "2026-06-27-1-common-docs-reconciliation.md"
_EXPECTED_INVARIANT: Final[int] = _EXPECTED_CENSUS - 1

#: Planning base refs that still hold the pre-move ``architecture/.../adr``
#: originals. The merge-base of HEAD with the first that resolves is the
#: pre-image source. ``SPEC_KITTY_ADR_BASE`` overrides for unusual CI layouts.
#: Ordered so a base that still holds the pre-move originals is found whether
#: the mission branch is unrebased (its own tip straddles the old base) or has
#: been rebased onto a ``main`` that predates the move (the branch self-ref then
#: degenerates to HEAD — a *post-move* tree — and must be rejected, not used).
#: Every candidate is validated by :func:`_tree_has_premove_originals` before
#: use, so ordering is a preference, not a correctness dependency.
_BASE_REF_CANDIDATES: Final[tuple[str, ...]] = (
    "main",
    "upstream/main",
    "origin/main",
    "docs/2165-mission-b-structural-move",
    "origin/docs/2165-mission-b-structural-move",
)


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _adr_files_on_disk() -> list[Path]:
    """Every dated ADR file under ``docs/adr/<era>/`` (READMEs excluded)."""
    found: list[Path] = []
    for era in _ERAS:
        era_dir = _DOCS_ADR / era
        if not era_dir.is_dir():
            continue
        for path in era_dir.glob("*.md"):
            if path.is_file() and _DATE_PREFIX.match(path.name):
                found.append(path)
    return found


def _tree_has_premove_originals(sha: str) -> bool:
    """True iff the tree at *sha* still holds the legacy ADR originals.

    A valid pre-image base predates WP06's move: its tree carries
    ``architecture/<era>/adr`` (or flat ``architecture/adrs``) originals and has
    **not** yet grown the post-move ``docs/adr/<era>`` tree. A post-move tree —
    e.g. HEAD after the mission branch is rebased onto a moved ``main``, or the
    branch self-ref degenerating to HEAD — yields converted MADR files the
    legacy converter cannot parse; selecting it would make the proof error
    spuriously, so it is rejected here rather than silently mis-read downstream.
    """
    paths = _git("ls-tree", "-r", "--name-only", sha).splitlines()
    has_legacy = any(
        p.startswith("architecture/adrs/")
        or any(p.startswith(f"architecture/{era}/adr/") for era in _ERAS)
        for p in paths
    )
    has_postmove = any(
        p.startswith("docs/adr/") and _DATE_PREFIX.match(p.rsplit("/", 1)[-1])
        for p in paths
    )
    return has_legacy and not has_postmove


def _resolve_base_sha() -> str:
    """Merge-base SHA whose tree still has the pre-move ADR originals.

    Rebase-robust: each candidate's merge-base is validated to actually hold
    pre-move originals (see :func:`_tree_has_premove_originals`); a post-move
    merge-base (the self-branch ref after a rebase, or HEAD itself) is rejected.
    Fails loudly when none resolve — a missing/post-move base would make the
    invariance proof vacuous or spuriously error, the false-green this guards.
    """
    override = os.environ.get("SPEC_KITTY_ADR_BASE")
    refs = (override, *_BASE_REF_CANDIDATES) if override else _BASE_REF_CANDIDATES
    rejected: list[str] = []
    for ref in refs:
        try:
            sha = _git("merge-base", "HEAD", ref).strip()
        except subprocess.CalledProcessError:
            rejected.append(f"{ref}: ref unresolved")
            continue
        if not sha:
            rejected.append(f"{ref}: empty merge-base")
            continue
        if not _tree_has_premove_originals(sha):
            rejected.append(f"{ref}: merge-base {sha[:9]} is a post-move tree")
            continue
        return sha
    pytest.fail(
        "cannot resolve a pre-move ADR base — invariance proof would be "
        "vacuous. Candidates tried:\n  " + "\n  ".join(rejected)
        + "\nSet SPEC_KITTY_ADR_BASE to a commit/ref whose tree still holds "
        "the architecture/<era>/adr originals."
    )


def _preimage_originals(base_sha: str) -> dict[Path, str]:
    """Map each post-move ADR path → its verbatim pre-move original text.

    Reads the base tree via ``git``: real ADR blobs (mode ``100644``) under the
    four legacy ADR homes, skipping symlinks (mode ``120000``) and READMEs.
    """
    listing = _git(
        "ls-tree", "-r", "--format=%(objectmode) %(path)", base_sha
    )
    originals: dict[Path, str] = {}
    for line in listing.splitlines():
        mode, _, path = line.partition(" ")
        if mode == "120000":  # back-compat symlink — never a distinct ADR
            continue
        name = path.rsplit("/", 1)[-1]
        if not _DATE_PREFIX.match(name):
            continue
        if name == _SANCTIONED_SELF_AMENDMENT:
            # FR-013 sanctioned self-amendment — excluded from byte-identity.
            continue
        era = _legacy_path_to_era(path)
        if era is None:
            continue
        post_path = _DOCS_ADR / era / name
        originals[post_path] = _git("show", f"{base_sha}:{path}")
    return originals


def _legacy_path_to_era(path: str) -> str | None:
    """Resolve a legacy ADR path to its destination era under ``docs/adr``."""
    for era in _ERAS:
        if path.startswith(f"architecture/{era}/adr/"):
            return era
    # The 20 era-less ADRs lived in the flat ``architecture/adrs/`` home (and a
    # late-mission ``docs/adr/3.x/`` staging area). WP06's extended converter
    # moves both into ``docs/adr/3.x/`` at pinned names. The pre-image base for
    # these is ``architecture/adrs/<name>`` (the merge-base predates their
    # ``docs/adr/3.x/`` appearance), so recognising that flat home is what makes
    # the census reach the full 117 on the assembled tree.
    if path.startswith("architecture/adrs/") or path.startswith("docs/adr/3.x/"):
        return "3.x"
    return None


class TestCensus:
    def test_exactly_117_unique_adrs(self) -> None:
        files = _adr_files_on_disk()
        realpaths = {os.path.realpath(p) for p in files}
        assert len(files) == _EXPECTED_CENSUS, (
            f"expected {_EXPECTED_CENSUS} ADRs under docs/adr/<era>/, "
            f"found {len(files)}"
        )
        assert len(realpaths) == _EXPECTED_CENSUS, (
            "realpath-unique ADR count drifted from 117 — a duplicate leaked"
        )

    def test_no_dangling_back_compat_symlinks(self) -> None:
        dangling = [
            p
            for p in _DOCS_ADR.rglob("*")
            if p.is_symlink() and not p.exists()
        ]
        assert dangling == [], f"dangling symlinks under docs/adr: {dangling}"

    def test_every_adr_has_bare_madr_status_frontmatter(self) -> None:
        canonical = set(MADR_STATUSES.values())
        offenders: list[str] = []
        for path in _adr_files_on_disk():
            front = parse_frontmatter(path.read_text(encoding="utf-8"))
            status = front.get("status") if front else None
            if status not in canonical:
                offenders.append(f"{path.name}: status={status!r}")
        assert offenders == [], f"non-MADR / missing bare status: {offenders}"


class TestContentInvariance:
    def test_body_byte_identical_for_all_117_non_vacuous(self) -> None:
        base_sha = _resolve_base_sha()
        originals = _preimage_originals(base_sha)

        compared = 0
        mismatches: list[str] = []
        missing_post: list[str] = []
        convert_errors: list[str] = []
        divergences: list[str] = []
        # Collect every per-file failure instead of raising on the first, so a
        # red run names all offending ADRs at once (no manual bisect needed).
        for post_path, pre_text in originals.items():
            if not post_path.is_file():
                missing_post.append(post_path.name)
                continue
            post_text = post_path.read_text(encoding="utf-8")
            # Sanity: the committed post must be the converter's own output.
            try:
                rendered = convert(pre_text, filename=post_path.name)
            except AdrParseError as exc:
                convert_errors.append(f"{post_path.name}: {exc}")
                continue
            if post_text != rendered:
                divergences.append(post_path.name)
                continue
            if invariant(pre_text, post_text, filename=post_path.name):
                compared += 1
            else:
                mismatches.append(post_path.name)

        report: list[str] = []
        if missing_post:
            report.append(
                f"pre-image had no post file ({len(missing_post)}): {missing_post}"
            )
        if convert_errors:
            report.append(
                f"converter could not parse pre-image ({len(convert_errors)}): "
                f"{convert_errors}"
            )
        if divergences:
            report.append(
                f"committed output diverges from converter ({len(divergences)}): "
                f"{divergences}"
            )
        if mismatches:
            report.append(
                f"decision-body mutated, C-002 ({len(mismatches)}): {mismatches}"
            )
        assert not report, "ADR content-invariance failures:\n- " + "\n- ".join(report)

        # _EXPECTED_CENSUS - 1: the one FR-013 sanctioned self-amendment is
        # excluded from byte-identity (it is intentionally mutated), so a
        # non-vacuous run compares every *other* ADR.
        assert compared == _EXPECTED_INVARIANT, (
            f"non-vacuous invariance: compared {compared}, expected "
            f"{_EXPECTED_INVARIANT} — a 0/partial run is a false-green"
        )


class TestBaseResolutionIsRebaseRobust:
    """The pre-image base must resolve to a real pre-move tree regardless of
    whether the mission branch has been rebased onto a moved ``main`` (which
    makes the branch self-ref degenerate to a post-move HEAD)."""

    def test_resolved_base_is_a_premove_tree(self) -> None:
        base = _resolve_base_sha()
        assert _tree_has_premove_originals(base), (
            f"resolved base {base[:9]} is not a pre-move tree — the invariance "
            "proof would read already-converted MADR files as pre-images"
        )

    def test_head_is_rejected_as_a_postmove_tree(self) -> None:
        # HEAD on this branch is post-move; selecting it (the exact regression a
        # rebase introduces via the self-branch ref) must be rejected.
        head = _git("rev-parse", "HEAD").strip()
        assert not _tree_has_premove_originals(head), (
            "HEAD still carries legacy architecture/ ADR originals — the move "
            "has not happened, so this guard cannot detect the post-move case"
        )
