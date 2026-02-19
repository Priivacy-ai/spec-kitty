"""Validation helpers for doctrine curation import candidates."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


@dataclass
class ImportCandidateValidationResult:
    """Validation outcome for one import candidate artifact."""

    file_path: Path
    valid: bool
    errors: list[str]


REQUIRED_TOP_LEVEL: tuple[str, ...] = (
    "id",
    "source",
    "classification",
    "adaptation",
    "status",
)

REQUIRED_SOURCE_FIELDS: tuple[str, ...] = (
    "title",
    "type",
    "url",
    "accessed_on",
)

ADOPTED = "adopted"


def _load_yaml(path: Path) -> dict[str, Any]:
    yaml = YAML(typ="safe")
    data = yaml.load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def validate_import_candidate(path: Path) -> ImportCandidateValidationResult:
    """Validate core curation candidate structure and adoption traceability."""
    errors: list[str] = []
    data = _load_yaml(path)

    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be a mapping")
    else:
        for field in REQUIRED_SOURCE_FIELDS:
            if field not in source or not str(source[field]).strip():
                errors.append(f"source.{field} is required")

    classification = data.get("classification")
    if not isinstance(classification, dict):
        errors.append("classification must be a mapping")
    else:
        targets = classification.get("target_concepts")
        if not isinstance(targets, list) or not targets:
            errors.append("classification.target_concepts must contain at least one concept")

    if str(data.get("status", "")).strip().lower() == ADOPTED:
        artifacts = data.get("resulting_artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append(
                "status=adopted requires resulting_artifacts links to doctrine artifacts"
            )
        else:
            for idx, artifact in enumerate(artifacts, start=1):
                value = str(artifact).strip()
                if not value:
                    errors.append(f"resulting_artifacts[{idx}] must be a non-empty path")
                elif not value.startswith("src/doctrine/"):
                    errors.append(
                        f"resulting_artifacts[{idx}] must link to src/doctrine/*"
                    )

    return ImportCandidateValidationResult(
        file_path=path,
        valid=not errors,
        errors=errors,
    )


__all__ = ["ImportCandidateValidationResult", "validate_import_candidate"]
