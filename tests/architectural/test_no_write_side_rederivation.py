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

coord-primary-partition-lock WP07 (T033 / FR-011) extends this ratchet with a
SECOND, AST-based grammar (below the original three token grammars): it flags
``CommitTarget(...)`` / ``safe_commit(...)`` calls whose ``ref`` /
``destination_ref`` argument is constructed from a current-checkout expression
rather than a ``placement_seam(...).write_target(kind)`` call (contracts/
ratchet-contract.md). This is genuinely AST-based (not token-based): the
forbidden pattern is a *call construction*, so parsing the tree means a
docstring merely quoting ``CommitTarget(ref=coordination_branch)`` never
becomes a ``Call`` node and is never flagged, without needing tokenize's
comment/string-skipping machinery.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

from tests.architectural._ratchet_keys import code_tokens_by_line, composite_key

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src" / "specify_cli"

#: The write-side modules the adoption touched (US-1..US-4, FR-001/FR-002/
#: FR-003/FR-004/FR-008). These are the surfaces the boundary contract binds.
#:
#: coord-primary-partition-lock WP07 (T034, FR-011): expanded with the five
#: mission-artifact-placement write surfaces WP02-WP05 routed through
#: ``placement_seam(...).write_target(kind)`` -- each module is added to this
#: set in the SAME WP that routes it (contract sequencing rule), and by the
#: time WP07 lands all five are already routed.
_ADOPTED_MODULES: tuple[Path, ...] = (
    _SRC / "status" / "emit.py",
    _SRC / "status" / "work_package_lifecycle.py",
    _SRC / "status" / "lifecycle_events.py",
    _SRC / "status" / "store.py",
    _SRC / "coordination" / "status_transition.py",
    _SRC / "core" / "worktree.py",
    _SRC / "core" / "mission_creation.py",
    _SRC / "cli" / "commands" / "implement.py",
    _SRC / "cli" / "commands" / "agent" / "workflow.py",
    _SRC / "cli" / "commands" / "agent" / "tasks_move_task.py",
    _SRC / "cli" / "commands" / "agent" / "mission_record_analysis.py",
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
#:
#: coord-primary-partition-lock WP07 (T034, FR-011): contracts/ratchet-contract.md
#: projected this seed re-anchoring 343 -> 347 via a "#1842 tombstone hook" that,
#: as of this WP landing in this lane, has NOT touched
#: ``status_transition.py`` (the live line is still 343 -- verified by re-scan,
#: not assumed). The composite ``(qualname, token_line)`` key is the authoritative
#: comparand regardless (NFR-004); the seed below points at the line that is
#: ACTUALLY live today, honestly, rather than a projected number that would
#: silently resolve to the wrong code line via ``_composite_key_for_seed``.
#:
#: A SECOND entry is added here (``workflow.py``): expanding ``_ADOPTED_MODULES``
#: (T034) pulled in two pre-existing ``feature_dir.parent.parent`` occurrences in
#: ``_latest_review_feedback_reference`` / ``_resolve_review_feedback_context``
#: (workflow.py:843/885 pre-WP07). These are READ-side review-feedback-pointer
#: root navigation -- NOT an FR-005 write-target/identity re-derivation (they
#: never touch mission_id/mid8/primary_root or a write CommitTarget). WP07
#: deduplicated both call sites into one ``_review_feedback_root`` helper
#: (workflow.py) so the ratchet has exactly ONE new line to allow-list instead of
#: two duplicate ones. The write-side allow-list therefore grows 1 -> 2 here,
#: honestly reported: the ratchet-contract.md "seed stays at floor=1" baseline
#: did not anticipate this pre-existing, orthogonal READ-path helper being pulled
#: into scope by the T034 module-set expansion.
_ALLOW_LIST_SEED: tuple[tuple[str, int], ...] = (
    # write-surface-coherence WP02 / T031: threading the required STATUS_STATE kind
    # into ``_resolve_write_target`` shifted the deferred HEAD-selector fallback arm
    # from :336 to :343 (the ``coord_branch or _current_branch`` line). The seed is
    # re-anchored to the live line so the composite key still resolves it.
    # post-merge re-anchor (coord-primary-partition-lock aggregate landing):
    # cumulative cross-lane line drift on local main shifted the fallback arm
    # 343 -> 347 (same deferred selector, verified by re-scan, not a new offender).
    ("src/specify_cli/coordination/status_transition.py", 347),
    # coord-primary-partition-lock WP07 (T034): the sole, deduplicated
    # ``feature_dir.parent.parent`` READ-side review-feedback-root navigation
    # (see docstring above) -- categorically distinct from the deferred #1716
    # write-target selector above.
    # post-merge re-anchor (coord-primary-partition-lock aggregate landing):
    # cumulative cross-lane line drift shifted this 833 -> 838 (same helper,
    # verified by re-scan).
    # post-merge re-anchor (read-surface-ssot-closeout aggregate landing): WP04's
    # workflow.py campsite extractions (_render_isolation_banner /
    # _render_wp_prompt_wrapper + routing) shifted _review_feedback_root's
    # ``return feature_dir.parent.parent`` 838 -> 872 (same READ-side helper,
    # verified by re-scan, not a new offender).
    ("src/specify_cli/cli/commands/agent/workflow.py", 872),
    # tracked: #2453 - _status_commit_destination_branch's
    # ``get_current_branch(repo_root) or fallback_branch`` git-HEAD selector.
    # It ONLY predicts the pre-lane status-commit branch for the protected-branch
    # guard (_protected_branch_status_commit_error) -- it never feeds a write
    # CommitTarget/destination_ref. Newly pulled into the ratchet's field of view
    # by the checkout_head_selector grammar (above) so this last checkout-derived
    # selector in an adopted module cannot silently drift; routing the prediction
    # through the placement seam would change which branch the guard evaluates
    # (a behavior change), so it is deferred to the #2453 read-site sweep bucket
    # (D-1/C-003) rather than routed here.
    # post-merge re-anchor (read-surface-ssot-closeout aggregate landing): the
    # read-surface routing that merged into this test file dropped this seed entry
    # and its staleness twin-guard while keeping the checkout_head_selector grammar
    # + implement.py in _ADOPTED_MODULES; restored here re-anchored 87 -> 88 (same
    # pre-existing selector, verified by re-scan, not a new offender).
    ("src/specify_cli/cli/commands/implement.py", 88),
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

    Four re-derivation grammars (randy's write-path census / FR-005):

    * ``feature_dir.parent.parent`` (and deeper) root walks — tokenizes to
      ``. parent . parent`` / ``parent . parent``.
    * inline ``mission_id[:8]`` / ``mid8`` recompute — tokenizes to
      ``mission_id [ : 8 ]``.
    * ``coord_branch or _current_branch`` / ``coord_branch or current_branch``
      git-HEAD write-target selectors.
    * ``get_current_branch(...) or <fallback>`` git-HEAD branch selectors — the
      generic checkout-derived ``current-branch-or-fallback`` shape (e.g.
      ``implement.py``'s ``_status_commit_destination_branch``, which predicts
      the pre-lane status-commit branch for the protected-branch guard). Making
      this shape a first-class finding pulls the last checkout-derived selector
      an adopted module carries into the ratchet's field of view so it cannot
      silently drift; the one live site is tracked-VISIBLE in ``_ALLOW_LIST_SEED``
      (tracked: #2453 deferred read-site sweep, D-1/C-003).
    """
    findings: list[_Finding] = []
    for lineno, code in code_tokens_by_line(source).items():
        if "parent . parent" in code:
            findings.append(_Finding(path, lineno, "root_walk", code, source))
        if "mission_id [ : 8 ]" in code:
            findings.append(_Finding(path, lineno, "mid8_recompute", code, source))
        if "coord_branch or _current_branch" in code or "coord_branch or current_branch" in code:
            findings.append(_Finding(path, lineno, "write_target_head_selector", code, source))
        if "get_current_branch (" in code and ") or" in code:
            findings.append(_Finding(path, lineno, "checkout_head_selector", code, source))
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
        ("    branch = get_current_branch(repo_root) or fallback_branch\n", "checkout_head_selector"),
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


def test_checkout_head_selector_entry_is_still_a_live_finding() -> None:
    """Staleness twin-guard for the tracked #2453 checkout-HEAD selector seed.

    The ``implement.py`` seed pins ``_status_commit_destination_branch``'s
    ``get_current_branch(repo_root) or fallback_branch`` prediction selector. If
    that site is finally routed through the placement seam (or removed) the
    ``checkout_head_selector`` grammar stops flagging it and this test fails
    loudly — the fix is to DELETE the now-stale seed entry (shrink-only), never
    to leave a vacuous allow-list rule masking nothing.
    """
    rel_path = "src/specify_cli/cli/commands/implement.py"
    module = _REPO_ROOT / rel_path
    live = {
        f.lineno for f in _scan_module(module) if f.kind == "checkout_head_selector"
    }
    seed_linenos = {
        lineno for path, lineno in _ALLOW_LIST_SEED if path == rel_path
    }
    assert seed_linenos and seed_linenos <= live, (
        f"{rel_path} checkout_head_selector seed {seed_linenos} no longer matches "
        f"a live finding {live} — the site was routed through the seam (or "
        "removed); DELETE the now-stale allow-list entry (shrink-only)."
    )
    # The pinned line really IS the get_current_branch HEAD selector.
    (lineno,) = tuple(seed_linenos)
    _qualname, token_line = _composite_key_for_seed(rel_path, lineno)
    assert "get_current_branch (" in token_line, (
        f"allow-listed {rel_path}:{lineno} no longer holds the get_current_branch "
        f"HEAD selector (got token_line {token_line!r})."
    )


# ===========================================================================
# T033 (WP07 / FR-011) — the CommitTarget(ref=<checkout>) construction grammar.
# ===========================================================================
#
# contracts/ratchet-contract.md's "New grammar" section: the three token
# grammars above do not catch the ACTUAL bypass shape —
# ``CommitTarget(ref=<current-checkout expression>)`` — because the checkout
# read and the CommitTarget construction are usually two different lines. This
# section adds a fourth, AST-based grammar scoped to the write-site file set
# (the T034-expanded ``_ADOPTED_MODULES`` plus the residual/sanctioned files
# the squad's H-1/H-4/L-2 audit named): every ``CommitTarget(ref=...)`` /
# ``safe_commit(..., destination_ref=...)`` construction in that scope must be
# provably seam-derived (or allow-listed with a tracked rationale).

#: Callees whose result -- or a local variable assigned from a call to them --
#: is provably seam-derived, not a checkout read (mirrors the canonicalizer
#: discriminator's ``CANONICAL_FOLD_SEAM`` shape, SC-004 precedent). Each is a
#: documented thin wrapper over ``placement_seam(...).write_target(kind)``:
#: ``write_target`` itself (the seam method, e.g.
#: ``placement_seam(...).write_target(kind)``), ``_resolve_workflow_placement``
#: (workflow.py T017), ``_resolve_claim_commit_target`` (implement.py, wraps the
#: context's seam-resolved ``artifact_placement.placement_ref``), and
#: ``_require_record_analysis_placement`` (mission_record_analysis.py, same
#: pattern).
_SEAM_FOLD_CALLEES: frozenset[str] = frozenset(
    {
        "write_target",
        "_resolve_workflow_placement",
        "_resolve_claim_commit_target",
        "_require_record_analysis_placement",
    }
)

#: T033 scan scope: every module WP02–WP05 routed (``_ADOPTED_MODULES``, T034)
#: plus the residual/sanctioned files named by contracts/ratchet-contract.md
#: that are NOT themselves mission-artifact write surfaces adopted elsewhere.
_EXTRA_CHECKOUT_GRAMMAR_MODULES: tuple[Path, ...] = (
    _SRC / "orchestrator_api" / "commands.py",
    _SRC / "coordination" / "transaction.py",
    _SRC / "retrospective" / "writer.py",
)
_CHECKOUT_GRAMMAR_MODULES: tuple[Path, ...] = _ADOPTED_MODULES + _EXTRA_CHECKOUT_GRAMMAR_MODULES

#: Detection-boundary invariant (contract: "Guard the detection boundary"):
#: the sanctioned coord primitives / legacy-migration modules the contract
#: names are NEVER added to the scanned scope above -- they ARE the sanctioned
#: grammar (branch composition, worktree resolution, seam internals, migration
#: bookkeeping), not a write site awaiting a seam route. Guarded by
#: ``test_checkout_grammar_boundary_excludes_sanctioned_modules`` below so a
#: future edit accidentally widening the scope into one of these fails loudly
#: instead of silently needing a mass allow-list.
_BOUNDARY_SANCTIONED_MODULES: frozenset[str] = frozenset(
    {
        "src/specify_cli/lanes/branch_naming.py",
        "src/specify_cli/coordination/workspace.py",
        "src/specify_cli/upgrade/autocommit.py",
        "src/specify_cli/invocation/executor.py",
    }
)
_BOUNDARY_SANCTIONED_PREFIXES: tuple[str, ...] = (
    "src/mission_runtime/",
    "src/specify_cli/upgrade/migrations/",
    "src/specify_cli/migration/",
)


@dataclass(frozen=True)
class _CheckoutGrammarFinding:
    """One flagged ``CommitTarget(ref=...)`` / ``safe_commit(destination_ref=...)`` call."""

    path: Path
    lineno: int
    callee: str
    source: str

    def as_allow_key(self) -> tuple[str, str]:
        """The drift-proof ``(qualname, token_line)`` composite allow-list key."""
        return composite_key(self.source, self.lineno)


def _checkout_grammar_callee_name(call: ast.Call) -> str | None:
    """Return the callee identifier for bare-name OR attribute call forms."""
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _checkout_grammar_parent_map(tree: ast.Module) -> dict[int, ast.AST]:
    """Map ``id(child) -> parent`` for every node in *tree* (single pass)."""
    parents: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node
    return parents


def _checkout_grammar_enclosing_function(
    parents: dict[int, ast.AST], target: ast.AST
) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    """Return the DIRECT enclosing ``ast.FunctionDef`` of *target*, or ``None``."""
    cur: ast.AST | None = target
    while cur is not None:
        cur = parents.get(id(cur))
        if isinstance(cur, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return cur
    return None


def _names_assigned_from_seam(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Local names assigned from a call to a ``_SEAM_FOLD_CALLEES`` member.

    Intra-function only (FR-004 def-use discipline): a name assigned from the
    seam in a CALLER's scope never seam-derives a callee's bare parameter.
    """
    out: set[str] = set()
    for node in ast.walk(fn):
        value: ast.expr | None = None
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            value, targets = node.value, list(node.targets)
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            value, targets = node.value, [node.target]
        if isinstance(value, ast.Call) and _checkout_grammar_callee_name(value) in _SEAM_FOLD_CALLEES:
            for tgt in targets:
                if isinstance(tgt, ast.Name):
                    out.add(tgt.id)
    return out


def _is_seam_derived(
    arg: ast.expr | None,
    enclosing_fn: ast.FunctionDef | ast.AsyncFunctionDef | None,
) -> bool:
    """True when *arg* is provably sourced from the seam, not a checkout read.

    SAFE iff *arg* is (a) a plain string literal (a hardcoded ref, never
    checkout state -- e.g. a ``CommitTarget(ref="")`` default-factory
    placeholder), (b) a direct call to a ``_SEAM_FOLD_CALLEES`` member, or
    (c) a local name assigned from one of those callees earlier in the SAME
    function. Everything else -- a bare parameter, an attribute read
    (``self.x`` / ``st.x``), a subprocess call, an ``or``-fallback expression
    -- is presumptively checkout-derived and must be routed or allow-listed.
    """
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return True
    if isinstance(arg, ast.Call) and _checkout_grammar_callee_name(arg) in _SEAM_FOLD_CALLEES:
        return True
    if isinstance(arg, ast.Name) and enclosing_fn is not None:
        return arg.id in _names_assigned_from_seam(enclosing_fn)
    return False


def _commit_target_ref_arg(call: ast.Call) -> ast.expr | None:
    """The ``ref`` argument of a ``CommitTarget(...)`` call (positional or kw)."""
    if call.args:
        return call.args[0]
    for kw in call.keywords:
        if kw.arg == "ref":
            return kw.value
    return None


def _safe_commit_destination_ref_arg(call: ast.Call) -> ast.expr | None:
    """The ``destination_ref`` kwarg of a ``safe_commit(...)`` call, if used directly.

    ``safe_commit`` also accepts a ``target=CommitTarget(...)`` form; that
    construction is caught independently as its own ``CommitTarget(...)`` node
    during the same tree walk, so this helper returns ``None`` (skip) when no
    ``destination_ref=`` kwarg is present.
    """
    for kw in call.keywords:
        if kw.arg == "destination_ref":
            return kw.value
    return None


def _scan_checkout_grammar(source: str, path: Path) -> list[_CheckoutGrammarFinding]:
    """Flag non-seam-derived ``CommitTarget``/``safe_commit`` ref constructions.

    AST-based (unlike ``_scan_source`` above, which is token-based): the
    forbidden grammar is a call CONSTRUCTION, not a textual pattern, so parsing
    means a docstring merely quoting the pattern is inert prose (a ``Constant``
    string, never a ``Call`` node) and is never flagged.
    """
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    parents = _checkout_grammar_parent_map(tree)
    findings: list[_CheckoutGrammarFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        callee = _checkout_grammar_callee_name(node)
        if callee == "CommitTarget":
            arg = _commit_target_ref_arg(node)
        elif callee == "safe_commit":
            arg = _safe_commit_destination_ref_arg(node)
            if arg is None:
                continue
        else:
            continue
        fn = _checkout_grammar_enclosing_function(parents, node)
        if _is_seam_derived(arg, fn):
            continue
        findings.append(_CheckoutGrammarFinding(path, node.lineno, callee, source))
    return findings


def _scan_checkout_grammar_module(path: Path) -> list[_CheckoutGrammarFinding]:
    return _scan_checkout_grammar(path.read_text(encoding="utf-8"), path)


#: Tracked-VISIBLE allow-list (squad H-1/H-4/L-2, contracts/ratchet-contract.md):
#: every entry names a REAL, still-checkout-derived construction, each with an
#: explicit rationale -- flagged VISIBLE, never silently ignored. ``tracked:
#: #2453`` entries share the deferred read-site sweep bucket (D-1/C-003); the
#: ``PERMANENT`` entry documents a construction that will never route through
#: the MissionArtifactKind placement seam because it is not a placement
#: decision at all.
_CHECKOUT_GRAMMAR_ALLOW_LIST_SEED: tuple[tuple[str, int, str], ...] = (
    # NOTE: the former src/specify_cli/orchestrator_api/commands.py:1452 entry
    # (_resolve_history_commit_args' unresolvable-mission fallback) was
    # DELETED (shrink-only ratchet) after read-surface-ssot-closeout FR-004:
    # the ActionContextError catch now raises PlacementResolutionRequired
    # (fail-closed) instead of constructing a CommitTarget(ref=current_branch)
    # via 'git branch --show-current' -- there is no longer a checkout-grammar
    # construction at that site.
    (
        "src/specify_cli/coordination/transaction.py",
        1070,
        "tracked: #2453 - BookkeepingTransaction.commit()'s legacy-mission "
        "override (_resolve_legacy_lane_destination reads the lane worktree's "
        "HEAD) constructs CommitTarget(ref=self.destination_ref) for "
        "pre-coordination-topology missions; deferred to the #2453 sweep.",
    ),
    (
        "src/specify_cli/cli/commands/agent/tasks_map_requirements.py",
        177,
        "tracked: #2453 - st.target_branch is the "
        "_ensure_target_branch_checked_out current-checkout branch, not the "
        "seam-resolved placement; deferred to the #2453 sweep (this call "
        "predates the STATUS_STATE routing WP05 added elsewhere in this "
        "module).",
    ),
    (
        "src/specify_cli/cli/commands/agent/workflow.py",
        557,
        "tracked: #2453 - _commit_via_legacy_safe_commit's target_branch "
        "parameter is a pre-coordination-topology legacy mission's "
        "checked-out branch; same deferred bucket as the other #2453 "
        "residuals. post-merge re-anchor (coord-primary-partition-lock "
        "aggregate landing): cumulative cross-lane line drift shifted this "
        "524 -> 523 (same construction, verified by re-scan).",
    ),
    (
        "src/specify_cli/cli/commands/agent/tasks_move_task.py",
        454,
        "PERMANENT: _mt_commit_lane_deliverables commits arbitrary "
        "implementer deliverables onto the LANE's own branch "
        "(workspace.branch_name) -- not a MissionArtifactKind placement "
        "decision; the lane branch is fixed by lane allocation, never "
        "resolved via the placement seam. Out of IC-04 scope.",
    ),
)


def _checkout_grammar_composite_key_for_seed(rel_path: str, lineno: int) -> tuple[str, str]:
    """Derive the composite key for a checkout-grammar seed entry from live source."""
    source = (_REPO_ROOT / rel_path).read_text(encoding="utf-8")
    return composite_key(source, lineno)


_CHECKOUT_GRAMMAR_ALLOW_LIST: frozenset[tuple[str, str]] = frozenset(
    _checkout_grammar_composite_key_for_seed(rel_path, lineno)
    for rel_path, lineno, _rationale in _CHECKOUT_GRAMMAR_ALLOW_LIST_SEED
)


def test_checkout_grammar_boundary_excludes_sanctioned_modules() -> None:
    """Guard the detection boundary (contract): sanctioned primitives are never scanned.

    The scan scope is a fixed, explicit file list (the write-site census, not
    the whole ``src/`` tree). This asserts none of the sanctioned coord
    primitives / legacy-migration modules the contract names ever sneak into
    that scope -- if one did, the composite-key allow-list would be the WRONG
    tool for it (these ARE the sanctioned grammar, not a residual).
    """
    scanned_rel = {p.relative_to(_REPO_ROOT).as_posix() for p in _CHECKOUT_GRAMMAR_MODULES}
    for sanctioned in _BOUNDARY_SANCTIONED_MODULES:
        assert sanctioned not in scanned_rel, (
            f"{sanctioned} is a sanctioned coord primitive and must never enter "
            "the checkout-grammar scan scope"
        )
    for rel in scanned_rel:
        assert not rel.startswith(_BOUNDARY_SANCTIONED_PREFIXES), (
            f"{rel} falls under a sanctioned-primitive prefix "
            f"({_BOUNDARY_SANCTIONED_PREFIXES}) and must never enter the "
            "checkout-grammar scan scope"
        )


def test_adopted_and_residual_modules_have_no_checkout_derived_commit_target() -> None:
    """T033 / FR-011: the write-site census carries zero un-allow-listed offenders.

    A flag on a scanned module that is NOT on ``_CHECKOUT_GRAMMAR_ALLOW_LIST``
    means a real ``CommitTarget(ref=<checkout>)`` (or ``safe_commit(...,
    destination_ref=<checkout>)``) bypass — the exact split-brain root the
    placement seam exists to close (research.md D5 / plan D11).
    """
    offenders: list[str] = []
    for module in _CHECKOUT_GRAMMAR_MODULES:
        assert module.exists(), f"checkout-grammar module missing: {module}"
        for finding in _scan_checkout_grammar_module(module):
            if finding.as_allow_key() in _CHECKOUT_GRAMMAR_ALLOW_LIST:
                continue
            offenders.append(
                f"{finding.path.relative_to(_REPO_ROOT)}:{finding.lineno} "
                f"{finding.callee}(...) constructs a ref from a non-seam-derived "
                "expression — route it through placement_seam(...).write_target(kind) "
                "or allow-list it with a tracked rationale"
            )

    assert not offenders, (
        "Checkout-derived CommitTarget/safe_commit construction found (T033 / "
        "FR-011). Route through the placement seam or add a tracked, "
        "rationale-carrying allow-list entry. Offenders:\n" + "\n".join(offenders)
    )


def test_checkout_grammar_allow_list_entries_are_still_live() -> None:
    """Staleness twin-guard: every seeded entry still matches a REAL live finding.

    If a residual site is finally routed through the seam,
    ``_scan_checkout_grammar`` stops flagging it and this test fails loudly —
    the fix is to DELETE the now-stale seed entry (shrink-only governance),
    never to leave a vacuous allow-list rule masking nothing.
    """
    for rel_path, lineno, _rationale in _CHECKOUT_GRAMMAR_ALLOW_LIST_SEED:
        module = _REPO_ROOT / rel_path
        live_linenos = {f.lineno for f in _scan_checkout_grammar_module(module)}
        assert lineno in live_linenos, (
            f"{rel_path}:{lineno} no longer produces a checkout-grammar finding "
            "— the site was routed through the seam (or removed); DELETE this "
            "now-stale allow-list entry (shrink-only, never leave a vacuous rule)."
        )


def test_retrospective_writer_is_checkout_grammar_clean() -> None:
    """``retrospective/writer.py`` (the sanctioned #2119 RETROSPECTIVE authority)
    produces ZERO checkout-grammar findings, needing NO allow-list entry.

    It never constructs a ``CommitTarget`` at all (it resolves the RETROSPECTIVE
    HOME directory via ``resolve_retrospective_home``; the actual commit happens
    downstream in ``git/bookkeeping_commit.py``, out of this WP's scan scope).
    Pins this so a future change adding a construction here is caught by the
    main ratchet above rather than silently needing this file re-audited.
    """
    assert _scan_checkout_grammar_module(_SRC / "retrospective" / "writer.py") == []


# ---------------------------------------------------------------------------
# "The grammar bites" — self-tests (T036): a planted bypass goes RED.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("planted", "expected_callee"),
    [
        ("    return CommitTarget(ref=current_branch)\n", "CommitTarget"),
        (
            "    return safe_commit(repo_root=r, worktree_root=w, "
            "destination_ref=current_branch, message=m, paths=p)\n",
            "safe_commit",
        ),
    ],
)
def test_checkout_grammar_bites_on_planted_bypass(planted: str, expected_callee: str) -> None:
    """T036: re-introducing a ``CommitTarget(ref=<checkout>)`` bypass goes RED.

    Proves the new grammar is not inert by planting the EXACT forbidden
    construction contracts/ratchet-contract.md names
    (``CommitTarget(ref=current_branch)``) — plus the ``safe_commit(...,
    destination_ref=...)`` sibling form — into a fixture source and asserting
    the detector flags it.
    """
    fixture_source = (
        "def _adopted_write_site(current_branch, r, w, m, p):\n"
        f"{planted}"
    )
    findings = _scan_checkout_grammar(fixture_source, _SRC / "core" / "mission_creation.py")
    kinds = {f.callee for f in findings}
    assert expected_callee in kinds, (
        f"checkout-grammar failed to flag a planted {expected_callee}(...) bypass; "
        f"got {kinds}"
    )


def test_checkout_grammar_does_not_flag_seam_derived_construction() -> None:
    """Anti-false-positive: a ``write_target(...)``-derived ref is NOT flagged."""
    fixture_source = (
        "def _adopted_write_site(repo_root, mission_slug):\n"
        "    seam_target = placement_seam(repo_root, mission_slug).write_target(KIND)\n"
        "    return safe_commit(target=seam_target)\n"
    )
    assert (
        _scan_checkout_grammar(fixture_source, _SRC / "core" / "mission_creation.py") == []
    )


def test_checkout_grammar_does_not_flag_string_literal_placeholder() -> None:
    """Anti-false-positive: a hardcoded string literal ref is NEVER checkout state.

    Pins ``tasks_map_requirements.py``'s ``CommitTarget(ref="")``
    default-factory placeholder pattern.
    """
    fixture_source = (
        "def _factory():\n"
        '    return CommitTarget(ref="")\n'
    )
    assert (
        _scan_checkout_grammar(fixture_source, _SRC / "core" / "mission_creation.py") == []
    )


def test_checkout_grammar_ignores_prose_quoting_the_pattern() -> None:
    """A docstring that merely QUOTES the forbidden pattern is NOT flagged.

    Unlike the token-based scanner above, this is inherent to AST parsing (the
    string never becomes a ``Call`` node) — this test pins that guarantee for
    the new grammar specifically.
    """
    fixture_source = (
        "def _adopted_resolver(repo_root, mission_slug):\n"
        '    """The bypass looked like CommitTarget(ref=current_branch).\n'
        '    Never do that -- route through write_target(kind) instead.\n'
        '    """\n'
        "    return placement_seam(repo_root, mission_slug).write_target(KIND)\n"
    )
    assert (
        _scan_checkout_grammar(fixture_source, _SRC / "core" / "mission_creation.py") == []
    )
