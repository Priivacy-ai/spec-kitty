"""Build the immutable project-sync-consent evidence manifest (WP11 T049 + T054).

Two responsibilities, both fail-closed:

* **T049 prerequisite attestation** — verify the exact core candidate HEAD, the
  exact SaaS candidate HEAD, the canonical generated CLI-SaaS contract digest,
  the reviewed SaaS WP08 evidence checksum, and the SaaS WP02 tombstone
  commit/evidence checksum. Every input arrives as an explicit flag: there is
  no ambient sibling discovery, no branch-name resolution, and no default
  candidate. Any missing, floating (non-40-hex), or inconsistent input exits
  non-zero before a single byte of manifest is written.

* **T054 manifest** — emit
  ``<output-root>/<core-commit>/manifest.json`` binding schema version, exact
  candidate commits and contract digest, command/result records, artifact
  paths with a recomputed SHA-256 for every raw file, producer ownership
  (``core`` | ``saas``) with non-overlapping claims, injected creation time,
  and the retention URI/expiry. Output is deterministic for identical inputs
  (creation time is an explicit flag, never a wall-clock read) and immutable:
  an existing manifest is never overwritten.

Referenced SaaS-owned evidence (WP02 anti-rematerialization, WP08 admission
boundary) is recorded by URI + checksum only — this builder produces
core-owned rows and never regenerates or claims SaaS evidence
(FR-031/FR-033/FR-034, C-010).
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

MANIFEST_SCHEMA = "project-sync-consent-evidence-manifest/1"
CONTRACT_RELPATH = "contracts/cli-saas-current-api.yaml"
SAAS_PRODUCER_GATE = "SaaS WP04"
RETENTION_MINIMUM_DAYS = 90
SAAS_WP02_CLAIM = "saas-wp02-anti-rematerialization"
SAAS_WP08_CLAIM = "saas-wp08-admission-boundary"

_COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_CLAIM_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
_NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,79}\Z")
_LABEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")
_TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z")
_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
_SECONDS_PER_DAY = 86_400


class ManifestInputError(RuntimeError):
    """An explicit input is missing, floating, or inconsistent (fail closed)."""


@dataclass(frozen=True)
class CheckoutAttestation:
    """Sanitized immutable identity of one explicitly attested checkout."""

    commit: str
    label: str


@dataclass(frozen=True)
class EvidenceArtifact:
    """One core-produced raw evidence file with its verified digest."""

    owner: str
    claim: str
    sha256: str
    path: str


@dataclass(frozen=True)
class CommandRecord:
    """One executed command/result record bound into the manifest."""

    name: str
    exit_code: int
    command: str


def _require_commit(value: str, flag: str) -> str:
    if not _COMMIT_RE.fullmatch(value):
        raise ManifestInputError(f"{flag} must be an exact 40-character lowercase commit SHA, not a floating ref: {value!r}")
    return value


def _require_sha256(value: str, flag: str) -> str:
    if not _SHA256_RE.fullmatch(value):
        raise ManifestInputError(f"{flag} must be an exact 64-character lowercase SHA-256 digest: {value!r}")
    return value


def _require_https_uri(value: str, flag: str) -> str:
    if not value.startswith("https://") or any(ch.isspace() for ch in value):
        raise ManifestInputError(f"{flag} must be a persistent https:// retention coordinate: {value!r}")
    return value


def _timestamp_to_epoch(value: str, flag: str) -> int:
    if not _TIMESTAMP_RE.fullmatch(value):
        raise ManifestInputError(f"{flag} must be an exact UTC timestamp of the form YYYY-MM-DDTHH:MM:SSZ: {value!r}")
    try:
        parsed = time.strptime(value, _TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ManifestInputError(f"{flag} is not a real UTC timestamp: {value!r}") from exc
    return calendar.timegm(parsed)


def _git(checkout: Path, *arguments: str) -> str:
    try:
        completed = subprocess.run(
            ("git", "-C", str(checkout), *arguments),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ManifestInputError(f"git {' '.join(arguments)} failed for checkout {checkout.name!r}") from exc
    return completed.stdout.strip()


def attest_checkout(path_value: str, expected_commit: str, name: str) -> tuple[Path, CheckoutAttestation]:
    """Verify an explicit clean checkout at the exact expected commit."""
    _require_commit(expected_commit, f"--expected-{name}-commit")
    try:
        checkout = Path(path_value).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ManifestInputError(f"{name} checkout does not exist: {path_value!r}") from exc
    if not checkout.is_dir():
        raise ManifestInputError(f"{name} checkout is not a directory: {path_value!r}")
    head = _git(checkout, "rev-parse", "HEAD")
    if head != expected_commit:
        raise ManifestInputError(f"{name} checkout HEAD {head} differs from the expected candidate commit {expected_commit}")
    if _git(checkout, "status", "--porcelain"):
        raise ManifestInputError(f"{name} checkout is dirty; evidence requires an exact committed candidate")
    label = checkout.name
    if not _LABEL_RE.fullmatch(label):
        raise ManifestInputError(f"{name} checkout directory name is not a sanitized identity: {label!r}")
    return checkout, CheckoutAttestation(commit=head, label=label)


def verify_contract_digest(saas_checkout: Path, expected_sha256: str) -> str:
    """Verify the canonical generated contract digest inside the SaaS candidate."""
    _require_sha256(expected_sha256, "--expected-contract-sha256")
    contract = saas_checkout / CONTRACT_RELPATH
    if not contract.is_file():
        raise ManifestInputError(f"canonical generated SaaS contract is missing: {CONTRACT_RELPATH}")
    actual = hashlib.sha256(contract.read_bytes()).hexdigest()
    if actual != expected_sha256:
        raise ManifestInputError(f"canonical contract digest {actual} differs from the explicit expectation {expected_sha256}")
    return actual


def verify_tombstone_commit(saas_checkout: Path, candidate_commit: str, tombstone_commit: str) -> str:
    """Verify the SaaS WP02 tombstone milestone is a real ancestor commit, not a mock."""
    _require_commit(tombstone_commit, "--tombstone-commit")
    object_type = _git(saas_checkout, "cat-file", "-t", tombstone_commit)
    if object_type != "commit":
        raise ManifestInputError(f"tombstone ref {tombstone_commit} is a {object_type}, not a commit")
    _git(saas_checkout, "merge-base", "--is-ancestor", tombstone_commit, candidate_commit)
    return tombstone_commit


def parse_artifact(value: str, artifact_root: Path) -> EvidenceArtifact:
    """Parse one ``owner:claim:sha256:relative-path`` artifact and verify its bytes."""
    parts = value.split(":", 3)
    if len(parts) != 4:
        raise ManifestInputError(f"--artifact must be owner:claim:sha256:relative-path, got {value!r}")
    owner, claim, declared_sha256, relative = parts
    if owner != "core":
        raise ManifestInputError(f"this builder emits core-owned evidence only; owner {owner!r} for claim {claim!r} must arrive via explicit SaaS reference flags")
    if not _CLAIM_RE.fullmatch(claim):
        raise ManifestInputError(f"artifact claim is not a sanitized identifier: {claim!r}")
    _require_sha256(declared_sha256, f"--artifact {claim}")
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise ManifestInputError(f"artifact path must be a plain relative path inside the evidence root: {relative!r}")
    file = artifact_root / path
    if not file.is_file():
        raise ManifestInputError(f"artifact file is missing: {relative!r}")
    actual = hashlib.sha256(file.read_bytes()).hexdigest()
    if actual != declared_sha256:
        raise ManifestInputError(f"artifact {relative!r} checksum mismatch: recomputed {actual}, declared {declared_sha256}")
    return EvidenceArtifact(owner=owner, claim=claim, sha256=actual, path=path.as_posix())


def parse_command(value: str) -> CommandRecord:
    """Parse one ``name:exit_code:command`` record; only exit code 0 is evidence."""
    parts = value.split(":", 2)
    if len(parts) != 3:
        raise ManifestInputError(f"--command must be name:exit_code:command, got {value!r}")
    name, exit_code, command = parts
    if not _NAME_RE.fullmatch(name):
        raise ManifestInputError(f"command record name is not a sanitized identifier: {name!r}")
    if exit_code != "0":
        raise ManifestInputError(f"command record {name!r} has exit code {exit_code!r}; only passing (0) results are evidence")
    if not command.strip():
        raise ManifestInputError(f"command record {name!r} has an empty command")
    return CommandRecord(name=name, exit_code=0, command=command)


def verify_retention(created_at: str, retention_uri: str, expires_at: str) -> dict[str, object]:
    """Verify the retention coordinate exists and covers the 90-day minimum."""
    _require_https_uri(retention_uri, "--retention-uri")
    created_epoch = _timestamp_to_epoch(created_at, "--created-at")
    expires_epoch = _timestamp_to_epoch(expires_at, "--retention-expires-at")
    if expires_epoch - created_epoch < RETENTION_MINIMUM_DAYS * _SECONDS_PER_DAY:
        raise ManifestInputError(
            f"retention expiry {expires_at} does not cover the {RETENTION_MINIMUM_DAYS}-day minimum from creation time {created_at}"
        )
    return {"uri": retention_uri, "expires_at": expires_at, "minimum_days": RETENTION_MINIMUM_DAYS}


def _verify_claim_ownership(artifacts: list[EvidenceArtifact]) -> None:
    claims: set[str] = {SAAS_WP02_CLAIM, SAAS_WP08_CLAIM}
    for artifact in artifacts:
        if artifact.claim in claims:
            raise ManifestInputError(f"duplicate evidence ownership: claim {artifact.claim!r} is already owned")
        claims.add(artifact.claim)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-checkout", required=True, help="Path to the exact core candidate checkout")
    parser.add_argument("--expected-core-commit", required=True, help="Exact 40-hex core candidate commit")
    parser.add_argument("--saas-checkout", required=True, help="Path to the exact SaaS candidate checkout")
    parser.add_argument("--expected-saas-commit", required=True, help="Exact 40-hex SaaS candidate commit")
    parser.add_argument("--expected-contract-sha256", required=True, help="Exact SHA-256 of the canonical generated CLI-SaaS contract")
    parser.add_argument("--tombstone-commit", required=True, help="Exact 40-hex reviewed SaaS WP02 tombstone milestone commit")
    parser.add_argument("--saas-wp02-evidence-uri", required=True, help="Persistent URI of the reviewed SaaS WP02 anti-rematerialization evidence")
    parser.add_argument("--saas-wp02-evidence-sha256", required=True, help="SHA-256 of the reviewed SaaS WP02 evidence bundle")
    parser.add_argument("--saas-wp08-evidence-uri", required=True, help="Persistent URI of the approved SaaS WP08 evidence")
    parser.add_argument("--saas-wp08-evidence-sha256", required=True, help="SHA-256 of the approved SaaS WP08 evidence bundle")
    parser.add_argument("--artifact", action="append", default=[], help="Repeatable owner:claim:sha256:relative-path raw evidence file")
    parser.add_argument("--artifact-root", required=True, help="Directory the relative artifact paths resolve against")
    parser.add_argument("--command", action="append", default=[], help="Repeatable name:exit_code:command result record")
    parser.add_argument("--created-at", required=True, help="Injected UTC creation time (YYYY-MM-DDTHH:MM:SSZ); explicit for determinism")
    parser.add_argument("--retention-uri", required=True, help="Persistent https:// retention coordinate of the uploaded bundle")
    parser.add_argument("--retention-expires-at", required=True, help="UTC expiry of the retention coordinate (>= 90 days after creation)")
    parser.add_argument("--output-root", required=True, help="Evidence output root; the manifest lands at <output-root>/<core-commit>/manifest.json")
    return parser


def build_manifest(namespace: argparse.Namespace) -> tuple[Path, str]:
    """Validate every explicit input, then render the immutable manifest.

    Returns the manifest path and its rendered content. Raises
    :class:`ManifestInputError` before any filesystem write when any input is
    missing, floating, or inconsistent — there is no partial manifest.
    """
    _core_checkout, core = attest_checkout(namespace.core_checkout, namespace.expected_core_commit, "core")
    saas_checkout, saas = attest_checkout(namespace.saas_checkout, namespace.expected_saas_commit, "saas")
    contract_sha256 = verify_contract_digest(saas_checkout, namespace.expected_contract_sha256)
    tombstone_commit = verify_tombstone_commit(saas_checkout, saas.commit, namespace.tombstone_commit)
    wp02_uri = _require_https_uri(namespace.saas_wp02_evidence_uri, "--saas-wp02-evidence-uri")
    wp02_sha256 = _require_sha256(namespace.saas_wp02_evidence_sha256, "--saas-wp02-evidence-sha256")
    wp08_uri = _require_https_uri(namespace.saas_wp08_evidence_uri, "--saas-wp08-evidence-uri")
    wp08_sha256 = _require_sha256(namespace.saas_wp08_evidence_sha256, "--saas-wp08-evidence-sha256")

    try:
        artifact_root = Path(namespace.artifact_root).expanduser().resolve(strict=True)
    except OSError as exc:
        raise ManifestInputError(f"artifact root does not exist: {namespace.artifact_root!r}") from exc
    artifacts = sorted((parse_artifact(value, artifact_root) for value in namespace.artifact), key=lambda a: a.claim)
    if not artifacts:
        raise ManifestInputError("at least one core-owned raw evidence artifact is required")
    _verify_claim_ownership(artifacts)

    commands = sorted((parse_command(value) for value in namespace.command), key=lambda c: c.name)
    if not commands:
        raise ManifestInputError("at least one command/result record is required")
    if len({record.name for record in commands}) != len(commands):
        raise ManifestInputError("command record names must be unique")

    retention = verify_retention(namespace.created_at, namespace.retention_uri, namespace.retention_expires_at)

    manifest: dict[str, object] = {
        "schema": MANIFEST_SCHEMA,
        "created_at": namespace.created_at,
        "attestation": {
            "core": {"commit": core.commit, "checkout_label": core.label},
            "saas": {
                "producer_gate": SAAS_PRODUCER_GATE,
                "commit": saas.commit,
                "checkout_label": saas.label,
                "contract_path": CONTRACT_RELPATH,
                "contract_sha256": contract_sha256,
            },
        },
        "references": [
            {
                "owner": "saas",
                "claim": SAAS_WP02_CLAIM,
                "tombstone_commit": tombstone_commit,
                "evidence_uri": wp02_uri,
                "evidence_sha256": wp02_sha256,
            },
            {
                "owner": "saas",
                "claim": SAAS_WP08_CLAIM,
                "evidence_uri": wp08_uri,
                "evidence_sha256": wp08_sha256,
            },
        ],
        "commands": [
            {"name": record.name, "exit_code": record.exit_code, "command": record.command, "status": "passed"} for record in commands
        ],
        "artifacts": [
            {"owner": artifact.owner, "claim": artifact.claim, "path": artifact.path, "sha256": artifact.sha256} for artifact in artifacts
        ],
        "retention": retention,
    }
    rendered = json.dumps(manifest, sort_keys=True, indent=2) + "\n"

    output_root = Path(namespace.output_root).expanduser()
    manifest_path = output_root / core.commit / "manifest.json"
    if manifest_path.exists():
        raise ManifestInputError(f"manifest already exists and is immutable: {manifest_path}")
    return manifest_path, rendered


def main(argv: list[str] | None = None) -> int:
    namespace = _build_parser().parse_args(argv)
    try:
        manifest_path, rendered = build_manifest(namespace)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with manifest_path.open("x", encoding="utf-8") as handle:
            handle.write(rendered)
    except ManifestInputError as error:
        print(f"evidence manifest refused: {error}", file=sys.stderr)
        return 1
    digest = hashlib.sha256(rendered.encode("utf-8")).hexdigest()
    print(f"{manifest_path} sha256={digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
