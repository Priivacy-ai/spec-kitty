"""WP11 T049/T054: the evidence manifest builder fails closed and emits an immutable, deterministic bundle.

Exercises ``scripts/evidence/build_project_sync_consent_manifest.py`` through
its real CLI surface (subprocess, exact exit codes) against throwaway git
candidates, proving:

* floating or missing candidate refs are refused with no partial manifest;
* a one-byte artifact change is caught by checksum recomputation;
* a candidate commit mismatch, dirty checkout, contract digest drift, and a
  mocked (unreachable) tombstone commit each fail closed;
* duplicate evidence ownership (core re-claiming a SaaS claim, or two rows
  with one claim) is refused;
* missing/expired retention metadata is refused;
* a valid explicit input set produces a schema-complete manifest that is
  byte-deterministic for identical inputs and never overwritten once written.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _REPO_ROOT / "scripts" / "evidence" / "build_project_sync_consent_manifest.py"

_CONTRACT_BODY = "openapi: 3.1.0\ninfo:\n  title: cli-saas current api\n"
_CREATED_AT = "2026-08-13T00:00:00Z"
_EXPIRES_OK = "2026-11-12T00:00:00Z"  # 91 days after creation
_EXPIRES_SHORT = "2026-08-23T00:00:00Z"  # 10 days after creation


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 - file-integrity checksum of raw evidence bytes, not the charter hash


def _git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(("git", "-C", str(cwd), *args), check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def _init_repo(path: Path, files: dict[str, str]) -> str:
    path.mkdir(parents=True)
    _git(path, "init", "-q")
    _git(path, "config", "user.email", "evidence@example.test")
    _git(path, "config", "user.name", "Evidence Test")
    return _commit_files(path, files, "initial candidate state")


def _commit_files(path: Path, files: dict[str, str], message: str) -> str:
    for relative, content in files.items():
        target = path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _git(path, "add", "-A")
    _git(path, "commit", "-qm", message)
    return _git(path, "rev-parse", "HEAD")


class _Inputs:
    """One complete, valid explicit input set the tests mutate per scenario."""

    def __init__(self, tmp_path: Path) -> None:
        self.core_checkout = tmp_path / "core-candidate"
        self.core_commit = _init_repo(self.core_checkout, {"README.md": "core candidate\n"})

        self.saas_checkout = tmp_path / "saas-wp04-candidate"
        self.tombstone_commit = _init_repo(self.saas_checkout, {"TOMBSTONE.md": "wp02 milestone\n"})
        self.saas_commit = _commit_files(self.saas_checkout, {"contracts/cli-saas-current-api.yaml": _CONTRACT_BODY}, "candidate head")
        self.contract_sha256 = _sha256(_CONTRACT_BODY.encode("utf-8"))

        self.artifact_root = tmp_path / "raw"
        self.artifact_root.mkdir()
        self.artifact_body = b'{"samples": [1, 2, 3]}\n'
        (self.artifact_root / "six-project-omission.json").write_bytes(self.artifact_body)
        self.artifacts = [f"core:six-project-omission:{_sha256(self.artifact_body)}:six-project-omission.json"]

        self.commands = ["core-six-project-proof:0:uv run python -m pytest tests/integration/test_project_sync_six_project.py"]
        self.saas_wp02_evidence_uri = "https://evidence.example.test/saas-wp02/bundle"
        self.saas_wp02_evidence_sha256 = _sha256(b"saas wp02 evidence bundle")
        self.saas_wp08_evidence_uri = "https://evidence.example.test/saas-wp08/bundle"
        self.saas_wp08_evidence_sha256 = _sha256(b"saas wp08 evidence bundle")
        self.created_at = _CREATED_AT
        self.retention_uri = "https://evidence.example.test/retention/run-1"
        self.retention_expires_at = _EXPIRES_OK
        self.output_root = tmp_path / "bundle"

    def argv(self) -> list[str]:
        arguments = [
            "--core-checkout", str(self.core_checkout),
            "--expected-core-commit", self.core_commit,
            "--saas-checkout", str(self.saas_checkout),
            "--expected-saas-commit", self.saas_commit,
            "--expected-contract-sha256", self.contract_sha256,
            "--tombstone-commit", self.tombstone_commit,
            "--saas-wp02-evidence-uri", self.saas_wp02_evidence_uri,
            "--saas-wp02-evidence-sha256", self.saas_wp02_evidence_sha256,
            "--saas-wp08-evidence-uri", self.saas_wp08_evidence_uri,
            "--saas-wp08-evidence-sha256", self.saas_wp08_evidence_sha256,
            "--artifact-root", str(self.artifact_root),
            "--created-at", self.created_at,
            "--retention-uri", self.retention_uri,
            "--retention-expires-at", self.retention_expires_at,
            "--output-root", str(self.output_root),
        ]
        for artifact in self.artifacts:
            arguments.extend(["--artifact", artifact])
        for command in self.commands:
            arguments.extend(["--command", command])
        return arguments

    def run(self, argv: list[str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            (sys.executable, str(_SCRIPT), *(self.argv() if argv is None else argv)),
            check=False,
            capture_output=True,
            text=True,
        )

    @property
    def manifest_path(self) -> Path:
        return self.output_root / self.core_commit / "manifest.json"

    def assert_refused(self, fragment: str) -> subprocess.CompletedProcess[str]:
        """Run, assert a non-zero fail-closed exit, the message, and no partial manifest."""
        result = self.run()
        assert result.returncode == 1, result.stdout + result.stderr
        assert fragment in result.stderr
        assert not list(self.output_root.rglob("*")) if self.output_root.exists() else True
        return result


@pytest.fixture
def inputs(tmp_path: Path) -> _Inputs:
    return _Inputs(tmp_path)


def test_valid_inputs_produce_schema_complete_manifest(inputs: _Inputs) -> None:
    result = inputs.run()
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(inputs.manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema"] == "project-sync-consent-evidence-manifest/1"
    assert manifest["created_at"] == _CREATED_AT
    assert manifest["attestation"]["core"] == {"commit": inputs.core_commit, "checkout_label": "core-candidate"}
    assert manifest["attestation"]["saas"] == {
        "producer_gate": "SaaS WP04",
        "commit": inputs.saas_commit,
        "checkout_label": "saas-wp04-candidate",
        "contract_path": "contracts/cli-saas-current-api.yaml",
        "contract_sha256": inputs.contract_sha256,
    }
    references = {row["claim"]: row for row in manifest["references"]}
    assert references["saas-wp02-anti-rematerialization"]["owner"] == "saas"
    assert references["saas-wp02-anti-rematerialization"]["tombstone_commit"] == inputs.tombstone_commit
    assert references["saas-wp02-anti-rematerialization"]["evidence_sha256"] == inputs.saas_wp02_evidence_sha256
    assert references["saas-wp08-admission-boundary"] == {
        "owner": "saas",
        "claim": "saas-wp08-admission-boundary",
        "evidence_uri": inputs.saas_wp08_evidence_uri,
        "evidence_sha256": inputs.saas_wp08_evidence_sha256,
    }
    assert manifest["commands"] == [
        {
            "name": "core-six-project-proof",
            "exit_code": 0,
            "command": "uv run python -m pytest tests/integration/test_project_sync_six_project.py",
            "status": "passed",
        }
    ]
    assert manifest["artifacts"] == [
        {
            "owner": "core",
            "claim": "six-project-omission",
            "path": "six-project-omission.json",
            "sha256": _sha256(inputs.artifact_body),
        }
    ]
    assert manifest["retention"] == {"uri": inputs.retention_uri, "expires_at": _EXPIRES_OK, "minimum_days": 90}
    # Ownership claims are non-overlapping across artifacts and references.
    claims = [row["claim"] for row in (*manifest["artifacts"], *manifest["references"])]
    assert len(claims) == len(set(claims))


def test_manifest_is_byte_deterministic_for_identical_inputs(inputs: _Inputs, tmp_path: Path) -> None:
    assert inputs.run().returncode == 0
    first = inputs.manifest_path.read_bytes()
    inputs.output_root = tmp_path / "bundle-second"
    assert inputs.run().returncode == 0
    assert inputs.manifest_path.read_bytes() == first


def test_existing_manifest_is_never_overwritten(inputs: _Inputs) -> None:
    assert inputs.run().returncode == 0
    original = inputs.manifest_path.read_bytes()
    result = inputs.run()
    assert result.returncode == 1
    assert "immutable" in result.stderr
    assert inputs.manifest_path.read_bytes() == original


def test_floating_saas_ref_is_refused(inputs: _Inputs) -> None:
    inputs.saas_commit = "develop"
    inputs.assert_refused("floating ref")


def test_missing_candidate_ref_is_refused_without_partial_manifest(inputs: _Inputs) -> None:
    argv = inputs.argv()
    index = argv.index("--expected-saas-commit")
    del argv[index : index + 2]
    result = inputs.run(argv)
    assert result.returncode == 2  # argparse usage failure: the input set is incomplete
    assert "--expected-saas-commit" in result.stderr
    assert not inputs.output_root.exists()


def test_candidate_commit_mismatch_fails_closed(inputs: _Inputs) -> None:
    inputs.saas_commit = inputs.tombstone_commit  # a real commit, but not the candidate HEAD
    inputs.assert_refused("differs from the expected candidate commit")


def test_dirty_saas_candidate_is_refused(inputs: _Inputs) -> None:
    contract = inputs.saas_checkout / "contracts" / "cli-saas-current-api.yaml"
    contract.write_text(_CONTRACT_BODY + "# drift\n", encoding="utf-8")
    inputs.assert_refused("dirty")


def test_contract_digest_drift_fails_closed(inputs: _Inputs) -> None:
    inputs.contract_sha256 = _sha256(b"some other contract body")
    inputs.assert_refused("canonical contract digest")


def test_one_byte_artifact_change_fails_checksum(inputs: _Inputs) -> None:
    mutated = bytearray(inputs.artifact_body)
    mutated[0] ^= 0x01
    (inputs.artifact_root / "six-project-omission.json").write_bytes(bytes(mutated))
    inputs.assert_refused("checksum mismatch")


def test_mocked_tombstone_commit_is_refused(inputs: _Inputs) -> None:
    inputs.tombstone_commit = "0" * 40  # well-formed, but no such object in the SaaS candidate
    inputs.assert_refused("failed for checkout")

    inputs.tombstone_commit = inputs.core_commit  # a real commit, but from the wrong repository
    inputs.assert_refused("failed for checkout")


def test_duplicate_evidence_ownership_is_refused(inputs: _Inputs) -> None:
    inputs.artifacts = [inputs.artifacts[0], inputs.artifacts[0]]
    inputs.assert_refused("duplicate evidence ownership")


def test_core_cannot_claim_saas_owned_evidence(inputs: _Inputs) -> None:
    sha = _sha256(inputs.artifact_body)
    inputs.artifacts = [f"core:saas-wp08-admission-boundary:{sha}:six-project-omission.json"]
    inputs.assert_refused("duplicate evidence ownership")

    inputs.artifacts = [f"saas:stale-generation-refusal:{sha}:six-project-omission.json"]
    inputs.assert_refused("core-owned evidence only")


def test_expired_retention_metadata_is_refused(inputs: _Inputs) -> None:
    inputs.retention_expires_at = _EXPIRES_SHORT
    inputs.assert_refused("90-day minimum")


def test_malformed_retention_metadata_is_refused(inputs: _Inputs) -> None:
    inputs.retention_uri = "ftp://not-a-persistent-coordinate"
    inputs.assert_refused("retention coordinate")

    inputs.retention_uri = "https://evidence.example.test/retention/run-1"
    inputs.retention_expires_at = "whenever"
    inputs.assert_refused("UTC timestamp")
