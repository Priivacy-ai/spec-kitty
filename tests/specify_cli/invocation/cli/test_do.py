"""Integration tests for spec-kitty do CLI surface (open-Op dispatch).

The 'do' command routes via ActionRouter by default (profile_hint=None).
An optional --profile bypasses the router when the caller knows which
profile to target, avoiding ROUTER_AMBIGUOUS on generic verbs like "fix".

Open-Op lifecycle (FR-001/FR-002): a successful do writes the started event
only and leaves the Op OPEN — no completed event, no auto-commit. The close
contract is printed (rich) / embedded (JSON) per contracts/cli-do-output.md.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from specify_cli import app as cli_app
from glossary.chokepoint import GlossaryObservationBundle
from glossary.models import (
    ConflictType,
    SemanticConflict,
    SenseRef,
    Severity,
    TermSurface,
)
from specify_cli.invocation.writer import EVENTS_DIR

# Marked for mutmut sandbox skip (subprocess CLI invocation) and git_repo
# (FR-012 untracked-Op test runs git via subprocess).
pytestmark = [pytest.mark.non_sandbox, pytest.mark.git_repo]


class ArgvCliRunner(CliRunner):
    def invoke(self, app, args=None, **kwargs):  # type: ignore[no-untyped-def]
        argv = ["spec-kitty", *(list(args) if args is not None and not isinstance(args, str) else [])]
        with patch.object(sys, "argv", argv):
            return super().invoke(app, args, **kwargs)


runner = ArgvCliRunner()

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "profiles"


# ---------------------------------------------------------------------------
# Shared context mocks
# ---------------------------------------------------------------------------

_COMPACT_CTX = MagicMock()
_COMPACT_CTX.mode = "compact"
_COMPACT_CTX.text = "compact governance context"

_MISSING_CTX = MagicMock()
_MISSING_CTX.mode = "missing"
_MISSING_CTX.text = ""


def _setup_project(tmp_path: Path) -> Path:
    """Create minimal project structure with fixture profiles."""
    kittify_dir = tmp_path / ".kittify"
    kittify_dir.mkdir(parents=True)
    profiles_dir = kittify_dir / "profiles"
    profiles_dir.mkdir()
    for yaml_file in FIXTURES_DIR.glob("*.agent.yaml"):
        shutil.copy(yaml_file, profiles_dir / yaml_file.name)
    return tmp_path


def _high_severity_bundle() -> GlossaryObservationBundle:
    conflict = SemanticConflict(
        term=TermSurface("lane"),
        conflict_type=ConflictType.AMBIGUOUS,
        severity=Severity.HIGH,
        confidence=1.0,
        candidate_senses=[
            SenseRef(
                surface="lane",
                scope="spec_kitty_core",
                definition="Execution lane",
                confidence=1.0,
            ),
            SenseRef(
                surface="lane",
                scope="team_domain",
                definition="Worktree lane",
                confidence=1.0,
            ),
        ],
        context="request_text",
    )
    return GlossaryObservationBundle(
        matched_urns=("glossary:d93244e7",),
        high_severity=(conflict,),
        all_conflicts=(conflict,),
        tokens_checked=3,
        duration_ms=1.5,
        error_msg=None,
    )


def _make_mock_registry(profile_specs: list[dict]) -> MagicMock:
    """Build a lightweight mock ProfileRegistry with controlled profiles.

    Uses MagicMock to avoid shipped-profile interference.
    """
    from doctrine.agent_profiles.profile import Role

    mock_profiles = []
    for spec in profile_specs:
        p = MagicMock()
        p.profile_id = spec["profile_id"]
        p.role = Role(spec["role_value"])
        p.routing_priority = spec.get("routing_priority", 50)
        p.name = spec.get("name", spec["profile_id"])

        sc = MagicMock()
        sc.domain_keywords = spec.get("domain_keywords", [])
        p.specialization_context = sc

        collab = MagicMock()
        collab.canonical_verbs = spec.get("collab_verbs", [])
        p.collaboration = collab

        mock_profiles.append(p)

    registry = MagicMock()
    registry.list_all.return_value = mock_profiles

    def _get(pid: str) -> object:
        return next((p for p in mock_profiles if p.profile_id == pid), None)

    def _resolve(pid: str) -> object:
        from specify_cli.invocation.errors import ProfileNotFoundError  # noqa: PLC0415

        profile = _get(pid)
        if profile is None:
            raise ProfileNotFoundError(pid, [p.profile_id for p in mock_profiles])
        return profile

    registry.get.side_effect = _get
    registry.resolve.side_effect = _resolve
    return registry


def _IMPLEMENTER_REGISTRY() -> object:
    return _make_mock_registry(
        [
            {
                "profile_id": "implementer-fixture",
                "role_value": "implementer",
                "routing_priority": 50,
                "name": "Implementer (fixture)",
                "domain_keywords": ["implement", "build", "code"],
            },
        ]
    )


def _REVIEWER_REGISTRY() -> object:
    return _make_mock_registry(
        [
            {
                "profile_id": "reviewer-fixture",
                "role_value": "reviewer",
                "routing_priority": 50,
                "name": "Reviewer (fixture)",
                "domain_keywords": ["review", "audit"],
            },
        ]
    )


# ---------------------------------------------------------------------------
# Successful routing tests
# ---------------------------------------------------------------------------


class TestDoSuccessfulRouting:
    def test_implement_request_routes_to_implementer(self, tmp_path: Path) -> None:
        """'implement the feature' routes to implementer-fixture via CANONICAL_VERB_MAP."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["profile_id"] == "implementer-fixture"
        assert data["action"] == "implement"
        assert data["router_confidence"] == "canonical_verb"
        assert data["invocation_id"]

    def test_returns_valid_invocation_payload_shape(self, tmp_path: Path) -> None:
        """JSON output has all required InvocationPayload fields."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the payment module", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "invocation_id" in data
        assert "profile_id" in data
        assert "action" in data
        assert "router_confidence" in data
        assert "governance_context_available" in data

    def test_creates_jsonl_record_on_successful_routing(self, tmp_path: Path) -> None:
        """Successful routing creates a JSONL invocation record."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the payment module", "--json"],
            )
        assert result.exit_code == 0, result.output
        events_dir = project / EVENTS_DIR
        # Filter out ops-index.jsonl — it is the O(n) index aide, not an invocation file.
        invocation_files = [f for f in (events_dir.glob("*.jsonl") if events_dir.exists() else []) if f.name != "ops-index.jsonl"]
        assert len(invocation_files) == 1
        # FR-001/FR-002: do leaves the Op OPEN — exactly one started lifecycle
        # event, never a completed event.
        events = [json.loads(line) for line in invocation_files[0].read_text().splitlines() if line.strip()]
        lifecycle = [e.get("event") for e in events if e.get("event") in ("started", "completed")]
        assert lifecycle == ["started"], f"do must write exactly one started event and no completed event, got: {lifecycle}"

    def test_rich_output_exits_zero(self, tmp_path: Path) -> None:
        """Without --json, rich output is produced with exit 0."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature"],
            )
        assert result.exit_code == 0, result.output
        assert "Close this record" not in result.output

    def test_rich_output_includes_close_contract(self, tmp_path: Path) -> None:
        """Rich output prints the close-contract block with the real invocation id.

        The retired commit hint (git add kitty-ops/…) must be gone — close-time
        auto-commit (FR-012) makes it wrong advice.
        """
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature"],
            )
        assert result.exit_code == 0, result.output
        # Rich may wrap at narrow terminal widths; check parts independently
        flat = result.output.replace("\n", " ")
        assert "This Op is OPEN" in flat
        assert "profile-invocation complete" in flat.replace("  ", " ") or ("profile-invocation" in flat and "complete" in flat)
        # The real invocation id is interpolated into the complete command.
        events_dir = project / EVENTS_DIR
        invocation_files = [f for f in events_dir.glob("*.jsonl") if f.name != "ops-index.jsonl"]
        assert len(invocation_files) == 1
        invocation_id = invocation_files[0].stem
        squashed = flat.replace(" ", "")
        assert invocation_id in squashed
        assert "doctor ops" in flat
        assert "git add" not in flat, "retired commit hint must not appear in rich output"

    def test_json_output_omits_close_contract_hint_text(self, tmp_path: Path) -> None:
        """--json output is pure JSON: no rich hint text, no commit hint."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "--json", "implement the feature"],
            )
        assert result.exit_code == 0, result.output
        assert "git add kitty-ops/" not in result.output
        assert "This Op is OPEN" not in result.output
        # Output parses as a single JSON document.
        json.loads(result.output)

    def test_json_output_does_not_render_inline_glossary_notices(self, tmp_path: Path) -> None:
        """--json output must not be polluted by post-payload inline notices."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch("glossary.observation.ObservationSurface.collect_notices") as collect,
            patch("glossary.observation.ObservationSurface.render_notices") as render,
        ):
            result = runner.invoke(
                cli_app,
                ["do", "--json", "implement the feature"],
            )
        assert result.exit_code == 0, result.output
        json.loads(result.output)
        collect.assert_not_called()
        render.assert_not_called()

    def test_rich_output_surfaces_high_severity_glossary_warning(self, tmp_path: Path) -> None:
        """High-severity glossary conflicts should be shown inline before governance context."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch(
                "glossary.chokepoint.GlossaryChokepoint.run",
                return_value=_high_severity_bundle(),
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature"],
            )
        assert result.exit_code == 0, result.output
        assert "High-severity terminology conflicts detected before this invocation." in result.output
        assert "lane (ambiguous)" in result.output
        assert result.output.index("lane (ambiguous)") < result.output.index("compact governance context")


# ---------------------------------------------------------------------------
# Open-Op lifecycle (FR-001/FR-002/FR-008, NFR-001)
# ---------------------------------------------------------------------------


class TestDoOpenOpLifecycle:
    def _invoke_do(self, project: Path, args: list[str], extra_patches: tuple = ()):  # type: ignore[no-untyped-def]
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            from contextlib import ExitStack

            with ExitStack() as stack:
                for p in extra_patches:
                    stack.enter_context(p)
                return runner.invoke(cli_app, ["do", *args])

    def test_json_output_has_status_open_and_close_contract(self, tmp_path: Path) -> None:
        """--json payload carries status="open" and the close_contract object."""
        project = _setup_project(tmp_path)
        result = self._invoke_do(project, ["implement the feature", "--json"])
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["status"] == "open"
        contract = data["close_contract"]
        assert data["invocation_id"] in contract["command"]
        assert contract["command"].startswith("spec-kitty profile-invocation complete")
        assert contract["outcomes"] == ["done", "failed", "abandoned"]
        assert contract["evidence_flag"] == "--evidence"
        assert contract["artifact_flag"] == "--artifact"
        assert contract["commit_flag"] == "--commit"

    def test_successful_do_leaves_op_file_untracked(self, tmp_path: Path) -> None:
        """Open Ops are never auto-committed (FR-012): file stays untracked."""
        project = _setup_project(tmp_path)
        subprocess.run(["git", "init", "-q"], cwd=project, check=True)
        result = self._invoke_do(project, ["implement the feature", "--json"])
        assert result.exit_code == 0, result.output
        invocation_id = json.loads(result.output)["invocation_id"]
        op_rel = f"{EVENTS_DIR}/{invocation_id}.jsonl"
        assert (project / op_rel).exists()
        tracked = subprocess.run(
            ["git", "ls-files", "--", op_rel],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        assert tracked == "", f"open Op record must stay untracked, but git tracks: {tracked}"
        status = subprocess.run(
            ["git", "status", "--porcelain", "--", op_rel],
            cwd=project,
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        assert status.startswith("??"), f"expected untracked (??) status, got: {status!r}"

    def test_propagator_receives_started_event(self, tmp_path: Path) -> None:
        """FR-008: do submits the started event to the SaaS propagator (parity with ask/advise)."""
        from specify_cli.invocation.propagator import InvocationSaaSPropagator
        from specify_cli.invocation.record import OpStartedEvent

        project = _setup_project(tmp_path)
        submitted: list[object] = []

        def _spy_submit(self: object, record: object) -> None:
            submitted.append(record)

        result = self._invoke_do(
            project,
            ["implement the feature", "--json"],
            extra_patches=(patch.object(InvocationSaaSPropagator, "submit", _spy_submit),),
        )
        assert result.exit_code == 0, result.output
        assert len(submitted) == 1, "exactly one (started) event must be submitted"
        record = submitted[0]
        assert isinstance(record, OpStartedEvent)
        assert record.invocation_id == json.loads(result.output)["invocation_id"]

    def test_sync_disabled_writes_locally_without_propagation(self, tmp_path: Path) -> None:
        """Sync-gated: with sync disabled, the SaaS client is never consulted but
        the local started record is still written (LOCAL-FIRST invariant)."""
        from specify_cli.invocation import propagator as propagator_mod
        from specify_cli.sync.routing import CheckoutSyncRouting

        project = _setup_project(tmp_path)
        routing = CheckoutSyncRouting(
            repo_root=project,
            project_uuid="test-uuid",
            project_slug="test-slug",
            build_id=None,
            repo_slug="test-repo",
            local_sync_enabled=False,
            repo_default_sync_enabled=None,
            effective_sync_enabled=False,
        )

        # Run propagation synchronously so the sync-gate is exercised in-test.
        def _sync_submit(self: propagator_mod.InvocationSaaSPropagator, record: object) -> None:
            propagator_mod._propagate_one(record, project)  # type: ignore[arg-type]

        client_spy = MagicMock()
        result = self._invoke_do(
            project,
            ["implement the feature", "--json"],
            extra_patches=(
                patch.object(propagator_mod.InvocationSaaSPropagator, "submit", _sync_submit),
                patch.object(propagator_mod, "resolve_checkout_sync_routing", return_value=routing),
                patch.object(propagator_mod, "_get_saas_client", client_spy),
            ),
        )
        assert result.exit_code == 0, result.output
        client_spy.assert_not_called()
        invocation_id = json.loads(result.output)["invocation_id"]
        assert (project / EVENTS_DIR / f"{invocation_id}.jsonl").exists(), "local started record must be written even when sync is disabled"

    def test_propagator_submission_is_non_blocking(self, tmp_path: Path) -> None:
        """NFR-001: do returns without awaiting propagation delivery.

        A propagation worker blocked on an event the test never sets (until
        teardown) must not delay command exit.
        """
        from specify_cli.invocation import propagator as propagator_mod

        project = _setup_project(tmp_path)
        release = threading.Event()
        started_propagating = threading.Event()

        def _blocking_propagate(record: object, repo_root: Path) -> None:
            started_propagating.set()
            release.wait(timeout=30)

        try:
            start = time.monotonic()
            result = self._invoke_do(
                project,
                ["implement the feature", "--json"],
                extra_patches=(patch.object(propagator_mod, "_propagate_one", _blocking_propagate),),
            )
            elapsed = time.monotonic() - start
        finally:
            release.set()  # unblock the worker so the executor can drain at exit
        assert result.exit_code == 0, result.output
        assert started_propagating.wait(timeout=5), "propagation worker never started"
        assert elapsed < 10, f"do blocked for {elapsed:.1f}s — propagator submission must be non-blocking"


# ---------------------------------------------------------------------------
# Routing failure / error tests
# ---------------------------------------------------------------------------


class TestDoRoutingFailures:
    def test_ambiguous_request_exits_1(self, tmp_path: Path) -> None:
        """Vague request 'help me' — no canonical verb match — exits 1."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "help me", "--json"],
            )
        assert result.exit_code == 1

    def test_no_match_request_exits_1(self, tmp_path: Path) -> None:
        """Request with no recognizable verbs exits 1 (ROUTER_NO_MATCH)."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "the quick brown fox", "--json"],
            )
        assert result.exit_code == 1

    def test_no_match_writes_error_to_stderr(self, tmp_path: Path) -> None:
        """ROUTER_NO_MATCH or ROUTER_AMBIGUOUS error is reported (CliRunner merges streams)."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "the quick brown fox", "--json"],
                catch_exceptions=False,
            )
        # CliRunner merges stderr into output by default
        assert result.exit_code == 1
        out = result.output.strip()
        assert out, "Expected error output on failure"
        err_data = json.loads(out)
        assert err_data.get("error") == "routing_failed"
        assert err_data.get("error_code") in ("ROUTER_NO_MATCH", "ROUTER_AMBIGUOUS")

    def test_no_profiles_exits_1(self, tmp_path: Path) -> None:
        """When no profiles are registered, router raises RouterAmbiguityError → exit 1."""
        project = _setup_project(tmp_path)
        # Empty mock registry — no profiles
        empty_registry = _make_mock_registry([])
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=empty_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature", "--json"],
            )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# Profile-hint: None by default, forwarded when --profile is supplied
# ---------------------------------------------------------------------------


class TestDoProfileHint:
    def test_executor_called_with_none_profile_hint_by_default(self, tmp_path: Path) -> None:
        """Without --profile, do passes profile_hint=None to executor.invoke()."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        captured_hints: list[object] = []

        from specify_cli.invocation.executor import ProfileInvocationExecutor

        original_invoke = ProfileInvocationExecutor.invoke

        def _spy_invoke(self: object, request_text: str, profile_hint: object = None, actor: str = "unknown", **kwargs: object) -> object:  # type: ignore[misc]
            captured_hints.append(profile_hint)
            return original_invoke(self, request_text, profile_hint=profile_hint, actor=actor, **kwargs)  # type: ignore[misc]

        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch.object(ProfileInvocationExecutor, "invoke", _spy_invoke),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "implement the feature", "--json"],
            )
        assert result.exit_code == 0, result.output
        assert len(captured_hints) == 1
        assert captured_hints[0] is None, f"do without --profile must pass profile_hint=None, got: {captured_hints[0]!r}"

    def test_executor_called_with_profile_hint_when_profile_flag_given(self, tmp_path: Path) -> None:
        """With --profile, do forwards the profile ID as profile_hint to executor.invoke()."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        captured_hints: list[object] = []

        from specify_cli.invocation.executor import ProfileInvocationExecutor

        original_invoke = ProfileInvocationExecutor.invoke

        def _spy_invoke(self: object, request_text: str, profile_hint: object = None, actor: str = "unknown", **kwargs: object) -> object:  # type: ignore[misc]
            captured_hints.append(profile_hint)
            return original_invoke(self, request_text, profile_hint=profile_hint, actor=actor, **kwargs)  # type: ignore[misc]

        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
            patch.object(ProfileInvocationExecutor, "invoke", _spy_invoke),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "--profile", "implementer-fixture", "implement the feature", "--json"],
            )
        assert result.exit_code == 0, result.output
        assert len(captured_hints) == 1
        assert captured_hints[0] == "implementer-fixture", f"do --profile must forward the profile ID as profile_hint, got: {captured_hints[0]!r}"

    def test_profile_flag_bypasses_ambiguous_routing(self, tmp_path: Path) -> None:
        """--profile succeeds even when the request would otherwise be ROUTER_AMBIGUOUS."""
        project = _setup_project(tmp_path)
        # Two implementer profiles — "fix" alone would be ambiguous
        ambiguous_registry = _make_mock_registry(
            [
                {"profile_id": "implementer-a", "role_value": "implementer", "routing_priority": 50},
                {"profile_id": "implementer-b", "role_value": "implementer", "routing_priority": 50},
            ]
        )
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=ambiguous_registry),
            # executor.py also creates its own ProfileRegistry — patch both
            patch("specify_cli.invocation.executor.ProfileRegistry", return_value=ambiguous_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "--profile", "implementer-a", "fix the bug", "--json"],
            )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["profile_id"] == "implementer-a"
        # executor resolves profile_hint directly, bypassing the router — confidence is None
        assert data["router_confidence"] is None


# ---------------------------------------------------------------------------
# Invalid --profile: structured JSON error, no mutation
# ---------------------------------------------------------------------------


class TestDoInvalidProfile:
    def test_invalid_profile_exits_1(self, tmp_path: Path) -> None:
        """--profile with unknown ID exits 1."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch("specify_cli.invocation.executor.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "--profile", "no-such-profile", "fix the bug", "--json"],
                catch_exceptions=False,
            )
        assert result.exit_code == 1

    def test_invalid_profile_emits_structured_json(self, tmp_path: Path) -> None:
        """--profile with unknown ID emits PROFILE_NOT_FOUND JSON on stderr (merged by CliRunner)."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch("specify_cli.invocation.executor.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "--profile", "no-such-profile", "fix the bug", "--json"],
                catch_exceptions=False,
            )
        out = result.output.strip()
        assert out, "Expected JSON error output on invalid profile"
        data = json.loads(out)
        assert data["error"] == "routing_failed"
        assert data["error_code"] == "PROFILE_NOT_FOUND"

    def test_invalid_profile_writes_no_op_record(self, tmp_path: Path) -> None:
        """--profile with unknown ID must not write any Op record (no mutation on failure)."""
        project = _setup_project(tmp_path)
        mock_registry = _IMPLEMENTER_REGISTRY()
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=mock_registry),
            patch("specify_cli.invocation.executor.ProfileRegistry", return_value=mock_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            runner.invoke(
                cli_app,
                ["do", "--profile", "no-such-profile", "fix the bug", "--json"],
            )
        events_dir = project / EVENTS_DIR
        op_files = [f for f in (events_dir.glob("*.jsonl") if events_dir.exists() else []) if f.name != "ops-index.jsonl"]
        assert op_files == [], f"No Op records should be written on PROFILE_NOT_FOUND, got: {op_files}"


# ---------------------------------------------------------------------------
# Ambiguity error surfaces --profile escape hatch
# ---------------------------------------------------------------------------


class TestDoAmbiguityMentionsProfileFlag:
    def test_ambiguity_error_mentions_do_profile(self, tmp_path: Path) -> None:
        """ROUTER_AMBIGUOUS suggestion must mention 'do --profile' so agents know the escape hatch."""
        project = _setup_project(tmp_path)
        ambiguous_registry = _make_mock_registry(
            [
                {"profile_id": "implementer-a", "role_value": "implementer", "routing_priority": 50},
                {"profile_id": "implementer-b", "role_value": "implementer", "routing_priority": 50},
            ]
        )
        with (
            patch("specify_cli.cli.commands.do_cmd.find_repo_root", return_value=project),
            patch("specify_cli.cli.commands.do_cmd.ProfileRegistry", return_value=ambiguous_registry),
            patch(
                "specify_cli.invocation.executor.build_charter_context",
                return_value=_COMPACT_CTX,
            ),
        ):
            result = runner.invoke(
                cli_app,
                ["do", "fix the bug", "--json"],
                catch_exceptions=False,
            )
        assert result.exit_code == 1
        data = json.loads(result.output.strip())
        assert "do --profile" in data["suggestion"], f"Ambiguity suggestion must mention 'do --profile', got: {data['suggestion']!r}"


# ---------------------------------------------------------------------------
# Help / discoverability tests
# ---------------------------------------------------------------------------


class TestDoHelp:
    def test_do_help_exits_zero(self) -> None:
        result = runner.invoke(cli_app, ["do", "--help"])
        assert result.exit_code == 0
        assert "do" in result.output.lower()

    def test_do_help_mentions_router(self) -> None:
        result = runner.invoke(cli_app, ["do", "--help"])
        assert result.exit_code == 0
        # Should mention routing / ActionRouter concept
        assert any(keyword in result.output.lower() for keyword in ("route", "router", "profile", "dispatch"))
