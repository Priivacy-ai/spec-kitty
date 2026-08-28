"""WP01 T002/T006 (mission charter-authority-flip-01M14RB3): the Charter
artifact owner-map, actually executed.

Asserts the M1 owner actions M1 itself performs:
  - the glossary-authority-quartet flip (charter present / doctrine absent,
    pinned in detail by ``test_glossary_authority_parity.py``);
  - the ``### charter`` Terminology-Canon entry landed in
    ``docs/context/charter.md`` (T004);
  - ``docs/context/doctrine.md`` -> ``docs/context/charter.md`` (OC-40).

H4 (squad finding): ``.kittify/charter/graph.yml`` and
``.kittify/charter/synthesis-manifest.yaml`` are **verify-no-op**, not
resynthesised -- M1 raises no owner action against them at all. This test
pins that they are byte-identical to the WP01 base commit
(``7b0c2d3ed53cd47ad50e4f75da84c7b9ca4c3044``, recorded in
``kitty-specs/charter-authority-flip-01M14RB3/tasks/WP01-glossary-quartet-parity.md``),
so a future edit that "helpfully" resynthesises them is caught immediately.

``.kittify/charter/context-state.json`` is deliberately NOT part of this
check: it is gitignored runtime state (``.gitignore`` line 91), never
tracked at any commit -- ``git ls-tree upstream/main --
.kittify/charter/context-state.json`` returns nothing, and it may not even
exist on disk in a given checkout. H4's "M1 raised no owner action" claim
is a statement about a TRACKED artifact's git history; it cannot apply to
untracked runtime state, which has no history to diff against.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.doctrine]


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


_REPO_ROOT = _repo_root()
_DOCTRINE_MD_PATH = _REPO_ROOT / "docs" / "context" / "doctrine.md"
_CHARTER_MD_PATH = _REPO_ROOT / "docs" / "context" / "charter.md"

#: WP01's own recorded base commit (tasks/WP01-glossary-quartet-parity.md
#: frontmatter `base_commit`) -- the point M1 branched from. H4's three
#: verify-no-op files must be byte-identical to their content at this
#: commit, proving M1 raised no owner action against them.
_WP01_BASE_COMMIT = "7b0c2d3ed53cd47ad50e4f75da84c7b9ca4c3044"

#: ``context-state.json`` is deliberately excluded here (see module
#: docstring): it is gitignored runtime state, never tracked at any commit,
#: so H4's "byte-identical to the WP01 base commit" check cannot apply to it.
_H4_VERIFY_NO_OP_FILES: tuple[Path, ...] = (
    _REPO_ROOT / ".kittify" / "charter" / "graph.yml",
    _REPO_ROOT / ".kittify" / "charter" / "synthesis-manifest.yaml",
)


def _git_diff_is_empty(repo_root: Path, base_commit: str, path: Path) -> bool | None:
    """Return True/False for a resolvable diff, or None if the base commit
    cannot be resolved locally (e.g. a shallow checkout) -- callers should
    skip rather than false-red in that case."""
    resolve = subprocess.run(
        ["git", "cat-file", "-e", f"{base_commit}^{{commit}}"],
        cwd=repo_root,
        capture_output=True,
    )
    if resolve.returncode != 0:
        return None
    result = subprocess.run(
        ["git", "diff", "--quiet", base_commit, "--", str(path.relative_to(repo_root))],
        cwd=repo_root,
        capture_output=True,
    )
    return result.returncode == 0


# ---------------------------------------------------------------------------
# Owner actions M1 actually performs
# ---------------------------------------------------------------------------


def test_glossary_authority_flip_ran() -> None:
    """The charter present / doctrine absent flip landed on the seed + pack."""
    from ruamel.yaml import YAML

    yaml = YAML(typ="safe")
    seed_path = _REPO_ROOT / ".kittify" / "glossaries" / "spec_kitty_core.yaml"
    with seed_path.open("r", encoding="utf-8") as fh:
        seed_data = yaml.load(fh)
    seed_surfaces = {t["surface"] for t in seed_data["terms"]}

    assert "charter" in seed_surfaces, "glossary flip owner action did not run: 'charter' absent from seed"
    assert "doctrine" not in seed_surfaces, "glossary flip owner action did not run: 'doctrine' still present in seed"


def test_charter_canon_entry_landed() -> None:
    assert _CHARTER_MD_PATH.exists(), "docs/context/charter.md does not exist -- OC-40 move did not run"
    text = _CHARTER_MD_PATH.read_text(encoding="utf-8")
    assert "### charter" in text, (
        "Terminology-Canon owner action did not run: no '### charter' entry in docs/context/charter.md"
    )


def test_doctrine_md_moved_to_charter_md() -> None:
    assert not _DOCTRINE_MD_PATH.exists(), "OC-40 move owner action did not run: docs/context/doctrine.md still present"
    assert _CHARTER_MD_PATH.exists(), "OC-40 move owner action did not run: docs/context/charter.md missing"


# ---------------------------------------------------------------------------
# H4: verify-no-op files untouched by M1
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target", _H4_VERIFY_NO_OP_FILES, ids=lambda p: p.name)
def test_h4_verify_no_op_files_unchanged_by_m1(target: Path) -> None:
    assert target.exists(), f"{target} unexpectedly missing -- H4 expects this file untouched, not deleted"

    is_empty = _git_diff_is_empty(_REPO_ROOT, _WP01_BASE_COMMIT, target)
    if is_empty is None:
        pytest.skip(
            f"WP01 base commit {_WP01_BASE_COMMIT} not resolvable in this checkout "
            "(likely a shallow clone) -- cannot verify H4 no-op via git diff"
        )
    assert is_empty, (
        f"{target.relative_to(_REPO_ROOT)} differs from its content at WP01 base commit "
        f"{_WP01_BASE_COMMIT} -- H4 requires M1 to raise NO owner action on this file "
        "(no resynthesis), only verify-no-op"
    )
