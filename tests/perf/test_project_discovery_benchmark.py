"""Scaled-down guard for ``scripts/benchmarks/bench_project_discovery.py`` (T053 / NFR-006).

Runs the real benchmark at a small scale (10 stores, 20 warm scans, 3 cold
subprocesses) and asserts its *shape*:

* raw-sample JSON schema completeness (every percentile recomputable from the
  retained raw samples),
* runtime metadata fields present (OS, filesystem, storage hint, CPU, Python,
  SQLite, git commit, seed),
* the zero-denied-payload-open correctness gate is actually enforced (a real
  payload read against a denied store trips it — no mocked violation),
* store generation is deterministic for a seed.

Deliberately asserts NO wall-clock threshold: the timing gates are local-SSD
release gates documented in the script (warm p95 <= 500 ms, process-cold
p95 <= 1 s; CI timing advisory only), and a threshold here would be a flake
generator — see ``docs/development/testing/testing-flakiness.md``.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path
from types import ModuleType
from typing import Any, cast

import pytest

pytestmark = [pytest.mark.slow]

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "scripts" / "benchmarks" / "bench_project_discovery.py"

_SCALED_SEED = 20260812
_SCALED_STORES = 10
_SCALED_AUTHORITY_READS = 2
_SCALED_DENIED = _SCALED_STORES - _SCALED_AUTHORITY_READS
_SCALED_WARM_SCANS = 20
_SCALED_COLD_PROCESSES = 3

#: One benchmark run shared by the schema/metadata/correctness assertions below
#: (xdist ``--dist loadfile`` keeps this file on a single worker).
_REPORT_CACHE: dict[str, dict[str, Any]] = {}


@pytest.fixture(scope="module")
def bench() -> ModuleType:
    """Import the benchmark script by path (scripts/ is not a package)."""
    spec = importlib.util.spec_from_file_location("bench_project_discovery", _SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # The script's dataclasses resolve string annotations (PEP 563) through
    # sys.modules[cls.__module__]; exec without registration breaks them.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(spec.name, None)
        raise
    return module


@pytest.fixture
def scaled_report(
    bench: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, Any]:
    """Run the scaled-down benchmark once; reuse the report across tests."""
    if "report" not in _REPORT_CACHE:
        home = tmp_path / "home"
        home.mkdir(parents=True)
        monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
        _REPORT_CACHE["report"] = cast(
            "dict[str, Any]",
            bench.run_benchmark(
                home=home,
                seed=_SCALED_SEED,
                store_count=_SCALED_STORES,
                authority_read_count=_SCALED_AUTHORITY_READS,
                warm_scan_count=_SCALED_WARM_SCANS,
                cold_process_count=_SCALED_COLD_PROCESSES,
                storage_hint="test-fixture",
            ),
        )
    return _REPORT_CACHE["report"]


# --------------------------------------------------------------------------- #
# Deterministic generation                                                     #
# --------------------------------------------------------------------------- #


def test_project_specs_are_deterministic_for_a_seed(bench: ModuleType) -> None:
    """The same seed must always derive the same UUIDs and role assignment."""
    first = bench.build_project_specs(seed=7, store_count=_SCALED_STORES, authority_read_count=_SCALED_AUTHORITY_READS)
    second = bench.build_project_specs(seed=7, store_count=_SCALED_STORES, authority_read_count=_SCALED_AUTHORITY_READS)
    other_seed = bench.build_project_specs(seed=8, store_count=_SCALED_STORES, authority_read_count=_SCALED_AUTHORITY_READS)

    assert first == second, "identical seeds must derive identical populations"
    assert first != other_seed, "a different seed must derive a different population"
    roles = [spec.role for spec in first]
    assert roles.count(bench.ROLE_DENIED_HINT) == _SCALED_DENIED
    assert roles.count(bench.ROLE_AUTHORITY_READ) == _SCALED_AUTHORITY_READS
    assert len({spec.project_uuid for spec in first}) == _SCALED_STORES, "every project needs a distinct UUID"


def test_generated_stores_match_the_specs_on_disk(
    bench: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Materialization must produce exactly the seeded stores and deny hints."""
    home = tmp_path / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    specs = bench.build_project_specs(seed=11, store_count=3, authority_read_count=1)
    denied_paths = bench.generate_stores(specs)

    denied_specs = [spec for spec in specs if spec.role == bench.ROLE_DENIED_HINT]
    hint_dir = home / "projects" / ".deny-hints"
    hint_names = sorted(path.name for path in hint_dir.iterdir())
    assert hint_names == sorted(f"{spec.project_uuid}.json" for spec in denied_specs), "deny hints must exist for exactly the denied projects"
    for spec in specs:
        database = home / "projects" / spec.project_uuid / "sync" / "sync.db"
        assert database.is_file(), f"store missing for {spec.project_uuid} ({spec.role})"
    assert denied_paths == frozenset(str(home / "projects" / spec.project_uuid / "sync" / "sync.db") for spec in denied_specs)


# --------------------------------------------------------------------------- #
# Raw-sample schema and metadata completeness                                  #
# --------------------------------------------------------------------------- #


def test_report_retains_raw_samples_with_recomputable_percentiles(
    bench: ModuleType,
    scaled_report: dict[str, Any],
) -> None:
    """NFR-006 forbids derived-only numbers: raw samples must be retained."""
    warm = scaled_report["warm"]
    cold = scaled_report["cold"]

    assert len(warm["samples_ms"]) == _SCALED_WARM_SCANS
    assert len(cold["samples_ms"]) == _SCALED_COLD_PROCESSES
    assert len(cold["subprocess_wall_ms"]) == _SCALED_COLD_PROCESSES
    for section in (warm, cold):
        assert all(isinstance(sample, float) and sample > 0.0 for sample in section["samples_ms"])
        assert section["sample_count"] == len(section["samples_ms"])
        # Every derived figure must be recomputable from the retained raws.
        assert section["p95_ms"] == bench.percentile(section["samples_ms"], 0.95)
        assert section["p50_ms"] == bench.percentile(section["samples_ms"], 0.50)
        assert section["min_ms"] == min(section["samples_ms"])
        assert section["max_ms"] == max(section["samples_ms"])
    assert "OS page cache is NOT evicted" in cold["note"], "the cold phase must not claim OS-cache eviction"


def test_report_carries_complete_runtime_metadata(scaled_report: dict[str, Any]) -> None:
    """Raw samples are meaningless without the environment that produced them."""
    runtime = scaled_report["runtime"]
    for key in ("os", "filesystem", "storage_hint", "python", "sqlite", "git_commit", "seed"):
        assert key in runtime, f"runtime metadata is missing {key!r}"
        assert runtime[key] not in ("", None), f"runtime metadata field {key!r} is empty"
    assert runtime["storage_hint"] == "test-fixture"
    assert runtime["seed"] == _SCALED_SEED
    cpu = runtime["cpu"]
    assert cpu["machine"], "CPU machine field is empty"
    assert cpu["logical_cores"] >= 1

    config = scaled_report["config"]
    assert config["store_count"] == _SCALED_STORES
    assert config["denied_hint_count"] == _SCALED_DENIED
    assert config["authority_read_count"] == _SCALED_AUTHORITY_READS
    assert scaled_report["schema_version"] == 1
    assert scaled_report["generated_at"]


def test_report_documents_local_ssd_release_gates_as_advisory_on_ci(
    scaled_report: dict[str, Any],
) -> None:
    """The 500 ms / 1 s gates are release-machine gates, never CI assertions."""
    gates = scaled_report["release_gates"]
    assert gates["warm_p95_gate_ms"] == 500.0
    assert gates["cold_p95_gate_ms"] == 1000.0
    assert "advisory" in gates["scope"], "the gate scope must state that CI timing is advisory"
    assert "local" in gates["scope"].lower(), "the gate scope must name the local-SSD profile"


# --------------------------------------------------------------------------- #
# Correctness gate: zero payload-table opens for denied projects               #
# --------------------------------------------------------------------------- #


def test_scaled_run_passes_the_zero_denied_payload_open_gate(
    scaled_report: dict[str, Any],
) -> None:
    """The measured scans must never have read a denied project's payload."""
    correctness = scaled_report["correctness"]
    assert correctness["passed"] is True
    assert correctness["denied_payload_table_opens"] == 0
    assert correctness["denied_project_count"] == _SCALED_DENIED
    # The warm phase must have used the hints: denied stores stay closed.
    assert correctness["warm_denied_store_connections"] == 0
    # The cold workers legitimately re-read authority for every store (FR-011),
    # so denied-store *connections* are expected there — payload opens are not.
    assert correctness["cold_denied_store_connections"] > 0


def test_correctness_gate_trips_on_a_real_denied_payload_read(
    bench: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A genuine payload-table read against a denied store must fail the run."""
    home = tmp_path / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    specs = bench.build_project_specs(seed=13, store_count=2, authority_read_count=0)
    denied_paths = bench.generate_stores(specs)
    violated_path = sorted(denied_paths)[0]

    with bench.denied_payload_guard(denied_paths) as log:
        connection = sqlite3.connect(violated_path)
        try:
            connection.execute("SELECT COUNT(*) FROM journal_entries").fetchone()
        finally:
            connection.close()

    assert log.connections == 1
    assert len(log.payload_statements) == 1
    with pytest.raises(bench.BenchmarkCorrectnessError):
        bench.enforce_zero_denied_payload_opens(log.payload_statements)


def test_guard_ignores_authority_reads_on_denied_stores(
    bench: ModuleType,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FR-011 allows authority re-reads on denied stores; only payload is banned."""
    home = tmp_path / "home"
    home.mkdir(parents=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))

    specs = bench.build_project_specs(seed=17, store_count=1, authority_read_count=0)
    denied_paths = bench.generate_stores(specs)

    with bench.denied_payload_guard(denied_paths) as log:
        connection = sqlite3.connect(sorted(denied_paths)[0])
        try:
            connection.execute("SELECT state FROM project_consent_decisions").fetchall()
        finally:
            connection.close()

    assert log.connections == 1
    assert log.payload_statements == []
    bench.enforce_zero_denied_payload_opens(log.payload_statements)  # must not raise
