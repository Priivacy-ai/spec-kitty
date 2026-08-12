"""Unit tests for the network-isolated PlantUML invocation seam (WP01).

These run everywhere — no docker required. The security-critical flags on the
docker argv, the sha256 fail-closed behaviour, and the error-SVG detector are
pinned here; the *actual* network-isolated render is proven by the
``plantuml-egress-spike.yml`` CI matrix (both runners).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Import the render seam the way the docs workflows do: put scripts/docs on the
# path and import by module name (this registers it in sys.modules, which the
# frozen @dataclass in the module needs). Mirrors glossary_linker's bootstrap.
_DOCS_DIR = Path(__file__).resolve().parents[2] / "scripts" / "docs"
if str(_DOCS_DIR) not in sys.path:
    sys.path.insert(0, str(_DOCS_DIR))

import plantuml_invoke  # noqa: E402  # deliberate post-bootstrap import (see above)


def _pins() -> plantuml_invoke.Pins:
    return plantuml_invoke.load_pins()


def test_pins_load_from_repo() -> None:
    pins = _pins()
    assert pins.plantuml_version
    assert len(pins.plantuml_jar_sha256) == 64
    assert pins.jre_image_digest.startswith("eclipse-temurin@sha256:")


def test_docker_argv_carries_isolation_and_sandbox_flags(tmp_path: Path) -> None:
    pins = _pins()
    argv = plantuml_invoke.build_docker_argv(
        image_digest=pins.jre_image_digest,
        workdir=tmp_path,
        jar_path=tmp_path / "plantuml.jar",
        infile=tmp_path / "d.puml",
    )
    # Security-critical: network isolation + SANDBOX + headless must be present.
    assert "--network=none" in argv
    assert "-DPLANTUML_SECURITY_PROFILE=SANDBOX" in argv
    assert "-Djava.awt.headless=true" in argv
    assert pins.jre_image_digest in argv
    # Ordering: JVM opts before -jar; PlantUML opts after the jar.
    assert argv.index("-DPLANTUML_SECURITY_PROFILE=SANDBOX") < argv.index("-jar")
    assert argv.index("-jar") < argv.index("-failfast2")
    assert argv.index("-jar") < argv.index("-tsvg")


def test_verify_jar_sha256_rejects_mismatch(tmp_path: Path) -> None:
    jar = tmp_path / "plantuml.jar"
    jar.write_bytes(b"not the real jar")
    with pytest.raises(plantuml_invoke.PlantumlRenderError):
        plantuml_invoke.verify_jar_sha256(jar, _pins().plantuml_jar_sha256)


def test_verify_jar_sha256_accepts_match(tmp_path: Path) -> None:
    # File-integrity checksum of a synthetic jar (not a charter content hash);
    # sha256 is the algorithm under test in verify_jar_sha256.
    import hashlib

    jar = tmp_path / "plantuml.jar"
    payload = b"deterministic-bytes"
    jar.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()  # noqa: TID251 - file-integrity checksum under test
    plantuml_invoke.verify_jar_sha256(jar, expected)


def test_svg_is_error_detects_error_signatures() -> None:
    assert plantuml_invoke.svg_is_error(b"<svg><text>An error has occurred</text></svg>")
    assert plantuml_invoke.svg_is_error(b"<svg><text>Syntax Error?</text></svg>")
    assert not plantuml_invoke.svg_is_error(
        b'<svg><text>Agent Profile Schema</text><text>researcher-ryan</text></svg>'
    )


def test_extract_title_reads_plantuml_title() -> None:
    src = "@startyaml\ntitle Agent Profile Schema\nprofile_id: x\n@endyaml\n"
    assert plantuml_invoke.extract_title(src) == "Agent Profile Schema"
    assert plantuml_invoke.extract_title("@startyaml\nprofile_id: x\n@endyaml") is None
