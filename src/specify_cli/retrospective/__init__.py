"""Retrospective record schema, atomic writer, schema-validating reader, and policy resolver.

Public API:
    schema   — Pydantic v2 models for retrospective.yaml (schema_version=1)
    writer   — write_record(): atomic YAML write via ruamel.yaml + os.replace
    reader   — read_record(): YAML parse + schema validation + pending guard
    policy   — RetrospectivePolicy resolver (FR-001, FR-002, FR-003, FR-004, FR-015, FR-024)
"""

from specify_cli.retrospective.policy import (
    PolicyResolutionError,
    RetrospectivePermissions,
    RetrospectivePolicy,
    default_policy,
    resolve_policy,
)
from specify_cli.retrospective.reader import SchemaError, YAMLParseError, read_record
from specify_cli.retrospective.schema import RetrospectiveRecord
from specify_cli.retrospective.writer import WriterError, write_record

__all__ = [
    # policy (WP01)
    "RetrospectivePolicy",
    "RetrospectivePermissions",
    "PolicyResolutionError",
    "default_policy",
    "resolve_policy",
    # record schema / IO
    "RetrospectiveRecord",
    "WriterError",
    "write_record",
    "SchemaError",
    "YAMLParseError",
    "read_record",
]
