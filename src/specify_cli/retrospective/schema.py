"""Pydantic v2 schema for retrospective.yaml (schema_version=1).

Source-of-truth: kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/data-model.md
Contract:       kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/retrospective_yaml_v1.md
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    model_validator,
)

# ---------------------------------------------------------------------------
# Identity primitives
# ---------------------------------------------------------------------------

#: 26-char Crockford base32 ULID (no I, L, O, U)
_ULID_PATTERN = r"^[0-9A-HJ-KM-NP-TV-Z]{26}$"

MissionId = Annotated[str, StringConstraints(pattern=_ULID_PATTERN)]
Mid8 = Annotated[str, StringConstraints(min_length=8, max_length=8)]
EventId = Annotated[str, StringConstraints(pattern=_ULID_PATTERN)]
ProposalId = Annotated[str, StringConstraints(pattern=_ULID_PATTERN)]
Timestamp = Annotated[str, StringConstraints(min_length=1)]


# ---------------------------------------------------------------------------
# ActorRef
# ---------------------------------------------------------------------------


class ActorRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["human", "agent", "runtime"]
    id: str
    profile_id: str | None = None


# ---------------------------------------------------------------------------
# MissionIdentity, ModeSourceSignal, Mode
# ---------------------------------------------------------------------------


class MissionIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mission_id: MissionId
    mid8: Mid8
    mission_slug: str
    mission_type: str
    mission_started_at: Timestamp
    mission_completed_at: Timestamp | None = None


class ModeSourceSignal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["charter_override", "explicit_flag", "environment", "parent_process"]
    evidence: str


class Mode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: Literal["autonomous", "human_in_command"]
    source_signal: ModeSourceSignal


# ---------------------------------------------------------------------------
# TargetReference
# ---------------------------------------------------------------------------


class TargetReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal[
        "doctrine_directive",
        "doctrine_tactic",
        "doctrine_procedure",
        "drg_edge",
        "drg_node",
        "glossary_term",
        "prompt_template",
        "test",
        "context_artifact",
    ]
    urn: str


# ---------------------------------------------------------------------------
# Provenance models
# ---------------------------------------------------------------------------


class FindingProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_mission_id: MissionId
    evidence_event_ids: list[EventId] = Field(min_length=1)
    actor: ActorRef
    captured_at: Timestamp


class ProposalProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_mission_id: MissionId
    source_evidence_event_ids: list[EventId]
    authored_by: ActorRef
    approved_by: ActorRef | None = None


class RecordProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    authored_by: ActorRef
    runtime_version: str
    written_at: Timestamp
    schema_version: Literal["1"]


# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    target: TargetReference
    note: str = Field(max_length=2000)
    provenance: FindingProvenance


# ---------------------------------------------------------------------------
# ProposalState, ProposalApplyAttempt
# ---------------------------------------------------------------------------


class ProposalApplyAttempt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: EventId
    at: Timestamp
    outcome: Literal["applied", "rejected_conflict", "rejected_stale", "rejected_invalid"]
    error: str | None = None


class ProposalState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "accepted", "rejected", "applied", "superseded"]
    decided_at: Timestamp | None = None
    decided_by: ActorRef | None = None
    apply_attempts: list[ProposalApplyAttempt] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Proposal payload models (discriminated union)
# ---------------------------------------------------------------------------


class SynthesizeScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actions: list[str] = Field(default_factory=list)
    profiles: list[str] = Field(default_factory=list)


# Validator applied to filesystem-bound identifiers (term_key, artifact_id).
# The contract uses both lowercase glossary terms (e.g. ``mission-id``) and
# mixed-case doctrine artifact ids (e.g. ``DIRECTIVE_001``,
# ``TACTIC_phase_2``, ``PROCEDURE-v2``), so the alphabet must accept both.
# The security shape is what matters:
#   * length 1-128 (rules out empty)
#   * alphabet limited to [A-Za-z0-9._-] (no path separators, no spaces, no
#     control characters or shell meta)
#   * no leading dot (no hidden file)
#   * no ``..`` substring anywhere (no traversal)
# Pydantic v2 uses the Rust regex engine, which has no look-around, so the
# composite check is split into a regex (alphabet + length) plus an
# AfterValidator for the structural ``..``/leading-dot rules.
# ``_assert_within`` in apply.py adds defense in depth at write time.
_SLUG_REGEX = r"^[A-Za-z0-9._-]{1,128}$"


def _validate_safe_slug(value: str) -> str:
    if value.startswith("."):
        raise ValueError("identifier must not start with '.': leading-dot names are reserved")
    if ".." in value:
        raise ValueError("identifier must not contain '..': path-traversal sequences are forbidden")
    return value


# A reusable Annotated type so all filesystem-bound identifier fields share
# one definition. AfterValidator runs after the regex pattern validates the
# alphabet + length.
SafeSlug = Annotated[
    str,
    Field(pattern=_SLUG_REGEX),
    AfterValidator(_validate_safe_slug),
]


class SynthesizeDirectivePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["synthesize_directive"]
    artifact_id: SafeSlug
    body: str
    body_hash: str
    scope: SynthesizeScope


class SynthesizeTacticPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["synthesize_tactic"]
    artifact_id: SafeSlug
    body: str
    body_hash: str
    scope: SynthesizeScope


class SynthesizeProcedurePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["synthesize_procedure"]
    artifact_id: SafeSlug
    body: str
    body_hash: str
    scope: SynthesizeScope


class EdgeSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_node: str
    to_node: str
    kind: str


class RewireEdgePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["rewire_edge"]
    edge_old: EdgeSpec
    edge_new: EdgeSpec


class AddEdgePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["add_edge"]
    edge: EdgeSpec


class RemoveEdgePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["remove_edge"]
    edge: EdgeSpec


class AddGlossaryTermPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["add_glossary_term"]
    term_key: SafeSlug
    definition: str
    definition_hash: str
    related_terms: list[str] = Field(default_factory=list)


class UpdateGlossaryTermPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["update_glossary_term"]
    term_key: SafeSlug
    definition: str
    definition_hash: str
    related_terms: list[str] = Field(default_factory=list)


class FlagNotHelpfulPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["flag_not_helpful"]
    target: TargetReference


# Discriminated union for all proposal payloads
ProposalPayload = Annotated[
    SynthesizeDirectivePayload
    | SynthesizeTacticPayload
    | SynthesizeProcedurePayload
    | RewireEdgePayload
    | AddEdgePayload
    | RemoveEdgePayload
    | AddGlossaryTermPayload
    | UpdateGlossaryTermPayload
    | FlagNotHelpfulPayload,
    Field(discriminator="kind"),
]


# ---------------------------------------------------------------------------
# Proposal
# ---------------------------------------------------------------------------


class Proposal(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ProposalId
    kind: Literal[
        "synthesize_directive",
        "synthesize_tactic",
        "synthesize_procedure",
        "rewire_edge",
        "add_edge",
        "remove_edge",
        "add_glossary_term",
        "update_glossary_term",
        "flag_not_helpful",
    ]
    payload: ProposalPayload
    rationale: str = Field(max_length=2000)
    state: ProposalState
    provenance: ProposalProvenance


# ---------------------------------------------------------------------------
# RetrospectiveFailure
# ---------------------------------------------------------------------------


class RetrospectiveFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal[
        "writer_io_error",
        "schema_invalid",
        "facilitator_error",
        "evidence_unreachable",
        "mode_resolution_error",
        "internal_error",
    ]
    message: str
    error_chain: list[str] = Field(max_length=16)


# ---------------------------------------------------------------------------
# RetrospectiveRecord (top-level)
# ---------------------------------------------------------------------------


class RetrospectiveRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1"]
    mission: MissionIdentity
    mode: Mode
    status: Literal["completed", "skipped", "failed", "pending"]
    started_at: Timestamp
    completed_at: Timestamp | None = None
    actor: ActorRef
    helped: list[Finding] = Field(default_factory=list)
    not_helpful: list[Finding] = Field(default_factory=list)
    gaps: list[Finding] = Field(default_factory=list)
    proposals: list[Proposal] = Field(default_factory=list)
    provenance: RecordProvenance
    skip_reason: str | None = None
    failure: RetrospectiveFailure | None = None
    successor_mission_id: MissionId | None = None

    @model_validator(mode="after")
    def validate_status_conditionals(self) -> RetrospectiveRecord:
        """Enforce status-conditional field requirements."""
        status = self.status

        if status == "completed" and self.completed_at is None:
            raise ValueError("status='completed' requires completed_at to be set")

        if status == "skipped" and (self.skip_reason is None or len(self.skip_reason) == 0):
            raise ValueError("status='skipped' requires a non-empty skip_reason")

        if status == "failed" and self.failure is None:
            raise ValueError("status='failed' requires failure to be set")

        if status == "pending":
            raise ValueError("status='pending' is not persistable; the writer refuses to materialize a pending record")

        return self

    @model_validator(mode="after")
    def validate_unique_finding_ids(self) -> RetrospectiveRecord:
        """Ensure all Finding.id values are unique within the record."""
        all_findings = list(self.helped) + list(self.not_helpful) + list(self.gaps)
        ids = [f.id for f in all_findings]
        seen: set[str] = set()
        for fid in ids:
            if fid in seen:
                raise ValueError(f"Duplicate Finding.id '{fid}' found in record")
            seen.add(fid)
        return self

    @model_validator(mode="after")
    def validate_unique_proposal_ids(self) -> RetrospectiveRecord:
        """Ensure all Proposal.id values are unique within the record."""
        ids = [p.id for p in self.proposals]
        seen: set[str] = set()
        for pid in ids:
            if pid in seen:
                raise ValueError(f"Duplicate Proposal.id '{pid}' found in record")
            seen.add(pid)
        return self
