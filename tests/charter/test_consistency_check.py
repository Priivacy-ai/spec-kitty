"""Tests for ``charter.activation.consistency_check`` (WP07, T033).

Covers:
- ``test_coherent_when_all_activated_ids_exist_in_doctrine``: All activated IDs
  are real doctrine IDs → report is coherent.
- ``test_unknown_reference_detected``: A planted fake ID → appears in
  ``unknown_references``; ``coherent`` is False.
- ``test_suggestion_contains_resolution_command``: Suggestion for unknown ID
  contains "charter deactivate".
- ``test_none_kind_skipped``: A kind with None activation (no config key) is
  skipped and produces no ``unknown_references`` entry for that kind.
- ``test_coherent_false_when_incoherent``: Any unknown ID → coherent is False.
- ``test_run_consistency_check_returns_report_object``: Return type and field
  types are correct.
- ``test_run_consistency_check_completes_within_budget``: NFR-003 performance guard.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from charter.activation.consistency_check import ConsistencyReport, run_consistency_check
from charter.activation.invocation_context import ProjectContext
from charter.activation.pack_context import PackContext

pytestmark = pytest.mark.unit

# ---------------------------------------------------------------------------
# A real directive ID that exists in the built-in doctrine.
# Used in coherent tests to avoid false unknowns.
# ---------------------------------------------------------------------------
_REAL_DIRECTIVE_ID = "001-architectural-integrity-standard"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_config(tmp_path: Path, content: str) -> None:
    """Write a .kittify/config.yaml with the given content."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir(exist_ok=True)
    (kittify / "config.yaml").write_text(content, encoding="utf-8")


def _ctx_with_config(tmp_path: Path, config_yaml: str) -> ProjectContext:
    """Build a ProjectContext with the supplied config content.

    ``mission_type_activations`` is appended unconditionally: every caller
    here supplies only ``activated_directives`` content (or none at all),
    and ``ProjectContext.from_repo`` eagerly resolves
    ``PackContext.from_config()``, which now hard-fails (WP04, C-A1) when
    that key is absent. The mission-type kind is unrelated to the
    consistency-check behavior these tests pin.
    """
    _write_config(tmp_path, config_yaml + "mission_type_activations:\n  - software-dev\n")
    return ProjectContext.from_repo(tmp_path)


def _ctx_with_config_no_activation_keys(tmp_path: Path, config_yaml: str) -> ProjectContext:
    """Build a ProjectContext against config content with NO activation keys
    at all -- including no ``mission_type_activations``.

    Unlike ``_ctx_with_config``, this does NOT append
    ``mission_type_activations`` to the written config.yaml: doing so would
    make ``_has_explicit_activation`` (which loops over every
    ``YAML_KEY_MAP`` entry, including the "mission-type" ->
    ``mission_type_activations`` mapping) see a non-``None`` value for that
    kind and incorrectly flip "no activation keys at all" to "one activation
    key present" -- exactly the kind of uniform-loop assertion this
    module's ``test_no_activation_keys_skips_doctrine_scan`` pins (see
    module docstring hazard notes in the WP04 remediation task). Instead,
    ``pack_context`` is built directly via the ``PackContext`` dataclass
    constructor (bypassing ``PackContext.from_config``, so the WP04, C-A1
    hard-fail on an absent ``mission_type_activations`` key never fires)
    while ``_load_raw_activation_lists`` -- which reads activation state
    from the ON-DISK ``config.yaml``/``charter.yaml``, not from
    ``ctx.pack_context`` -- still observes the genuinely key-free config
    content this test needs.
    """
    _write_config(tmp_path, config_yaml)
    pack_context = PackContext(
        activated_kinds=frozenset(
            {
                "directives",
                "tactics",
                "styleguides",
                "toolguides",
                "paradigms",
                "procedures",
                "agent_profiles",
                "mission_step_contracts",
            }
        ),
        activated_mission_types=frozenset({"software-dev"}),
        pack_roots=(),
        org_pack_names=(),
        repo_root=tmp_path,
    )
    return ProjectContext(repo_root=tmp_path, pack_context=pack_context)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.doctrine
def test_coherent_when_all_activated_ids_exist_in_doctrine(tmp_path: Path) -> None:
    """Activating a real doctrine directive ID → report is coherent."""
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {_REAL_DIRECTIVE_ID}\n",
    )
    report = run_consistency_check(ctx)

    assert report.coherent is True
    assert report.unknown_references == []


@pytest.mark.doctrine
def test_unknown_reference_detected(tmp_path: Path) -> None:
    """A planted fake directive ID → appears in unknown_references."""
    fake_id = "totally-fake-directive-zzz"
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {fake_id}\n",
    )
    report = run_consistency_check(ctx)

    assert any(fake_id in ref for ref in report.unknown_references), (
        f"Expected '{fake_id}' in unknown_references but got: "
        f"{report.unknown_references}"
    )
    assert report.coherent is False


@pytest.mark.doctrine
def test_duplicate_activation_entry_detected(tmp_path: Path) -> None:
    """Duplicate YAML entries must not be hidden by frozenset conversion."""
    ctx = _ctx_with_config(
        tmp_path,
        (
            "activated_directives:\n"
            f"  - {_REAL_DIRECTIVE_ID}\n"
            f"  - {_REAL_DIRECTIVE_ID}\n"
        ),
    )
    report = run_consistency_check(ctx)

    assert report.coherent is False
    assert any("Duplicate entry" in v for v in report.kind_violations)


@pytest.mark.doctrine
def test_suggestion_contains_resolution_command(tmp_path: Path) -> None:
    """Suggestion for an unknown ID must contain 'charter deactivate'."""
    fake_id = "totally-fake-directive-zzz"
    ctx = _ctx_with_config(
        tmp_path,
        f"activated_directives:\n  - {fake_id}\n",
    )
    report = run_consistency_check(ctx)

    assert any("charter deactivate" in s for s in report.suggestions), (
        f"Expected a suggestion containing 'charter deactivate' but got: "
        f"{report.suggestions}"
    )


@pytest.mark.doctrine
def test_none_kind_skipped(tmp_path: Path) -> None:
    """When a kind has no config key (None state), it is skipped silently.

    No 'directive/' entries should appear in unknown_references when
    activated_directives is absent from config.yaml.
    """
    # Config with no activated_directives key at all.
    ctx = _ctx_with_config(tmp_path, "# no activation keys\n")
    report = run_consistency_check(ctx)

    assert not any(
        ref.startswith("directive/") for ref in report.unknown_references
    ), (
        f"Expected no directive/ unknown_references but got: "
        f"{report.unknown_references}"
    )


@pytest.mark.doctrine
def test_coherent_false_when_incoherent(tmp_path: Path) -> None:
    """Any planted unknown ID → coherent is False."""
    ctx = _ctx_with_config(
        tmp_path,
        "activated_directives:\n  - totally-fake-id-xyz\n",
    )
    report = run_consistency_check(ctx)

    assert report.coherent is False


@pytest.mark.doctrine
def test_run_consistency_check_returns_report_object(tmp_path: Path) -> None:
    """Return type is ConsistencyReport with correct field types."""
    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")
    report = run_consistency_check(ctx)

    assert isinstance(report, ConsistencyReport)
    assert isinstance(report.coherent, bool)
    assert isinstance(report.unknown_references, list)
    assert isinstance(report.missing_from_doctrine, list)
    assert isinstance(report.kind_violations, list)
    assert isinstance(report.suggestions, list)


@pytest.mark.doctrine
def test_no_activation_keys_skips_doctrine_scan(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A minimal project has no IDs to validate, so it must not scan doctrine."""
    import charter.activation.consistency_check as consistency_check

    ctx = _ctx_with_config_no_activation_keys(tmp_path, "# minimal valid project\n")

    def fail_scan(*_args: object, **_kwargs: object) -> dict[str, frozenset[str]]:
        raise AssertionError("doctrine scan should not run without activation keys")

    monkeypatch.setattr(consistency_check, "_collect_all_doctrine_ids", fail_scan)

    report = run_consistency_check(ctx)

    assert report.coherent is True
    assert report.unknown_references == []


@pytest.mark.doctrine
@pytest.mark.timing
# NFR-003 perf guard, routed to the serial `-m timing` gate (2026-08-07, PR
# #3246 landing fold). ``run_consistency_check`` is pure in-process work,
# nominal ~1.2s wall locally. Earlier revisions of this test lived in the
# parallel ``fast-tests-charter`` shard (`-n auto`), where the dominant flake
# source was CACHE CONTENTION: ~4 xdist workers on a 4-vCPU runner thrash the
# shared L2/L3, so this memory-touching check's measured time inflated to
# ~4.8s and tripped every absolute budget (and even a CPU-calibration ratio,
# because a register-bound calibration does not track a memory-bound workload
# under cache pressure). Marking it ``timing`` moves it to the dedicated
# ``timing-nfr-serial`` job (``-m timing -n0``), which runs one test at a time
# with the whole cache available -- restoring the ~1.2s nominal and letting a
# simple wall-clock budget be both stable and meaningful. The 3.0s ceiling is
# ~2.5x nominal: headroom for the 4-vCPU runner's single-thread speed while a
# genuine algorithmic regression still trips it. (Not a #3246 regression:
# nominal is identical on this branch and upstream/main's charter sources.)
def test_run_consistency_check_completes_within_budget(tmp_path: Path) -> None:
    """NFR-003: consistency check against the built-in doctrine stays fast.

    Runs in the serial ``timing-nfr-serial`` gate (no parallel cache
    contention), so a plain wall-clock budget is stable; ~1.2s nominal.
    """
    ctx = _ctx_with_config(tmp_path, "# minimal valid project\n")

    start = time.perf_counter()
    run_consistency_check(ctx)
    elapsed = time.perf_counter() - start

    assert elapsed < 3.0, (
        f"consistency check took {elapsed:.2f}s (limit: 3s; nominal ~1.2s, "
        "serial timing gate)"
    )
