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
guard (formerly ``tests/architectural/test_coverage_consumer_needs.py``, retired
per planning#57 alongside the deleted ``ci-quality.yml`` it asserted against).
That guard asked "is the emitter in the aggregator's ``needs:`` list so the
aggregator waits for it?"; this guard asks "does the aggregator's
download/``find`` wildcard actually pick up the emitter's uploaded report
file?". A job can sit in the aggregator's ``needs:`` yet still upload under a
non-matching artifact name (or write a non-matching filename), and vice versa —
the two invariants were independent, so both were required to make coverage
drops impossible.

The coverage-emitting job set was cross-validated against the reused workflow
model in ``tests.architectural._gate_coverage`` (its public ``cov_targets``
relation): every emitter this guard detected was a model-recognised coverage
job. The step-level artifact detail the model deliberately does not carry
(upload artifact names, ``--cov-report=xml:`` filenames, the aggregator's
download ``pattern`` and ``find`` glob) was read through the model's own
``load_spliced_workflow`` reader of the same workflow file.

Retired (planning#57): the LIVE half of this guard (``load_coverage_topology``
and its ``_steps``/``_step_run_text``/``_emitter_upload_names``/
``_emitted_report_filenames``/``_discover_download_name_globs``/
``_discover_report_file_globs``/``_normalize_gha`` parse helpers, plus the six
``test_*`` functions that consumed the module-scoped ``topology`` fixture)
asserted FR-006 against the real ``.github/workflows/ci-quality.yml`` — the
leftover pre-programme GitHub Actions YAML deleted per PROGRAM.md §2. With no
workflow YAML left to parse, that half has no remaining subject matter and was
removed with the file. ``unconsumed_emitters`` — the pure emit/consume relation
— never read a real workflow; it stays, exercised only by the two RED-negative
fault-injection tests below, which build their own synthetic
``CoverageTopology``/``CoverageEmitter`` objects and prove the relation still
catches an unconsumed upload name and an unconsumed report filename.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

import pytest

pytestmark = [pytest.mark.fast]


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
