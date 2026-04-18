"""Fixture adapter for deterministic, offline testing.

This module lives under src/ (not tests/) so integration tests can import it,
but it is wired only in test entrypoints. The production CLI never selects it
unless --adapter fixture is passed explicitly (R-0-5).

Fixture layout
--------------
    tests/charter/fixtures/synthesizer/<kind>/<slug>/<short_hash>.<kind>.yaml

where <short_hash> is the first 12 hex chars of the SHA-256 digest computed
by request.compute_inputs_hash() over the normalized SynthesisRequest.

The .<kind>.yaml suffix matches the shipped repository glob so fixtures
round-trip through the same loaders WP02-WP05 use.

On generate(request):
1. Compute expected_path from hash.
2. If fixture present → load YAML, return AdapterOutput (adapter_id="fixture",
   adapter_version=FIXTURE_VERSION, generated_at=deterministic UTC epoch).
3. If absent → raise FixtureAdapterMissingError with expected_path.

See KD-4, R-0-6, data-model.md §E-3.
"""

from __future__ import annotations

from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from collections.abc import Mapping

from ruamel.yaml import YAML

from .adapter import AdapterOutput
from .errors import FixtureAdapterMissingError
from .request import SynthesisRequest, compute_inputs_hash, short_hash

# Pinned version for provenance stamping. Bump when fixture format changes.
FIXTURE_VERSION = "1.0.0"

# Deterministic epoch for generated_at — seeded from hash for uniqueness
# but fully deterministic (NFR-006 / FR-014).
_EPOCH = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _deterministic_generated_at(inputs_hash_hex: str) -> datetime:
    """Return a deterministic UTC datetime derived from the inputs hash.

    The first 8 hex chars (32 bits) are used as a micro-second offset from
    the fixed epoch. This keeps generated_at byte-stable across runs for
    identical inputs while making it unique per fixture (not a constant).
    """
    offset_us = int(inputs_hash_hex[:8], 16)
    from datetime import timedelta
    return _EPOCH + timedelta(microseconds=offset_us)


class FixtureAdapter:
    """Test-only adapter that loads pre-recorded fixture files by content hash.

    Parameters
    ----------
    fixture_root:
        Root directory for fixture files. Defaults to the canonical
        tests/charter/fixtures/synthesizer/ directory (resolved relative to
        this module's package, climbing up to the repo root).
    """

    id: str = "fixture"
    version: str = FIXTURE_VERSION

    def __init__(self, fixture_root: Path | None = None) -> None:
        if fixture_root is None:
            # Resolve canonical fixture root relative to this file's location.
            # src/charter/synthesizer/ -> climb 3 levels -> repo root
            # -> tests/charter/fixtures/synthesizer/
            _here = Path(__file__).parent
            _repo_root = _here.parent.parent.parent
            fixture_root = _repo_root / "tests" / "charter" / "fixtures" / "synthesizer"
        self._fixture_root = fixture_root

    def _fixture_path(self, request: SynthesisRequest) -> Path:
        """Return the expected fixture file path for the given request."""
        full = compute_inputs_hash(request, self.id, self.version)
        shorthash = short_hash(full, 12)
        kind = request.target.kind
        slug = request.target.slug
        return self._fixture_root / kind / slug / f"{shorthash}.{kind}.yaml"

    def generate(self, request: SynthesisRequest) -> AdapterOutput:
        """Load a pre-recorded fixture or raise FixtureAdapterMissingError."""
        expected = self._fixture_path(request)
        full_hash = compute_inputs_hash(request, self.id, self.version)

        if not expected.exists():
            raise FixtureAdapterMissingError(
                expected_path=str(expected),
                kind=request.target.kind,
                slug=request.target.slug,
                inputs_hash=full_hash,
            )

        yaml = YAML()
        yaml.preserve_quotes = True
        with expected.open("r", encoding="utf-8") as fh:
            body: Mapping[str, Any] = yaml.load(fh)

        return AdapterOutput(
            body=body,
            generated_at=_deterministic_generated_at(full_hash),
            adapter_id_override=None,
            adapter_version_override=None,
            notes=f"fixture:{full_hash[:12]}",
        )

    def generate_batch(
        self, requests: list[SynthesisRequest]
    ) -> list[AdapterOutput]:
        """Sequential batch generate (fixture adapter has no batching benefit)."""
        return [self.generate(r) for r in requests]
