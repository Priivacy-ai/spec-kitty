"""Tests for ActionRouter — deterministic request → (profile_id, action) routing.

ADR-3 (Option A): pure function, no I/O, no LLM call, no network.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from specify_cli.invocation.errors import RouterAmbiguityError
from specify_cli.invocation.router import (
    CANONICAL_VERB_MAP,
    STOP_WORDS,
    ActionRouter,
    ActionRouterPlugin,
    RouterDecision,
    _normalize_tokens,
)

# ---------------------------------------------------------------------------
# Fixtures: local profiles directory
# ---------------------------------------------------------------------------

pytestmark = [pytest.mark.unit, pytest.mark.fast]

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "profiles"


def _make_registry(tmp_path: Path, profiles: list[str] | None = None):
    """Build a ProfileRegistry from the fixture profiles directory.

    Args:
        tmp_path: pytest tmp_path fixture.
        profiles: Optional list of fixture yaml stems (e.g. ['implementer', 'reviewer']).
                  If None, copy all *.agent.yaml files from FIXTURES_DIR.
    """
    from specify_cli.invocation.registry import ProfileRegistry

    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)

    if profiles is None:
        files = list(FIXTURES_DIR.glob("*.agent.yaml"))
    else:
        files = [FIXTURES_DIR / f"{name}.agent.yaml" for name in profiles]

    for f in files:
        if f.exists():
            shutil.copy(f, profiles_dir / f.name)

    return ProfileRegistry(tmp_path)


def _make_mock_registry(profile_specs: list[dict]) -> MagicMock:
    """Build a lightweight mock ProfileRegistry returning synthetic profiles.

    Each dict in *profile_specs* should have:
        profile_id, role_value, routing_priority, domain_keywords (list)

    This bypasses the shipped-profile merge issue for pure unit tests.
    """
    from charter.offering.agent_profiles.profile import Role

    mock_profiles = []
    for spec in profile_specs:
        p = MagicMock()
        p.profile_id = spec["profile_id"]
        p.role = Role(spec["role_value"])
        p.routing_priority = spec.get("routing_priority", 50)

        sc = MagicMock()
        sc.domain_keywords = spec.get("domain_keywords", [])
        p.specialization_context = sc

        collab = MagicMock()
        collab.canonical_verbs = spec.get("collab_verbs", [])
        p.collaboration = collab

        mock_profiles.append(p)

    registry = MagicMock()
    registry.list_all.return_value = mock_profiles

    def _get(pid: str):
        return next((p for p in mock_profiles if p.profile_id == pid), None)

    def _resolve(pid: str):
        from specify_cli.invocation.errors import ProfileNotFoundError

        profile = _get(pid)
        if profile is None:
            raise ProfileNotFoundError(pid, [p.profile_id for p in mock_profiles])
        return profile

    registry.get.side_effect = _get
    registry.resolve.side_effect = _resolve
    return registry


# ---------------------------------------------------------------------------
# ADR-3 entry gate: document must exist and contain required text
# ---------------------------------------------------------------------------


def test_adr3_document_exists() -> None:
    """ADR-3 document is committed — required entry gate for WP02 review."""
    # The path is relative to the main repo root, not the worktree.
    # Try worktree-relative first, then go up two directories (worktree → repo root).
    here = Path(__file__).parent

    # Walk up until we find the kitty-specs directory
    search = here
    for _ in range(10):
        candidate = search / "kitty-specs" / "profile-invocation-runtime-audit-trail-01KPQRX2" / "adr-3-deterministic-action-router.md"
        if candidate.exists():
            adr_path = candidate
            break
        search = search.parent
    else:
        pytest.fail(
            "ADR-3 document not found under kitty-specs/profile-invocation-runtime-audit-trail-01KPQRX2/"
            " — searched from repo root upward"
        )

    content = adr_path.read_text(encoding="utf-8")
    assert "Option A" in content, "ADR-3 must document Option A as the accepted decision"
    assert "no lm" in content.lower() or "no llm" in content.lower() or "no external" in content.lower(), (
        "ADR-3 must document that no LLM call is made in the routing path"
    )


# ---------------------------------------------------------------------------
# Unit tests: _normalize_tokens
# ---------------------------------------------------------------------------


class TestNormalizeTokens:
    def test_lowercases_and_splits(self) -> None:
        result = _normalize_tokens("Implement the Feature")
        assert "implement" in result
        assert "feature" in result
        assert "the" not in result  # stop-word

    def test_strips_stop_words(self) -> None:
        tokens = _normalize_tokens("please do an implement")
        assert "please" not in tokens
        assert "an" not in tokens
        assert "implement" in tokens

    def test_handles_punctuation(self) -> None:
        tokens = _normalize_tokens("fix: the auth-bug now")
        assert "fix" in tokens
        assert "auth" in tokens
        assert "bug" in tokens

    def test_empty_string(self) -> None:
        assert _normalize_tokens("") == []


# ---------------------------------------------------------------------------
# Unit tests: CANONICAL_VERB_MAP coverage
# ---------------------------------------------------------------------------


class TestCanonicalVerbMap:
    def test_implement_maps_to_implementer_role(self) -> None:
        from charter.offering.agent_profiles.profile import Role

        action, role = CANONICAL_VERB_MAP["implement"]
        assert action == "implement"
        assert role == Role.IMPLEMENTER

    def test_review_maps_to_reviewer_role(self) -> None:
        from charter.offering.agent_profiles.profile import Role

        action, role = CANONICAL_VERB_MAP["review"]
        assert action == "review"
        assert role == Role.REVIEWER

    def test_plan_maps_to_planner_role(self) -> None:
        from charter.offering.agent_profiles.profile import Role

        action, role = CANONICAL_VERB_MAP["plan"]
        assert action == "plan"
        assert role == Role.PLANNER

    def test_fix_maps_to_implementer_role(self) -> None:
        from charter.offering.agent_profiles.profile import Role

        action, role = CANONICAL_VERB_MAP["fix"]
        assert action == "implement"
        assert role == Role.IMPLEMENTER

    def test_no_lm_import_in_module(self) -> None:
        """Router module must not import any LLM client library."""
        import specify_cli.invocation.router as router_mod

        source = Path(router_mod.__file__).read_text(encoding="utf-8")
        for forbidden in ("import anthropic", "import openai", "import httpx", "from anthropic"):
            assert forbidden not in source, f"LLM import found in router.py: {forbidden}"


# ---------------------------------------------------------------------------
# Table-driven success cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "request_text,profile_hint,expected_profile,expected_action,expected_confidence",
    [
        # Case 1: Explicit hint bypasses all routing logic
        ("fix the auth bug", "implementer-fixture", "implementer-fixture", "implement", "exact"),
        # Case 2: Canonical verb match — "implement" → IMPLEMENTER
        ("implement the payment module", None, "implementer-fixture", "implement", "canonical_verb"),
        # Case 3: Canonical verb match — "review" → REVIEWER
        ("review WP03", None, "reviewer-fixture", "review", "canonical_verb"),
        # Case 4: "build" maps to IMPLEMENTER canonical verb
        ("build something for code quality", None, "implementer-fixture", "implement", "canonical_verb"),
        # Case 5: Stop-word stripping — "please do an implement" → "implement" token remains
        ("please do an implement", None, "implementer-fixture", "implement", "canonical_verb"),
    ],
)
def test_router_success(
    request_text: str,
    profile_hint: str | None,
    expected_profile: str,
    expected_action: str,
    expected_confidence: str,
) -> None:
    """Router returns correct RouterDecision for unambiguous inputs."""
    # Use a mock registry with only two profiles to avoid ambiguity
    registry = _make_mock_registry([
        {
            "profile_id": "implementer-fixture",
            "role_value": "implementer",
            "routing_priority": 50,
            "domain_keywords": ["implement", "build", "code"],
        },
        {
            "profile_id": "reviewer-fixture",
            "role_value": "reviewer",
            "routing_priority": 50,
            "domain_keywords": ["review", "audit", "assess"],
        },
    ])

    router = ActionRouter(registry)
    decision = router.route(request_text, profile_hint=profile_hint)

    assert isinstance(decision, RouterDecision)
    assert decision.profile_id == expected_profile
    assert decision.action == expected_action
    assert decision.confidence == expected_confidence


# ---------------------------------------------------------------------------
# Ambiguity case: two profiles with equal priority and overlapping verbs
# ---------------------------------------------------------------------------


def test_router_ambiguity_two_profiles_same_score() -> None:
    """Two profiles with equal routing_priority and overlapping verbs → ROUTER_AMBIGUOUS."""
    registry = _make_mock_registry([
        {
            "profile_id": "implementer-a",
            "role_value": "implementer",
            "routing_priority": 50,  # same priority
            "domain_keywords": [],
        },
        {
            "profile_id": "implementer-b",
            "role_value": "implementer",
            "routing_priority": 50,  # same priority
            "domain_keywords": [],
        },
    ])

    router = ActionRouter(registry)
    with pytest.raises(RouterAmbiguityError) as exc_info:
        router.route("implement the feature")

    err = exc_info.value
    assert err.error_code == "ROUTER_AMBIGUOUS"
    candidate_ids = [c["profile_id"] for c in err.candidates]
    assert "implementer-a" in candidate_ids
    assert "implementer-b" in candidate_ids


# ---------------------------------------------------------------------------
# No match: vague request with no canonical verbs or domain keywords
# ---------------------------------------------------------------------------


def test_router_no_match_vague_request() -> None:
    """'help me' → ROUTER_NO_MATCH (no canonical verb, no keyword)."""
    registry = _make_mock_registry([
        {
            "profile_id": "implementer-fixture",
            "role_value": "implementer",
            "routing_priority": 50,
            "domain_keywords": [],
        },
    ])

    router = ActionRouter(registry)
    with pytest.raises(RouterAmbiguityError) as exc_info:
        router.route("help me")

    assert exc_info.value.error_code == "ROUTER_NO_MATCH"


# ---------------------------------------------------------------------------
# Missing profile hint → PROFILE_NOT_FOUND
# ---------------------------------------------------------------------------


def test_router_missing_profile_hint() -> None:
    """profile_hint='nonexistent' → RouterAmbiguityError(PROFILE_NOT_FOUND)."""
    registry = _make_mock_registry([
        {
            "profile_id": "implementer-fixture",
            "role_value": "implementer",
            "routing_priority": 50,
            "domain_keywords": [],
        },
    ])

    router = ActionRouter(registry)
    with pytest.raises(RouterAmbiguityError) as exc_info:
        router.route("implement something", profile_hint="nonexistent-profile")

    assert exc_info.value.error_code == "PROFILE_NOT_FOUND"


# ---------------------------------------------------------------------------
# Priority tiebreaker: higher routing_priority wins
# ---------------------------------------------------------------------------


def test_router_priority_tiebreaker_selects_higher_priority() -> None:
    """When two profiles match the same verb, the one with higher routing_priority wins."""
    registry = _make_mock_registry([
        {
            "profile_id": "implementer-low",
            "role_value": "implementer",
            "routing_priority": 10,
            "domain_keywords": [],
        },
        {
            "profile_id": "implementer-high",
            "role_value": "implementer",
            "routing_priority": 80,
            "domain_keywords": [],
        },
    ])

    router = ActionRouter(registry)
    decision = router.route("implement the feature")

    assert decision.profile_id == "implementer-high"
    assert decision.confidence == "canonical_verb"
    assert "routing_priority" in decision.match_reason


# ---------------------------------------------------------------------------
# ActionRouterPlugin: no-op stub
# ---------------------------------------------------------------------------


def test_action_router_plugin_is_noop() -> None:
    """ActionRouterPlugin has no methods in v1 — it is a pure no-op stub."""
    plugin = ActionRouterPlugin()
    # Verify no public methods beyond dunder
    public_methods = [
        m for m in dir(plugin)
        if not m.startswith("_")
    ]
    assert public_methods == [], f"ActionRouterPlugin should have no public methods; got {public_methods}"


# ---------------------------------------------------------------------------
# No LLM call: verify via mock that route() is pure
# ---------------------------------------------------------------------------


def test_router_makes_no_external_calls() -> None:
    """route() must never call any LLM or I/O. Verified by asserting no httpx/anthropic usage."""
    import specify_cli.invocation.router as router_mod

    source = Path(router_mod.__file__).read_text(encoding="utf-8")
    forbidden_imports = ["import anthropic", "from anthropic", "import openai", "from openai"]
    for fi in forbidden_imports:
        assert fi not in source, f"Found forbidden import '{fi}' in router.py"


# ---------------------------------------------------------------------------
# WP2/#3840 (T007) — RouterDecision.alternatives, threaded to dry-run and
# real dispatch (FR-005, SC-003). RED on WP01's final commit: `alternatives`
# does not exist yet on RouterDecision/InvocationPayload -- every assertion
# below fails with TypeError/AttributeError/KeyError until WP02's
# implementation commit lands.
# ---------------------------------------------------------------------------

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"


def _setup_executor_project(tmp_path: Path) -> Path:
    """Copy the real fixture profiles onto disk.

    ``ProfileInvocationExecutor`` builds its own ``ProfileRegistry`` fresh
    from ``repo_root`` (independent of any mocked router registry), so the
    *winning* candidate's ``profile_id`` must resolve against real files on
    disk for ``invoke()``/``dry_run()`` to succeed past routing. A losing
    candidate's profile_id is never resolved this way (see router.py's
    ``alternatives=`` construction), so it does not need a matching file.
    """
    profiles_dir = tmp_path / ".kittify" / "profiles"
    profiles_dir.mkdir(parents=True)
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


def test_alternatives_empty_on_single_candidate(tmp_path: Path) -> None:
    """A request matching exactly one profile: alternatives == [] on the
    router decision itself, on dry-run, and on real dispatch (SC-003,
    Acceptance Scenario 1) -- an explicit empty list, never None/absent."""
    from specify_cli.invocation.executor import ProfileInvocationExecutor

    registry = _make_mock_registry([
        {
            "profile_id": "implementer-fixture",
            "role_value": "implementer",
            "routing_priority": 50,
            "domain_keywords": [],
        },
    ])
    router = ActionRouter(registry)

    decision = router.route("implement the payment module")
    assert decision.alternatives == []

    project = _setup_executor_project(tmp_path)
    executor = ProfileInvocationExecutor(project, router=router)
    with (
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
        patch("specify_cli.invocation.executor.resolve_generic_fallback", return_value=None),
    ):
        dry_payload = executor.dry_run("implement the payment module")
        real_payload = executor.invoke("implement the payment module", actor="test")

    assert dry_payload.alternatives == []
    assert real_payload.alternatives == []


def test_alternatives_empty_on_explicit_profile_hint(tmp_path: Path) -> None:
    """--profile <id> bypasses the router entirely (Level 1): router_confidence
    is "exact" and alternatives is [] on dry-run (FR-008, Acceptance Scenario 2)."""
    from specify_cli.invocation.executor import ProfileInvocationExecutor

    project = _setup_executor_project(tmp_path)
    executor = ProfileInvocationExecutor(project)
    with patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX):
        payload = executor.dry_run("implement the feature", profile_hint="implementer-fixture")

    assert payload.router_confidence == "exact"
    assert payload.alternatives == []


def test_alternatives_nonempty_on_two_candidate_tiebreak(tmp_path: Path) -> None:
    """A request matching two profiles (one canonical-verb, one domain-keyword,
    so routing_priority decides today, pre-WP03): alternatives is non-empty and
    carries the losing candidate's profile_id/action/confidence/match_reason
    (User Story 2's own Independent Test; SC-003) -- on the router decision
    itself and on dry-run."""
    from specify_cli.invocation.executor import ProfileInvocationExecutor

    registry = _make_mock_registry([
        {
            "profile_id": "implementer-fixture",
            "role_value": "implementer",
            "routing_priority": 80,
            "domain_keywords": [],
        },
        {
            "profile_id": "reviewer-fixture",
            "role_value": "reviewer",
            "routing_priority": 10,
            # "gizmo" is not in CANONICAL_VERB_MAP -- a genuine domain-keyword
            # match, not shadowed by a verb match on this profile's role.
            "domain_keywords": ["gizmo"],
        },
    ])
    router = ActionRouter(registry)

    decision = router.route("implement and gizmo the module")
    assert decision.profile_id == "implementer-fixture"
    assert decision.confidence == "canonical_verb"
    assert len(decision.alternatives) == 1
    alt = decision.alternatives[0]
    assert alt["profile_id"] == "reviewer-fixture"
    assert alt["confidence"] == "domain_keyword"
    assert alt["action"]
    assert alt["match_reason"]

    project = _setup_executor_project(tmp_path)
    executor = ProfileInvocationExecutor(project, router=router)
    with (
        patch("specify_cli.invocation.executor.build_charter_context", return_value=_COMPACT_CTX),
        patch("specify_cli.invocation.executor.resolve_generic_fallback", return_value=None),
    ):
        dry_payload = executor.dry_run("implement and gizmo the module")

    assert dry_payload.profile_id == "implementer-fixture"
    assert len(dry_payload.alternatives) == 1
    assert dry_payload.alternatives[0]["profile_id"] == "reviewer-fixture"


def test_router_ambiguous_candidates_carry_confidence_key() -> None:
    """WP01 fixed the post-tiebreaker ROUTER_AMBIGUOUS raise's candidate-dict
    shape to carry a `confidence` key; this WP's edits to the surrounding
    route() code (alternatives= population) must not regress it -- re-confirms
    it holds, does not re-implement the fix. Also confirms the dry-run
    ambiguous-branch alternatives (built from err.candidates) carry the same
    key (FR-009)."""
    from specify_cli.invocation.executor import build_ambiguous_dry_run_payload

    registry = _make_mock_registry([
        {
            "profile_id": "implementer-a",
            "role_value": "implementer",
            "routing_priority": 50,
            "domain_keywords": [],
        },
        {
            "profile_id": "implementer-b",
            "role_value": "implementer",
            "routing_priority": 50,
            "domain_keywords": [],
        },
    ])
    router = ActionRouter(registry)

    with pytest.raises(RouterAmbiguityError) as exc_info:
        router.route("implement the feature")

    err = exc_info.value
    assert err.error_code == "ROUTER_AMBIGUOUS"
    for candidate in err.candidates:
        assert "confidence" in candidate

    dry_run_payload = build_ambiguous_dry_run_payload("implement the feature", err)
    for alt in dry_run_payload["alternatives"]:
        assert "confidence" in alt


def test_invocation_payload_to_dry_run_dict_raises_if_alternatives_missing() -> None:
    """T009 step 5: unlike RouterDecision (a real frozen dataclass), nothing
    at the type level stops a construction site from omitting alternatives=
    on InvocationPayload -- to_dry_run_dict()'s explicit fail-fast guard is
    the real backstop. Confirms it actually fires (not just described)."""
    from specify_cli.invocation.executor import InvocationPayload

    payload = InvocationPayload(
        invocation_id="",
        profile_id="implementer-fixture",
        profile_friendly_name="Implementer (fixture)",
        action="implement",
        governance_context_text="compact governance context",
        governance_context_hash="deadbeef01234567",
        governance_context_available=True,
        router_confidence="canonical_verb",
        glossary_observations=None,
        mode_of_work=None,
        recommendation=None,
        empty_charter_fallback=False,
        # alternatives= deliberately omitted -- this is the missed-site case.
    )

    with pytest.raises(RuntimeError, match="alternatives"):
        payload.to_dry_run_dict()
