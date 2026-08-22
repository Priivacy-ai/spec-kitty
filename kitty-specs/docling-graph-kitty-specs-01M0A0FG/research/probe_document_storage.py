#!/usr/bin/env python3
"""Supplementary storage observation for structural DoclingDocument JSON."""

from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import tempfile
from pathlib import Path

from docling.document_converter import DocumentConverter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--revision", default="cf0f7e3a7")
    args = parser.parse_args()
    converter = DocumentConverter()
    results: list[dict[str, object]] = []
    with args.manifest.open(newline="", encoding="utf-8") as handle, tempfile.TemporaryDirectory(prefix="docling-storage-") as temp_name:
        for index, row in enumerate(csv.DictReader(handle)):
            source = subprocess.run(
                ["git", "show", f"{args.revision}:{row['path']}"],
                check=True,
                capture_output=True,
            ).stdout
            path = Path(temp_name) / f"{index:03d}.md"
            path.write_bytes(source)
            document = converter.convert(path).document
            encoded = json.dumps(document.export_to_dict(), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            results.append(
                {
                    "path": row["path"],
                    "source_bytes": len(source),
                    "docling_json_bytes": len(encoded),
                    "amplification": len(encoded) / len(source),
                    "texts": len(document.texts),
                    "tables": len(document.tables),
                    "pictures": len(document.pictures),
                    "groups": len(document.groups),
                }
            )
    ratios = [float(row["amplification"]) for row in results]
    total_source = sum(int(row["source_bytes"]) for row in results)
    total_json = sum(int(row["docling_json_bytes"]) for row in results)
    output = {
        "schema_version": 1,
        "status": "supplementary_postseal_observation_not_preregistered",
        "revision": args.revision,
        "summary": {
            "documents": len(results),
            "source_bytes": total_source,
            "docling_json_bytes": total_json,
            "aggregate_amplification": total_json / total_source,
            "median_amplification": statistics.median(ratios),
            "minimum_amplification": min(ratios),
            "maximum_amplification": max(ratios),
        },
        "results": results,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
