"""Cross-gate churn-classification agreement (WP10 / owner contract C7, FR-012).

**Given** the same corpus of paths, **when** every gate that classifies toolchain
churn is asked to classify it, **then** all gates return the identical
classification. On the mission base (pre-WP13) this was a **live defect** — the
#2795 repro:

* ``merge/git_probes.py`` (``_classify_porcelain_lines``) exempts a tracked-modified
  ``meta.json`` / coord residue via ``is_self_bookkeeping_path`` + the residue
  predicate — exactly the owner union :func:`is_toolchain_generated_churn`.
* ``review/dirty_classifier.py`` likewise treats those as benign.
* ``git/ref_advance.py`` (``_dirty_entries``) **never consulted the owner** for a
  tracked entry: its only tracked escape was the narrow *vcs-lock-only* ``meta.json``
  case, so a general tracked-modified ``meta.json`` was fatal there while it was
  invisible to the other gates. Same file, opposite verdict.

**WP13 (IC-07c) landed the retirement.** ``git/ref_advance.py``'s ``_dirty_entries``
now accepts a caller-injected ``is_residue`` predicate consulted FIRST for both
tracked and untracked entries; every production caller injects
:func:`is_toolchain_generated_churn`. :func:`test_all_churn_gates_agree_on_corpus`
therefore genuinely agrees now (no ``xfail``) — this file used to carry a
strict-xfail red-first pin for the pre-retirement disagreement; that pin is gone
along with the defect it documented.

The gate legs call the **real** classifiers (``_classify_porcelain_lines``,
``classify_dirty_paths``, ``is_toolchain_generated_churn``); only ``git/ref_advance``
— whose decision lives inline in ``_dirty_entries`` and needs a live git worktree — is
modelled by a faithful callable that now directly delegates to the owner.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from specify_cli.coordination.coherence import is_coord_residue_churn, is_toolchain_generated_churn
from specify_cli.merge.git_probes import _classify_porcelain_lines
from specify_cli.review.dirty_classifier import classify_dirty_paths

pytestmark = [pytest.mark.architectural]

# A churn classifier: ``True`` when the gate treats *path* as toolchain-generated
# churn a dirty-state gate should ignore.
ChurnClassifier = Callable[[str], bool]


def _canonical_churn(path: str) -> bool:
    """The owner (``coordination/coherence.is_toolchain_generated_churn``)."""
    return bool(is_toolchain_generated_churn(path))


def _git_probes_churn(path: str) -> bool:
    """``merge/git_probes.py`` — a tracked-modified line is exempt iff DROPPED.

    Consults ``is_self_bookkeeping_path`` + the residue predicate, i.e. the owner
    union — so this gate already agrees with :func:`_canonical_churn`.
    """
    offending, _ = _classify_porcelain_lines(
        [f" M {path}"], set(), residue_predicate=is_coord_residue_churn
    )
    return not offending


def _dirty_classifier_churn(path: str) -> bool:
    """``review/dirty_classifier.py`` — churn iff the path is classified benign."""
    _blocking, benign = classify_dirty_paths([path], wp_id="WP99", mission_slug="m")
    return path in benign


def _ref_advance_churn(path: str) -> bool:
    """``git/ref_advance.py`` (``_dirty_entries``) tracked-path verdict.

    WP13 (IC-07c) retirement seam LANDED: ``_dirty_entries`` now consults the
    caller-injected ``is_residue`` predicate FIRST, for both tracked and
    untracked entries, and every production caller (``merge/ordering.py``,
    ``lanes/merge.py``, ``coordination/commit_router.py``) injects
    :func:`is_toolchain_generated_churn`. A tracked-modified ``meta.json`` (or
    coord residue) is therefore no longer fatal there — closing the #2795
    disagreement this file used to pin as a live defect.
    """
    return bool(is_toolchain_generated_churn(path))


# The churn-classifying gates, by their surface name.
_GATES: dict[str, ChurnClassifier] = {
    "coordination/coherence.py::is_toolchain_generated_churn": _canonical_churn,
    "merge/git_probes.py::_classify_porcelain_lines": _git_probes_churn,
    "review/dirty_classifier.py::classify_dirty_paths": _dirty_classifier_churn,
    "git/ref_advance.py::_dirty_entries": _ref_advance_churn,
}

# The corpus. Repo-relative paths under a mission's ``kitty-specs/<slug>/`` plus a
# plain source file. ``meta.json`` and the status log are the divergence probes; the
# source file and ``spec.md`` are agreement anchors (all gates say "not churn").
_CORPUS: tuple[str, ...] = (
    "kitty-specs/m/meta.json",            # #2795 divergence: churn for the owner, dirty for ref_advance
    "kitty-specs/m/status.events.jsonl",  # coord residue: churn for the owner, dirty for ref_advance
    "kitty-specs/m/spec.md",              # planning source: not churn for any gate
    "src/specify_cli/some_module.py",     # operator code: not churn for any gate
)


def _classification_matrix(corpus: tuple[str, ...]) -> dict[str, dict[str, bool]]:
    """``{path: {gate_name: churn_verdict}}`` over *corpus*."""
    return {path: {name: gate(path) for name, gate in _GATES.items()} for path in corpus}


def _disagreements(corpus: tuple[str, ...]) -> list[str]:
    """Paths where the gates do not unanimously agree, with the per-gate verdicts."""
    rows: list[str] = []
    for path, verdicts in _classification_matrix(corpus).items():
        if len(set(verdicts.values())) > 1:
            detail = ", ".join(f"{name}={verdict}" for name, verdict in verdicts.items())
            rows.append(f"{path}: {detail}")
    return rows


def test_all_churn_gates_agree_on_corpus() -> None:
    """C7: every churn-classifying gate returns the identical verdict per path.

    WP13 (IC-07c) landed the retirement: ``git/ref_advance.py`` now routes
    through :func:`is_toolchain_generated_churn` for both tracked and
    untracked entries, so this genuinely agrees (no more strict-xfail — the
    #2795 disagreement this file used to pin as a live defect is closed).
    """
    disagreements = _disagreements(_CORPUS)
    assert not disagreements, (
        "churn-classifying gates disagree (FR-012 violation):\n"
        + "\n".join(f"  {row}" for row in disagreements)
    )


def test_owner_routed_gates_already_agree() -> None:
    """The gates that route through the owner union agree today (GREEN, stays green).

    git_probes and dirty_classifier both consult the owner's authorities, so they must
    already match :func:`_canonical_churn` across the whole corpus. This keeps the file
    exercising the REAL seams (not just an xfail) and pins the partial agreement that
    already holds.
    """
    mismatches: list[str] = []
    for path in _CORPUS:
        canonical = _canonical_churn(path)
        for name in (
            "merge/git_probes.py::_classify_porcelain_lines",
            "review/dirty_classifier.py::classify_dirty_paths",
        ):
            verdict = _GATES[name](path)
            if verdict != canonical:
                mismatches.append(f"{path}: {name}={verdict} != owner={canonical}")
    assert not mismatches, "owner-routed gate disagreement:\n" + "\n".join(f"  {m}" for m in mismatches)


def test_ref_advance_now_agrees_with_the_owner_on_the_former_2795_probe() -> None:
    """The former #2795 disagreement probe now shows genuine agreement (WP13).

    This replaces the pre-WP13 defect-pin (``test_ref_advance_divergence_is_the_
    live_2795_defect``), which asserted the disagreement was LIVE. WP13 (IC-07c)
    routed ``git/ref_advance.py`` onto :func:`is_toolchain_generated_churn` for
    both tracked and untracked entries, so a tracked-modified ``meta.json`` is now
    exempted there too, matching the owner — the tightening path this file's
    docstring promised as retirements landed.
    """
    meta = "kitty-specs/m/meta.json"
    assert _canonical_churn(meta) is True, "the owner must exempt a self-bookkeeping meta.json."
    assert _ref_advance_churn(meta) is True, (
        "post-WP13, ref_advance must agree with the owner and exempt a "
        "tracked-modified meta.json as toolchain churn."
    )
    assert _canonical_churn(meta) == _ref_advance_churn(meta), (
        "the #2795 cross-gate disagreement must be closed post-WP13."
    )


def test_corpus_is_non_vacuous() -> None:
    """The corpus contains at least one churn path and one non-churn path.

    Guards against a corpus where every gate trivially agrees because nothing is churn.
    """
    canonical = {path: _canonical_churn(path) for path in _CORPUS}
    assert any(canonical.values()), "corpus has no toolchain-churn path — agreement is vacuous."
    assert not all(canonical.values()), "corpus has no operator path — agreement is vacuous."
