"""Authoritative cutover artifact and helper semantics for the 3.0.0 contract release."""

from __future__ import annotations

from typing import Any, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field


class CutoverArtifact(BaseModel):
    """Machine-readable cutover policy shipped with the package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    release_version: str = Field(..., pattern=r"^\d+\.\d+\.\d+$")
    signal_field_name: str = Field(..., min_length=1)
    signal_location: Literal["event_envelope", "payload", "artifact_only"]
    cutover_contract_version: str = Field(..., min_length=1)
    accepted_major: int = Field(..., ge=0)
    forbidden_legacy_keys: tuple[str, ...]
    forbidden_legacy_event_names: tuple[str, ...]
    forbidden_legacy_aggregate_names: tuple[str, ...]
    forbidden_legacy_contract_surfaces: tuple[str, ...] = ()


_CUTOVER_ARTIFACT_DATA = {
    "artifact_version": "1.0.0",
    "release_version": "3.0.0",
    "signal_field_name": "schema_version",
    "signal_location": "event_envelope",
    "cutover_contract_version": "3.0.0",
    "accepted_major": 3,
    "forbidden_legacy_keys": ["feature_slug", "feature_number", "mission_key"],
    "forbidden_legacy_event_names": ["FeatureCreated", "FeatureClosed"],
    "forbidden_legacy_aggregate_names": ["feature", "feature_catalog"],
    "forbidden_legacy_contract_surfaces": ["legacy-cleanup"],
}

CUTOVER_ARTIFACT = CutoverArtifact.model_validate(_CUTOVER_ARTIFACT_DATA)


def load_cutover_artifact() -> CutoverArtifact:
    """Return the authoritative cutover artifact."""

    return CUTOVER_ARTIFACT


def canonical_signal_field_name() -> str:
    """Return the exact on-wire field name used for cutover gating."""

    return CUTOVER_ARTIFACT.signal_field_name


def canonical_signal_location() -> str:
    """Return where the canonical cutover signal must appear on wire."""

    return CUTOVER_ARTIFACT.signal_location


def _signal_container(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    location = CUTOVER_ARTIFACT.signal_location
    if location == "event_envelope":
        return payload
    if location == "payload":
        inner_payload = payload.get("payload")
        if not isinstance(inner_payload, Mapping):
            raise TypeError("payload must contain a mapping-valued 'payload' field")
        return inner_payload
    raise RuntimeError("artifact_only cutover signals cannot classify live payloads")


def read_cutover_signal(payload: Mapping[str, Any]) -> str | None:
    """Read the canonical cutover signal from a payload."""

    container = _signal_container(payload)
    value = container.get(CUTOVER_ARTIFACT.signal_field_name)
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError(
            f"{CUTOVER_ARTIFACT.signal_field_name} must be a string; got {type(value).__name__}"
        )
    return value


def accepted_major_matches(signal_value: str) -> bool:
    """Return whether the signal value matches the accepted major version policy."""

    major_token = signal_value.split(".", 1)[0]
    if not major_token.isdigit():
        raise ValueError(f"cutover signal must start with a numeric major version: {signal_value!r}")
    return int(major_token) == CUTOVER_ARTIFACT.accepted_major


def required_cutover_value_matches(signal_value: str) -> bool:
    """Return whether the signal value matches the exact required cutover value."""

    return signal_value == CUTOVER_ARTIFACT.cutover_contract_version


def forbidden_legacy_keys(payload: Mapping[str, Any]) -> set[str]:
    """Return any forbidden legacy keys present in the envelope or payload body."""

    present = {
        key
        for key in CUTOVER_ARTIFACT.forbidden_legacy_keys
        if key in payload or (isinstance(payload.get("payload"), Mapping) and key in payload["payload"])
    }
    return present


def forbidden_legacy_event_names(payload: Mapping[str, Any]) -> set[str]:
    """Return any forbidden legacy event names present in the payload."""

    event_type = payload.get("event_type")
    if not isinstance(event_type, str):
        return set()
    if event_type in CUTOVER_ARTIFACT.forbidden_legacy_event_names:
        return {event_type}
    return set()


def forbidden_legacy_aggregate_names(payload: Mapping[str, Any]) -> set[str]:
    """Return any forbidden legacy aggregate names present in the payload."""

    aggregate_id = payload.get("aggregate_id")
    if not isinstance(aggregate_id, str):
        return set()
    aggregate_name = aggregate_id.split("/", 1)[0]
    if aggregate_name in CUTOVER_ARTIFACT.forbidden_legacy_aggregate_names:
        return {aggregate_name}
    return set()


def is_pre_cutover_payload(payload: Mapping[str, Any]) -> bool:
    """Classify whether a payload is pre-cutover according to the artifact."""

    signal_value = read_cutover_signal(payload)
    if signal_value is None:
        return True
    if not accepted_major_matches(signal_value):
        return True
    if not required_cutover_value_matches(signal_value):
        return True
    return any(
        (
            forbidden_legacy_keys(payload),
            forbidden_legacy_event_names(payload),
            forbidden_legacy_aggregate_names(payload),
        )
    )


def assert_canonical_cutover_signal(payload: Mapping[str, Any]) -> None:
    """Raise when a payload is not canonical for the cutover artifact."""

    signal_value = read_cutover_signal(payload)
    if signal_value is None:
        raise ValueError(
            f"missing canonical cutover signal {CUTOVER_ARTIFACT.signal_field_name!r}"
        )
    if not accepted_major_matches(signal_value):
        raise ValueError(
            f"unsupported cutover major version in {CUTOVER_ARTIFACT.signal_field_name!r}: {signal_value!r}"
        )
    if not required_cutover_value_matches(signal_value):
        raise ValueError(
            f"cutover signal must equal {CUTOVER_ARTIFACT.cutover_contract_version!r}; got {signal_value!r}"
        )

    legacy_keys = forbidden_legacy_keys(payload)
    if legacy_keys:
        raise ValueError(f"payload contains forbidden legacy keys: {sorted(legacy_keys)!r}")

    legacy_event_names = forbidden_legacy_event_names(payload)
    if legacy_event_names:
        raise ValueError(
            f"payload contains forbidden legacy event names: {sorted(legacy_event_names)!r}"
        )

    legacy_aggregate_names = forbidden_legacy_aggregate_names(payload)
    if legacy_aggregate_names:
        raise ValueError(
            "payload contains forbidden legacy aggregate names: "
            f"{sorted(legacy_aggregate_names)!r}"
        )
