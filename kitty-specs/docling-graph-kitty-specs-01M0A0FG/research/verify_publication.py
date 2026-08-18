#!/usr/bin/env python3
"""Verify the sealed Docling Graph research publication without changing it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


MISSION = "docling-graph-kitty-specs-01M0A0FG"
REPORT_DIR = Path("docs/research/docling-graph-kitty-specs")
MISSION_DIR = Path("kitty-specs") / MISSION
COMPATIBILITY_ROOT = Path("docs/research") / MISSION
EVIDENCE_PATTERN = re.compile(r"EV-\d{3}")
EVIDENCE_RANGE_PATTERN = re.compile(r"EV-(\d{3})[–-]EV-(\d{3})")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
RFC3339_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})")
EXPECTED_REVIEWERS = {
    "/root/postgather_authority:architect-alphonso",
    "/root/postgather_claims:reviewer-renata",
    "/root/postgather_empirical:debugger-debbie",
}
EXACT_ARTIFACTS = {
    str(REPORT_DIR / "report.md"),
    str(REPORT_DIR / "option-scorecard.csv"),
    str(REPORT_DIR / "risk-register.md"),
    str(REPORT_DIR / "data/results-summary.json"),
    str(REPORT_DIR / "data/redaction-manifest.json"),
    str(REPORT_DIR / "data/roundtrip/execution-manifest.json"),
    str(REPORT_DIR / "data/operations/execution-manifest.json"),
    str(REPORT_DIR / "data/privacy/execution-manifest.json"),
    str(REPORT_DIR / "data/semantic/execution-manifest.json"),
    str(REPORT_DIR / "data/corpus-census-execution-manifest.json"),
    str(REPORT_DIR / "data/document-storage-execution-manifest.json"),
    str(MISSION_DIR / "report.md"),
    str(MISSION_DIR / "spec.md"),
    str(MISSION_DIR / "plan.md"),
    str(MISSION_DIR / "findings.md"),
    str(MISSION_DIR / "data-model.md"),
    str(MISSION_DIR / "research.md"),
    str(MISSION_DIR / "source-register.csv"),
    str(MISSION_DIR / "research/adversarial-reviews.md"),
    str(MISSION_DIR / "research/authority-inventory.csv"),
    str(MISSION_DIR / "research/baseline-observations.yaml"),
    str(MISSION_DIR / "research/build_execution_manifests.py"),
    str(MISSION_DIR / "research/candidate-registry.csv"),
    str(MISSION_DIR / "research/consumer-matrix.csv"),
    str(MISSION_DIR / "research/contradictions.csv"),
    str(MISSION_DIR / "research/empirical-evidence-register.csv"),
    str(MISSION_DIR / "research/evidence-log.csv"),
    str(MISSION_DIR / "research/execution-ledger.jsonl"),
    str(MISSION_DIR / "research/materialize_recorded_baseline.py"),
    str(MISSION_DIR / "research/preregistration-manifest.json"),
    str(MISSION_DIR / "research/results/B0-answers.csv"),
    str(MISSION_DIR / "research/results/B0-evaluation.json"),
    str(MISSION_DIR / "research/results/B1-answers.csv"),
    str(MISSION_DIR / "research/results/B1-evaluation.json"),
    str(MISSION_DIR / "research/sanitize_public_results.py"),
    str(MISSION_DIR / "research/source-coverage.csv"),
    str(MISSION_DIR / "research/source-exclusions.csv"),
    str(MISSION_DIR / "research/source-register.csv"),
    str(MISSION_DIR / "research/summarize_results.py"),
    str(MISSION_DIR / "research/verify_publication.py"),
}
EXPECTED_EXECUTION_COUNTS = {
    str(REPORT_DIR / "data/document-storage-execution-manifest.json"): 2,
    str(REPORT_DIR / "data/corpus-census-execution-manifest.json"): 2,
    str(REPORT_DIR / "data/privacy/execution-manifest.json"): 17,
    str(REPORT_DIR / "data/operations/execution-manifest.json"): 39,
    str(REPORT_DIR / "data/roundtrip/execution-manifest.json"): 120,
    str(REPORT_DIR / "data/semantic/execution-manifest.json"): 3,
}
EXPECTED_EMPIRICAL_PROBES = {
    "frozen-corpus-census",
    "confirmatory-structural-roundtrip",
    "supplementary-doclingdocument-storage",
    "bounded-operations",
    "privacy-confinement",
    "semantic-backend-availability",
}
EXPECTED_REDACTION_PATHS = {
    str(REPORT_DIR / "data/operations/install-time.txt"),
    str(REPORT_DIR / "data/operations/uname.txt"),
    str(REPORT_DIR / "data/operations/uninstall.txt"),
    str(REPORT_DIR / "data/operations/venv-time.txt"),
    str(REPORT_DIR / "data/privacy/exception.stderr.txt"),
    str(REPORT_DIR / "data/privacy/normal.stderr.txt"),
    str(REPORT_DIR / "data/privacy/residue-modes.txt"),
    str(REPORT_DIR / "data/privacy/wait.stderr.txt"),
}
EXPECTED_HASHED_EVIDENCE_IDS = {
    *(f"EV-{value:03d}" for value in range(13, 24)),
    "EV-027",
    "EV-028",
    "EV-029",
}
EXPECTED_NA_SHA_BY_ID = {
    **{f"EV-{value:03d}": "N/A_pinned_git_object_19815e3147503f78a06e263255667e237830bab9" for value in range(1, 8)},
    **{f"EV-{value:03d}": "N/A_pinned_git_object_cf0f7e3a7db149f8b73006f9bca8bb97df880704" for value in range(8, 13)},
    "EV-024": "N/A_generated_annotation",
    "EV-025": "N/A_sealed_methodology",
    "EV-026": "N/A_synthesis_input",
}
COMPATIBILITY_FILES = {
    str(MISSION_DIR / "tasks.md"),
    str(MISSION_DIR / "tasks/.gitkeep"),
    str(MISSION_DIR / "tasks/README.md"),
    str(MISSION_DIR / "tasks/WP01-research-closeout-acceptance.md"),
    str(MISSION_DIR / "status.json"),
    str(COMPATIBILITY_ROOT / "research/README.md"),
    str(COMPATIBILITY_ROOT / "data/README.md"),
    str(COMPATIBILITY_ROOT / "findings/README.md"),
    str(COMPATIBILITY_ROOT / "reports/README.md"),
}
COMPATIBILITY_POINTERS = {
    str(COMPATIBILITY_ROOT / "research/README.md"): MISSION_DIR / "research",
    str(COMPATIBILITY_ROOT / "data/README.md"): REPORT_DIR / "data",
    str(COMPATIBILITY_ROOT / "findings/README.md"): MISSION_DIR / "findings.md",
    str(COMPATIBILITY_ROOT / "reports/README.md"): REPORT_DIR / "report.md",
}
REQUIRED_ABSENT_COMPATIBILITY_FILES = {str(MISSION_DIR / "acceptance-matrix.json")}
SUBSTANTIVE_REVIEW_PATHS = tuple(sorted((EXACT_ARTIFACTS - {str(MISSION_DIR / "research/adversarial-reviews.md")}) | COMPATIBILITY_FILES))


def sha256(path: Path) -> str:
    # Publication file-integrity checksum, not a charter semantic hash.
    digest = hashlib.sha256()  # noqa: TID251
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def confined_path(repo: Path, raw_path: str) -> Path | None:
    relative = Path(raw_path)
    if relative.is_absolute() or ".." in relative.parts:
        return None
    resolved = (repo / relative).resolve()
    return resolved if resolved.is_relative_to(repo.resolve()) else None


def verify_file_record(
    repo: Path,
    record: dict[str, object],
    errors: list[str],
    *,
    context: str,
) -> bool:
    raw_path = str(record.get("path", ""))
    path = confined_path(repo, raw_path)
    if path is None:
        errors.append(f"{context}: path escapes repository: {raw_path}")
        return False
    if not path.is_file():
        errors.append(f"{context}: missing file: {raw_path}")
        return False
    actual_bytes = path.stat().st_size
    actual_sha = sha256(path)
    if actual_bytes != record.get("bytes"):
        errors.append(f"{context}: byte mismatch: {raw_path} expected={record.get('bytes')} actual={actual_bytes}")
    if actual_sha != record.get("sha256"):
        errors.append(f"{context}: sha256 mismatch: {raw_path} expected={record.get('sha256')} actual={actual_sha}")
    return actual_bytes == record.get("bytes") and actual_sha == record.get("sha256")


def expand_evidence_references(text: str) -> set[str]:
    references = set(EVIDENCE_PATTERN.findall(text))
    for start_text, end_text in EVIDENCE_RANGE_PATTERN.findall(text):
        start, end = int(start_text), int(end_text)
        references.update(f"EV-{value:03d}" for value in range(start, end + 1))
    return references


def verify_preregistration(repo: Path, errors: list[str]) -> bool:
    verifier = repo / MISSION_DIR / "research/verify_preregistration.py"
    result = subprocess.run(
        [sys.executable, str(verifier)],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        errors.append(f"preregistration verification failed: {result.stderr.strip()}")
        return False
    return True


def verify_reviewed_revision(
    repo: Path,
    event: dict[str, object],
    paths: tuple[str, ...],
    errors: list[str],
) -> bool:
    revision = str(event.get("reviewed_revision", ""))
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        errors.append("publication gate lacks a full reviewed_revision")
        return False
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", revision, "HEAD"],
        cwd=repo,
        check=False,
    )
    if ancestor.returncode:
        errors.append("reviewed revision is not an ancestor of HEAD")
        return False
    valid = True
    for path in paths:
        try:
            reviewed_blob = git(repo, "rev-parse", f"{revision}:{path}")
            current_blob = git(repo, "hash-object", path)
        except subprocess.CalledProcessError:
            errors.append(f"reviewed revision does not contain {path}")
            valid = False
            continue
        if reviewed_blob != current_blob:
            errors.append(f"publication artifact changed after review: {path}")
            valid = False
    return valid


def verify(require_gate: bool) -> dict[str, object]:  # noqa: C901, PLR0915
    repo = Path(__file__).resolve().parents[3]
    manifest_path = repo / REPORT_DIR / "publication-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors: list[str] = []

    if manifest.get("schema_version") != 1 or manifest.get("mission") != MISSION:
        errors.append("publication manifest schema or mission identity mismatch")
    artifacts = manifest.get("artifacts", [])
    artifact_paths = [str(record.get("path", "")) for record in artifacts]
    if len(artifact_paths) != len(set(artifact_paths)):
        errors.append("publication manifest contains duplicate artifact paths")
    if set(artifact_paths) != EXACT_ARTIFACTS:
        errors.append("publication manifest does not match the exact direct-artifact inventory")
    expected_exclusions = {
        str(REPORT_DIR / "publication-manifest.json"),
        str(MISSION_DIR / "mission-events.jsonl"),
        str(MISSION_DIR / "meta.json"),
        str(MISSION_DIR / "status.events.jsonl"),
        str(MISSION_DIR / "traces"),
    }
    actual_exclusions = {str(record.get("path", "")) for record in manifest.get("artifact_hash_exclusions", [])}
    if actual_exclusions != expected_exclusions:
        errors.append("publication manifest artifact exclusions are incomplete or unexpected")
    expected_compatibility_contract = {
        "schema_version": 1,
        "authority": "acceptance_projection_not_research_evidence",
        "paths": sorted(COMPATIBILITY_FILES),
        "required_absent": sorted(REQUIRED_ABSENT_COMPATIBILITY_FILES),
    }
    if manifest.get("compatibility_contract") != expected_compatibility_contract:
        errors.append("publication manifest compatibility contract is incomplete or unexpected")
    for record in artifacts:
        verify_file_record(repo, record, errors, context="publication artifact")

    prereg_path = repo / MISSION_DIR / "research/preregistration-manifest.json"
    prereg = json.loads(prereg_path.read_text(encoding="utf-8"))
    if manifest.get("preregistration_tree_sha256") != prereg.get("tree_sha256"):
        errors.append("publication/preregistration tree hashes differ")
    if manifest.get("docling_graph_revision") != prereg.get("docling_graph_revision"):
        errors.append("publication/preregistration Docling Graph revisions differ")
    if not str(manifest.get("spec_kitty_revision", "")).startswith(str(prereg.get("spec_kitty_baseline", ""))):
        errors.append("publication/preregistration Spec Kitty revisions differ")
    prereg_rel = str(MISSION_DIR / "research/preregistration-manifest.json")
    sealed_prereg_blob = git(
        repo,
        "rev-parse",
        f"{manifest['preregistration_commit']}:{prereg_rel}",
    )
    if sealed_prereg_blob != git(repo, "hash-object", prereg_rel):
        errors.append("current preregistration manifest differs from sealed commit")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", manifest["preregistration_commit"], "HEAD"],
        cwd=repo,
        check=False,
    )
    if ancestor.returncode:
        errors.append("preregistration commit is not an ancestor of HEAD")
    prereg_records = prereg.get("files", [])
    prereg_paths = [str(record["path"]) for record in prereg_records]
    if len(prereg_paths) != 32 or len(set(prereg_paths)) != 32:
        errors.append("preregistration manifest must contain 32 unique files")
    for sealed_record in prereg_records:
        sealed_path = str(sealed_record["path"])
        try:
            sealed_file_blob = git(
                repo,
                "rev-parse",
                f"{manifest['preregistration_commit']}:{sealed_path}",
            )
            current_file_blob = git(repo, "hash-object", sealed_path)
        except subprocess.CalledProcessError:
            errors.append(f"sealed preregistration file unavailable: {sealed_path}")
            continue
        if sealed_file_blob != current_file_blob:
            errors.append(f"preregistered file differs from sealed commit: {sealed_path}")
    preregistration_verified = verify_preregistration(repo, errors)

    transitive_paths: list[str] = []
    execution_manifests = [record for record in artifacts if str(record.get("path", "")).endswith("execution-manifest.json")]
    if len(execution_manifests) != 6:
        errors.append(f"expected 6 execution manifests; got {len(execution_manifests)}")
    if {str(record["path"]) for record in execution_manifests} != set(EXPECTED_EXECUTION_COUNTS):
        errors.append("execution-manifest path set mismatch")
    for record in execution_manifests:
        execution_path = repo / str(record["path"])
        execution = json.loads(execution_path.read_text(encoding="utf-8"))
        if execution.get("executed_after_seal") is not True:
            errors.append(f"{record['path']}: not declared executed_after_seal")
        for key in ("docling_graph_revision", "preregistration_commit", "preregistration_tree_sha256"):
            if execution.get(key) != manifest.get(key):
                errors.append(f"{record['path']}: inconsistent {key}")
        nested_records = list(execution.get("files", []))
        if execution.get("procedure"):
            nested_records.append(execution["procedure"])
        if len(nested_records) != EXPECTED_EXECUTION_COUNTS.get(str(record["path"])):
            errors.append(f"{record['path']}: unexpected nested record count")
        for nested in nested_records:
            transitive_paths.append(str(nested["path"]))
            verify_file_record(repo, nested, errors, context=str(record["path"]))
    if len(transitive_paths) != 183 or len(set(transitive_paths)) != 183:
        errors.append("execution manifests must cover 183 unique files/procedures")

    report_rel = str(REPORT_DIR / "report.md")
    sealed_blob = git(
        repo,
        "rev-parse",
        f"{manifest['report_source_commit']}:{report_rel}",
    )
    current_blob = git(repo, "hash-object", report_rel)
    expected_blob = manifest["report_git_blob"]
    if sealed_blob != expected_blob:
        errors.append(f"sealed report blob mismatch: {sealed_blob} != {expected_blob}")
    if current_blob != expected_blob:
        errors.append(f"current report blob mismatch: {current_blob} != {expected_blob}")

    pointer = (repo / MISSION_DIR / "report.md").read_text(encoding="utf-8")
    report_record = next(record for record in manifest["artifacts"] if record["path"] == report_rel)
    for token in (
        report_record["sha256"],
        manifest["report_git_blob"],
        manifest["report_source_commit"],
    ):
        if token not in pointer:
            errors.append(f"publication pointer omits integrity token: {token}")

    source_register = repo / MISSION_DIR / "source-register.csv"
    nested_register = repo / MISSION_DIR / "research/source-register.csv"
    if source_register.read_bytes() != nested_register.read_bytes():
        errors.append("root and research source registers are not byte-identical")

    scorecard = read_csv(repo / REPORT_DIR / "option-scorecard.csv")
    candidates = read_csv(repo / MISSION_DIR / "research/candidate-registry.csv")
    candidate_ids = {row["candidate_id"] for row in candidates}
    score_ids = {row["candidate_id"] for row in scorecard}
    if len(candidate_ids) != 21 or len(candidates) != 21:
        errors.append(f"candidate registry must contain 21 unique rows; got {len(candidate_ids)}")
    if score_ids != candidate_ids or len(scorecard) != 21:
        errors.append("scorecard and candidate registry IDs differ or are not one-to-one")

    gate_columns = (
        "fidelity",
        "provenance",
        "semantic_quality",
        "utility",
        "lifecycle_identity",
        "privacy",
        "operational_default",
        "cross_platform",
        "consumer_migration",
    )
    valid_gate_values = {"PASS", "FAIL", "UNKNOWN", "N/A"}
    valid_dispositions = {
        "RETAIN_CONTROL",
        "DEFER_UNEVALUATED",
        "REJECT",
        "PRUNED_REJECT",
        "SCORED_CANDIDATE",
    }
    for row in scorecard:
        candidate = row["candidate_id"]
        gates = [row[column] for column in gate_columns]
        invalid = set(gates) - valid_gate_values
        if invalid:
            errors.append(f"{candidate}: invalid gate values {sorted(invalid)}")
        disposition = row["disposition"]
        if disposition not in valid_dispositions:
            errors.append(f"{candidate}: invalid disposition {disposition}")
        if candidate in {"C0", "C1"} and disposition != "RETAIN_CONTROL":
            errors.append(f"{candidate}: control must retain RETAIN_CONTROL disposition")
        if candidate not in {"C0", "C1"} and disposition == "RETAIN_CONTROL":
            errors.append(f"{candidate}: only C0/C1 may retain control disposition")
        if disposition in {"REJECT", "PRUNED_REJECT"} and "FAIL" not in gates:
            errors.append(f"{candidate}: {disposition} requires an observed FAIL")
        if "FAIL" in gates and disposition not in {"REJECT", "PRUNED_REJECT"}:
            errors.append(f"{candidate}: an observed FAIL requires rejection")
        if disposition.startswith("DEFER") and "UNKNOWN" not in gates:
            errors.append(f"{candidate}: DEFER requires an UNKNOWN gate")
        if candidate not in {"C0", "C1"} and "UNKNOWN" in gates and "FAIL" not in gates and not disposition.startswith("DEFER"):
            errors.append(f"{candidate}: UNKNOWN without FAIL requires deferral")
        all_applicable_pass = all(gate in {"PASS", "N/A"} for gate in gates)
        numeric_score = not row["weighted_score"].startswith("N/A")
        if candidate not in {"C0", "C1"} and all_applicable_pass and (disposition != "SCORED_CANDIDATE" or not numeric_score):
            errors.append(f"{candidate}: all-PASS candidate must be scored")
        if disposition == "SCORED_CANDIDATE" and not all_applicable_pass:
            errors.append(f"{candidate}: only all-PASS candidates may be scored")
        if numeric_score:
            if not all_applicable_pass:
                errors.append(f"{candidate}: non-PASS candidate cannot receive a weighted score")
            try:
                weighted_score = float(row["weighted_score"])
            except ValueError:
                errors.append(f"{candidate}: weighted score is neither numeric nor N/A")
            else:
                if not math.isfinite(weighted_score) or not 0.0 <= weighted_score <= 5.0:
                    errors.append(f"{candidate}: weighted score must be finite and within 0–5")

    evidence_rows = read_csv(repo / MISSION_DIR / "research/evidence-log.csv")
    expected_evidence_columns = {
        "evidence_id",
        "timestamp",
        "evidence_kind",
        "source_id",
        "claim",
        "method",
        "confidence",
        "limitation",
        "raw_result",
        "raw_sha256",
    }
    if set(evidence_rows[0]) != expected_evidence_columns:
        errors.append("evidence log schema mismatch")
    evidence_ids = {row["evidence_id"] for row in evidence_rows}
    if len(evidence_rows) != len(evidence_ids):
        errors.append("evidence log contains duplicate evidence IDs")
    if evidence_ids != {f"EV-{value:03d}" for value in range(1, 30)}:
        errors.append("evidence log must contain exactly EV-001 through EV-029")
    source_rows = read_csv(repo / MISSION_DIR / "research/source-register.csv")
    expected_source_columns = {"source_id", "citation", "url", "accessed_date", "relevance", "status"}
    if set(source_rows[0]) != expected_source_columns:
        errors.append("source register schema mismatch")
    source_ids = {row["source_id"] for row in source_rows}
    if len(source_rows) != len(source_ids):
        errors.append("source register contains duplicate source IDs")
    hashed_evidence_ids = {row["evidence_id"] for row in evidence_rows if SHA256_PATTERN.fullmatch(row["raw_sha256"])}
    if hashed_evidence_ids != EXPECTED_HASHED_EVIDENCE_IDS:
        errors.append("hashed evidence-ID set differs from the sealed 14-row contract")
    evidence_raw_files = 0
    for row in evidence_rows:
        unknown_sources = set(row["source_id"].split(";")) - source_ids
        if unknown_sources:
            errors.append(f"{row['evidence_id']}: unknown source IDs {sorted(unknown_sources)}")
        if row["evidence_id"] in EXPECTED_NA_SHA_BY_ID:
            if row["raw_sha256"] != EXPECTED_NA_SHA_BY_ID[row["evidence_id"]]:
                errors.append(f"{row['evidence_id']}: invalid non-file evidence hash token")
            continue
        if not SHA256_PATTERN.fullmatch(row["raw_sha256"]):
            errors.append(f"{row['evidence_id']}: raw_sha256 is neither sealed hash nor approved N/A token")
            continue
        evidence_raw_files += 1
        raw_path = confined_path(repo, row["raw_result"])
        if raw_path is None or not raw_path.is_file():
            errors.append(f"{row['evidence_id']}: missing or unconfined raw_result")
        elif sha256(raw_path) != row["raw_sha256"]:
            errors.append(f"{row['evidence_id']}: raw_result sha256 mismatch")
    reference_paths = (
        repo / REPORT_DIR / "report.md",
        repo / REPORT_DIR / "risk-register.md",
        repo / REPORT_DIR / "option-scorecard.csv",
        repo / MISSION_DIR / "findings.md",
        repo / MISSION_DIR / "report.md",
        repo / MISSION_DIR / "research/adversarial-reviews.md",
    )
    cited_ids: set[str] = set()
    for path in reference_paths:
        cited_ids.update(expand_evidence_references(path.read_text(encoding="utf-8")))
    unresolved = cited_ids - evidence_ids
    if unresolved:
        errors.append(f"unresolved evidence references: {sorted(unresolved)}")

    redaction_path = repo / REPORT_DIR / "data/redaction-manifest.json"
    redaction = json.loads(redaction_path.read_text(encoding="utf-8"))
    redaction_records = redaction.get("files", [])
    redaction_paths = {str(record.get("path", "")) for record in redaction_records}
    if redaction_paths != EXPECTED_REDACTION_PATHS or len(redaction_records) != 8:
        errors.append("redaction manifest must contain the exact 8-path publication set")
    for record in redaction_records:
        raw_path = confined_path(repo, str(record.get("path", "")))
        if raw_path is None or not raw_path.is_file():
            errors.append(f"redaction manifest path missing or unconfined: {record.get('path')}")
        elif sha256(raw_path) != record.get("published_sha256"):
            errors.append(f"redaction published hash mismatch: {record.get('path')}")

    empirical_rows = read_csv(repo / MISSION_DIR / "research/empirical-evidence-register.csv")
    expected_empirical_columns = {
        "probe_id",
        "result",
        "sha256",
        "execution_manifest",
        "platform",
        "scope",
    }
    if set(empirical_rows[0]) != expected_empirical_columns:
        errors.append("empirical evidence register schema mismatch")
    probe_ids = {row["probe_id"] for row in empirical_rows}
    if probe_ids != EXPECTED_EMPIRICAL_PROBES or len(empirical_rows) != 6:
        errors.append("empirical evidence register must contain the exact 6-probe set")
    for row in empirical_rows:
        result_path = confined_path(repo, row["result"])
        if result_path is None or not result_path.is_file():
            errors.append(f"{row['probe_id']}: missing or unconfined empirical result")
        elif sha256(result_path) != row["sha256"]:
            errors.append(f"{row['probe_id']}: empirical result sha256 mismatch")
        if row["execution_manifest"] not in artifact_paths:
            errors.append(f"{row['probe_id']}: execution manifest is not publication-sealed")
            continue
        execution = json.loads((repo / row["execution_manifest"]).read_text(encoding="utf-8"))
        if execution.get("probe_id") != row["probe_id"]:
            errors.append(f"{row['probe_id']}: execution-manifest probe ID mismatch")
        if row["result"] != row["execution_manifest"]:
            result_records = {(str(record.get("path", "")), str(record.get("sha256", ""))) for record in execution.get("files", [])}
            if (row["result"], row["sha256"]) not in result_records:
                errors.append(f"{row['probe_id']}: result/hash absent from execution manifest")

    for raw_path in sorted(COMPATIBILITY_FILES):
        path = confined_path(repo, raw_path)
        if path is None or not path.is_file():
            errors.append(f"compatibility contract file missing or unconfined: {raw_path}")
            continue
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", raw_path],
            cwd=repo,
            check=False,
            capture_output=True,
        )
        if tracked.returncode:
            errors.append(f"compatibility contract file is not tracked: {raw_path}")

    pointer_files = set(git(repo, "ls-files", str(COMPATIBILITY_ROOT)).splitlines())
    if pointer_files != set(COMPATIBILITY_POINTERS):
        errors.append("legacy acceptance projection must contain exactly four tracked pointer READMEs")
    local_pointer_files = {str(path.relative_to(repo)) for path in (repo / COMPATIBILITY_ROOT).rglob("*") if path.is_file()}
    if local_pointer_files != set(COMPATIBILITY_POINTERS):
        errors.append("legacy acceptance projection contains untracked or unexpected files")
    for raw_path, expected_target in COMPATIBILITY_POINTERS.items():
        pointer_path = repo / raw_path
        if not pointer_path.is_file():
            continue
        pointer_text = pointer_path.read_text(encoding="utf-8")
        links = re.findall(r"\]\(([^)]+)\)", pointer_text)
        if not pointer_text.startswith("# Acceptance compatibility pointer\n") or "legacy Deep Research path contract" not in pointer_text or len(links) != 1:
            errors.append(f"compatibility pointer content contract failed: {raw_path}")
            continue
        resolved_target = (pointer_path.parent / links[0]).resolve()
        if resolved_target != (repo / expected_target).resolve() or not resolved_target.exists():
            errors.append(f"compatibility pointer target mismatch: {raw_path}")

    expected_task_files = {
        str(MISSION_DIR / "tasks/.gitkeep"),
        str(MISSION_DIR / "tasks/README.md"),
        str(MISSION_DIR / "tasks/WP01-research-closeout-acceptance.md"),
    }
    if set(git(repo, "ls-files", str(MISSION_DIR / "tasks")).splitlines()) != expected_task_files:
        errors.append("acceptance compatibility task directory does not match its exact three-file contract")
    task_index = (repo / MISSION_DIR / "tasks.md").read_text(encoding="utf-8")
    if (
        "compatibility projection" not in task_index
        or "21bcce5a70b72e385fad77954a9f45d7806b7835" not in task_index
        or "not canonical `requirement_refs`" not in task_index
    ):
        errors.append("acceptance compatibility task index omits authority or lifecycle disclosures")
    wp_text = (repo / MISSION_DIR / "tasks/WP01-research-closeout-acceptance.md").read_text(encoding="utf-8")
    for token in (
        "requirement_refs: []",
        "https://github.com/Priivacy-ai/spec-kitty/issues/3546",
        "migrate backfill-runtime-state",
        "`force:false`",
    ):
        if token not in wp_text:
            errors.append(f"acceptance compatibility WP omits required disclosure: {token}")
    if re.search(r"^requirement_refs:\s*\[(?!\])", wp_text, flags=re.MULTILINE):
        errors.append("acceptance compatibility WP falsely claims canonical requirement refs")
    for raw_path in REQUIRED_ABSENT_COMPATIBILITY_FILES:
        if (repo / raw_path).exists():
            errors.append(f"planning-artifact-only research mission must not materialize {raw_path}")

    status_result = subprocess.run(
        [sys.executable, "-m", "specify_cli", "agent", "status", "validate", "--mission", MISSION, "--json"],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )
    try:
        status_validation = json.loads(status_result.stdout)
    except json.JSONDecodeError:
        status_validation = {}
    if status_result.returncode or status_validation.get("passed") is not True:
        errors.append("canonical acceptance status replay failed")
    status = json.loads((repo / MISSION_DIR / "status.json").read_text(encoding="utf-8"))
    wp_status = status.get("work_packages", {}).get("WP01", {})
    if status.get("mission_slug") != MISSION or status.get("mission_type") != "research":
        errors.append("acceptance status mission identity/type mismatch")
    if wp_status.get("lane") not in {"for_review", "in_review", "approved", "done"}:
        errors.append("acceptance compatibility WP is not in a review-or-terminal lane")
    if wp_status.get("force_count") != 0:
        errors.append("acceptance compatibility WP used a forced transition")
    if wp_status.get("subtasks") != {f"T{value:03d}": "done" for value in range(1, 5)}:
        errors.append("acceptance compatibility WP subtask projection mismatch")

    covered_paths = set(artifact_paths) | set(prereg_paths) | set(transitive_paths) | COMPATIBILITY_FILES
    tracked_scope = set(git(repo, "ls-files", str(REPORT_DIR), str(MISSION_DIR), str(COMPATIBILITY_ROOT)).splitlines())
    uncovered = {
        path
        for path in tracked_scope
        if path not in covered_paths and not any(path == excluded or path.startswith(f"{excluded}/") for excluded in actual_exclusions)
    }
    if uncovered:
        errors.append(f"tracked publication closure has unaccounted paths: {sorted(uncovered)}")

    expected_gate_spec = {
        "event_type": "gate_passed",
        "name": "publication_approved",
        "path": str(MISSION_DIR / "mission-events.jsonl"),
    }
    if manifest.get("publication_gate") != expected_gate_spec:
        errors.append("publication gate specification is not canonical")
    gate_path = confined_path(repo, expected_gate_spec["path"])
    if gate_path is None or not gate_path.is_file():
        errors.append("canonical publication gate path is missing or unconfined")
        events_path = repo / MISSION_DIR / "mission-events.jsonl"
    else:
        events_path = gate_path

    review_path = repo / MISSION_DIR / "research/adversarial-reviews.md"
    review_lines = [line for line in review_path.read_text(encoding="utf-8").splitlines() if "| Publication integrity, round 2 |" in line]
    review_cells = [cell.strip() for cell in review_lines[0].strip().strip("|").split("|")] if len(review_lines) == 1 else []
    ledger_reviewed_revision = review_cells[3] if len(review_cells) == 6 else ""
    review_approved = len(review_cells) == 6 and re.fullmatch(r"[0-9a-f]{40}", ledger_reviewed_revision) is not None and review_cells[5] == "APPROVE"
    if not review_approved:
        errors.append("adversarial ledger does not record round-2 APPROVE")

    gate_found = False
    approval_events: list[dict[str, object]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        event_type = event.get("type", event.get("event_type"))
        if event_type == "gate_passed" and event.get("name") == "publication_approved":
            approval_events.append(event)
    if approval_events:
        event = approval_events[-1]
        expected_gate = {
            "verdict": "APPROVE",
            "review_kind": "final-seal-receipt",
            "reviewed_content_revision": ledger_reviewed_revision,
            "publication_manifest_sha256": sha256(manifest_path),
            "report_sha256": report_record["sha256"],
            "report_git_blob": manifest["report_git_blob"],
            "report_source_commit": manifest["report_source_commit"],
            "review_ledger_sha256": sha256(review_path),
        }
        gate_found = all(event.get(key) == value for key, value in expected_gate.items())
        gate_found = gate_found and set(event.get("reviewers", [])) == EXPECTED_REVIEWERS
        try:
            timestamp = str(event.get("timestamp", ""))
            if RFC3339_PATTERN.fullmatch(timestamp) is None:
                raise ValueError("timestamp is not strict RFC3339")
            event_time = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            revision_time = datetime.fromisoformat(git(repo, "show", "-s", "--format=%cI", str(event.get("reviewed_revision", ""))))
            verification_time = datetime.now(tz=event_time.tzinfo)
            gate_found = gate_found and event_time.tzinfo is not None and revision_time < event_time <= verification_time + timedelta(minutes=5)
        except (ValueError, subprocess.CalledProcessError):
            gate_found = False
        gate_found = gate_found and review_approved
        if gate_found:
            gate_found = verify_reviewed_revision(
                repo,
                {"reviewed_revision": ledger_reviewed_revision},
                SUBSTANTIVE_REVIEW_PATHS,
                errors,
            )
        if gate_found:
            gate_found = verify_reviewed_revision(
                repo,
                event,
                (
                    str(REPORT_DIR / "publication-manifest.json"),
                    str(REPORT_DIR / "report.md"),
                    str(MISSION_DIR / "report.md"),
                    str(MISSION_DIR / "research/adversarial-reviews.md"),
                    str(MISSION_DIR / "research/verify_publication.py"),
                    *sorted(COMPATIBILITY_FILES),
                ),
                errors,
            )
    if require_gate and not gate_found:
        errors.append("exact hash-bound publication_approved gate event not found")

    for raw_path in artifact_paths:
        tracked = subprocess.run(
            ["git", "ls-files", "--error-unmatch", raw_path],
            cwd=repo,
            check=False,
            capture_output=True,
        )
        if tracked.returncode:
            errors.append(f"publication artifact is not tracked: {raw_path}")
    dirty = git(repo, "status", "--porcelain", "--untracked-files=all")
    if dirty:
        errors.append("repository is not clean during sealed publication verification")

    result: dict[str, object] = {
        "status": "PASS" if not errors else "FAIL",
        "artifacts_verified": len(artifacts),
        "compatibility_files_verified": len(COMPATIBILITY_FILES),
        "transitive_files_verified": len(transitive_paths),
        "evidence_raw_files_verified": evidence_raw_files,
        "preregistration_verified": preregistration_verified,
        "candidate_rows_verified": len(scorecard),
        "evidence_references_verified": len(cited_ids),
        "report_git_blob": current_blob,
        "publication_gate_found": gate_found,
        "errors": errors,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="verify a pre-approval publication while explicitly allowing the gate to be absent",
    )
    args = parser.parse_args()
    result = verify(require_gate=not args.preflight)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
