"""Network-isolated PlantUML invocation seam (WP01).

This is the *single* place the mission wraps the untrusted ``java -jar
plantuml.jar`` call. The docsite render post-processor (WP02) and the no-egress
proofs (WP03) consume this module; they must never re-implement the docker /
SANDBOX / sha256 contract.

Design invariants (see kitty-specs/doctrine-schema-diagrams-01KZTQTH):

* **stdlib-only** — ``docs-pages.yml`` has no ``pip install``; import only the
  standard library so the module runs host-native under a bare ``python3``.
* **no doctrine-content egress** — the jar runs inside
  ``docker run --network=none`` with a *digest-pinned* JRE image (prefetched
  before the isolated run) and ``-DPLANTUML_SECURITY_PROFILE=SANDBOX``.
* **fail closed** — a jar sha256 mismatch, a non-zero exit, empty output, or a
  PlantUML *error* SVG (which PlantUML emits as a valid, non-empty SVG at exit 0
  on e.g. a font/DNS failure) all raise, never return a bad diagram.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "Pins",
    "PlantumlRenderError",
    "build_docker_argv",
    "ensure_jar",
    "load_pins",
    "render_startyaml",
    "svg_is_error",
    "verify_jar_sha256",
]

# GitHub release downloads flake with RemoteDisconnected; retry a bounded
# number of times with linear backoff before giving up.
_DOWNLOAD_ATTEMPTS = 5

# PlantUML renders a failed diagram (bad font, refused include, syntax error
# without -failfast) as a *valid* SVG carrying one of these signatures. The
# render must fail closed on them rather than ship a broken diagram.
_ERROR_SIGNATURES: tuple[str, ...] = (
    "An error has occurred",
    "Syntax Error",
    "cannot be loaded",
    "java.lang.",
    "SecurityProfile",
)

_DEFAULT_PINS_PATH = Path(__file__).with_name("plantuml_pins.json")


class PlantumlRenderError(RuntimeError):
    """Raised (fail-closed) on any unsafe or failed render."""


@dataclass(frozen=True)
class Pins:
    """Resolved pin registry from ``plantuml_pins.json``."""

    plantuml_version: str
    plantuml_jar_sha256: str
    plantuml_jar_url: str
    jre_image: str
    jre_image_digest: str


def load_pins(pins_path: Path | None = None) -> Pins:
    """Load and validate the pin registry (stdlib ``json`` only)."""
    path = pins_path or _DEFAULT_PINS_PATH
    data = json.loads(path.read_text(encoding="utf-8"))
    try:
        return Pins(
            plantuml_version=str(data["plantuml_version"]),
            plantuml_jar_sha256=str(data["plantuml_jar_sha256"]).lower(),
            plantuml_jar_url=str(data["plantuml_jar_url"]),
            jre_image=str(data["jre_image"]),
            jre_image_digest=str(data["jre_image_digest"]),
        )
    except KeyError as exc:  # pragma: no cover - guards a malformed pins file
        raise PlantumlRenderError(f"plantuml_pins.json missing key: {exc}") from exc


def verify_jar_sha256(jar_path: Path, expected_sha256: str) -> None:
    """Raise ``PlantumlRenderError`` unless ``jar_path`` matches the pin."""
    digest = hashlib.sha256(jar_path.read_bytes()).hexdigest()
    if digest.lower() != expected_sha256.lower():
        raise PlantumlRenderError(
            f"plantuml.jar sha256 mismatch: expected {expected_sha256}, got {digest}"
        )


def _download_once(url: str, dest: Path) -> None:
    """Download ``url`` to ``dest``, retrying transient failures with backoff."""
    last: Exception | None = None
    for attempt in range(_DOWNLOAD_ATTEMPTS):
        try:
            urllib.request.urlretrieve(url, dest)  # noqa: S310 - pinned https URL
            return
        except Exception as exc:  # noqa: BLE001 - retry any transient download error
            last = exc
            time.sleep(2 * (attempt + 1))
    assert last is not None  # loop always sets `last` before exhausting attempts
    raise last


def ensure_jar(pins: Pins, dest: Path) -> Path:
    """Provision ``dest`` with a sha256-verified plantuml.jar, safe for concurrent callers.

    Multiple pytest-xdist workers (or any concurrent processes) may call this
    against the *same* ``dest`` path at once. A cross-process ``fcntl.flock``
    (stdlib, POSIX — matches this module's stdlib-only invariant: it is
    imported via bare ``python3`` with no ``pip install`` in ``docs-pages.yml``
    and ``plantuml-egress-spike.yml``, so a third-party lock library is not an
    option here) on a sidecar lock path serializes the whole
    check-download-verify sequence so no reader ever observes a file that is
    still being written. The download itself lands on a unique per-process
    temp path and is sha256-verified *before* being published to ``dest`` via
    an atomic ``os.replace`` — a truncated or interleaved download can
    therefore never be mistaken for a valid jar, and a mismatch on the temp
    file simply triggers a fresh download attempt rather than corrupting the
    shared file.
    """
    lock_path = dest.with_suffix(dest.suffix + ".lock")
    with open(lock_path, "w", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        try:
            return _provision_locked(pins, dest)
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)


def _provision_locked(pins: Pins, dest: Path) -> Path:
    """Download-and-publish ``dest``, assuming the caller already holds the lock."""
    if dest.exists():
        try:
            verify_jar_sha256(dest, pins.plantuml_jar_sha256)
            return dest
        except PlantumlRenderError:
            pass  # existing file is stale/corrupt — fall through and re-provision
    tmp = dest.parent / f".{dest.name}.{os.getpid()}.tmp"
    try:
        for _ in range(_DOWNLOAD_ATTEMPTS):
            _download_once(pins.plantuml_jar_url, tmp)
            try:
                verify_jar_sha256(tmp, pins.plantuml_jar_sha256)
                break
            except PlantumlRenderError:
                continue  # sha mismatch on a fresh download — retry
        else:
            raise PlantumlRenderError(
                f"plantuml.jar download repeatedly failed sha256 verification "
                f"after {_DOWNLOAD_ATTEMPTS} attempts"
            )
        os.replace(tmp, dest)
    finally:
        tmp.unlink(missing_ok=True)
    return dest


def build_docker_argv(
    *, image_digest: str, workdir: Path, jar_path: Path, infile: Path
) -> list[str]:
    """Build the network-isolated docker argv.

    Kept pure/testable so a unit test can assert the security-critical flags are
    present without needing docker. Note the flag ordering: JVM options precede
    ``-jar``; PlantUML options (``-tsvg``, ``-failfast2``) follow the jar. Both the
    working directory AND the jar's directory are bind-mounted (deduped) so the jar
    is always reachable inside the container even when it lives outside ``workdir``.
    """
    mounts: list[str] = []
    seen: set[str] = set()
    for directory in (workdir, jar_path.parent):
        as_str = str(directory)
        if as_str not in seen:
            seen.add(as_str)
            mounts.extend(("-v", f"{as_str}:{as_str}"))
    return [
        "docker",
        "run",
        "--rm",
        "--network=none",
        *mounts,
        "-w",
        str(workdir),
        image_digest,
        "java",
        "-Djava.awt.headless=true",
        "-DPLANTUML_SECURITY_PROFILE=SANDBOX",
        "-jar",
        str(jar_path),
        "-tsvg",
        "-failfast2",
        str(infile),
    ]


def svg_is_error(svg: bytes) -> bool:
    """True if the SVG carries a PlantUML error signature (fail-closed check)."""
    text = svg.decode("utf-8", errors="replace")
    return any(sig in text for sig in _ERROR_SIGNATURES)


def render_startyaml(
    source_text: str,
    *,
    workdir: Path,
    jar_path: Path,
    pins: Pins,
    timeout_s: int = 120,
) -> bytes:
    """Render one PlantUML block to SVG bytes under network isolation.

    ``jar_path`` must already be sha256-verified against ``pins`` (call
    :func:`verify_jar_sha256`); the caller prefetches ``pins.jre_image_digest``
    outside isolation. Fails closed on any error.
    """
    verify_jar_sha256(jar_path, pins.plantuml_jar_sha256)
    with tempfile.TemporaryDirectory(dir=workdir) as tmp:
        tmp_dir = Path(tmp)
        infile = tmp_dir / "diagram.puml"
        infile.write_text(source_text, encoding="utf-8")
        argv = build_docker_argv(
            image_digest=pins.jre_image_digest,
            workdir=workdir,
            jar_path=jar_path,
            infile=infile,
        )
        proc = subprocess.run(  # noqa: S603 - argv is built from pinned inputs, not shell
            argv,
            capture_output=True,
            timeout=timeout_s,
            check=False,
        )
        outfile = infile.with_suffix(".svg")
        if proc.returncode != 0 or not outfile.exists():
            raise PlantumlRenderError(
                f"render failed (exit {proc.returncode}): "
                f"{proc.stderr.decode('utf-8', 'replace')[:500]}"
            )
        svg = outfile.read_bytes()
    if not svg.strip():
        raise PlantumlRenderError("render produced empty SVG")
    if svg_is_error(svg):
        raise PlantumlRenderError(
            "render produced a PlantUML error SVG (font/DNS/syntax); failing closed"
        )
    return svg


def extract_title(source_text: str) -> str | None:
    """Return the PlantUML ``title`` line's text, if present (alt-text source)."""
    match = re.search(r"^\s*title\s+(.+?)\s*$", source_text, flags=re.MULTILINE)
    return match.group(1) if match else None
