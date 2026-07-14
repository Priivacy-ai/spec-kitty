"""Sonar UI-e2e coverage-discovery wiring guard (FR-013, IC-12, #2623).

Mission ``test-suite-friction-remediation-01KXDKBX`` WP17. Single-file
ownership: serialized AFTER ``test_suite_jobs_gate_blocking.py`` (FR-012) on
the same ``.github/workflows/ci-quality.yml`` surface (the plan's IC-11-then-
IC-12 order).

``coverage-ui-e2e.xml`` (``--cov=src/specify_cli/dashboard``) is produced by
the SEPARATE ``ui-e2e.yml`` workflow (mission
``ci-test-topology-performance-01KXBJRT`` WP08) — that file's own header
comment documents, as an explicit known gap, that the ``sonarcloud`` job in
``ci-quality.yml`` only ever discovered artifacts from ITS OWN workflow run
(the ``current`` / ``prev_run``-fallback download-artifact steps are both
scoped to ``workflow_id: 'ci-quality.yml'``), so the ui-e2e dashboard coverage
never reached Sonar's denominator. This WP wires a THIRD, cross-workflow
discovery tier into the ``sonarcloud`` job: a ``github-script`` step resolves
the most recent **successful** ``ui-e2e.yml`` run for the **same head SHA**
this sonarcloud run is analyzing, a ``download-artifact`` step fetches that
run's ``ui-e2e-coverage-reports`` artifact, and the existing "Discover
coverage XMLs" step's ``find ... -name 'coverage-*.xml'`` sweep is extended to
also scan that download directory.

IC-12 is verifiable only POST-MERGE (a live SonarCloud run, gated on
``secrets.SONAR_TOKEN`` and the ``schedule``/``workflow_dispatch`` trigger) —
this module is the PRE-MERGE proxy the plan requires it be paired with: it
statically parses the committed workflow YAML (never re-typing the shell
logic as a literal string-equality copy — C-002) and asserts the wiring is
present and internally consistent, so the artifact path cannot silently rot
out of the discovery sweep between here and a real Sonar run.
"""

from __future__ import annotations

import re
from typing import cast

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.architectural]

_CI_QUALITY = gc.WORKFLOWS_DIR / "ci-quality.yml"
_UI_E2E = gc.WORKFLOWS_DIR / "ui-e2e.yml"
_SONARCLOUD_JOB = "sonarcloud"
_UI_E2E_JOB = "ui-e2e"
_UI_E2E_WORKFLOW_FILE = "ui-e2e.yml"
_UI_E2E_ARTIFACT_NAME = "ui-e2e-coverage-reports"
_DISCOVERY_STEP_NAME = "[ENFORCED] Discover coverage XMLs and build Sonar config"
_DOWNLOAD_ARTIFACT_ACTION = "actions/download-artifact"
_UPLOAD_ARTIFACT_ACTION = "actions/upload-artifact"

# ``find <dir> -name 'coverage-*.xml'`` — the discovery step's directory scan.
_FIND_DIR_RE = re.compile(r"find\s+(\S+)\s+-name\s+'coverage-\*\.xml'")


# ---------------------------------------------------------------------------
# Pure parsing helpers (the fault-injection substrate — no I/O).
# ---------------------------------------------------------------------------


def discovery_scanned_dirs(discovery_step_run: str) -> frozenset[str]:
    """Directories the 'Discover coverage XMLs' step globs for ``coverage-*.xml``."""
    return frozenset(_FIND_DIR_RE.findall(discovery_step_run))


def _steps_using(job: dict[str, object], action_prefix: str) -> list[dict[str, object]]:
    steps = job.get("steps")
    if not isinstance(steps, list):
        return []
    return [
        step
        for step in steps
        if isinstance(step, dict) and str(step.get("uses", "")).startswith(action_prefix)
    ]


def ui_e2e_artifact_download_dir(job: dict[str, object]) -> str | None:
    """The local ``path`` a download-artifact step writes the ui-e2e artifact to.

    Matched on the artifact's exact ``name`` (not merely a directory-name
    guess) so a step downloading some OTHER artifact into a similarly-named
    directory would not be mistaken for the real wiring.
    """
    for step in _steps_using(job, _DOWNLOAD_ARTIFACT_ACTION):
        with_block = step.get("with")
        if not isinstance(with_block, dict):
            continue
        if with_block.get("name") == _UI_E2E_ARTIFACT_NAME:
            path = with_block.get("path")
            return str(path) if path is not None else None
    return None


def cross_workflow_run_lookup_is_head_sha_keyed(job: dict[str, object]) -> bool:
    """A ``github-script`` step resolves a ``ui-e2e.yml`` run keyed to the head SHA.

    Both substrings must appear in the SAME step's script: a step that merely
    mentions ``ui-e2e.yml`` elsewhere (e.g. a comment in an unrelated step)
    must not satisfy this — mirrors the "anchor on the real token, not a
    stray mention" discipline the sibling FR-012 guard applies to ``pytest``.
    """
    steps = job.get("steps")
    if not isinstance(steps, list):
        return False
    for step in steps:
        if not isinstance(step, dict):
            continue
        with_block = step.get("with")
        script = str((with_block or {}).get("script") or "") if isinstance(with_block, dict) else ""
        if _UI_E2E_WORKFLOW_FILE in script and "head_sha" in script:
            return True
    return False


def _run_text_of(job: dict[str, object], step_name: str) -> str:
    steps = job.get("steps")
    if isinstance(steps, list):
        for step in steps:
            if isinstance(step, dict) and step.get("name") == step_name and "run" in step:
                return str(step["run"])
    raise AssertionError(f"step {step_name!r} not found")


def uploaded_artifact_basename(ui_e2e_job: dict[str, object]) -> str | None:
    """The file ``ui-e2e.yml``'s own upload step publishes (basename only)."""
    for step in _steps_using(ui_e2e_job, _UPLOAD_ARTIFACT_ACTION):
        with_block = step.get("with")
        if not isinstance(with_block, dict):
            continue
        path = with_block.get("path")
        if isinstance(path, str) and path:
            return path.rsplit("/", 1)[-1]
    return None


# ---------------------------------------------------------------------------
# Live fixtures.
# ---------------------------------------------------------------------------


def _sonarcloud_job() -> dict[str, object]:
    data = yaml.safe_load(_CI_QUALITY.read_text(encoding="utf-8"))
    return cast("dict[str, object]", data["jobs"][_SONARCLOUD_JOB])


def _ui_e2e_job() -> dict[str, object]:
    data = yaml.safe_load(_UI_E2E.read_text(encoding="utf-8"))
    return cast("dict[str, object]", data["jobs"][_UI_E2E_JOB])


# ---------------------------------------------------------------------------
# Live assertions.
# ---------------------------------------------------------------------------


def test_ui_e2e_artifact_is_downloaded_cross_workflow_live() -> None:
    """FR-013: a download-artifact step fetches ``ui-e2e-coverage-reports``."""
    download_dir = ui_e2e_artifact_download_dir(_sonarcloud_job())
    assert download_dir is not None, (
        f"no download-artifact step in {_SONARCLOUD_JOB!r} targets "
        f"{_UI_E2E_ARTIFACT_NAME!r} (the ui-e2e.yml-produced coverage artifact)"
    )


def test_ui_e2e_run_lookup_is_head_sha_keyed_live() -> None:
    """FR-013: the cross-workflow run resolution is keyed to the head SHA."""
    assert cross_workflow_run_lookup_is_head_sha_keyed(_sonarcloud_job()), (
        "no github-script step resolves a ui-e2e.yml run keyed to the head SHA "
        "(expected 'ui-e2e.yml' and 'head_sha' in the same step's script)"
    )


def test_coverage_ui_e2e_xml_is_in_discovered_set_live() -> None:
    """FR-013 / IC-12: ``coverage-ui-e2e.xml`` is a member of the discovered set.

    Models the 'Discover coverage XMLs' step's directory scan (parsed, not
    literal-copied) and asserts the ui-e2e artifact's local download directory
    is one of the scanned directories, AND that ``ui-e2e.yml``'s own upload
    step publishes a file whose basename matches the ``coverage-*.xml`` glob
    the discovery step applies — so the sweep will actually pick up
    ``coverage-ui-e2e.xml`` rather than silently missing it on a filename
    drift in either workflow.
    """
    sonarcloud = _sonarcloud_job()
    discovery_run = _run_text_of(sonarcloud, _DISCOVERY_STEP_NAME)
    scanned_dirs = discovery_scanned_dirs(discovery_run)

    download_dir = ui_e2e_artifact_download_dir(sonarcloud)
    assert download_dir is not None
    assert download_dir in scanned_dirs, (
        f"ui-e2e artifact download dir {download_dir!r} is not scanned by the "
        f"'{_DISCOVERY_STEP_NAME}' step (scanned dirs: {sorted(scanned_dirs)}) — "
        "coverage-ui-e2e.xml would silently rot out of Sonar's denominator"
    )

    uploaded_basename = uploaded_artifact_basename(_ui_e2e_job())
    assert uploaded_basename == "coverage-ui-e2e.xml", (
        f"ui-e2e.yml's own upload step publishes {uploaded_basename!r}, not "
        "'coverage-ui-e2e.xml' — the discovery glob and the producer have drifted"
    )
    assert re.fullmatch(r"coverage-.*\.xml", uploaded_basename), (
        f"{uploaded_basename!r} does not match the discovery step's own "
        "'coverage-*.xml' glob"
    )


# ---------------------------------------------------------------------------
# Fault-injection (pure — no I/O — proving each relation actually bites).
# ---------------------------------------------------------------------------


def test_faultinjection_download_dir_not_scanned_reds() -> None:
    """A download dir the discovery step never globs is NOT in the scanned set."""
    discovery_run = (
        "declare -A seen_reports\n"
        "find out/reports/artifacts/current -name 'coverage-*.xml' -print0\n"
        "find out/reports/artifacts/fallback -name 'coverage-*.xml' -print0\n"
    )
    scanned = discovery_scanned_dirs(discovery_run)
    assert scanned == {"out/reports/artifacts/current", "out/reports/artifacts/fallback"}
    assert "out/reports/artifacts/ui-e2e" not in scanned


def test_faultinjection_missing_download_step_is_none() -> None:
    """No download-artifact step targeting the ui-e2e artifact -> ``None``."""
    job_without_wiring: dict[str, object] = {
        "steps": [
            {
                "uses": "actions/download-artifact@v8",
                "with": {"name": "some-other-reports", "path": "out/reports/artifacts/other"},
            },
        ],
    }
    assert ui_e2e_artifact_download_dir(job_without_wiring) is None


def test_faultinjection_run_lookup_without_head_sha_is_not_keyed() -> None:
    """A script mentioning ui-e2e.yml but never keying on head_sha is REJECTED."""
    job_unkeyed: dict[str, object] = {
        "steps": [
            {
                "uses": "actions/github-script@v9",
                "with": {
                    "script": (
                        "const { data } = await github.rest.actions.listWorkflowRuns("
                        "{ workflow_id: 'ui-e2e.yml', per_page: 10 });"
                    ),
                },
            },
        ],
    }
    assert not cross_workflow_run_lookup_is_head_sha_keyed(job_unkeyed)


def test_faultinjection_uploaded_basename_mismatch_is_caught() -> None:
    """A producer publishing a differently-named file is NOT silently accepted."""
    drifted_job: dict[str, object] = {
        "steps": [
            {
                "uses": "actions/upload-artifact@v4",
                "with": {"name": "ui-e2e-coverage-reports", "path": "out/reports/coverage/renamed.xml"},
            },
        ],
    }
    assert uploaded_artifact_basename(drifted_job) == "renamed.xml"
    assert uploaded_artifact_basename(drifted_job) != "coverage-ui-e2e.xml"
