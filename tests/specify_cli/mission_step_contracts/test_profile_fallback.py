"""#4115: role-based fallback for built-in mission step default profiles.

A project that deactivated a shipped agent profile named in
``_ACTION_PROFILE_DEFAULTS`` (``charter deactivate agent-profile
researcher-robbie`` — which succeeds, and ``charter preflight`` reports
FRESH) used to block every built-in mission at that step: the executor
returned the table default unconditionally and ``ProfileInvocationExecutor``
crashed with ``ProfileNotFoundError``. These tests pin the fix's resolution
order (see ``StepContractExecutor._resolve_available_default``'s docstring):

1. explicit ``context.profile_hint`` always wins;
2. the table default when the invocation catalog can resolve it
   (byte-identical dispatch for projects that never deactivated it);
3. the highest-``routing-priority`` available profile carrying the default's
   role, with a WARNING naming both profiles;
4. a structured ``StepContractExecutionError`` (never a laundered
   ``ProfileNotFoundError`` crash) when no same-role profile is available;
5. no catalog accessor at all (the fake-executor test pattern) keeps the
   legacy return-the-default behavior.

The catalog is faked deliberately: the fallback's contract is "choose from
whatever ``list_available_profiles()`` returns", and faking the catalog
makes every branch (default present/absent, role-mate present/absent,
priority ties) reachable without provisioning real activation state.
"""

from __future__ import annotations

import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
from ruamel.yaml import YAML

from charter.offering.missions.step_contracts import MissionStepContractRepository
from charter.profiles import AgentProfile
from specify_cli.mission_step_contracts.executor import (
    _ACTION_PROFILE_DEFAULTS,
    _DEFAULT_PROFILE_ROLES,
    StepContractExecutionContext,
    StepContractExecutionError,
    StepContractExecutor,
)
from specify_cli.mission_step_contracts.profile_defaults import (
    mission_default_profile_warning,
)

pytestmark = pytest.mark.fast

_REPO_ROOT = Path(__file__).resolve().parents[3]
_PACK_AGENT_PROFILES_DIR = _REPO_ROOT / "packs" / "built-in" / "agent_profiles"

# (mission, action) under test: a table entry whose default is
# ``researcher-robbie`` (role ``researcher``).
_MISSION = "software-dev"
_ACTION = "specify"
_DEFAULT_PROFILE = "researcher-robbie"
_DEFAULT_ROLE = "researcher"


def _profile(profile_id: str, role: str, *, routing_priority: int = 50) -> AgentProfile:
    """Build a minimal valid ``AgentProfile`` for the fake catalog."""
    return AgentProfile(
        profile_id=profile_id,
        name=profile_id,
        roles=[role],
        purpose="Fixture profile for the #4115 fallback tests.",
        specialization={"primary-focus": "Fixture focus"},
        routing_priority=routing_priority,
    )


class _CatalogFakeInvocationExecutor:
    """Fake ``ProfileInvocationExecutor`` exposing a controlled catalog.

    Records every ``profile_hint`` it was invoked with so a test can assert
    the SAME fallback id reached every composed step (not just the first).
    """

    def __init__(self, catalog: list[AgentProfile]) -> None:
        self._catalog = catalog
        self.profile_hints: list[object] = []

    def list_available_profiles(self) -> list[AgentProfile]:
        return list(self._catalog)

    def invoke(self, _request_text: str, **kwargs: object) -> object:
        self.profile_hints.append(kwargs.get("profile_hint"))
        return SimpleNamespace(invocation_id="inv-profile-fallback-1")

    def complete_invocation(self, _invocation_id: str, *, outcome: str, closed_by: str) -> None:
        assert outcome == "done"
        assert closed_by == "agent"


class _LegacyFakeInvocationExecutor:
    """The pre-#4115 fake shape: no ``list_available_profiles`` at all.

    Every existing fake-executor test in this suite uses this shape; the
    executor must keep returning the table default for it.
    """

    def invoke(self, _request_text: str, **_kwargs: object) -> object:
        return SimpleNamespace(invocation_id="inv-profile-fallback-1")

    def complete_invocation(self, _invocation_id: str, *, outcome: str, closed_by: str) -> None:
        assert outcome == "done"
        assert closed_by == "agent"


def _execute(
    repo_root: Path,
    invocation_executor: object,
    *,
    profile_hint: str | None = None,
):
    """Execute the shipped ``software-dev/specify`` contract end-to-end."""
    return StepContractExecutor(
        repo_root=repo_root,
        contract_repository=MissionStepContractRepository(),
        invocation_executor=invocation_executor,  # type: ignore[arg-type]
    ).execute(
        StepContractExecutionContext(
            repo_root=repo_root,
            mission=_MISSION,
            action=_ACTION,
            actor="pytest",
            profile_hint=profile_hint,
        )
    )


def _repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


# ---------------------------------------------------------------------------
# Resolution-order tests
# ---------------------------------------------------------------------------


def test_deactivated_default_falls_back_to_same_role_profile(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """The reporter's headline scenario, catalog half: the default is absent
    from the catalog but a same-role profile is available → every composed
    step dispatches through that profile, with a WARNING naming both."""
    repo_root = _repo(tmp_path)
    fake = _CatalogFakeInvocationExecutor(
        [
            _profile("architect-alphonso", "architect"),
            _profile("project-researcher", _DEFAULT_ROLE, routing_priority=70),
        ]
    )
    with caplog.at_level(logging.WARNING, logger="specify_cli.mission_step_contracts.executor"):
        result = _execute(repo_root, fake)

    assert result.profile_hint == "project-researcher"
    assert fake.profile_hints
    assert all(hint == "project-researcher" for hint in fake.profile_hints)

    warnings = [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]
    assert any(_DEFAULT_PROFILE in message and "project-researcher" in message for message in warnings), warnings


def test_default_present_in_catalog_dispatches_unchanged(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """Negative case: the default is activated → byte-identical dispatch
    (the table default), and no fallback WARNING fires."""
    repo_root = _repo(tmp_path)
    fake = _CatalogFakeInvocationExecutor([_profile(_DEFAULT_PROFILE, _DEFAULT_ROLE), _profile("other", "reviewer")])
    with caplog.at_level(logging.WARNING, logger="specify_cli.mission_step_contracts.executor"):
        result = _execute(repo_root, fake)

    assert result.profile_hint == _DEFAULT_PROFILE
    assert all(hint == _DEFAULT_PROFILE for hint in fake.profile_hints)
    assert not [record for record in caplog.records if record.levelno == logging.WARNING]


def test_deactivated_default_without_role_mate_raises_structured_error(
    tmp_path: Path,
) -> None:
    """No same-role profile anywhere in the catalog → the structured
    FR-009 composition-failure surface, naming the mission/action, the
    deactivated default, its role, and the remedy — never the pre-fix
    laundered ``ProfileNotFoundError`` crash."""
    repo_root = _repo(tmp_path)
    fake = _CatalogFakeInvocationExecutor([_profile("architect-alphonso", "architect")])

    with pytest.raises(StepContractExecutionError) as excinfo:
        _execute(repo_root, fake)

    message = str(excinfo.value)
    assert f"{_MISSION}/{_ACTION}" in message
    assert _DEFAULT_PROFILE in message
    assert _DEFAULT_ROLE in message
    assert "no available profile carries that role" in message


def test_empty_catalog_raises_structured_error(tmp_path: Path) -> None:
    """The reporter's exact state — every shipped profile deactivated, the
    catalog empty (``Available: []``) — must produce the structured error,
    not a crash."""
    repo_root = _repo(tmp_path)
    fake = _CatalogFakeInvocationExecutor([])

    with pytest.raises(StepContractExecutionError, match=_DEFAULT_PROFILE):
        _execute(repo_root, fake)


def test_explicit_profile_hint_bypasses_the_catalog_entirely(tmp_path: Path) -> None:
    """An explicit ``context.profile_hint`` never consults the catalog (and
    never falls back), even when neither it nor the default is available."""
    repo_root = _repo(tmp_path)
    fake = _CatalogFakeInvocationExecutor([])

    result = _execute(repo_root, fake, profile_hint="my-explicit-profile")

    assert result.profile_hint == "my-explicit-profile"


def test_legacy_fake_executor_without_catalog_keeps_default(tmp_path: Path) -> None:
    """The established fake-executor test pattern (no
    ``list_available_profiles``) keeps the pre-#4115 behavior: the table
    default is returned unjudged, so every existing test of that shape
    stays green."""
    repo_root = _repo(tmp_path)

    result = _execute(repo_root, _LegacyFakeInvocationExecutor())

    assert result.profile_hint == _DEFAULT_PROFILE


# ---------------------------------------------------------------------------
# Deterministic selection within the fallback
# ---------------------------------------------------------------------------


def test_select_role_fallback_prefers_highest_routing_priority() -> None:
    """Higher ``routing_priority`` wins — the router's own tie-break
    semantics (``invocation/router.py``)."""
    catalog = [
        _profile("a-researcher", _DEFAULT_ROLE, routing_priority=30),
        _profile("z-researcher", _DEFAULT_ROLE, routing_priority=90),
    ]
    chosen = StepContractExecutor._select_role_fallback(catalog, _DEFAULT_ROLE)
    assert chosen is not None
    assert chosen.profile_id == "z-researcher"


def test_select_role_fallback_breaks_priority_ties_by_profile_id() -> None:
    """Equal priorities → profile_id ascending: two same-priority candidates
    can never dispatch nondeterministically."""
    catalog = [
        _profile("z-researcher", _DEFAULT_ROLE, routing_priority=90),
        _profile("b-researcher", _DEFAULT_ROLE, routing_priority=90),
    ]
    chosen = StepContractExecutor._select_role_fallback(catalog, _DEFAULT_ROLE)
    assert chosen is not None
    assert chosen.profile_id == "b-researcher"


def test_select_role_fallback_returns_none_without_role_mate() -> None:
    chosen = StepContractExecutor._select_role_fallback([_profile("architect-alphonso", "architect")], _DEFAULT_ROLE)
    assert chosen is None


# ---------------------------------------------------------------------------
# Table/pack consistency guard (both directions of the mirror)
# ---------------------------------------------------------------------------


def test_default_profile_roles_cover_every_table_value() -> None:
    """Every profile the table can name has a pinned role — a table entry
    without one would silently lose the fallback (no role to match)."""
    assert set(_DEFAULT_PROFILE_ROLES) == set(_ACTION_PROFILE_DEFAULTS.values())


def test_default_profile_roles_mirror_shipped_pack_yaml() -> None:
    """Each pinned role equals the shipped profile's first ``roles:`` entry,
    so the fallback matches the same profiles the shipped pack declares."""
    yaml = YAML(typ="safe")
    for profile_id, role in sorted(_DEFAULT_PROFILE_ROLES.items()):
        path = _PACK_AGENT_PROFILES_DIR / f"{profile_id}.agent.yaml"
        assert path.is_file(), f"shipped profile {profile_id} not found at {path}"
        data = yaml.load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        roles = data.get("roles")
        assert isinstance(roles, list) and roles, f"{path} declares no roles"
        assert roles[0] == role, f"{profile_id}: pinned role {role!r} drifted from the shipped pack's first role {roles[0]!r} — update _DEFAULT_PROFILE_ROLES"


# ---------------------------------------------------------------------------
# Shared advisory warning text (deactivate + preflight surfaces)
# ---------------------------------------------------------------------------


def test_mission_default_profile_warning_names_bound_steps() -> None:
    warning = mission_default_profile_warning(_DEFAULT_PROFILE)
    assert warning is not None
    assert f"{_MISSION}/{_ACTION}" in warning
    assert "research/scoping" in warning
    assert _DEFAULT_ROLE in warning


def test_mission_default_profile_warning_none_for_ordinary_profile() -> None:
    assert mission_default_profile_warning("architect-alphonso") is not None  # also a default
    assert mission_default_profile_warning("my-custom-profile") is None
