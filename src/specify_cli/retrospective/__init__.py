"""Retrospective record schema, atomic writer, and schema-validating reader.

Public API:
    schema   — Pydantic v2 models for retrospective.yaml (schema_version=1)
    writer   — write_record(): atomic YAML write via ruamel.yaml + os.replace
    reader   — read_record(): YAML parse + schema validation + pending guard
"""

from specify_cli.retrospective.reader import SchemaError, YAMLParseError, read_record
from specify_cli.retrospective.schema import RetrospectiveRecord
from specify_cli.retrospective.writer import WriterError, write_record

__all__ = [
    "RetrospectiveRecord",
    "WriterError",
    "write_record",
    "SchemaError",
    "YAMLParseError",
    "read_record",
]
