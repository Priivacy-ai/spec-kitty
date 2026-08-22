#!/usr/bin/env python3
"""Convert a synthetic privacy canary without persisting source text."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

from docling.document_converter import DocumentConverter


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--mode", choices=["normal", "exception", "wait"], required=True)
    args = parser.parse_args()
    output = DocumentConverter().convert(args.input).document.export_to_markdown().encode("utf-8")
    output_hash = hashlib.sha256(output).hexdigest()  # noqa: TID251 - privacy probe output integrity
    print(
        json.dumps({"conversion_complete": True, "output_sha256": output_hash, "output_bytes": len(output)}),
        flush=True,
    )
    if args.mode == "exception":
        raise RuntimeError("forced post-conversion privacy probe exception")
    if args.mode == "wait":
        print("READY_FOR_SIGTERM", flush=True)
        time.sleep(300)


if __name__ == "__main__":
    main()
