"""Post-move census gate for the 117 unique ADRs (WP06).

WP06 ran WP05's extended converter over the live tree, moving the **117
realpath-unique** ADRs to ``docs/adr/<era>/`` with bare-``status`` frontmatter and
dropping the 71 back-compat symlinks. This module is the surviving **merge-blocker**
CI gate for that move (C-002 / NFR-001):

* :class:`TestCensus` — exactly **117** ADR files live under ``docs/adr/<era>/``
  (a count ``< 117`` is a *lost* ADR; ``> 117`` is a leaked duplicate or an
  undropped mirror), no dangling back-compat symlink survives, and every ADR
  carries bare-``status`` MADR frontmatter. These are permanent on-disk
  invariants — they read only the assembled tree.

Retired (2026-06-29): the byte-identity content-invariance proof
(``TestContentInvariance`` + its ``TestBaseResolutionIsRebaseRobust`` support)
was a **transitional** gate for the move itself. It recovered each ADR's
pre-move original by resolving the merge-base of HEAD with a planning-base ref
that still held the ``architecture/<era>/adr`` originals. That premise is
**unreachable once the move is merged to main**: a branch cut from post-move
main has no candidate whose merge-base predates the move, and the only ref that
still resolved (the ``docs/2165-mission-b-structural-move`` mission branch) does
not exist on a fresh CI checkout — so the gate failed loudly on every PR after
the move landed (a self-invalidating gate). It also conflicted by construction
with WP08's ``bulk_ref_rewrite.py``, which deliberately rewrote moved cross-ADR
links *after* conversion, so the committed ADRs no longer match a fresh
converter run on the pre-move original. The move was proven byte-identical at
the time it was made; that proof is in mission B's history. The permanent census
invariants below continue to guard the result.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Final

import pytest

# ``conftest.py`` puts the repo root on sys.path so ``scripts.docs`` imports.
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs._inventory import parse_frontmatter  # noqa: E402
from scripts.docs.adr_converter import MADR_STATUSES  # noqa: E402

# On-disk census invariants over the assembled tree. ``architectural`` puts this
# in the dedicated arch shard; ``git_repo`` is retained so CI's ``-m git_repo``
# filter keeps selecting it in the shard it has always run in.
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_DOCS_ADR: Final[Path] = _REPO_ROOT / "docs" / "adr"
_ERAS: Final[tuple[str, ...]] = ("1.x", "2.x", "3.x")
_DATE_PREFIX: Final[re.Pattern[str]] = re.compile(r"^\d{4}-\d{2}-\d{2}-")
_EXPECTED_CENSUS: Final[int] = 117


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
