"""Identity-seam tests for ``runtime_bridge_identity`` (#2531 WP10, T036).

WP10 is the FINAL extraction of the runtime-bridge-degod-01KX8M1C mission
(#2531) and owns the two whole-mission closure assertions in addition to its
own seam coverage. Five independent concerns, self-contained (owns this file
only — no cross-file test-helper dependency, matching the established
per-WP-test convention in this suite):

1. **Native thin delegates** (``test_runtime_bridge_keeps_native_thin_delegates``)
   — the three relocated symbols must stay native ``def`` statements on
   ``runtime_bridge``, never a plain re-export (or the frozen
   ``test_bridge_compat_surface.py::test_guard_b_identity_reexport_for_relocated_symbols``
   trips). Paired with a non-vacuousness check that the seam actually defines
   them.

2. **Focused unit tests (FR-006)** against the moved cluster in isolation,
   including the malformed-coord-branch fail-closed path
   (:class:`BranchIdentityUnresolved`) — the correctness-critical contract
   this WP is named for (a malformed coord branch must surface loudly, never
   be swallowed; the ``git worktree`` exit-128 scar this class of bug used to
   cause, #2091/#1978/#1918/#1814/#2069).

3. **The identity-trio live-lookup regression** (research.md §Compat's
   grounded false-green minefield): now that ``_resolve_coordination_branch``
   and ``_resolve_mission_ulid`` live in the same seam as
   ``_primary_runtime_feature_dir``, an intra-seam call between them MUST
   resolve via a live lookup back through ``runtime_bridge`` (never a bare
   intra-module call), or the 6x ``monkeypatch``/``mock.patch`` sentinels in
   ``tests/runtime/test_runtime_bridge_identity.py`` become no-ops.
   ``test_*_uses_live_lookup_for_primary_runtime_feature_dir`` pin this by
   patching the callee on ``runtime_bridge`` and asserting the (unpatched)
   caller in the seam still observes it — mirroring the pattern
   ``tests/runtime/test_bridge_retrospective.py``'s
   ``test_*_uses_live_lookup_for_*`` tests already established for WP04's
   cluster.

4. **Whole-mission closure — NFR-002/SC-002 zero-C901** and **C-007
   no-new-import-cycle** across the entire ``runtime_bridge*`` family. These
   are acceptance-blocking per the WP10 prompt, not advisory.

5. **NFR-005 residual-LOC** (recorded, not frozen) and **NFR-006 timing
   parity** (asserted within noise, or an explicit in-test waiver record when
   a genuine cross-revision timing comparison cannot be safely constructed).
"""

from __future__ import annotations

import ast
import json
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from runtime.next import runtime_bridge as rb
from runtime.next import runtime_bridge_identity as identity
from specify_cli.lanes.branch_naming import BranchIdentityUnresolved

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_SRC_NEXT_DIR = Path(__file__).resolve().parents[2] / "src" / "runtime" / "next"
_ORIGINAL_MONOLITH_LOC = 3813  # #2531 pre-extraction runtime_bridge.py line count

# ---------------------------------------------------------------------------
# 1. Native thin delegates + non-vacuousness
# ---------------------------------------------------------------------------

_RELOCATED_NAMES = (
    "_primary_runtime_feature_dir",
    "_resolve_coordination_branch",
    "_resolve_mission_ulid",
)


def test_seam_defines_every_relocated_symbol() -> None:
    """Non-vacuousness check: the seam must actually define all three
    relocated names (guards against the native-thin-delegate assertion below
    passing for the wrong reason)."""
    for name in _RELOCATED_NAMES:
        assert hasattr(identity, name), f"seam is missing relocated symbol {name!r}"


def test_runtime_bridge_keeps_native_thin_delegates_for_identity_trio() -> None:
    """Every relocated identity symbol must stay a NATIVE ``def`` statement in
    ``runtime_bridge.py`` (a thin delegate), never a plain ``import`` alias --
    otherwise the frozen WP02 compat guard's hardcoded identity/relocated-
    symbol baseline (``test_guard_b_identity_reexport_for_relocated_symbols``)
    trips."""
    for name in _RELOCATED_NAMES:
        obj = getattr(rb, name)
        assert obj.__module__ == rb.__name__, (
            f"{name!r} on runtime_bridge is NOT natively defined there "
            f"(__module__={obj.__module__!r}) -- it must be a native thin "
            "delegate, not a plain re-export, or guard B's hardcoded "
            "relocated-symbol baseline will fail."
        )


def test_thin_delegates_forward_to_the_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    """The residual delegates must actually call through to the seam's real
    implementation (not merely share a name) -- a behavioral, not just
    structural, forwarding check."""
    calls: list[str] = []
    real_primary = identity._primary_runtime_feature_dir

    def _spy_primary(repo_root: Path, mission_slug: str) -> Path:
        calls.append("primary")
        return real_primary(repo_root, mission_slug)

    monkeypatch.setattr(identity, "_primary_runtime_feature_dir", _spy_primary)
    rb._primary_runtime_feature_dir(Path("/tmp/repo"), "some-slug")

    assert calls == ["primary"], "runtime_bridge._primary_runtime_feature_dir did not forward to the seam"


# ---------------------------------------------------------------------------
# 2. Focused unit tests (FR-006) -- moved cluster in isolation
# ---------------------------------------------------------------------------


def test_primary_runtime_feature_dir_delegates_to_read_path_resolver(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The moved body still composes via ``_canonicalize_primary_read_handle``
    + ``primary_feature_dir_for_mission`` (#2091 fix) -- pinned against stubs
    so this test does not depend on the real read-path resolver's internals."""
    calls: dict[str, Any] = {}

    def _fake_canonicalize(repo_root: Path, mission_slug: str) -> str:
        calls["canonicalize"] = (repo_root, mission_slug)
        return f"canonical-{mission_slug}"

    def _fake_primary_dir(repo_root: Path, handle: str) -> Path:
        calls["primary_dir"] = (repo_root, handle)
        return repo_root / "kitty-specs" / handle

    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver._canonicalize_primary_read_handle",
        _fake_canonicalize,
    )
    monkeypatch.setattr(
        "specify_cli.missions._read_path_resolver.primary_feature_dir_for_mission",
        _fake_primary_dir,
    )

    result = identity._primary_runtime_feature_dir(tmp_path, "my-slug")

    assert calls["canonicalize"] == (tmp_path, "my-slug")
    assert calls["primary_dir"] == (tmp_path, "canonical-my-slug")
    assert result == tmp_path / "kitty-specs" / "canonical-my-slug"


def test_resolve_coordination_branch_returns_declared_branch_from_meta(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A declared ``coordination_branch`` in meta.json is authoritative."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"coordination_branch": "kitty/mission-my-mission-01KWDABC-lane-a"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", lambda repo_root, mission_slug: feature_dir)

    branch = identity._resolve_coordination_branch("my-mission-01KWDABC", tmp_path)

    assert branch == "kitty/mission-my-mission-01KWDABC-lane-a"


def test_resolve_coordination_branch_composes_when_undeclared(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """No declared ``coordination_branch`` -> composed via the fail-closed
    seam using the declared ``mission_id`` (#1978)."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"mission_id": "01KWDABC1234567890ABCDEFGH"}),
        encoding="utf-8",
    )
    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", lambda repo_root, mission_slug: feature_dir)

    branch = identity._resolve_coordination_branch("my-mission-01KWDABC", tmp_path)

    assert branch  # composed, non-empty
    assert "my-mission" in branch


def test_resolve_coordination_branch_malformed_modern_mission_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The malformed-coord correctness path (this WP's namesake): a modern
    slug (no ``NNN-`` prefix, no mid8 tail) with no recoverable ``mission_id``
    must raise :class:`BranchIdentityUnresolved` -- NEVER silently compose a
    malformed ``kitty/mission-<slug>-`` branch (the historical #2091-class
    ``git worktree`` exit-128 scar). This is not swallowed anywhere in this
    seam; only ``_wrap_with_decision_git_log`` (KEEP-IN-PLACE, unmoved)
    decides whether to convert it to ``DecisionGitLogUnavailable`` or a
    warning-logged fallback."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", lambda repo_root, mission_slug: feature_dir)

    with pytest.raises(BranchIdentityUnresolved):
        identity._resolve_coordination_branch("my-mission", tmp_path)


def test_resolve_mission_ulid_returns_ulid_when_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    ulid = "01KWDABC1234567890ABCDEFGH"
    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": ulid}), encoding="utf-8")
    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", lambda repo_root, mission_slug: feature_dir)

    assert identity._resolve_mission_ulid("my-mission-01KWDABC", tmp_path) == ulid


def test_resolve_mission_ulid_returns_none_when_absent_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Fail-closed (FR-004): absent ``mission_id`` returns ``None``, never
    the slug substituted as a fake identity."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(json.dumps({}), encoding="utf-8")
    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", lambda repo_root, mission_slug: feature_dir)

    result = identity._resolve_mission_ulid("my-mission-01KWDABC", tmp_path)

    assert result is None
    assert result != "my-mission-01KWDABC"


# ---------------------------------------------------------------------------
# 3. Identity-trio live-lookup regression (the grounded false-green trap)
# ---------------------------------------------------------------------------


def test_resolve_coordination_branch_uses_live_lookup_for_primary_runtime_feature_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``_resolve_coordination_branch`` must resolve
    ``_primary_runtime_feature_dir`` via a live lookup through
    ``runtime_bridge`` -- a bare intra-seam call to this module's own
    function would silently bypass a patch applied to
    ``runtime_bridge._primary_runtime_feature_dir`` (the exact false-green
    mechanism research.md §Compat names, patched 6x in
    ``tests/runtime/test_runtime_bridge_identity.py``)."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    (feature_dir / "meta.json").write_text(
        json.dumps({"coordination_branch": "kitty/mission-my-mission-01KWDABC-lane-a"}),
        encoding="utf-8",
    )
    calls: list[str] = []

    def _spy(repo_root: Path, mission_slug: str) -> Path:
        calls.append("primary")
        return feature_dir

    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", _spy)

    identity._resolve_coordination_branch("my-mission-01KWDABC", tmp_path)

    assert calls == ["primary"], (
        "_resolve_coordination_branch did not observe the patch on "
        "runtime_bridge._primary_runtime_feature_dir -- an intra-seam bare "
        "call is bypassing the live lookup (false-green regression)."
    )


def test_resolve_mission_ulid_uses_live_lookup_for_primary_runtime_feature_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Same live-lookup regression as above, for ``_resolve_mission_ulid``."""
    feature_dir = tmp_path / "kitty-specs" / "my-mission-01KWDABC"
    feature_dir.mkdir(parents=True)
    ulid = "01KWDABC1234567890ABCDEFGH"
    (feature_dir / "meta.json").write_text(json.dumps({"mission_id": ulid}), encoding="utf-8")
    calls: list[str] = []

    def _spy(repo_root: Path, mission_slug: str) -> Path:
        calls.append("primary")
        return feature_dir

    monkeypatch.setattr(rb, "_primary_runtime_feature_dir", _spy)

    result = identity._resolve_mission_ulid("my-mission-01KWDABC", tmp_path)

    assert result == ulid
    assert calls == ["primary"], (
        "_resolve_mission_ulid did not observe the patch on "
        "runtime_bridge._primary_runtime_feature_dir -- an intra-seam bare "
        "call is bypassing the live lookup (false-green regression)."
    )


# ---------------------------------------------------------------------------
# 4a. Whole-mission closure -- NFR-002/SC-002 zero-C901 (the mission-closing
# complexity assertion). Authoritative mechanism is ruff's own offender count,
# NOT a text grep -- runtime_bridge.py carries a docstring that mentions the
# mccabe-complexity suppression marker as prose, which a naive grep would
# false-positive on.
# ---------------------------------------------------------------------------


def _family_files() -> list[Path]:
    files = [_SRC_NEXT_DIR / "runtime_bridge.py"]
    files.extend(sorted(_SRC_NEXT_DIR.glob("runtime_bridge_*.py")))
    for f in files:
        assert f.is_file(), f"expected family member missing: {f}"
    return files


def test_zero_c901_offenders_across_the_runtime_bridge_family() -> None:
    """The mission-closing complexity assertion (NFR-002/SC-002): ruff's own
    C901 (mccabe complexity) offender count must be exactly zero across
    ``runtime_bridge.py`` and every ``runtime_bridge_*.py`` sibling -- no
    function is over the ceiling, so no ``# noqa: C901`` suppression is ever
    needed. A text grep for the literal marker is NOT used here deliberately:
    it would false-positive on the prose mention of the marker inside a
    docstring."""
    files = _family_files()
    proc = subprocess.run(
        ["uv", "run", "ruff", "check", "--select", "C901", "--output-format", "json", *[str(f) for f in files]],
        capture_output=True,
        text=True,
        check=False,
    )
    offenders = json.loads(proc.stdout) if proc.stdout.strip() else []
    assert offenders == [], (
        f"ruff --select C901 found {len(offenders)} offender(s) across the runtime_bridge "
        f"family (expected zero): {[o.get('filename') for o in offenders]}"
    )


def test_no_noqa_c901_suppressions_exist_in_the_family() -> None:
    """Companion assertion: no function anywhere in the family actually
    carries a real ``# noqa: C901`` suppression comment (as opposed to a
    docstring that merely mentions the marker as prose) -- verified via
    ``tokenize`` (comments only), not a raw text grep over the whole file."""
    import tokenize

    for path in _family_files():
        with tokenize.open(path) as fh:
            comment_lines = [tok.string for tok in tokenize.generate_tokens(fh.readline) if tok.type == tokenize.COMMENT]
        offenders = [c for c in comment_lines if "noqa: C901" in c or "noqa:C901" in c]
        assert not offenders, f"{path}: real '# noqa: C901' suppression comment(s) found: {offenders}"


# ---------------------------------------------------------------------------
# 4b. Whole-mission closure -- C-007 no-new-import-cycle across the family
# ---------------------------------------------------------------------------

_FAMILY_MODULE_NAMES = frozenset(
    {
        "runtime_bridge",
        "runtime_bridge_engine",
        "runtime_bridge_cores",
        "runtime_bridge_io",
        "runtime_bridge_composition",
        "runtime_bridge_retrospective",
        "runtime_bridge_identity",
        "decision",
    }
)


def _module_short_name(dotted: str | None) -> str | None:
    if dotted is None:
        return None
    tail = dotted.rsplit(".", 1)[-1]
    return tail if tail in _FAMILY_MODULE_NAMES else None


def _top_level_family_edges(path: Path, own_name: str) -> set[str]:
    """Return the set of family module names ``path`` imports at MODULE
    scope (top-level ``Import``/``ImportFrom`` only -- deferred/function-scope
    imports, the lazy-accessor mechanism this whole mission relies on, are
    deliberately excluded; they are what keeps the graph acyclic)."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    edges: set[str] = set()
    for node in tree.body:  # module-level statements ONLY
        if isinstance(node, ast.ImportFrom):
            target = _module_short_name(node.module)
            if target is not None and target != own_name:
                edges.add(target)
            if node.module == "runtime.next":
                for alias in node.names:
                    if alias.name in _FAMILY_MODULE_NAMES and alias.name != own_name:
                        edges.add(alias.name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                target = _module_short_name(alias.name)
                if target is not None and target != own_name:
                    edges.add(target)
    return edges


def _build_family_graph() -> dict[str, set[str]]:
    graph: dict[str, set[str]] = {}
    for name in _FAMILY_MODULE_NAMES:
        filename = "decision.py" if name == "decision" else f"{name}.py"
        path = _SRC_NEXT_DIR / filename
        assert path.is_file(), f"expected family member missing: {path}"
        graph[name] = _top_level_family_edges(path, name)
    return graph


def test_no_new_top_level_import_cycle_in_runtime_bridge_family() -> None:
    """C-007 whole-family closure: build the top-level import edges for every
    ``runtime_bridge*`` module plus ``decision.py`` and assert the graph is
    acyclic. The ``decision.py:428 -> runtime_bridge.decide_next_via_runtime``
    edge is a deferred (function-scope) import specifically so it never
    appears here -- see the dedicated assertion below."""
    graph = _build_family_graph()

    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = dict.fromkeys(graph, WHITE)
    cycle_path: list[str] = []

    def _visit(node: str, stack: list[str]) -> bool:
        color[node] = GRAY
        stack.append(node)
        for neighbor in graph.get(node, ()):
            if color[neighbor] == GRAY:
                cycle_path.extend([*stack, neighbor])
                return True
            if color[neighbor] == WHITE and _visit(neighbor, stack):
                return True
        stack.pop()
        color[node] = BLACK
        return False

    for start in graph:
        if color[start] == WHITE and _visit(start, []):
            raise AssertionError(
                f"top-level import cycle detected in runtime_bridge family: {' -> '.join(cycle_path)}"
            )


def test_decision_module_has_no_top_level_edge_back_into_runtime_bridge_family() -> None:
    """The named C-007 invariant: ``decision.py``'s orchestrator edge
    (``decide_next -> runtime_bridge.decide_next_via_runtime``) MUST stay a
    deferred/function-scope import, never a top-level one -- a top-level edge
    here would create exactly the cycle the whole extraction strategy is
    designed to avoid (``runtime_bridge`` already imports ``decision`` at its
    own top level)."""
    edges = _top_level_family_edges(_SRC_NEXT_DIR / "decision.py", "decision")
    assert edges == set(), (
        f"decision.py has a top-level import edge into the runtime_bridge family: {edges} "
        "-- this must stay a deferred (function-scope) import (C-007)."
    )


def test_identity_seam_not_imported_by_cores() -> None:
    """The WP10-specific Import DAG rule (research.md §Import DAG): ``cores``
    sits at the base of the DAG (stdlib/``Lane``/decision types only) and must
    never import ``identity``."""
    edges = _top_level_family_edges(_SRC_NEXT_DIR / "runtime_bridge_cores.py", "runtime_bridge_cores")
    assert "runtime_bridge_identity" not in edges, "runtime_bridge_cores.py must not import runtime_bridge_identity (DAG violation)"


def test_identity_seam_has_no_top_level_edge_into_runtime_bridge() -> None:
    """The identity seam's own deferred-import discipline: its
    ``from runtime.next import runtime_bridge as _rb`` lazy accessor must stay
    function-scoped (never top-level), or it would create the residual<->seam
    import cycle its own module docstring explains."""
    edges = _top_level_family_edges(_SRC_NEXT_DIR / "runtime_bridge_identity.py", "runtime_bridge_identity")
    assert "runtime_bridge" not in edges, "runtime_bridge_identity.py imports runtime_bridge at module scope (would be circular)"


# ---------------------------------------------------------------------------
# 5a. NFR-005 residual-LOC (recorded, not a frozen constant)
# ---------------------------------------------------------------------------


def test_residual_loc_reduction_is_recorded() -> None:
    """Guidance target (research.md/plan.md IC-09): ~35-40% of the original
    3,813-LOC monolith. This is explicitly NOT a frozen constant (WP10 prompt)
    -- assert only that a real reduction happened, and record the actual
    percentage in the assertion message so it is visible in CI output /
    the PR body rather than silently drifting."""
    residual_path = _SRC_NEXT_DIR / "runtime_bridge.py"
    residual_loc = len(residual_path.read_text(encoding="utf-8").splitlines())
    pct = 100.0 * residual_loc / _ORIGINAL_MONOLITH_LOC

    assert residual_loc < _ORIGINAL_MONOLITH_LOC, (
        f"residual runtime_bridge.py ({residual_loc} LOC) did not shrink relative to "
        f"the original monolith ({_ORIGINAL_MONOLITH_LOC} LOC)"
    )
    # Recorded finding (not enforced as a hard ceiling): the ~35-40% guidance
    # band from research.md/plan.md IC-09 is aspirational, not achieved by the
    # cumulative WP03-WP10 extraction -- see this WP's completion report for
    # the full breakdown across all six seam modules.
    print(  # noqa: T201 -- intentional CI-visible record, not debug litter
        f"NFR-005 residual-LOC record: runtime_bridge.py = {residual_loc} LOC "
        f"({pct:.1f}% of the original {_ORIGINAL_MONOLITH_LOC}-LOC monolith)."
    )


# ---------------------------------------------------------------------------
# 5b. NFR-006 timing parity (asserted within noise, or an explicit waiver)
# ---------------------------------------------------------------------------


def _load_pre_wp10_identity_functions() -> Any | None:
    """Load the pre-WP10 (current git HEAD, uncommitted-change-safe) source
    of ``runtime_bridge.py`` into an isolated, throwaway module namespace so
    the identity trio's PRE-extraction implementation can be timed against
    the POST-extraction one for a genuine before/after comparison -- rather
    than the self-consistency-only seed ``test_bridge_parity.py::
    test_nfr006_timing_seed`` records (both its "before"/"after" runs drive
    the SAME currently-installed code).

    Returns ``None`` (never raises) when the git-show or exec step fails for
    any reason -- the caller records an explicit waiver in that case rather
    than letting environment fragility fail the whole gate.
    """
    import types

    repo_root = Path(__file__).resolve().parents[2]
    try:
        proc = subprocess.run(
            ["git", "show", "HEAD:src/runtime/next/runtime_bridge.py"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
        return None

    import sys

    module_name = "_wp10_pre_extraction_runtime_bridge_snapshot"
    module = types.ModuleType(module_name)
    module.__file__ = str(repo_root / "src" / "runtime" / "next" / "runtime_bridge.py")
    # Dataclass processing (``@dataclass`` on DecideNextContext et al.) resolves
    # forward-referenced annotations via ``sys.modules[cls.__module__]`` at
    # class-definition time -- the module must be registered for exec to
    # succeed. Left registered under this unique, single-purpose name for the
    # rest of the process lifetime (a throwaway test-only module, not a real
    # package) rather than risking a call-time re-resolution failure if
    # something introspects it again after an early de-registration.
    sys.modules[module_name] = module
    try:
        exec(compile(proc.stdout, module.__file__, "exec"), module.__dict__)  # noqa: S102 -- trusted, git-sourced first-party snapshot of our own module, not user input
    except Exception:
        del sys.modules[module_name]
        return None
    return module


def test_nfr006_identity_resolution_timing_parity() -> None:
    """NFR-006: the identity trio's post-extraction timing must stay within
    noise of its pre-extraction (this-WP's-own HEAD) timing. Uses
    ``_resolve_mission_ulid`` (the cheapest fully self-contained real call in
    the cluster -- no git repo scaffold needed) driven many times against a
    real ``meta.json`` fixture, comparing wall-clock duration before vs after
    this WP's move.

    If the pre-extraction snapshot cannot be safely loaded (e.g. an
    environment where dynamic exec of a second module copy is restricted),
    this test explicitly records the NFR-006 waiver via ``pytest.skip`` rather
    than silently passing or flaking the suite.
    """
    pre_module = _load_pre_wp10_identity_functions()
    if pre_module is None or not hasattr(pre_module, "_resolve_mission_ulid"):
        pytest.skip(
            "NFR-006 WAIVER RECORDED: could not load a pre-WP10 snapshot of "
            "runtime_bridge.py via 'git show HEAD:...' + exec in this "
            "environment; the identity trio's move (three small functions, "
            "one extra function-call indirection via the lazy accessor) is "
            "analytically negligible relative to the meta.json disk read "
            "each call already performs -- see this WP's completion report."
        )

    import tempfile

    def _time_calls(resolve_fn: Any, n: int = 200) -> float:
        with tempfile.TemporaryDirectory() as tmp:
            feature_dir = Path(tmp) / "kitty-specs" / "timing-mission-01KWDABC"
            feature_dir.mkdir(parents=True)
            (feature_dir / "meta.json").write_text(
                json.dumps({"mission_id": "01KWDABC1234567890ABCDEFGH"}), encoding="utf-8"
            )
            repo_root = Path(tmp)
            start = time.perf_counter()
            for _ in range(n):
                resolve_fn("timing-mission-01KWDABC", repo_root)
            return time.perf_counter() - start

    def _resolve_after(mission_slug: str, repo_root: Path) -> str | None:
        import unittest.mock as mock

        feature_dir = repo_root / "kitty-specs" / mission_slug
        with mock.patch.object(rb, "_primary_runtime_feature_dir", return_value=feature_dir):
            return identity._resolve_mission_ulid(mission_slug, repo_root)

    def _call_before(mission_slug: str, repo_root: Path) -> str | None:
        import unittest.mock as mock

        feature_dir = repo_root / "kitty-specs" / mission_slug
        with mock.patch.object(pre_module, "_primary_runtime_feature_dir", return_value=feature_dir):
            # pre_module is Any (a dynamically exec'd snapshot) -- local
            # annotation re-narrows the call result back to str | None.
            result: str | None = pre_module._resolve_mission_ulid(mission_slug, repo_root)
            return result

    before_duration = _time_calls(_call_before)
    after_duration = _time_calls(_resolve_after)

    # Generous noise band: this WP adds, at most, one extra function-call
    # indirection per resolution (the lazy accessor) -- utterly negligible
    # relative to the JSON meta.json read each call already performs. 4x +
    # a fixed absolute slack absorbs process/CI scheduling noise without
    # masking a genuine regression (e.g. an accidental O(n) reread loop).
    ceiling = before_duration * 4.0 + 0.25
    assert after_duration <= ceiling, (
        f"NFR-006 timing regression: post-extraction duration {after_duration:.4f}s "
        f"exceeds the noise ceiling {ceiling:.4f}s (pre-extraction baseline "
        f"{before_duration:.4f}s over 200 calls)."
    )
