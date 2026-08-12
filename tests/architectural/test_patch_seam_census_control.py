"""Control test for ``scripts/patch_seam_census.py`` — SC-015.

The census is the sole instrument for SC-001, SC-002 and SC-013. A census that
simply *printed* the expected table would satisfy all three. This file exists to
make that impossible: it pins a **hand-derived** ground truth over a committed
fixture whose decoys a naive ``grep`` over-counts, and it narrows the analyzer at
runtime to prove the instrument can still fail (Arm E).

Seven arms:

* **A** — fixture ground truth: patch sites and corruptible assertions.
* **B** — the three decoys contribute nothing, and ``grep`` over-counts.
* **C** — the ``in``-form reports ``n=0`` (otherwise SC-002 is fakeable).
* **D** — bucket counts over ``tests/sync/``, ``unresolvable`` included.
* **E** — self-mutation: a narrowed analyzer must miss the fixture's positives.
* **F** — cross-check against the regex extractor in ``check_patch_targets.py``.
* **G** — an ``own_module`` sleep seam counts but is **not** corruptible.

Arm F's exception set is *derived* rather than transcribed (see ``_prose_lines``
below), so a docstring edit that moves lines cannot silently widen or narrow
what the arm excuses.

The census is consumed **only through its CLI, by subprocess**. That makes
SC-001's own invocation the single front door and sidesteps the double-import
hazard ``pytest.ini:2-9`` documents (``scripts`` is an implicit namespace
package, so ``check_patch_targets`` and ``scripts.check_patch_targets`` would be
two module identities with two incompatible verdict vocabularies). Hence: no
``sys.path`` insertion and no ``# noqa: E402`` anywhere in this file.

``len(x) == N`` is avoided throughout in favour of frozenset equality. That is a
stronger contract — it names the delta on failure instead of a bare cardinality —
and it keeps ``tests/architectural`` off the ``test_golden_count_ban.py``
ratchet, whose ceiling for this directory is at 25/25 with zero headroom.
"""

from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import tokenize
from pathlib import Path
from typing import Any

import pytest

pytestmark = [pytest.mark.architectural]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CENSUS = _REPO_ROOT / "scripts" / "patch_seam_census.py"
_FIXTURE_DIR = _REPO_ROOT / "tests" / "architectural" / "_fixtures" / "patch_seam_control"
_SYNC_TREE = _REPO_ROOT / "tests" / "sync"


def _prose_lines(path: Path) -> frozenset[int]:
    """Line numbers covered by a string-literal span or a comment.

    Arm F's exception set is *derived* from this, not transcribed. A hand-listed
    ``(file, line)`` set is a snapshot, not a contract: WP02's edits to the same
    docstrings move every one of those lines, and keying on the line rather than
    the target string does not immunise the pin — it only changes which edit
    breaks it.
    """
    source = path.read_text(encoding="utf-8")
    covered: set[int] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            covered.update(range(node.lineno, (node.end_lineno or node.lineno) + 1))
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT:
            covered.update(range(token.start[0], token.end[0] + 1))
    return frozenset(covered)


# --------------------------------------------------------------------------
# Hand-derived ground truth (T018). Derived by reading the fixture modules as
# they were written — NOT transcribed from spec.md, and NOT copied from census
# output. If the census and this table disagree, one of them is wrong and the
# failure message names which sites differ.
# --------------------------------------------------------------------------

# (module, line, verdict) for every AST-visible patch() site in the fixture.
_GROUND_TRUTH_SITES = frozenset(
    {
        ("seam_decorator_cases.py", 22, "reach_through"),
        ("seam_decorator_cases.py", 29, "reach_through"),
        ("seam_decorator_cases.py", 37, "reach_through"),
        ("seam_contextmanager_cases.py", 29, "reach_through"),
        ("seam_contextmanager_cases.py", 38, "reach_through"),
        ("seam_negative_cases.py", 24, "own_module"),
        ("seam_negative_cases.py", 30, "reach_through"),
        ("seam_negative_cases.py", 37, "reach_through"),
        ("seam_decoy_cases.py", 36, "reach_through"),
    }
)

# (module, line, n) for every corruptible assertion — an assertion that READS a
# patched sleep seam. `n` comes from the assertion's own cardinality
# expression, never from the length of a printed delay list.
_GROUND_TRUTH_CORRUPTIBLE = frozenset(
    {
        ("seam_decorator_cases.py", 26, 1),  # assert_called_once_with
        ("seam_decorator_cases.py", 34, 2),  # .call_count comparison
        ("seam_decorator_cases.py", 47, 3),  # len(alias) == 3
        ("seam_decorator_cases.py", 49, 3),  # whole-list equality via alias
        # NB: neither trailing comment may end with the bare word "patch" —
        # check_patch_targets.py's regex bridges the newline with `\s*` and
        # would read `patch` + the next line's `("seam_..._cases.py"` as a
        # phantom patch target, reddening an [ENFORCED] CI job.
        ("seam_contextmanager_cases.py", 32, 4),  # context-manager form
        ("seam_contextmanager_cases.py", 41, 2),  # side_effect= sink
        ("seam_negative_cases.py", 41, 0),  # `in` form — no cardinality
        ("seam_decoy_cases.py", 43, 1),  # live seam among the decoys
    }
)

# Functions that patch a sleep seam. `case_monotonic_only` is deliberately
# absent: it patches a reach-through seam that is not a *sleep* seam.
_GROUND_TRUTH_SLEEP_NODES = frozenset(
    {
        ("seam_decorator_cases.py", "case_assert_called_once"),
        ("seam_decorator_cases.py", "case_call_count_comparison"),
        ("seam_decorator_cases.py", "case_alias_whole_list_equality"),
        ("seam_contextmanager_cases.py", "case_context_manager_call_count"),
        ("seam_contextmanager_cases.py", "case_side_effect_sink_whole_list"),
        ("seam_negative_cases.py", "case_membership_without_cardinality"),
        ("seam_decoy_cases.py", "case_live_seam_among_decoys"),
    }
)

# Arm D: bucket counts over `tests/sync/`, pinned to the tree's live measurement.
# The current-main project-store reconciliation removes eight stale patch seams
# (including the retired global body/row migration helpers) and reclassifies two
# remaining non-import targets. The census instrument is unchanged; these are
# the hand-reviewed buckets for the reconciled test tree.
#
# `unresolvable` is pinned too (at 0), deliberately: classification runs through
# import success, so a thinner environment that could not import a module under
# test would shrink the flagged set for free, and the gate would pass by getting
# weaker rather than by anything actually improving.
_EXPECTED_BUCKETS = frozenset(
    {
        ("own_module", 341),
        ("reach_through", 191),
        ("foreign", 6),
        ("not_a_module", 17),
        ("unresolvable", 0),
    }
)


def _census(*args: str) -> dict[str, Any]:
    """Run the census CLI and return its parsed ``--json`` payload.

    ``PYTHONPATH`` is pinned to this checkout's ``src`` so the census resolves
    ``specify_cli.*`` against *this* tree. The venv carries an editable-install
    path file pointing at the repository-root checkout, so an unpinned run would
    silently classify against a different working tree.
    """
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_REPO_ROOT / "src")
    proc = subprocess.run(
        [sys.executable, str(_CENSUS), *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    assert proc.returncode == 0, f"census exited {proc.returncode} for args {args!r}\n--- stdout ---\n{proc.stdout}\n--- stderr ---\n{proc.stderr}"
    parsed: dict[str, Any] = json.loads(proc.stdout)
    return parsed


def _seam_sleep_sites(payload: dict[str, Any]) -> frozenset[tuple[int, str, str]]:
    return frozenset((int(s["line"]), str(s["attr"]), str(s["verdict"])) for s in payload["sleep_seam_patch_sites"])


def _assertion_lines(payload: dict[str, Any], key: str) -> frozenset[tuple[int, int]]:
    return frozenset((int(a["line"]), int(a["n"])) for a in payload[key])


def _sites(payload: dict[str, Any]) -> frozenset[tuple[str, int, str]]:
    return frozenset((Path(s["file"]).name, int(s["line"]), str(s["verdict"])) for s in payload["sites"])


def _corruptible(payload: dict[str, Any]) -> frozenset[tuple[str, int, int]]:
    return frozenset((Path(a["file"]).name, int(a["line"]), int(a["n"])) for a in payload["corruptible_assertions"])


# --------------------------------------------------------------------------
# Arm A — fixture ground truth
# --------------------------------------------------------------------------


def test_arm_a_fixture_patch_sites_match_hand_derived_ground_truth() -> None:
    """Every AST-visible patch site in the fixture, with its resolver verdict."""
    observed = _sites(_census(str(_FIXTURE_DIR), "--json"))
    assert observed == _GROUND_TRUTH_SITES, (
        "census patch-site set diverged from the hand-derived ground truth\n"
        f"  missing from census : {sorted(_GROUND_TRUTH_SITES - observed)}\n"
        f"  unexpected extras   : {sorted(observed - _GROUND_TRUTH_SITES)}"
    )


def test_arm_a_fixture_corruptible_assertions_match_ground_truth() -> None:
    """Corruptible assertions and their cardinality, hand-derived."""
    observed = _corruptible(_census(str(_FIXTURE_DIR), "--json"))
    assert observed == _GROUND_TRUTH_CORRUPTIBLE, (
        "corruptible-assertion set diverged from the hand-derived ground truth\n"
        f"  missing from census : {sorted(_GROUND_TRUTH_CORRUPTIBLE - observed)}\n"
        f"  unexpected extras   : {sorted(observed - _GROUND_TRUTH_CORRUPTIBLE)}"
    )


def test_arm_a_sleep_nodes_exclude_the_monotonic_only_function() -> None:
    """A monotonic-only node is reach-through but is not a *sleep* node."""
    payload = _census(str(_FIXTURE_DIR), "--json")
    observed = frozenset((Path(n["file"]).name, str(n["node_id"])) for n in payload["nodes_with_sleep_assertions"])
    assert observed == _GROUND_TRUTH_SLEEP_NODES, (
        "sleep-node set diverged from the hand-derived ground truth\n"
        f"  missing from census : {sorted(_GROUND_TRUTH_SLEEP_NODES - observed)}\n"
        f"  unexpected extras   : {sorted(observed - _GROUND_TRUTH_SLEEP_NODES)}"
    )


# --------------------------------------------------------------------------
# Arm B — decoys defeated
# --------------------------------------------------------------------------


def test_arm_b_decoys_contribute_nothing_and_grep_overcounts() -> None:
    """A docstring, a comment and a bare literal must all be inert (NFR-007)."""
    payload = _census(str(_FIXTURE_DIR), "--json")
    decoy_lines = frozenset((Path(s["file"]).name, int(s["line"])) for s in payload["sites"] if Path(s["file"]).name == "seam_decoy_cases.py")
    # Only the live decorator at :36 is real. The docstring's quoted @patch and
    # the commented-out @patch must not appear.
    assert decoy_lines == frozenset({("seam_decoy_cases.py", 36)}), f"decoys leaked into the census: {sorted(decoy_lines)}"

    # The docstring assertion at :10 must not be a corruptible assertion.
    corruptible_decoy_lines = frozenset(line for name, line, _ in _corruptible(payload) if name == "seam_decoy_cases.py")
    assert corruptible_decoy_lines == frozenset({43}), f"docstring assertion leaked into corruptible set: {sorted(corruptible_decoy_lines)}"

    grep_hits = sum(path.read_text(encoding="utf-8").count("patch(") for path in _FIXTURE_DIR.glob("*.py"))
    census_hits = len(payload["sites"])
    assert grep_hits > census_hits, (
        "the fixture no longer demonstrates grep over-counting: "
        f"naive grep 'patch(' = {grep_hits}, AST census = {census_hits}. "
        "The gap between these two numbers is the point of the fixture."
    )


# --------------------------------------------------------------------------
# Arm C — the `in` form reports n=0
# --------------------------------------------------------------------------


def test_arm_c_membership_assertion_reports_zero_cardinality() -> None:
    """``assert 3.0 in [c.args[0] for c in m.call_args_list]`` asserts no count.

    Deriving ``n`` from the length of the printed delay list would report
    ``n=1`` here — honestly printed, and completely wrong about what the
    assertion constrains. If this reports anything but 0, SC-002 is fakeable.
    """
    observed = _corruptible(_census(str(_FIXTURE_DIR), "--json"))
    membership = frozenset((name, line, n) for name, line, n in observed if (name, line) == ("seam_negative_cases.py", 41))
    assert membership == frozenset({("seam_negative_cases.py", 41, 0)}), f"the `in` form must report n=0; census reported {sorted(membership)}"


# --------------------------------------------------------------------------
# Arm D — bucket counts over tests/sync/
# --------------------------------------------------------------------------


def test_arm_d_bucket_counts_over_tests_sync() -> None:
    """Pin all five buckets, ``unresolvable`` included, for the live tree.

    ``unresolvable`` is pinned deliberately: classification runs through import
    success, so a thinner environment would otherwise shrink the flagged set for
    free and the gate would pass by getting weaker.
    """
    payload = _census(str(_SYNC_TREE), "--json")
    observed = frozenset(payload["buckets"].items())
    assert observed == _EXPECTED_BUCKETS, (
        "bucket counts over tests/sync/ moved\n"
        f"  expected but absent : {sorted(_EXPECTED_BUCKETS - observed)}\n"
        f"  observed unexpected : {sorted(observed - _EXPECTED_BUCKETS)}"
    )


# --------------------------------------------------------------------------
# Arm E — self-mutation (SC-015)
# --------------------------------------------------------------------------


def test_arm_e_narrowed_analyzer_misses_the_fixture_positives() -> None:
    """Narrow the analyzer to decorators only; the fixture must go under-counted.

    The narrowing is driven through an injected CLI parameter, never by editing
    the shipped file. If a decorator-only analyzer still finds every positive,
    the context-manager and ``side_effect=`` recognisers are decoration and
    SC-015 is not being enforced.
    """
    full = _corruptible(_census(str(_FIXTURE_DIR), "--json"))
    narrowed = _corruptible(_census(str(_FIXTURE_DIR), "--json", "--only-forms", "decorator"))

    assert narrowed < full, (
        "narrowing the analyzer to decorator-only did NOT shrink the result set. "
        "The census is not actually keyed on the patch form.\n"
        f"  full     : {sorted(full)}\n"
        f"  narrowed : {sorted(narrowed)}"
    )

    lost = full - narrowed
    expected_lost = frozenset(
        {
            ("seam_contextmanager_cases.py", 32, 4),
            ("seam_contextmanager_cases.py", 41, 2),
        }
    )
    assert lost == expected_lost, (
        "the narrowed analyzer lost a different set than the two forms R1 could "
        "not see\n"
        f"  expected lost : {sorted(expected_lost)}\n"
        f"  actually lost : {sorted(lost)}"
    )


# --------------------------------------------------------------------------
# Arm F — cross-check against the regex extractor
# --------------------------------------------------------------------------


def test_arm_f_ast_superset_of_regex_after_removing_prose_spans() -> None:
    """AST ⊇ regex, once regex hits inside string/comment spans are removed.

    ``plan.md:846-847`` words this as a plain superset claim. That is **false on
    the base tree**: the regex extractor scans raw source and therefore sees
    ``patch()`` targets quoted inside docstrings, which NFR-007 requires the AST
    to exclude. Measured on this tree the regex finds 4 sites the AST does not,
    and all 4 are docstrings. Stating the arm as a plain superset would make it
    red on arrival, so it is restated to grade *correctness* rather than the two
    extractors' known and correct asymmetry.

    A regex-only hit that does **not** sit inside a string-literal or comment
    span fails. An AST-only hit is reported, not failed — the regex's ``\\s*``
    cannot bridge a comment sitting between ``patch(`` and its target string,
    which is a regex limitation rather than an AST defect.

    The exception set is **derived** — every regex-only line is checked against
    the file's own string/comment spans (:func:`_prose_lines`). It used to be a
    hand-transcribed ``(file, line)`` list, which is a snapshot rather than a
    contract: WP02 edits three of those very docstrings and adds a fourth file,
    so the transcribed list was red on arrival at consolidation
    (``residual-ledger.md:448-449`` predicted exactly this). The derived form is
    green in both tree states while still failing on a genuine divergence,
    because a *real* missed patch site is by definition not inside prose.
    """
    payload = _census(str(_SYNC_TREE), "--json", "--cross-check")

    regex_only = frozenset((str(s["file"]), int(s["line"])) for s in payload["cross_check"]["regex_only"])
    ast_only = frozenset((str(s["file"]), int(s["line"])) for s in payload["cross_check"]["ast_only"])

    # Non-vacuity: the two extractors are known to disagree in this direction on
    # every tree state seen so far. An empty set means the cross-check stopped
    # computing, not that the asymmetry was fixed.
    assert regex_only, (
        "cross_check reported no regex-only hits at all; the arm would then "
        "pass for free. The regex extractor reads raw source and has always "
        "seen at least the docstring-quoted targets the AST excludes."
    )

    unexplained = frozenset((file, line) for file, line in regex_only if line not in _prose_lines(_REPO_ROOT / file))
    assert unexplained == frozenset(), (
        "regex-only hits that are NOT inside a string-literal or comment span\n"
        f"  unexplained : {sorted(unexplained)}\n"
        f"  (all regex-only hits: {sorted(regex_only)})\n"
        "  A regex-only hit outside prose is a live patch() call the AST walker "
        "missed — a real divergence, not the two extractors' known asymmetry."
    )

    # AST-only hits are reported, not failed. No assertion is made on their
    # content — but the arm must not be able to pass because the census forgot
    # to compute the direction at all, so the key's presence is asserted.
    print(f"[arm F] AST-only sites (reported, not a failure): {sorted(ast_only)}")
    assert "ast_only" in payload["cross_check"], "census omitted the ast_only direction; the arm must print the difference in BOTH directions"


# --------------------------------------------------------------------------
# Arm G — an own-module sleep seam counts, but is not corruptible
# --------------------------------------------------------------------------

# The seam module is interpolated rather than written literally. Written
# literally, this file's own raw source would carry
# `@patch("<seam>._sleep")`, and `check_patch_targets.py`'s regex — which
# reads raw source, not an AST — would extract it as a live target and red the
# [ENFORCED] lint on any tree where the alias does not yet exist.
_SEAM = "specify_cli.tracker.saas_client"

# Built in-memory under tmp_path rather than committed under
# `tests/architectural/_fixtures/`, for the same reason: the post-fix target
# `<seam>._sleep` does not resolve on the pre-fix tree, and
# `check_patch_targets.py` rglobs every `*.py` beneath `tests/`. Reproduced:
#   `'specify_cli.tracker.saas_client' has no attribute '_sleep'` -> exit 1.
# The WP03 prompt's binding fixture decision sanctions exactly this escape for
# a target that cannot resolve on the current tree; spec.md:350-372 requires the
# resulting lint red to stay inside WP02's single work package.
#
# Line numbers are hand-derived from the template below (the module docstring
# occupies 1-6), never read back from census output.
_OWN_MODULE_SLEEP_CASE = '''\
"""An own-module sleep seam beside a reach-through one.

The two differ only in resolver verdict: `{seam}._sleep` patches the alias
where it is defined, so nothing is reached through; `{seam}.time.sleep`
mutates the process-wide stdlib `time` module.
"""

from unittest.mock import MagicMock, patch


@patch("{seam}._sleep")
def case_own_module_sleep_alias(mock_sleep: MagicMock) -> None:
    """Reads the seam, so it is a sleep assertion — but it is NOT corruptible."""
    mock_sleep(1.0)
    mock_sleep(2.0)
    assert mock_sleep.call_count == 2


@patch("{seam}.time.sleep")
def case_reach_through_sleep(mock_sleep: MagicMock) -> None:
    """The same read shape against a reach-through seam: corruptible."""
    mock_sleep(3.0)
    assert mock_sleep.call_count == 1
'''

_ARM_G_SITES = frozenset({(11, "_sleep", "own_module"), (19, "sleep", "reach_through")})
_ARM_G_SLEEP_ASSERTIONS = frozenset({(16, 2), (23, 1)})
_ARM_G_CORRUPTIBLE = frozenset({(23, 1)})


def test_arm_g_own_module_sleep_seam_counts_but_is_not_corruptible(tmp_path: Path) -> None:
    """`sleep_assertions` and `corruptible_assertions` are two properties, not one.

    `spec.md:551-555` requires `sleep_assertions: 5` **and**
    `corruptible_assertions: 0` post-fix — "these three denominators must not
    move; only `corruptible_assertions` may". Rendering both from one list makes
    that pair unreachable by construction, and no arm over the pre-fix tree can
    notice, because pre-fix every sleep seam happens to be `reach_through`.

    The census's own `_disposition()` already says `own_module` is
    `correct-by-alias`. This arm holds the report to that vocabulary: a sleep
    seam patched where the symbol is *defined* is read, counted, and safe.
    """
    (tmp_path / "seam_own_module_sleep_case.py").write_text(_OWN_MODULE_SLEEP_CASE.format(seam=_SEAM), encoding="utf-8")
    payload = _census(str(tmp_path), "--json")

    assert _seam_sleep_sites(payload) == _ARM_G_SITES, (
        f"the two seam sites did not resolve to the expected verdict pair\n  observed : {sorted(_seam_sleep_sites(payload))}"
    )

    sleep_assertions = _assertion_lines(payload, "sleep_assertions")
    corruptible = _assertion_lines(payload, "corruptible_assertions")

    assert sleep_assertions == _ARM_G_SLEEP_ASSERTIONS, (
        "`sleep_assertions` must be verdict-AGNOSTIC: every assertion reading a "
        "sleep seam counts, however the seam resolves\n"
        f"  expected but absent : {sorted(_ARM_G_SLEEP_ASSERTIONS - sleep_assertions)}\n"
        f"  observed unexpected : {sorted(sleep_assertions - _ARM_G_SLEEP_ASSERTIONS)}"
    )
    assert corruptible == _ARM_G_CORRUPTIBLE, (
        "`corruptible_assertions` must be the VERDICT-FILTERED subset: an "
        "own-module alias patch is correct-by-alias, not corruptible\n"
        f"  expected but absent : {sorted(_ARM_G_CORRUPTIBLE - corruptible)}\n"
        f"  observed unexpected : {sorted(corruptible - _ARM_G_CORRUPTIBLE)}"
    )
    assert corruptible < sleep_assertions, (
        "the two denominators are rendered from the same list, so they can "
        "never differ — which is exactly what spec.md:554-555 says "
        "`sleep_assertions` was added to prevent"
    )
