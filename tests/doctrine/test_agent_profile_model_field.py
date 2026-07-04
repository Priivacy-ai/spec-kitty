"""Tests for the optional per-profile ``model``/``effort`` field (WP04, FR-005).

The field must reach the DOMAIN model (``AgentProfile`` in ``profile.py``),
not merely the generated schema — ``AgentProfile``'s ``model_config`` has no
explicit ``extra`` setting, which defaults to Pydantic v2's ``"ignore"``, so
an unknown key is silently dropped. This test asserts the value is present
on the *loaded* ``AgentProfile`` object.

NFR-003 back-compat: existing profiles without the field must load unchanged.
"""

import pytest

from doctrine.agent_profiles.profile import AgentProfile

pytestmark = [pytest.mark.doctrine, pytest.mark.fast]

_BASE = {
    "profile-id": "test-model-field",
    "name": "Test Profile",
    "purpose": "Test purpose",
    "specialization": {"primary-focus": "Testing"},
    "roles": ["implementer"],
}


class TestAgentProfileModelEffortField:
    def test_model_field_reaches_domain_model(self):
        """A YAML profile with ``model:`` exposes it on the loaded AgentProfile.

        This is the load-bearing assertion: it proves the value reaches the
        domain object, not just schema validation. Pre-fix, this fails
        because ``AgentProfile`` has no ``preferred_model``/``model`` field
        and ``extra="ignore"`` (the Pydantic v2 default for this model)
        silently drops the unknown ``model`` key.
        """
        profile = AgentProfile(**_BASE, model="opus")
        assert profile.preferred_model == "opus"

    def test_effort_field_reaches_domain_model(self):
        """A YAML profile with ``effort:`` exposes it on the loaded AgentProfile."""
        profile = AgentProfile(**_BASE, effort="high")
        assert profile.effort == "high"

    def test_both_model_and_effort_fields_reach_domain_model(self):
        profile = AgentProfile(**_BASE, model="sonnet", effort="medium")
        assert profile.preferred_model == "sonnet"
        assert profile.effort == "medium"

    def test_model_and_effort_default_to_none(self):
        """A profile that never declares model/effort still loads (NFR-003)."""
        profile = AgentProfile(**_BASE)
        assert profile.preferred_model is None
        assert profile.effort is None

    def test_existing_profile_without_field_loads_unchanged(self):
        """Back-compat (NFR-003): a profile missing model/effort is unaffected.

        Uses a realistic full profile shape (not just the minimal base) to
        prove the addition does not perturb any other field or validation
        path for profiles authored before this WP.
        """
        data = {
            "profile-id": "legacy-profile",
            "name": "Legacy Profile",
            "purpose": "Exercises pre-existing profile shape",
            "specialization": {"primary-focus": "Legacy behavior"},
            "roles": ["implementer"],
            "routing-priority": 75,
            "max-concurrent-tasks": 3,
        }
        profile = AgentProfile(**data)
        assert profile.routing_priority == 75
        assert profile.max_concurrent_tasks == 3
        assert profile.preferred_model is None
        assert profile.effort is None

    def test_attribute_name_avoids_protected_model_namespace(self):
        """The Python attribute is ``preferred_model``, never ``model``/``model_*``.

        Pydantic v2 reserves the ``model_`` prefix for its own namespace; the
        fixed contract aliases the YAML key ``model`` to the Python attribute
        ``preferred_model`` to avoid any collision or warning.
        """
        assert hasattr(AgentProfile, "model_fields")
        assert "preferred_model" in AgentProfile.model_fields
        field_info = AgentProfile.model_fields["preferred_model"]
        assert field_info.alias == "model"
        effort_info = AgentProfile.model_fields["effort"]
        assert effort_info.alias == "effort"


class TestSchemaExposesModelEffort:
    """The generated JSON-schema contract MUST expose ``model``/``effort``.

    ``AgentProfileSchema`` has ``extra="forbid"``, so if the schema source did
    not register these fields (e.g. a bare ``model`` attribute that fails to
    register), a profile declaring ``model:`` would be *rejected* by
    schema validation despite the domain model accepting it — a silent
    contract/runtime mismatch. Guard both the schema-source model and the
    generated ``by_alias`` JSON schema.
    """

    def test_schema_source_registers_fields_with_aliases(self):
        from doctrine.agent_profiles.schema_models import AgentProfileSchema

        assert "preferred_model" in AgentProfileSchema.model_fields
        assert AgentProfileSchema.model_fields["preferred_model"].alias == "model"
        assert "effort" in AgentProfileSchema.model_fields

    def test_generated_json_schema_exposes_model_and_effort(self):
        from doctrine.agent_profiles.schema_models import AgentProfileSchema

        props = AgentProfileSchema.model_json_schema(by_alias=True)["properties"]
        assert "model" in props, "profiles declaring model: would fail schema validation"
        assert "effort" in props
