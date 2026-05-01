"""Schema-validating reader for retrospective.yaml.

Raises typed exceptions so callers can distinguish missing-file,
corrupt-YAML, and schema-invalid cases without catching broad exceptions.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from specify_cli.retrospective.schema import RetrospectiveRecord


class YAMLParseError(Exception):
    """The file exists but contains invalid YAML syntax."""


class SchemaError(Exception):
    """The file contains valid YAML but fails schema validation."""


def read_record(path: Path, *, verify_evidence: bool = False) -> RetrospectiveRecord:
    """Load a retrospective record from disk, schema-validated.

    Args:
        path: Absolute path to the retrospective.yaml file.
        verify_evidence: When True, perform a soft check that evidence event ids
            referenced by findings/proposals exist in the mission event log.
            # TODO: WP03 wires the actual event log lookup; for now this is a no-op.

    Returns:
        A fully-validated :class:`RetrospectiveRecord`.

    Raises:
        FileNotFoundError: The file does not exist.
        YAMLParseError: The file exists but cannot be parsed as YAML.
        SchemaError: The file parses as YAML but fails schema validation,
            or the record has status='pending' (not persistable).
    """
    # Let FileNotFoundError propagate naturally from read_text.
    raw_text = path.read_text(encoding="utf-8")

    # Parse YAML.
    yaml = YAML(typ="safe")
    try:
        data = yaml.load(raw_text)
    except YAMLError as exc:
        raise YAMLParseError(f"Failed to parse YAML from {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise SchemaError(f"Expected a YAML mapping at the top level of {path}, got {type(data).__name__}")

    # Schema validation via Pydantic.
    try:
        record = RetrospectiveRecord.model_validate(data)
    except ValidationError as exc:
        raise SchemaError(
            f"Schema validation failed for {path}:\n{exc}"
        ) from exc

    # status='pending' is explicitly refused at the read boundary too.
    # (The model validator already raises for pending, but guard explicitly
    # in case the validator is bypassed via model_construct in future.)
    if record.status == "pending":
        raise SchemaError(
            f"Refused to return a record with status='pending' from {path}. "
            "Pending records must not be persisted."
        )

    # Evidence verification (stub; WP03 wires the actual event log lookup).
    if verify_evidence:
        # TODO: WP03 wires the actual event log lookup.
        pass

    return record
