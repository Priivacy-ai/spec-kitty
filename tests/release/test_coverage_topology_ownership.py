"""FR-006 coverage-topology emit-consume ownership guard.

Mission ``ci-topology-shrink-01KWQAVX`` WP05. Every CI job that *emits* a
``coverage-*.xml`` report must have that report *consumed* by the coverage
aggregator by construction — never by convention, never by memory. The
aggregator (``diff-coverage`` / ``sonarcloud``) consumes reports in two glob
steps: it ``actions/download-artifact``s every artifact whose *name* matches a
``pattern:`` glob (today ``*-reports``), then ``find``s every downloaded file
whose *name* matches a shell glob (today ``coverage-*.xml``). A shard that
uploads its report under a name outside the download glob, or writes a report
filename outside the ``find`` glob, is silently dropped from coverage with no
red — an invisible coverage hole exactly of the kind mission
``ci-topology-shrink`` exists to close.

This is a *distinct* silent-drop vector from WP02's C-005 needs-list membership
guard (``tests/architectural/test_coverage_consumer_needs.py``). That guard asks
"is the emitter in the aggregator's ``needs:`` list so the aggregator waits for
it?"; this guard asks "does the aggregator's download/``find`` wildcard actually
pick up the emitter's uploaded report file?". A job can sit in the aggregator's
``needs:`` yet still upload under a non-matching artifact name (or write a
non-matching filename), and vice versa — the two invariants are independent, so
both are required to make coverage drops impossible.

The coverage-emitting job set is cross-validated against the reused workflow
model in ``tests.architectural._gate_coverage`` (its public ``cov_targets``
relation): every emitter this guard detects is a model-recognised coverage job.
The step-level artifact detail the model deliberately does not carry (upload
artifact names, ``--cov-report=xml:`` filenames, the aggregator's download
``pattern`` and ``find`` glob) is read through a structured ``yaml.safe_load`` of
the same workflow file — the identical structured parse the model itself uses,
not a regex hand-parse of raw YAML text. The consumer globs are discovered live
from the aggregator's own steps, so the guard tracks the real aggregator instead
of a hand-maintained mirror.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
import yaml

from tests.architectural import _gate_coverage as gc

pytestmark = [pytest.mark.fast]

_CI_QUALITY_PATH = gc.WORKFLOWS_DIR / "ci-quality.yml"
_CI_QUALITY_KEY = "ci-quality.yml"

# GitHub Actions ``${{ ... }}`` interpolations (e.g. ``${{ matrix.shard }}``)
# collapse to a single lowercase placeholder so a matrix report filename such as
# ``coverage-arch-adversarial-${{ matrix.shard }}.xml`` is checked statically as
# ``coverage-arch-adversarial-x.xml`` (still inside ``coverage-*.xml``), and its
# upload ``arch-adversarial-${{ matrix.shard }}-reports`` as
# ``arch-adversarial-x-reports`` (still inside ``*-reports``).
_GHA_EXPR_RE = re.compile(r"\$\{\{.*?\}\}")
_COV_REPORT_XML_RE = re.compile(r"--cov-report=xml:(\S+\.xml)")
_FIND_NAME_RE = re.compile(r"-name\s+'([^']+)'")

_UPLOAD_ARTIFACT_PREFIX = "actions/upload-artifact"
_DOWNLOAD_ARTIFACT_PREFIX = "actions/download-artifact"

# Named emitters the shrink topology must keep consumed — pins the guard against
# a vacuous green if the parse regexes ever stop matching (a count would be
# brittle to benign workflow growth; these behavioural anchors are not). The
# de-serialised ``arch-adversarial`` pole (WP03) is included by name because
# FR-006 specifically requires its ``coverage-arch-adversarial-*.xml`` to be
# glob-consumed by the aggregator.
_REQUIRED_EMITTER_JOBS = frozenset(
    {
        "kernel-tests",
        "fast-tests-core-misc",
        "integration-tests-core-misc",
        "arch-adversarial",
    },
)


def _normalize_gha(text: str) -> str:
    """Replace every ``${{ ... }}`` interpolation with a static placeholder."""
    return _GHA_EXPR_RE.sub("x", text)


@dataclass(frozen=True)
class CoverageEmitter:
    """One CI job that writes ``coverage-*.xml`` report(s) and uploads them.

    ``report_filenames`` and ``upload_names`` are GHA-normalised: ``${{ ... }}``
    interpolations are collapsed to a static placeholder so matrix shards are
    checked by their static shape.
    """

    job: str
    report_filenames: tuple[str, ...]
    upload_names: tuple[str, ...]


@dataclass(frozen=True)
class CoverageTopology:
    """Emit/consume relation surface of the coverage aggregation pipeline."""

    emitters: tuple[CoverageEmitter, ...]
    download_name_globs: tuple[str, ...]
    report_file_globs: tuple[str, ...]


def _steps(job: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the structured ``steps`` mappings of a parsed workflow job."""
    return [step for step in job.get("steps") or [] if isinstance(step, dict)]


def _step_run_text(job: dict[str, Any]) -> str:
    """Join a job's ``run:`` script blocks (mirrors the model's run-text read).

    Kept as a local structured-dict traversal rather than importing the model's
    private ``_job_run_text`` helper, so this file stays clean under ruff's
    ``SLF001`` (private-member access) while performing the identical join.
    """
    return "\n".join(
        str(step["run"]) for step in _steps(job) if "run" in step
    )


def _emitter_upload_names(job: dict[str, Any]) -> tuple[str, ...]:
    """Return GHA-normalised ``actions/upload-artifact`` names for a job."""
    names: list[str] = []
    for step in _steps(job):
        if not str(step.get("uses", "")).startswith(_UPLOAD_ARTIFACT_PREFIX):
            continue
        name = (step.get("with") or {}).get("name")
        if name is not None:
            names.append(_normalize_gha(str(name)))
    return tuple(names)


def _emitted_report_filenames(job: dict[str, Any]) -> tuple[str, ...]:
    """Return GHA-normalised ``--cov-report=xml:`` report basenames for a job."""
    run_text = _normalize_gha(_step_run_text(job))
    return tuple(Path(match).name for match in _COV_REPORT_XML_RE.findall(run_text))


def _discover_download_name_globs(jobs: dict[str, Any]) -> tuple[str, ...]:
    """Collect every aggregator ``download-artifact`` ``pattern:`` glob."""
    globs: list[str] = []
    for job in jobs.values():
        for step in _steps(job):
            if not str(step.get("uses", "")).startswith(_DOWNLOAD_ARTIFACT_PREFIX):
                continue
            pattern = (step.get("with") or {}).get("pattern")
            if pattern is not None and str(pattern) not in globs:
                globs.append(str(pattern))
    return tuple(globs)


def _discover_report_file_globs(jobs: dict[str, Any]) -> tuple[str, ...]:
    """Collect every aggregator ``find -name`` coverage-report glob."""
    globs: list[str] = []
    for job in jobs.values():
        for step in _steps(job):
            run = step.get("run")
            if not isinstance(run, str):
                continue
            for glob in _FIND_NAME_RE.findall(run):
                if "coverage" in glob and glob not in globs:
                    globs.append(glob)
    return tuple(globs)


def load_coverage_topology(path: Path = _CI_QUALITY_PATH) -> CoverageTopology:
    """Parse the emit/consume coverage topology out of a workflow file."""
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    jobs: dict[str, Any] = data["jobs"]
    emitters = [
        CoverageEmitter(
            job=name,
            report_filenames=reports,
            upload_names=_emitter_upload_names(job),
        )
        for name, job in jobs.items()
        if (reports := _emitted_report_filenames(job))
    ]
    return CoverageTopology(
        emitters=tuple(emitters),
        download_name_globs=_discover_download_name_globs(jobs),
        report_file_globs=_discover_report_file_globs(jobs),
    )


def unconsumed_emitters(topology: CoverageTopology) -> list[str]:
    """Return one violation message per emitter the aggregator would drop.

    An emitter is *consumed* iff at least one of its upload artifact names is
    matched by a download-``pattern`` glob (so the aggregator downloads it) AND
    every emitted report filename is matched by a ``find`` glob (so the
    aggregator collects the file once downloaded). Either miss is a silent
    coverage drop and yields a violation.
    """
    violations: list[str] = []
    for emitter in topology.emitters:
        name_consumed = any(
            fnmatch.fnmatch(name, glob)
            for name in emitter.upload_names
            for glob in topology.download_name_globs
        )
        if not name_consumed:
            violations.append(
                f"{emitter.job}: upload names {emitter.upload_names or ()} match no "
                f"aggregator download glob {topology.download_name_globs}",
            )
        violations.extend(
            f"{emitter.job}: report {report!r} matches no aggregator "
            f"consume glob {topology.report_file_globs}"
            for report in emitter.report_filenames
            if not any(
                fnmatch.fnmatch(report, glob) for glob in topology.report_file_globs
            )
        )
    return violations


@pytest.fixture(scope="module")
def topology() -> CoverageTopology:
    """Load the live ``ci-quality.yml`` coverage emit/consume topology once."""
    return load_coverage_topology()


def test_aggregator_consumer_globs_are_discovered(
    topology: CoverageTopology,
) -> None:
    """Fail closed if the aggregator's consumer globs were not parsed.

    Without this, an empty ``download_name_globs`` / ``report_file_globs`` would
    make :func:`unconsumed_emitters` vacuously flag everything (or, paired with
    an empty emitter set, vacuously pass). Both globs must be present.
    """
    assert topology.download_name_globs, "no download-artifact pattern glob parsed"
    assert topology.report_file_globs, "no find -name coverage glob parsed"


def test_coverage_emitters_are_present(topology: CoverageTopology) -> None:
    """Fail closed if the emitter parse produced a vacuous (empty) set.

    Pins the named critical emitters (including the de-serialised
    ``arch-adversarial`` pole) so a regex regression that stops matching cannot
    hide behind an empty-set green.
    """
    parsed_jobs = {emitter.job for emitter in topology.emitters}
    missing = sorted(_REQUIRED_EMITTER_JOBS - parsed_jobs)
    assert not missing, f"expected coverage emitters not parsed: {missing}"


def test_detected_emitters_are_model_recognised_coverage_jobs(
    topology: CoverageTopology,
) -> None:
    """Cross-check every emitter against the reused ``_gate_coverage`` model.

    Ties this guard's structured artifact parse to the workflow model's own
    ``cov_targets`` authority: a job that emits a ``coverage-*.xml`` report must
    also be a job the model sees running ``--cov`` coverage.
    """
    model = gc.load_workflow_models()[_CI_QUALITY_KEY]
    coverage_jobs = {job for job, targets in model.cov_targets.items() if targets}
    unrecognised = sorted(
        emitter.job
        for emitter in topology.emitters
        if emitter.job not in coverage_jobs
    )
    assert not unrecognised, (
        "coverage-report emitters not seen as --cov jobs by the gate model: "
        f"{unrecognised}"
    )


def test_every_emitted_coverage_report_is_consumed(
    topology: CoverageTopology,
) -> None:
    """FR-006: every emitted ``coverage-*.xml`` is glob-consumed by construction."""
    violations = unconsumed_emitters(topology)
    assert not violations, (
        "coverage reports emitted but not consumed by the aggregator "
        f"(silent coverage drop): {violations}"
    )


def test_deserialized_arch_pole_report_is_consumed(
    topology: CoverageTopology,
) -> None:
    """FR-006: the WP03 always-on ``arch-adversarial`` pole is glob-consumed.

    The de-serialised architectural pole emits
    ``coverage-arch-adversarial-<shard>.xml`` under
    ``arch-adversarial-<shard>-reports``; both must fall inside the aggregator's
    download/``find`` globs so removing the ``needs`` edge did not orphan its
    coverage.
    """
    arch = next(
        (e for e in topology.emitters if e.job == "arch-adversarial"),
        None,
    )
    assert arch is not None, "arch-adversarial emitter not parsed"
    assert unconsumed_emitters(
        CoverageTopology(
            emitters=(arch,),
            download_name_globs=topology.download_name_globs,
            report_file_globs=topology.report_file_globs,
        ),
    ) == []


def test_guard_reds_when_upload_name_is_outside_download_glob() -> None:
    """RED-negative: an emitter uploaded outside the download glob is flagged.

    A shard emits a valid ``coverage-orphan-d.xml`` but uploads it under
    ``orphan-shard-artifacts`` — outside the aggregator's ``*-reports`` download
    pattern — so the aggregator never downloads it. The guard must red on it
    while leaving the healthy shard alone.
    """
    synthetic = CoverageTopology(
        emitters=(
            CoverageEmitter(
                job="healthy-shard",
                report_filenames=("coverage-healthy.xml",),
                upload_names=("healthy-reports",),
            ),
            CoverageEmitter(
                job="orphan-shard",
                report_filenames=("coverage-orphan-d.xml",),
                upload_names=("orphan-shard-artifacts",),
            ),
        ),
        download_name_globs=("*-reports",),
        report_file_globs=("coverage-*.xml",),
    )
    violations = unconsumed_emitters(synthetic)
    assert any("orphan-shard" in violation for violation in violations)
    assert not any("healthy-shard" in violation for violation in violations)


def test_guard_reds_when_report_filename_is_outside_find_glob() -> None:
    """RED-negative: a report filename outside the ``find`` glob is flagged.

    A shard uploads under a matching ``misnamed-reports`` artifact but writes
    ``cov-orphan-d.xml`` — outside the aggregator's ``coverage-*.xml`` ``find``
    glob — so ``find`` never collects it. The guard must red on it.
    """
    synthetic = CoverageTopology(
        emitters=(
            CoverageEmitter(
                job="misnamed-shard",
                report_filenames=("cov-orphan-d.xml",),
                upload_names=("misnamed-reports",),
            ),
        ),
        download_name_globs=("*-reports",),
        report_file_globs=("coverage-*.xml",),
    )
    violations = unconsumed_emitters(synthetic)
    assert any("misnamed-shard" in violation for violation in violations)
    assert any("cov-orphan-d.xml" in violation for violation in violations)
