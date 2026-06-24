"""FR-005 boundary-contract ratchet — no write-side re-derivation (WP08 / T037).

The Mission A boundary contract (IC-01), ENFORCED here: after the write-side
adoption (WP02–WP06), **no** write surface in the adopted scope re-derives
``mission_id`` / ``mid8`` / ``primary_root`` independently. Identity/root/target
flow from the factory-projected fragments via the existing public resolvers
(``resolve_canonical_root`` / ``resolve_status_surface`` /
``resolve_placement_only`` / ``resolve_lanes_dir``), not hand-rolled walks.

This is the one allowed form-coupled test (NFR-003): a guard that FLAGS write-side
re-derivation in the adopted modules. It must:

* be **line-scoped**, not file-scoped — a file-level allow-list is a blanket
  escape and is rejected (paula SF-2). The allow-list is seeded with ONLY the
  genuinely-deferred S2 #1716 ladder line.
* **bite** — a companion self-test plants a re-derivation in a fixture string and
  asserts the detector FLAGS it, proving the guard is not inert.
* **pass on the post-adoption tree** — a flag on an adopted module would mean that
  module still re-derives (a real FR-005 finding).

Detection is **token-based** (``tokenize``): only real code tokens are scanned, so
docstrings and comments that merely *describe* the prior walk (e.g. the
``_resolve_write_target`` docstring quoting the old selector) are NOT flagged. A
naive line/regex scan would false-flag those narrative lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import code_tokens_by_line, composite_key

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "specify_cli"

#: The write-side modules the adoption touched (US-1..US-4, FR-001/FR-002/
#: FR-003/FR-004/FR-008). These are the surfaces the boundary contract binds.
_ADOPTED_MODULES: tuple[Path, ...] = (
    _SRC / "status" / "emit.py",
    _SRC / "status" / "work_package_lifecycle.py",
    _SRC / "status" / "lifecycle_events.py",
    _SRC / "status" / "store.py",
    _SRC / "coordination" / "status_transition.py",
    _SRC / "core" / "worktree.py",
)


@dataclass(frozen=True)
class _Finding:
    """A flagged write-side re-derivation: (path, line, kind, code, source)."""

    path: Path
    lineno: int
    kind: str
    code: str
    source: str

    def as_allow_key(self) -> tuple[str, str]:
        """The drift-proof ``(qualname, token_line)`` composite allow-list key.

        Content-addressed (enclosing function + tokenized code line), not
        line-number addressed, so a benign blank/comment-line insertion above the
        guarded site leaves the key unchanged (FR-008 / WP06).
        """
        return composite_key(self.source, self.lineno)


#: Line-scoped allow-list, re-keyed onto the drift-proof
#: ``(enclosing_qualname, token_line)`` composite key (FR-008 / WP06).  It is
#: still line-SCOPED (a single specific deferred line, NOT a blanket file
#: escape), but content-addressed rather than line-NUMBER addressed: a benign
#: blank/comment insertion above the site no longer flips the ratchet RED.
#:
#: The single seed is ``coordination/status_transition.py`` line ~336
#: (re-grounded from ~295 by the single-mission-surface-resolver WP06 #1900
#: predicate migration, which added the canonical-seam delegating helpers above
#: this line — same deferred selector, shifted lineno, NOT a new offender):
#: ``return coord_branch or _current_branch(repo_root)`` — the FALLBACK arm of
#: ``_resolve_write_target``, reached only when ``resolve_placement_only`` cannot
#: resolve the mission (pre-meta create window / ad-hoc fixture). It is the last
#: surviving ``_current_branch`` git-HEAD selector and belongs to the deferred
#: #1716 write-surface-SELECTION ladder (spec C-003 / plan D-1, OUT of scope).
#: It is NOT on the genuine-simple-case path (NFR-006) and is asserted as deferred
#: residual in ``test_simple_case_flat_topology.py``.
#:
#: Adding a NEW entry here is a deliberate scope decision, not a routine escape:
#: it must point at a specific deferred-by-spec line, with a one-line rationale.

#: Seed mapping each deferred line to ``(rel_path, line)``.  The composite key is
#: derived LIVE from this seed via ``composite_key`` at import (NFR-004: never
#: hand-author a ``(qualname, token_line)`` literal).  ``_ALLOW_LIST_SEED`` is
#: also the staleness anchor — ``test_allow_listed_line_is_the_deferred_head_selector``
#: re-reads the seed file to prove the composite key still holds the deferred
#: HEAD selector.
_ALLOW_LIST_SEED: tuple[tuple[str, int], ...] = (
    # write-surface-coherence WP02 / T031: threading the required STATUS_STATE kind
    # into ``_resolve_write_target`` shifted the deferred HEAD-selector fallback arm
    # from :336 to :343 (the ``coord_branch or _current_branch`` line). The seed is
    # re-anchored to the live line so the composite key still resolves it.
    ("src/specify_cli/coordination/status_transition.py", 343),
)


def _composite_key_for_seed(rel_path: str, lineno: int) -> tuple[str, str]:
    """Derive the composite key for a seed entry from the live source file."""
    source = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
    return composite_key(source, lineno)


#: Composite-keyed allow-list: ``frozenset[(qualname, token_line)]``.
_ALLOW_LIST: frozenset[tuple[str, str]] = frozenset(
    _composite_key_for_seed(rel_path, lineno)
    for rel_path, lineno in _ALLOW_LIST_SEED
)


def _scan_source(source: str, path: Path) -> list[_Finding]:
    """Flag write-side re-derivation in CODE lines of ``source``.

    Three re-derivation grammars (randy's write-path census / FR-005):

    * ``feature_dir.parent.parent`` (and deeper) root walks — tokenizes to
      ``. parent . parent`` / ``parent . parent``.
    * inline ``mission_id[:8]`` / ``mid8`` recompute — tokenizes to
      ``mission_id [ : 8 ]``.
    * ``coord_branch or _current_branch`` / ``coord_branch or current_branch``
      git-HEAD write-target selectors.
    """
    findings: list[_Finding] = []
    for lineno, code in code_tokens_by_line(source).items():
        if "parent . parent" in code:
            findings.append(_Finding(path, lineno, "root_walk", code, source))
        if "mission_id [ : 8 ]" in code:
            findings.append(_Finding(path, lineno, "mid8_recompute", code, source))
        if "coord_branch or _current_branch" in code or "coord_branch or current_branch" in code:
            findings.append(_Finding(path, lineno, "write_target_head_selector", code, source))
    return findings


def _scan_module(path: Path) -> list[_Finding]:
    return _scan_source(path.read_text(encoding="utf-8"), path)


# ---------------------------------------------------------------------------
# The ratchet: adopted modules carry no un-allow-listed re-derivation.
# ---------------------------------------------------------------------------


def test_adopted_modules_have_no_write_side_rederivation() -> None:
    """FR-005 / C-BOUNDARY: every adopted module is free of re-derivation.

    A flag on an adopted module that is NOT on the line-scoped allow-list means
    that module still re-derives identity/root/target by hand — a real boundary
    violation. The only permitted residual is the deferred S2 #1716 ladder line.
    """
    offenders: list[str] = []
    for module in _ADOPTED_MODULES:
        assert module.exists(), f"adopted module missing: {module}"
        for finding in _scan_module(module):
            if finding.as_allow_key() in _ALLOW_LIST:
                continue
            offenders.append(
                f"{finding.path.relative_to(_REPO_ROOT)}:{finding.lineno} "
                f"[{finding.kind}] {finding.code}"
            )

    assert not offenders, (
        "Write-side re-derivation found in adopted modules (FR-005 / C-BOUNDARY). "
        "Identity/root/target MUST flow from the factory-projected fragments via "
        "the public resolvers, not hand-rolled walks. Offenders:\n"
        + "\n".join(offenders)
    )


# ---------------------------------------------------------------------------
# "Ratchet bites" — the guard is not inert.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("planted", "expected_kind"),
    [
        ("    root = feature_dir.parent.parent\n", "root_walk"),
        ("    mid8 = mission_id[:8]\n", "mid8_recompute"),
        ("    ref = coord_branch or _current_branch(repo_root)\n", "write_target_head_selector"),
    ],
)
def test_ratchet_bites_on_planted_rederivation(planted: str, expected_kind: str) -> None:
    """The detector FLAGS a planted re-derivation — proving the guard bites.

    Without this, a vacuous detector (one that never matches) would pass the
    ratchet above regardless. We feed the detector a fixture source string
    carrying each forbidden grammar and assert it is flagged with the right kind.
    """
    fixture_source = (
        "def _adopted_write_site(feature_dir, mission_id, coord_branch, repo_root):\n"
        '    """A docstring that merely mentions feature_dir.parent.parent must NOT flag."""\n'
        "    # a comment quoting coord_branch or _current_branch must NOT flag\n"
        f"{planted}"
        "    return root\n"
    )
    findings = _scan_source(fixture_source, _SRC / "coordination" / "status_transition.py")
    kinds = {f.kind for f in findings}
    assert expected_kind in kinds, (
        f"ratchet failed to flag planted {expected_kind!r}; got {kinds}"
    )


def test_ratchet_ignores_prose_quoting_a_prior_walk() -> None:
    """Docstrings/comments that DESCRIBE the prior walk are NOT flagged.

    The adopted ``_resolve_write_target`` docstring quotes the old
    ``coord_branch or _current_branch`` selector to document the fix; a
    line/regex scan would false-flag it. The token-based detector must see only
    code — this pins that the prose-only source yields ZERO findings.
    """
    prose_only = (
        "def _adopted_resolver(repo_root, mission_slug, coord_branch):\n"
        '    """The prior inline selector was coord_branch or _current_branch(repo_root).\n'
        "\n"
        "    It walked feature_dir.parent.parent and sliced mission_id[:8] by hand.\n"
        '    """\n'
        "    # historical: coord_branch or _current_branch(repo_root) and mission_id[:8]\n"
        "    return resolve_placement_only(repo_root, mission_slug).ref\n"
    )
    assert _scan_source(prose_only, _SRC / "coordination" / "status_transition.py") == []


def test_allow_list_is_line_scoped_not_a_blanket_file_escape() -> None:
    """The allow-list keys are ``(qualname, token_line)`` composites — never bare paths.

    A file-scoped allow-list would silently excuse any future re-derivation added
    anywhere in that file (a blanket escape, rejected by paula SF-2). The
    composite re-key (FR-008 / WP06) keeps the entry line-SCOPED — it pins a
    specific enclosing function AND a specific tokenized code line, NOT a whole
    file. This re-expresses the original anti-blanket-escape intent for the new
    key shape: each entry must be a 2-tuple of non-empty ``str``s whose second
    component (the token_line) is a real code line, never a whole-file wildcard.
    """
    assert _ALLOW_LIST, "the allow-list must seed the known deferred S2 #1716 line"
    for entry in _ALLOW_LIST:
        assert isinstance(entry, tuple) and len(entry) == 2, (
            f"allow-list entry must be a (qualname, token_line) composite, got {entry!r}"
        )
        qualname, token_line = entry
        assert isinstance(qualname, str) and qualname, (
            f"qualname component must be a non-empty str, got {qualname!r}"
        )
        assert isinstance(token_line, str) and token_line, (
            "token_line component must be a non-empty code line (a real line, "
            f"not a whole-file wildcard), got {token_line!r}"
        )


def test_allow_listed_line_is_the_deferred_head_selector() -> None:
    """The single allow-listed line really IS the deferred #1716 HEAD selector.

    Guards against allow-list rot: if the seeded line drifts off the
    ``coord_branch or _current_branch`` fallback (e.g. the file is re-ordered or
    the deferred ladder is finally retired), this test fails loudly so the
    allow-list is re-grounded rather than silently masking a moved offender.

    Resolves the composite key back to its live token_line (the second component
    IS the tokenized source line) and asserts it still holds the selector. Also
    cross-checks the seed file still produces that composite key, so a function
    rename or code-line change is caught too.
    """
    rel_path, lineno = _ALLOW_LIST_SEED[0]
    key = _composite_key_for_seed(rel_path, lineno)
    _qualname, token_line = key
    assert "coord_branch or _current_branch" in token_line, (
        f"allow-listed {rel_path}:{lineno} no longer holds the deferred HEAD "
        f"selector (got token_line {token_line!r}); re-ground the allow-list "
        "against the current deferred S2 #1716 ladder line or remove the entry "
        "if it was retired."
    )
    # The seed must still resolve to an allow-listed composite key (no drift off
    # the function / code line).
    assert key in _ALLOW_LIST, (
        f"the seed {rel_path}:{lineno} composite key {key!r} is not in _ALLOW_LIST "
        "— the seed and the derived allow-list are out of sync."
    )
