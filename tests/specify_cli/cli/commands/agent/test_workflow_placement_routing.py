"""WP04 (T016) — ``workflow.py`` write sites route placement via the seam.

Before this WP, ``workflow.py``'s lifecycle/status write sites decided their
commit destination via an inline local-signal check (``if coord_branch …
else target_branch`` from :func:`_load_coord_branch_meta`, plus two bare
``CommitTarget(ref=target_branch)`` constructions at the legacy-commit leaf
and the baseline-artifact commit) rather than consulting the coord-primary
placement seam (``mission_runtime.placement_seam`` — WP01, T001) — the single
kind-aware authority the mission introduces.

RED-first proof (pre-fix): ``workflow.py`` never imports or calls
``placement_seam`` at all, so both assertions below fail on unmodified code —
(1) the structural scan finds no ``_resolve_workflow_placement`` helper, and
(2) the legacy commit leaf receives the raw, un-seam-resolved ``target_branch``
string instead of the seam's projected :class:`~mission_runtime.CommitTarget`.

Post-fix: a single ``_resolve_workflow_placement(repo_root, mission_slug,
kind)`` helper wraps ``placement_seam(...).write_target(kind)`` — the ONE
choke point (not 4x inlined, per the WP's reviewer guidance) — and
``_commit_workflow_change``'s legacy branch threads its resolved
``CommitTarget`` into :func:`_commit_via_legacy_safe_commit` instead of the
raw parameter.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from specify_cli.cli.commands.agent import workflow as _workflow_module

pytestmark = [pytest.mark.unit, pytest.mark.fast]

_WORKFLOW_MODULE_PATH = Path(_workflow_module.__file__).resolve()


def _parse_workflow_module() -> ast.Module:
    return ast.parse(_WORKFLOW_MODULE_PATH.read_text(encoding="utf-8"))


def _placement_seam_call_sites(tree: ast.AST) -> list[ast.Call]:
    """Every ``placement_seam(...)`` call expression in ``tree``."""
    sites: list[ast.Call] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name == "placement_seam":
            sites.append(node)
    return sites


def _enclosing_function_names(tree: ast.AST, target: ast.Call) -> list[str]:
    """Names of every function definition lexically enclosing ``target``.

    Uses line-number containment (``target.lineno`` within
    ``[node.lineno, node.end_lineno]``) rather than node identity, so callers
    may pass a freshly re-parsed tree without re-walking for the exact same
    node object.
    """
    names: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.lineno <= target.lineno <= (node.end_lineno or node.lineno):
            names.append(node.name)
    return names


# ---------------------------------------------------------------------------
# T016 (a) — structural: ONE seam choke point, not 4x inlined
# ---------------------------------------------------------------------------


def test_workflow_has_exactly_one_placement_seam_call_site() -> None:
    """``placement_seam(...)`` is invoked from exactly ONE place in workflow.py.

    RED anchor: pre-fix, ``workflow.py`` never calls ``placement_seam`` at
    all (count == 0) — the write sites decide placement from local
    ``coord_branch`` presence instead. Post-fix, the single
    ``_resolve_workflow_placement`` helper is the ONE call site; the reviewer
    guidance explicitly forbids inlining the seam call at each write site.

    read-surface-ssot-closeout WP04 (T017/T018): the invariant this test pins
    is "no per-site re-derivation of the seam construction" — NOT literally
    "only ``_resolve_workflow_placement`` may exist". WP04 adds a sibling
    READ-side wrapper (``_resolve_workflow_read_dir``) for IC-04's routing;
    both wrappers now share the ONE raw construction via the new
    ``_workflow_placement_seam(repo_root, mission_slug)`` helper, so the
    count assertion (exactly one raw call) still holds — see the companion
    test below for the (updated) enclosing-function check.
    """
    sites = _placement_seam_call_sites(_parse_workflow_module())
    assert len(sites) == 1, (
        f"expected exactly ONE placement_seam(...) call site in workflow.py, "
        f"found {len(sites)} at lines {[s.lineno for s in sites]} — route "
        "every read/write site through the single _workflow_placement_seam "
        "constructor instead of inlining the seam call per-site"
    )


def test_placement_seam_call_site_lives_in_workflow_placement_seam_constructor() -> None:
    """The lone seam call site is lexically inside ``_workflow_placement_seam``.

    read-surface-ssot-closeout WP04 (T017/T018): re-pinned from the prior
    ``_resolve_workflow_placement``-only shape. The raw ``placement_seam(...)``
    construction moved into a new shared ``_workflow_placement_seam`` helper
    so BOTH ``_resolve_workflow_placement`` (write) and the new
    ``_resolve_workflow_read_dir`` (read) can reuse the ONE construction
    without a second raw call appearing in the module (which would have
    broken the sibling "exactly one call site" test above).
    """
    tree = _parse_workflow_module()
    sites = _placement_seam_call_sites(tree)
    assert sites, "no placement_seam(...) call site found — helper not implemented yet"

    enclosing = _enclosing_function_names(tree, sites[0])
    assert "_workflow_placement_seam" in enclosing, (
        f"placement_seam(...) at line {sites[0].lineno} is not enclosed by a "
        f"'_workflow_placement_seam' function (enclosing: {enclosing}) — "
        "the WP mandates ONE named helper as the seam choke point"
    )


def test_resolve_workflow_placement_helper_exists_and_is_callable() -> None:
    """``workflow._resolve_workflow_placement`` is a real, importable callable."""
    from specify_cli.cli.commands.agent import workflow

    assert hasattr(workflow, "_resolve_workflow_placement"), (
        "workflow.py must define _resolve_workflow_placement(repo_root, "
        "mission_slug, kind) as the single placement choke point (T017)"
    )
    assert callable(workflow._resolve_workflow_placement)


# ---------------------------------------------------------------------------
# T016 (b) — behavioral: _resolve_workflow_placement delegates to the seam
# ---------------------------------------------------------------------------


def test_resolve_workflow_placement_delegates_to_the_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_resolve_workflow_placement`` is a thin wrapper over ``placement_seam``.

    Spies on ``mission_runtime.placement_seam`` (the lazy-import source
    ``_resolve_workflow_placement`` must read from, matching the sibling
    ``mission_feature_resolution.py`` lazy-import convention) and asserts the
    helper forwards ``(repo_root, mission_slug)`` unchanged and projects the
    ``kind`` through ``.write_target(kind)`` — never re-deriving placement
    itself.
    """
    import mission_runtime
    from mission_runtime import CommitTarget, MissionArtifactKind
    from specify_cli.cli.commands.agent import workflow

    calls: list[tuple[Path, str]] = []

    class _StubSeam:
        def __init__(self, repo_root: Path, mission_slug: str) -> None:
            calls.append((repo_root, mission_slug))

        def write_target(self, kind: MissionArtifactKind) -> CommitTarget:
            assert kind is MissionArtifactKind.STATUS_STATE
            return CommitTarget(ref="SEAM-ROUTED-REF")

    monkeypatch.setattr(mission_runtime, "placement_seam", _StubSeam)

    result = workflow._resolve_workflow_placement(
        repo_root=tmp_path, mission_slug="001-demo", kind=MissionArtifactKind.STATUS_STATE
    )

    assert calls == [(tmp_path, "001-demo")]
    assert result == CommitTarget(ref="SEAM-ROUTED-REF")


# ---------------------------------------------------------------------------
# read-surface-ssot-closeout WP04 (T017) — the sibling READ-side wrapper
# ---------------------------------------------------------------------------


def test_resolve_workflow_read_dir_helper_exists_and_is_callable() -> None:
    """``workflow._resolve_workflow_read_dir`` is a real, importable callable."""
    from specify_cli.cli.commands.agent import workflow

    assert hasattr(workflow, "_resolve_workflow_read_dir"), (
        "workflow.py must define _resolve_workflow_read_dir(repo_root, "
        "mission_slug, kind) as the READ-side placement choke point (IC-04/T017)"
    )
    assert callable(workflow._resolve_workflow_read_dir)


def test_resolve_workflow_read_dir_delegates_to_the_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_resolve_workflow_read_dir`` is a thin wrapper over ``placement_seam``.

    Mirrors ``test_resolve_workflow_placement_delegates_to_the_seam`` for the
    READ-side projection: forwards ``(repo_root, mission_slug)`` unchanged and
    projects ``kind`` through ``.read_dir(kind)`` — never re-deriving the read
    path itself.
    """
    import mission_runtime
    from mission_runtime import MissionArtifactKind
    from specify_cli.cli.commands.agent import workflow

    calls: list[tuple[Path, str]] = []
    read_target = tmp_path / "kitty-specs" / "001-demo"

    class _StubSeam:
        def __init__(self, repo_root: Path, mission_slug: str) -> None:
            calls.append((repo_root, mission_slug))

        def read_dir(self, kind: MissionArtifactKind) -> Path:
            assert kind is MissionArtifactKind.WORK_PACKAGE_TASK
            return read_target

    monkeypatch.setattr(mission_runtime, "placement_seam", _StubSeam)

    result = workflow._resolve_workflow_read_dir(
        repo_root=tmp_path, mission_slug="001-demo", kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )

    assert calls == [(tmp_path, "001-demo")]
    assert result == read_target


def test_placement_and_read_dir_wrappers_share_the_one_constructor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Both wrappers construct the seam via the ONE shared constructor.

    Spies on ``mission_runtime.placement_seam`` and asserts exactly one
    construction happens per call to either wrapper — proving the read/write
    split does not silently re-introduce a second independent seam
    construction (the invariant ``test_workflow_has_exactly_one_placement_seam_call_site``
    pins structurally).
    """
    import mission_runtime
    from mission_runtime import CommitTarget, MissionArtifactKind
    from specify_cli.cli.commands.agent import workflow

    construction_count = 0

    class _StubSeam:
        def __init__(self, repo_root: Path, mission_slug: str) -> None:
            nonlocal construction_count
            construction_count += 1

        def write_target(self, kind: MissionArtifactKind) -> CommitTarget:
            return CommitTarget(ref="W")

        def read_dir(self, kind: MissionArtifactKind) -> Path:
            return tmp_path

    monkeypatch.setattr(mission_runtime, "placement_seam", _StubSeam)

    workflow._resolve_workflow_placement(
        repo_root=tmp_path, mission_slug="001-demo", kind=MissionArtifactKind.STATUS_STATE
    )
    assert construction_count == 1

    workflow._resolve_workflow_read_dir(
        repo_root=tmp_path, mission_slug="001-demo", kind=MissionArtifactKind.WORK_PACKAGE_TASK
    )
    assert construction_count == 2


# ---------------------------------------------------------------------------
# T016 (c) — behavioral RED-first: the legacy write leaf uses the seam value
# ---------------------------------------------------------------------------


def test_commit_workflow_change_legacy_path_routes_through_the_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``_commit_workflow_change``'s legacy branch commits to the SEAM ref.

    RED-first proof: pre-fix, the legacy branch calls
    ``_commit_via_legacy_safe_commit(target_branch=target_branch, ...)`` with
    the RAW parameter — ``safe_commit`` receives
    ``CommitTarget(ref=target_branch)`` verbatim, never consulting the seam.
    This test stubs the seam to resolve to a DIFFERENT ref than the raw
    ``target_branch`` argument and asserts the value that reaches
    ``safe_commit`` is the seam's projection — failing on unmodified code
    (which passes the raw, un-resolved ``"raw-target-branch"`` straight
    through) and passing once T017 threads the resolved placement in.
    """
    import mission_runtime
    from mission_runtime import CommitTarget, MissionArtifactKind
    from specify_cli.cli.commands.agent import workflow

    feature_dir = tmp_path / "kitty-specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    events_path = feature_dir / "status.events.jsonl"
    status_path = feature_dir / "status.json"
    events_path.write_text('{"event_id":"before"}\n', encoding="utf-8")
    status_path.write_text('{"before":true}\n', encoding="utf-8")

    class _StubSeam:
        def __init__(self, repo_root: Path, mission_slug: str) -> None:
            del repo_root, mission_slug

        def write_target(self, kind: MissionArtifactKind) -> CommitTarget:
            assert kind is MissionArtifactKind.STATUS_STATE
            return CommitTarget(ref="SEAM-ROUTED-REF")

    monkeypatch.setattr(mission_runtime, "placement_seam", _StubSeam)
    monkeypatch.setattr(workflow, "_load_coord_branch_meta", lambda _fd: (None, None, None))

    captured: dict[str, object] = {}

    class _StubResult:
        sha = "deadbeef"

    def _fake_safe_commit(**kwargs: object) -> _StubResult:
        captured.update(kwargs)
        return _StubResult()

    monkeypatch.setattr(workflow, "safe_commit", _fake_safe_commit)
    workflow._reset_workflow_receipts()

    workflow._commit_workflow_change(
        repo_root=tmp_path,
        feature_dir=feature_dir,
        mission_slug="001-demo",
        target_branch="raw-target-branch",
        paths=[events_path, status_path],
        message="chore: WP01 claimed [claude]",
        operation="planned -> claimed for WP01",
        wp_id="WP01",
        pre_emit_event_size=len('{"event_id":"before"}\n'),
        pre_emit_status_bytes=b'{"before":true}\n',
    )

    assert "target" in captured, "safe_commit was never invoked by the legacy path"
    assert captured["target"] == CommitTarget(ref="SEAM-ROUTED-REF"), (
        f"legacy commit landed on {captured['target']!r} — expected the seam-"
        "resolved CommitTarget, not the raw un-resolved target_branch "
        "parameter. The write site must route through "
        "_resolve_workflow_placement (T017), not inline "
        "CommitTarget(ref=target_branch)."
    )


# ---------------------------------------------------------------------------
# T021 campsite regression anchor — empty except at the dossier-sync site
# ---------------------------------------------------------------------------


def test_dossier_sync_except_handler_is_not_empty() -> None:
    """The dossier-sync ``except Exception:`` block does more than ``pass``.

    Symbol-anchored (not line-anchored, #2032 drift): locates the
    ``try/except`` guarding the ``trigger_feature_dossier_sync_if_enabled``
    call inside the ``implement`` command body and asserts its handler body
    is not the bare Sonar-flagged ``pass`` (empty-except campsite, T021).
    """
    from specify_cli.cli.commands.agent import workflow

    source = inspect.getsource(workflow)
    tree = ast.parse(source)

    target_call = "trigger_feature_dossier_sync_if_enabled"
    matches: list[ast.Try] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Try):
            continue
        if target_call in ast.dump(node):
            matches.append(node)

    assert matches, (
        f"no try/except guarding {target_call!r} found — symbol drifted, "
        "re-anchor this test on the dossier-sync call site"
    )
    for try_node in matches:
        for handler in try_node.handlers:
            body_is_bare_pass = len(handler.body) == 1 and isinstance(
                handler.body[0], ast.Pass
            )
            assert not body_is_bare_pass, (
                f"dossier-sync except handler at line {handler.lineno} is a "
                "bare 'pass' — Sonar empty-except (T021); add logging or "
                "concrete recovery instead of silently swallowing"
            )
