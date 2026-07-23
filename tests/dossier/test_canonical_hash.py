"""Acceptance + unit tests for the canonical dossier snapshot hash (WP01).

Executable contract for FR-001, FR-002, FR-003, C-001, C-004, NFR-001 and the
churn-immunity acceptance scenario AS-4 of mission
``dossier-parity-reconciler-01KXYXVP``.

The canonical dossier snapshot hash is the single owning definition:

    sort entries by artifact path
    join ``"{path}\\t{content_hash}"`` lines with newlines
    sha256 the joined bytes (utf-8)
    prefix the hex digest with ``sha256:``

This is byte-identical to the server's
``apps/dossier/materialize.py::_compute_snapshot_hash`` shape (spec-kitty#2180,
cross-repo contract C-003). The per-WP ``content_hash`` input is the normalized
:class:`WPMetadata` static projection (C-004), not raw ``WP##.md`` bytes, so
runtime-mutable churn does not change the hash (FR-002, AS-4).
"""

from __future__ import annotations

import hashlib
import random

import pytest

from specify_cli.dossier.hasher import (
    WP_STATIC_PROJECTION_FIELDS,
    compute_dossier_snapshot_hash,
    hash_wp_static_projection,
    wp_static_projection,
)
from specify_cli.status.wp_metadata import WPMetadata

# Fast pure-function unit tests (mirrors tests/dossier/test_hasher.py) so the
# fast-tests-core-misc CI gate selects this module.
pytestmark = [pytest.mark.unit, pytest.mark.fast]

# ── Fixed golden inputs (structure contract, FR-003) ────────────────────────

GOLDEN_ENTRIES: list[tuple[str, str | None]] = [
    ("plan.md", "hash_plan"),
    ("spec.md", "hash_spec"),
    ("tasks/WP01.md", "hash_wp01"),
]
# Digest independently computed from the canonical definition (see module docstring).
GOLDEN_HASH = "sha256:dfa28d590e97d6eceed4de9c689e86eccd38c0b1c46f2ab7752b8a718000c610"
EMPTY_HASH = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


def _server_shape(entries: list[tuple[str, str | None]]) -> str:
    """Reference re-implementation of the SERVER algorithm, verbatim.

    Mirrors ``spec-kitty-saas apps/dossier/materialize.py::_compute_snapshot_hash``
    exactly so a byte-for-byte comparison proves cross-repo parity (C-003)
    without importing Django.
    """
    lines = "\n".join(f"{path}\t{content_hash or ''}" for path, content_hash in sorted(entries))
    # noqa: TID251 — deliberate verbatim re-implementation of the SERVER's
    # snapshot-hash algorithm (NOT charter freshness hashing); the whole point
    # is to prove byte-identity against an independent copy of the formula.
    return "sha256:" + hashlib.sha256(lines.encode("utf-8")).hexdigest()  # noqa: TID251


def _make_wp(**overrides) -> WPMetadata:
    """Build a WPMetadata carrying both static content and runtime-mutable state."""
    data = {
        "work_package_id": "WP01",
        "title": "Canonical Dossier Snapshot-Hash Definition",
        "dependencies": [],
        "requirement_refs": ["FR-001", "FR-002", "FR-003"],
        "tracker_refs": ["#2180"],
        "owned_files": [
            "src/specify_cli/dossier/hasher.py",
            "src/specify_cli/dossier/indexer.py",
        ],
        "phase": "Phase 1 - Canonical hash foundation",
        "task_type": "implement",
        "subtasks": ["T001", "T002", "T003", "T004", "T005"],
        # Runtime-mutable state that MUST NOT influence the hash:
        "lane": "in_progress",
        "agent": "claude:sonnet:python-pedro:implementer",
        "shell_pid": 2760042,
        "assignee": "someone",
        "review_status": "pending",
        "history": [{"at": "2026-07-20T06:13:30Z", "actor": "system"}],
    }
    data.update(overrides)
    return WPMetadata.model_validate(data)


# ── T002/T003 — canonical hash structure (FR-001, FR-003) ───────────────────


class TestCanonicalSnapshotHashStructure:
    def test_golden_value(self):
        assert compute_dossier_snapshot_hash(GOLDEN_ENTRIES) == GOLDEN_HASH

    def test_has_sha256_prefix_and_64_hex_digest(self):
        result = compute_dossier_snapshot_hash(GOLDEN_ENTRIES)
        assert result.startswith("sha256:")
        digest = result.removeprefix("sha256:")
        assert len(digest) == 64  # golden-count: cardinality-is-contract
        int(digest, 16)  # valid hex or raises

    def test_matches_server_shape_byte_for_byte(self):
        # Randomised entries to prove agreement is real, not incidental (C-003).
        rng = random.Random(2180)
        for _ in range(25):
            entries = [(f"path/{rng.randint(0, 99)}.md", f"h{rng.randint(0, 9999)}") for _ in range(rng.randint(0, 8))]
            assert compute_dossier_snapshot_hash(entries) == _server_shape(entries)

    def test_none_content_hash_treated_as_empty(self):
        # Server uses ``content_hash or ''`` — a None hash must not blow up.
        entries: list[tuple[str, str | None]] = [("a.md", None), ("b.md", "x")]
        assert compute_dossier_snapshot_hash(entries) == _server_shape(entries)

    def test_empty_dossier_is_stable_sentinel(self):
        assert compute_dossier_snapshot_hash([]) == EMPTY_HASH
        assert compute_dossier_snapshot_hash([]) == _server_shape([])


# ── T002 — order independence (FR-001) ──────────────────────────────────────


class TestOrderIndependence:
    def test_shuffled_input_same_hash(self):
        baseline = compute_dossier_snapshot_hash(GOLDEN_ENTRIES)
        rng = random.Random(7)
        for _ in range(20):
            shuffled = list(GOLDEN_ENTRIES)
            rng.shuffle(shuffled)
            assert compute_dossier_snapshot_hash(shuffled) == baseline

    def test_order_independence_is_real_not_incidental(self):
        # A genuinely different content set MUST produce a different hash,
        # otherwise "order independence" would be a trivially-true bug.
        other = [("plan.md", "hash_plan"), ("spec.md", "DIFFERENT")]
        assert compute_dossier_snapshot_hash(other) != compute_dossier_snapshot_hash(GOLDEN_ENTRIES)


# ── T002/T005 — determinism (FR-003, NFR-001) ───────────────────────────────


class TestDeterminism:
    def test_repeated_runs_identical(self):
        results = {compute_dossier_snapshot_hash(GOLDEN_ENTRIES) for _ in range(10)}
        assert len(results) == 1

    def test_100_runs_identical(self):
        # NFR-001: 100% identical hash across >= 100 repeated runs.
        first = compute_dossier_snapshot_hash(GOLDEN_ENTRIES)
        assert all(compute_dossier_snapshot_hash(GOLDEN_ENTRIES) == first for _ in range(100))


# ── T004/T005 — normalized WP static projection (FR-002, C-004, AS-4) ────────


class TestWPStaticProjection:
    def test_projection_shape_is_documented_and_static_only(self):
        meta = _make_wp()
        projection = wp_static_projection(meta)
        assert set(projection) == set(WP_STATIC_PROJECTION_FIELDS)
        # Runtime-mutable fields MUST NOT leak into the hashed projection.
        for runtime_field in (
            "lane",
            "agent",
            "shell_pid",
            "shell_pid_created_at",
            "assignee",
            "history",
            "review_status",
            "reviewed_by",
            "approved_by",
            "reviewer",
            "model",
            "agent_profile",
            "role",
            "base_commit",
        ):
            assert runtime_field not in projection

    def test_projection_hash_is_64_hex(self):
        digest = hash_wp_static_projection(_make_wp())
        assert len(digest) == 64  # golden-count: cardinality-is-contract
        int(digest, 16)

    @pytest.mark.parametrize(
        "runtime_change",
        [
            {"lane": "approved"},
            {"agent": "codex:gpt5:reviewer-rita:reviewer"},
            {"shell_pid": 999999},
            {"assignee": "another-person"},
            {"review_status": "approved"},
            {"approved_by": "alice"},
            {"history": [{"at": "2026-07-21T00:00:00Z", "actor": "claude"}]},
        ],
    )
    def test_churn_immunity_runtime_field_change_does_not_change_hash(self, runtime_change):
        # AS-4: runtime-mutable churn must NOT move the content hash.
        base = _make_wp()
        churned = base.update(**runtime_change)
        assert hash_wp_static_projection(churned) == hash_wp_static_projection(base)

    @pytest.mark.parametrize(
        "content_change",
        [
            {"title": "A different title"},
            {"owned_files": ["src/specify_cli/dossier/hasher.py"]},
            {"dependencies": ["WP00"]},
            {"requirement_refs": ["FR-999"]},
            {"phase": "Phase 2"},
        ],
    )
    def test_canonical_content_change_does_change_hash(self, content_change):
        # The projection must still be content-addressed: a real content edit
        # MUST move the hash, otherwise churn-immunity would be over-broad.
        base = _make_wp()
        edited = base.update(**content_change)
        assert hash_wp_static_projection(edited) != hash_wp_static_projection(base)
