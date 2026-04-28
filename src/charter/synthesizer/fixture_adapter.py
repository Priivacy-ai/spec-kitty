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

Auto-stub mode (test affordance)
--------------------------------
When the environment variable ``SPEC_KITTY_FIXTURE_AUTO_STUB`` is set to
``"1"``, the adapter substitutes a deterministic minimal stub artifact body
(matching the target's Pydantic schema) for any missing fixture instead of
raising. This is a test-only affordance for E2E flows that need the write
pipeline to materialize real on-disk artifacts but don't care about the
semantic content. See research.md R2 (charter-e2e-hardening-tranche-2)
for the full justification.

See KD-4, R-0-6, data-model.md §E-3.
"""

from __future__ import annotations

import os
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
        """Load a pre-recorded fixture or raise FixtureAdapterMissingError.

        When ``SPEC_KITTY_FIXTURE_AUTO_STUB=1`` is set in the environment and
        the keyed fixture is missing, return a deterministic schema-valid stub
        instead of raising. See module docstring for the full rationale.
        """
        expected = self._fixture_path(request)
        full_hash = compute_inputs_hash(request, self.id, self.version)

        if not expected.exists():
            if os.environ.get("SPEC_KITTY_FIXTURE_AUTO_STUB") == "1":
                return self._build_stub_output(request, full_hash)
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

    def _build_stub_output(
        self, request: SynthesisRequest, full_hash: str
    ) -> AdapterOutput:
        """Return a deterministic schema-valid stub AdapterOutput.

        Used only when ``SPEC_KITTY_FIXTURE_AUTO_STUB=1`` and the keyed
        fixture is missing. The body shape matches the shipped Pydantic
        schemas in ``src/doctrine/{directives,tactics,styleguides}/models.py``
        so the synthesis pipeline's schema gate accepts it.
        """
        target = request.target
        kind = target.kind
        slug = target.slug
        title = target.title or slug.replace("-", " ").title()

        body: dict[str, Any]
        if kind == "directive":
            artifact_id = target.artifact_id or "PROJECT_001"
            body = {
                "id": artifact_id,
                "schema_version": "1.0",
                "title": title,
                "intent": (
                    "Auto-generated stub directive for offline fixture testing. "
                    "Replace with a real fixture or generated artifact for production use."
                ),
                "enforcement": "advisory",
                "scope": "test-only stub artifact (SPEC_KITTY_FIXTURE_AUTO_STUB)",
                "procedures": [
                    "This stub is generated by FixtureAdapter for E2E testing only.",
                ],
            }
        elif kind == "tactic":
            body = {
                "id": slug,
                "schema_version": "1.0",
                "name": title,
                "purpose": (
                    "Auto-generated stub tactic for offline fixture testing. "
                    "Replace with a real fixture or generated artifact for production use."
                ),
                "steps": [
                    {
                        "title": "Stub step",
                        "description": (
                            "This stub tactic is generated by FixtureAdapter for "
                            "E2E testing only."
                        ),
                    }
                ],
            }
        elif kind == "styleguide":
            body = {
                "id": slug,
                "schema_version": "1.0",
                "title": title,
                "scope": "code",
                "principles": [
                    "Auto-generated stub styleguide; replace before production use.",
                ],
            }
        else:
            raise FixtureAdapterMissingError(
                expected_path=str(self._fixture_path(request)),
                kind=kind,
                slug=slug,
                inputs_hash=full_hash,
            )

        return AdapterOutput(
            body=body,
            generated_at=_deterministic_generated_at(full_hash),
            adapter_id_override=None,
            adapter_version_override=None,
            notes=f"fixture-auto-stub:{full_hash[:12]}",
        )

    def generate_batch(
        self, requests: list[SynthesisRequest]
    ) -> list[AdapterOutput]:
        """Sequential batch generate (fixture adapter has no batching benefit)."""
        return [self.generate(r) for r in requests]
