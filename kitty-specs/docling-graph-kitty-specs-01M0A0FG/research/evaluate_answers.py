#!/usr/bin/env python3
"""Execute a generic candidate against original and transformed sealed fixtures."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import yaml

ANSWER_FIELDS = [
    "query_id",
    "fixture_id",
    "atom_type",
    "subject",
    "predicate",
    "object",
    "source_path",
    "source_blob",
    "start_byte",
    "end_byte",
    "status",
]


def replace(value: str, replacements: dict[str, str]) -> str:
    for old in sorted(replacements, key=len, reverse=True):
        value = value.replace(old, replacements[old])
    return value


def apply_bytes(data: bytes, replacements: dict[str, str]) -> bytes:
    return replace(data.decode("utf-8"), replacements).encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--candidate-source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    research = Path(__file__).resolve().parent
    gold_path = research / "fixtures" / "gold" / "gold-approved.csv"
    with gold_path.open(newline="", encoding="utf-8") as handle:
        gold = list(csv.DictReader(handle))
    query = yaml.safe_load((research / "query-registry.yaml").read_text(encoding="utf-8"))
    revision = query["baseline_revision"]
    public = yaml.safe_load((research / "fixtures" / "metamorphic-fixtures.yaml").read_text(encoding="utf-8"))["mutations"]
    heldout = yaml.safe_load((research / "fixtures" / "withheld-mutations.yaml").read_text(encoding="utf-8"))["mutations"]

    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in ([args.candidate_source] if args.candidate_source.is_file() else sorted(args.candidate_source.rglob("*")))
        if path.is_file()
    )
    banned = (
        {row["fixture_id"] for row in gold}
        | {row["source_path"] for row in gold}
        | {row["subject"] for row in gold}
        | {row["object"] for row in gold}
        | {row["atom_id"] for row in gold}
    )
    local_id_pattern = re.compile(r"\b(?:FR|WP|AC|DR|QR|SC|NFR)-?[0-9]+\b", re.IGNORECASE)
    banned.update(match.group(0) for row in gold for value in row.values() for match in local_id_pattern.finditer(value))
    leaks = sorted(value for value in banned if value and value in source_text)
    if leaks:
        raise SystemExit(f"candidate source contains sealed fixture literals: {leaks}")

    source_paths = sorted({row["source_path"] for row in gold})
    originals = {path: subprocess.run(["git", "show", f"{revision}:{path}"], check=True, capture_output=True).stdout for path in source_paths}
    mutations = [{"id": "ORIGINAL", "replacements": {}}] + public + heldout
    run_results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="spk-sealed-evaluator-") as temp_name:
        temp = Path(temp_name)
        candidate_source = args.candidate_source.resolve()
        candidate = args.candidate.resolve()
        copied_source = temp / "candidate-source"
        if candidate_source.is_dir():
            shutil.copytree(candidate_source, copied_source)
            try:
                copied_candidate = copied_source / candidate.relative_to(candidate_source)
            except ValueError as exc:
                raise SystemExit("candidate executable must be inside candidate-source directory") from exc
        else:
            copied_source.mkdir()
            copied_candidate = copied_source / candidate.name
            shutil.copy2(candidate, copied_candidate)
        copied_candidate.chmod(copied_candidate.stat().st_mode | 0o100)
        repo = research.parents[2].resolve()
        isolation = "UNAVAILABLE:no_sandbox_exec"
        sandbox_prefix: list[str] = []
        sandbox_exec = shutil.which("sandbox-exec")
        if sandbox_exec:
            if any(character in str(repo) for character in {'"', "\\"}):
                raise SystemExit("repository path cannot be represented safely in sandbox profile")
            profile = temp / "candidate.sb"
            profile.write_text(
                "\n".join(
                    [
                        "(version 1)",
                        "(allow default)",
                        "(deny network*)",
                        f'(deny file-read* (subpath "{repo}"))',
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            sandbox_prefix = [sandbox_exec, "-f", str(profile)]
            isolation = "ENFORCED:sandbox_exec_repo_read_and_network_deny"
        candidate_env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(temp / "home"),
            "TMPDIR": str(temp),
            "NO_PROXY": "",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
        }
        (temp / "home").mkdir()
        for mutation in mutations:
            replacements = mutation["replacements"]
            documents: list[dict[str, str]] = []
            transformed: dict[str, tuple[str, bytes, str]] = {}
            for path, data in originals.items():
                new_path = replace(path, replacements)
                new_data = apply_bytes(data, replacements)
                blob = hashlib.sha256(new_data).hexdigest()  # noqa: TID251 - synthetic fixture integrity
                transformed[path] = (new_path, new_data, blob)
                documents.append(
                    {
                        "path": new_path,
                        "content_base64": base64.b64encode(new_data).decode(),
                        "content_sha256": blob,
                    }
                )
            expected: list[dict[str, str]] = []
            for row in gold:
                old_data = originals[row["source_path"]]
                old_start, old_end = int(row["start_byte"]), int(row["end_byte"])
                old_span = old_data[old_start:old_end]
                new_path, new_data, new_blob = transformed[row["source_path"]]
                new_span = apply_bytes(old_span, replacements)
                start = len(apply_bytes(old_data[:old_start], replacements))
                if new_data[start : start + len(new_span)] != new_span:
                    raise RuntimeError(f"transformed occurrence mismatch for {mutation['id']}:{row['atom_id']}")
                expected.append(
                    {
                        "query_id": row["query_id"],
                        "fixture_id": replace(row["fixture_id"], replacements),
                        "atom_type": replace(row["atom_type"], replacements),
                        "subject": replace(row["subject"], replacements),
                        "predicate": replace(row["predicate"], replacements),
                        "object": replace(row["object"], replacements),
                        "source_path": new_path,
                        "source_blob": f"sha256:{new_blob}",
                        "start_byte": str(start),
                        "end_byte": str(start + len(new_span)),
                        "status": "asserted",
                    }
                )
            bundle_path = temp / f"{mutation['id']}-bundle.json"
            queries_path = temp / f"{mutation['id']}-queries.json"
            answer_path = temp / f"{mutation['id']}-answers.csv"
            bundle_path.write_text(json.dumps({"documents": documents}), encoding="utf-8")
            queries_path.write_text(
                json.dumps(
                    {
                        "queries": [
                            {
                                "id": replace(item["id"], replacements),
                                "question": replace(item["question"], replacements),
                            }
                            for item in query["queries"]
                        ]
                    }
                ),
                encoding="utf-8",
            )
            completed = subprocess.run(
                sandbox_prefix
                + [
                    str(copied_candidate),
                    "--fixture-bundle",
                    str(bundle_path),
                    "--queries",
                    str(queries_path),
                    "--output",
                    str(answer_path),
                ],
                capture_output=True,
                text=True,
                cwd=temp,
                env=candidate_env,
            )
            actual: list[dict[str, str]] = []
            if completed.returncode == 0 and answer_path.exists():
                with answer_path.open(newline="", encoding="utf-8") as handle:
                    actual = [{field: row.get(field, "") for field in ANSWER_FIELDS} for row in csv.DictReader(handle)]
            expected_norm = sorted(tuple(row[field] for field in ANSWER_FIELDS) for row in expected)
            actual_norm = sorted(tuple(row[field] for field in ANSWER_FIELDS) for row in actual)
            run_results.append(
                {
                    "mutation": mutation["id"],
                    "returncode": completed.returncode,
                    "answer_match": actual_norm == expected_norm,
                    "eligible_for_material_utility": isolation.startswith("ENFORCED:") and actual_norm == expected_norm,
                    "expected_count": len(expected_norm),
                    "actual_count": len(actual_norm),
                    "stderr_sha256": hashlib.sha256(  # noqa: TID251 - immutable probe-log identity
                        completed.stderr.encode()
                    ).hexdigest(),
                }
            )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "isolation": isolation,
                "evidence_scope": "transparent exploratory unless every run is isolated and eligible",
                "runs": run_results,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if not all(row["eligible_for_material_utility"] for row in run_results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
