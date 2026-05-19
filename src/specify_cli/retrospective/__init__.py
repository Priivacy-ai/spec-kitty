"""Retrospective record schema, atomic writer, schema-validating reader, policy resolver,
and pure-Python generator (WP02).

Public API:
    schema   — Pydantic v2 models for retrospective.yaml (schema_version=1)
               + dataclass-based generator record types (GenRetrospectiveRecord etc.)
    writer   — write_record(): atomic YAML write via ruamel.yaml + os.replace
    reader   — read_record(): YAML parse + schema validation + pending guard
    policy   — RetrospectivePolicy resolver (FR-001, FR-002, FR-003, FR-004, FR-015, FR-024)
    generator — generate_retrospective(): pure-Python deterministic generator (WP02)

Note on naming: the generator schema types are defined in schema.py with "Gen" prefix
(GenRetrospectiveRecord, GenFinding, etc.) to coexist with the existing Pydantic models.
They are re-exported here under canonical names (RetrospectiveRecord, Finding, etc.)
from the generator schema perspective. Existing Pydantic schema models remain available
directly from specify_cli.retrospective.schema.
"""

from specify_cli.retrospective.generator import GENERATOR_VERSION, generate_retrospective
from specify_cli.retrospective.policy import (
    PolicyResolutionError,
    RetrospectivePermissions,
    RetrospectivePolicy,
    default_policy,
    resolve_policy,
)
from specify_cli.retrospective.reader import SchemaError, YAMLParseError, read_record

# Generator record types (WP02): exported under canonical names
from specify_cli.retrospective.schema import (
    GenActor as Actor,
    GenEvidenceRef as EvidenceRef,
    GenFinding as Finding,
    GenProposal as Proposal,
    GenProvenance as Provenance,
    GenRetrospectiveRecord as RetrospectiveRecord,
    RecordValidationError,
)

# Also re-export the prefixed names for consumers that prefer explicit names
from specify_cli.retrospective.schema import (
    GenActor,
    GenEvidenceRef,
    GenFinding,
    GenProposal,
    GenProvenance,
    GenRetrospectiveRecord,
    validate_record,
)
from specify_cli.retrospective.writer import WriterError, write_record

__all__ = [
    # policy (WP01)
    "RetrospectivePolicy",
    "RetrospectivePermissions",
    "PolicyResolutionError",
    "default_policy",
    "resolve_policy",
    # record schema / IO (existing Pydantic-based)
    "WriterError",
    "write_record",
    "SchemaError",
    "YAMLParseError",
    "read_record",
    # generator record schema (WP02 dataclass-based, canonical names)
    "RetrospectiveRecord",
    "Finding",
    "Proposal",
    "EvidenceRef",
    "Provenance",
    "Actor",
    "RecordValidationError",
    "validate_record",
    # generator record schema (WP02 prefixed names)
    "GenRetrospectiveRecord",
    "GenFinding",
    "GenProposal",
    "GenEvidenceRef",
    "GenProvenance",
    "GenActor",
    # generator (WP02)
    "generate_retrospective",
    "GENERATOR_VERSION",
]
