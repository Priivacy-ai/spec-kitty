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
_BASE_REF_CANDIDATES: Final[tuple[str, ...]] = (
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


def _resolve_base_sha() -> str:
    """Merge-base SHA whose tree still has the pre-move ADR originals.

    Fails loudly when unresolvable: a missing base would make the invariance
    proof vacuous, the exact false-green this gate guards against.
    """
    override = os.environ.get("SPEC_KITTY_ADR_BASE")
    refs = (override, *_BASE_REF_CANDIDATES) if override else _BASE_REF_CANDIDATES
    for ref in refs:
        try:
            sha = _git("merge-base", "HEAD", ref).strip()
        except subprocess.CalledProcessError:
            continue
        if sha:
            return sha
    pytest.fail(
        "cannot resolve a pre-move base ref "
        f"({', '.join(refs)}) — invariance proof would be vacuous"
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
        for post_path, pre_text in originals.items():
            if not post_path.is_file():
                missing_post.append(post_path.name)
                continue
            post_text = post_path.read_text(encoding="utf-8")
            # Sanity: the committed post must be the converter's own output.
            assert post_text == convert(pre_text, filename=post_path.name), (
                f"{post_path.name}: committed output diverges from converter"
            )
            if invariant(pre_text, post_text, filename=post_path.name):
                compared += 1
            else:
                mismatches.append(post_path.name)

        assert missing_post == [], f"pre-image had no post file: {missing_post}"
        assert mismatches == [], f"decision-body mutated (C-002): {mismatches}"
        # _EXPECTED_CENSUS - 1: the one FR-013 sanctioned self-amendment is
        # excluded from byte-identity (it is intentionally mutated), so a
        # non-vacuous run compares every *other* ADR.
        assert compared == _EXPECTED_INVARIANT, (
            f"non-vacuous invariance: compared {compared}, expected "
            f"{_EXPECTED_INVARIANT} — a 0/partial run is a false-green"
        )
