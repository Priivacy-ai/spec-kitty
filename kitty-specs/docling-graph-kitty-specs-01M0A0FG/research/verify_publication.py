#!/usr/bin/env python3
"""Verify the sealed Docling Graph research publication without changing it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


MISSION = "docling-graph-kitty-specs-01M0A0FG"
REPORT_DIR = Path("docs/research/docling-graph-kitty-specs")
MISSION_DIR = Path("kitty-specs") / MISSION
EVIDENCE_PATTERN = re.compile(r"EV-\d{3}")
EVIDENCE_RANGE_PATTERN = re.compile(r"EV-(\d{3})[–-]EV-(\d{3})")
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
EXPECTED_REVIEWERS = {
    "/root/postgather_authority:architect-alphonso",
    "/root/postgather_claims:reviewer-renata",
    "/root/postgather_empirical:debugger-debbie",
}
REQUIRED_ARTIFACTS = {
    str(REPORT_DIR / "report.md"),
    str(REPORT_DIR / "option-scorecard.csv"),
    str(REPORT_DIR / "risk-register.md"),
    str(MISSION_DIR / "report.md"),
    str(MISSION_DIR / "spec.md"),
    str(MISSION_DIR / "plan.md"),
    str(MISSION_DIR / "findings.md"),
    str(MISSION_DIR / "research/adversarial-reviews.md"),
    str(MISSION_DIR / "research/contradictions.csv"),
    str(MISSION_DIR / "research/empirical-evidence-register.csv"),
    str(MISSION_DIR / "research/evidence-log.csv"),
    str(MISSION_DIR / "research/execution-ledger.jsonl"),
    str(MISSION_DIR / "research/preregistration-manifest.json"),
    str(MISSION_DIR / "research/verify_publication.py"),
}


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
    missing_required = REQUIRED_ARTIFACTS - set(artifact_paths)
    if missing_required:
        errors.append(f"publication manifest omits required artifacts: {sorted(missing_required)}")
    expected_exclusions = {
        str(REPORT_DIR / "publication-manifest.json"),
        str(MISSION_DIR / "mission-events.jsonl"),
        str(MISSION_DIR / "lifecycle.jsonl"),
        str(MISSION_DIR / "status.events.jsonl"),
        str(MISSION_DIR / "traces"),
    }
    actual_exclusions = {str(record.get("path", "")) for record in manifest.get("artifact_hash_exclusions", [])}
    if actual_exclusions != expected_exclusions:
        errors.append("publication manifest artifact exclusions are incomplete or unexpected")
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
    for sealed_record in prereg.get("files", []):
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

    transitive_files = 0
    execution_manifests = [record for record in artifacts if str(record.get("path", "")).endswith("execution-manifest.json")]
    if len(execution_manifests) != 6:
        errors.append(f"expected 6 execution manifests; got {len(execution_manifests)}")
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
        for nested in nested_records:
            transitive_files += 1
            verify_file_record(repo, nested, errors, context=str(record["path"]))

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
    valid_dispositions = {"RETAIN_CONTROL", "DEFER_UNEVALUATED", "REJECT", "PRUNED_REJECT"}
    for row in scorecard:
        candidate = row["candidate_id"]
        gates = [row[column] for column in gate_columns]
        invalid = set(gates) - valid_gate_values
        if invalid:
            errors.append(f"{candidate}: invalid gate values {sorted(invalid)}")
        disposition = row["disposition"]
        if disposition not in valid_dispositions:
            errors.append(f"{candidate}: invalid disposition {disposition}")
        if disposition in {"REJECT", "PRUNED_REJECT"} and "FAIL" not in gates:
            errors.append(f"{candidate}: {disposition} requires an observed FAIL")
        if "FAIL" in gates and disposition not in {"REJECT", "PRUNED_REJECT"}:
            errors.append(f"{candidate}: an observed FAIL requires rejection")
        if disposition.startswith("DEFER") and "UNKNOWN" not in gates:
            errors.append(f"{candidate}: DEFER requires an UNKNOWN gate")
        if candidate not in {"C0", "C1"} and "UNKNOWN" in gates and "FAIL" not in gates and not disposition.startswith("DEFER"):
            errors.append(f"{candidate}: UNKNOWN without FAIL requires deferral")
        if not row["weighted_score"].startswith("N/A"):
            if any(gate in {"FAIL", "UNKNOWN"} for gate in gates):
                errors.append(f"{candidate}: non-PASS candidate cannot receive a weighted score")
            try:
                float(row["weighted_score"])
            except ValueError:
                errors.append(f"{candidate}: weighted score is neither numeric nor N/A")

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
    source_rows = read_csv(repo / MISSION_DIR / "research/source-register.csv")
    expected_source_columns = {"source_id", "citation", "url", "accessed_date", "relevance", "status"}
    if set(source_rows[0]) != expected_source_columns:
        errors.append("source register schema mismatch")
    source_ids = {row["source_id"] for row in source_rows}
    if len(source_rows) != len(source_ids):
        errors.append("source register contains duplicate source IDs")
    evidence_raw_files = 0
    for row in evidence_rows:
        unknown_sources = set(row["source_id"].split(";")) - source_ids
        if unknown_sources:
            errors.append(f"{row['evidence_id']}: unknown source IDs {sorted(unknown_sources)}")
        if not SHA256_PATTERN.fullmatch(row["raw_sha256"]):
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
    for record in redaction.get("files", []):
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
    if len(probe_ids) != len(empirical_rows):
        errors.append("empirical evidence register contains duplicate probe IDs")
    for row in empirical_rows:
        result_path = confined_path(repo, row["result"])
        if result_path is None or not result_path.is_file():
            errors.append(f"{row['probe_id']}: missing or unconfined empirical result")
        elif sha256(result_path) != row["sha256"]:
            errors.append(f"{row['probe_id']}: empirical result sha256 mismatch")
        if row["execution_manifest"] not in artifact_paths:
            errors.append(f"{row['probe_id']}: execution manifest is not publication-sealed")

    gate_found = False
    events_path = repo / manifest["publication_gate"]["path"]
    approval_events: list[dict[str, object]] = []
    for line in events_path.read_text(encoding="utf-8").splitlines():
        event = json.loads(line)
        event_type = event.get("type", event.get("event_type"))
        if event_type == "gate_passed" and event.get("name") == "publication_approved":
            approval_events.append(event)
    if approval_events:
        event = approval_events[-1]
        review_path = repo / MISSION_DIR / "research/adversarial-reviews.md"
        expected_gate = {
            "verdict": "APPROVE",
            "publication_manifest_sha256": sha256(manifest_path),
            "report_sha256": report_record["sha256"],
            "report_git_blob": manifest["report_git_blob"],
            "report_source_commit": manifest["report_source_commit"],
            "review_ledger_sha256": sha256(review_path),
        }
        gate_found = all(event.get(key) == value for key, value in expected_gate.items())
        gate_found = gate_found and set(event.get("reviewers", [])) == EXPECTED_REVIEWERS
        gate_found = gate_found and bool(event.get("timestamp"))
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
        "transitive_files_verified": transitive_files,
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
