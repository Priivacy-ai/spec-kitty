#!/usr/bin/env python3
"""Run repeated frozen structural Docling round-trip oracles."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path

from docling.document_converter import DocumentConverter

PATTERNS = {
    "frontmatter": re.compile(r"^---$", re.MULTILINE),
    "table": re.compile(r"^\|.*\|\s*$", re.MULTILINE),
    "fence": re.compile(r"^```", re.MULTILINE),
    "link": re.compile(r"\[[^]]+\]\([^)]+\)"),
    "html_comment": re.compile(r"<!--.*?-->", re.DOTALL),
    "checkbox": re.compile(r"^\s*[-*] \[[ xX]\]", re.MULTILINE),
    "cross_file_id": re.compile(r"\b(?:FR|WP|AC|DR|QR|SC|NFR)-?[0-9]+\b"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()  # noqa: TID251 - cross-project file-integrity metric


def counts(text: str) -> dict[str, int]:
    values = {name: len(pattern.findall(text)) for name, pattern in PATTERNS.items()}
    values["non_ascii"] = sum(ord(character) > 127 for character in text)
    return values


def blob(path: str, revision: str) -> bytes:
    return subprocess.run(["git", "show", f"{revision}:{path}"], check=True, capture_output=True).stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--revision", default="cf0f7e3a7")
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.repetitions < 2:
        raise SystemExit("at least two structural repetitions are required")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    exports = args.output_dir / "exports"
    exports.mkdir(exist_ok=True)
    with args.gold.open(newline="", encoding="utf-8") as handle:
        gold_rows = list(csv.DictReader(handle))
    gold_by_path: dict[str, list[dict[str, str]]] = {}
    for row in gold_rows:
        gold_by_path.setdefault(row["source_path"], []).append(row)
    converter = DocumentConverter()
    results: list[dict[str, object]] = []

    def run(
        *,
        kind: str,
        label: str,
        source: bytes,
        required_constructs: list[str],
        required_hex: list[str],
        declared_features: list[str],
        source_blob: str | None = None,
    ) -> None:
        source_hash = sha(source)
        stable_dir = Path(temp_root) / source_hash
        stable_dir.mkdir(parents=True, exist_ok=True)
        input_path = stable_dir / Path(label).name
        input_path.write_bytes(source)
        source_text = source.decode("utf-8-sig", errors="strict")
        source_counts = counts(source_text)
        prior_output_hash: str | None = None
        for repetition in range(1, args.repetitions + 1):
            started = time.perf_counter()
            try:
                output = converter.convert(input_path).document.export_to_markdown().encode("utf-8")
                error = None
            except Exception as exc:  # noqa: BLE001 - probe records candidate failure
                output = b""
                error = f"{type(exc).__name__}: {exc}"
            seconds = time.perf_counter() - started
            output_hash = sha(output)
            export_path = exports / source_hash / f"{repetition}-{output_hash}.md"
            export_path.parent.mkdir(parents=True, exist_ok=True)
            export_path.write_bytes(output)
            output_text = output.decode("utf-8", errors="strict")
            output_counts = counts(output_text)
            missing_constructs = [value for value in required_constructs if value not in output_text]
            missing_hex = [value for value in required_hex if value not in output.hex()]
            feature_oracles = {
                feature: {
                    "source": source_counts.get(feature, 0),
                    "output": output_counts.get(feature, 0),
                    "status": "PASS" if source_counts.get(feature, 0) == output_counts.get(feature, 0) else "FAIL",
                }
                for feature in declared_features
            }
            span_oracles: dict[str, str] = {}
            for row in gold_by_path.get(label, []):
                start, end = int(row["start_byte"]), int(row["end_byte"])
                cited = source[start:end]
                span_oracles[row["atom_id"]] = "PASS" if cited in output else "FAIL"
            result = {
                "kind": kind,
                "path": label,
                "source_blob": source_blob,
                "source_sha256": source_hash,
                "repetition": repetition,
                "seconds": seconds,
                "source_bytes": len(source),
                "output_bytes": len(output),
                "output_sha256": output_hash,
                "same_bytes": source == output,
                "repeat_same_as_previous": prior_output_hash in {None, output_hash},
                "construct_status": "PASS" if not missing_constructs and not missing_hex else "FAIL",
                "missing_constructs": missing_constructs,
                "missing_hex_sequences": missing_hex,
                "feature_oracles": feature_oracles,
                "gold_span_oracles": span_oracles,
                "error": error,
                "export_path": str(export_path.relative_to(args.output_dir)),
            }
            results.append(result)
            prior_output_hash = output_hash

    with tempfile.TemporaryDirectory(prefix="docling-roundtrip-") as temp_root:
        fixture_data = json.loads(args.fixtures.read_text(encoding="utf-8"))
        for fixture in fixture_data["fixtures"]:
            source = base64.b64decode(fixture["content_base64"])
            if sha(source) != fixture["sha256"]:
                raise RuntimeError(f"fixture hash mismatch: {fixture['name']}")
            run(
                kind="golden_fixture",
                label=fixture["name"],
                source=source,
                required_constructs=fixture.get("required_constructs", []) + fixture.get("required_text", []),
                required_hex=fixture.get("required_hex_sequences", []),
                declared_features=[],
            )
        with args.manifest.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                source = blob(row["path"], args.revision)
                actual_blob = (
                    subprocess.run(
                        ["git", "hash-object", "--stdin"],
                        input=source,
                        check=True,
                        capture_output=True,
                    )
                    .stdout.decode()
                    .strip()
                )
                if actual_blob != row["blob_sha"] or sha(source) != row["content_sha256"]:
                    raise RuntimeError(f"manifest identity mismatch: {row['path']}")
                run(
                    kind="corpus",
                    label=row["path"],
                    source=source,
                    required_constructs=[],
                    required_hex=[],
                    declared_features=[value for value in row["features"].split(";") if value],
                    source_blob=row["blob_sha"],
                )
    summary = {
        "schema_version": 2,
        "revision": args.revision,
        "repetitions": args.repetitions,
        "oracle_scope": {
            "same_bytes": "exact byte equality",
            "construct_status": "declared fixture literal/hex presence only",
            "feature_oracles": "count equality only; PASS does not establish semantic or lossless fidelity",
            "gold_span_oracles": "cited source-byte span presence only",
        },
        "results": results,
    }
    (args.output_dir / "roundtrip-results.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
