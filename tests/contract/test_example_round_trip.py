"""Contract example round-trip CI gate (Slice F WP03, FR-140 + FR-141).

Walker: discovers every ``kitty-specs/*/contracts/*.md`` file, extracts
fenced ``yaml`` codeblocks that carry the frontmatter convention introduced
by Slice F, and asserts the expected parse outcome against the declared
Pydantic model.

Frontmatter convention (per ``contract-round-trip-frontmatter.md``)
--------------------------------------------------------------------
Every parseable YAML codeblock in a contracts/ file that should be exercised
by this gate MUST have the first two non-blank comment lines inside the
codeblock be::

    # pydantic_model: <module.dotted.path.ClassName>
    # expect: valid | invalid

Optionally::

    # expect_message: <substring>   (only meaningful with ``expect: invalid``)

Codeblocks without ``# pydantic_model:`` are silently skipped (they are
documentation prose or shape sketches).

Legacy allowlist (FR-141)
-------------------------
Contracts from missions predating this convention are tracked in
``_LEGACY_CONTRACT_ALLOWLIST``.  Files in the allowlist emit a
``warnings.warn`` instead of failing when their YAML codeblocks lack
frontmatter.  The allowlist count is pinned in
``tests/architectural/_baselines.yaml::test_example_round_trip.legacy_contract_allowlist``
so it can shrink over time as legacy contracts are backfilled.

ATDD anchors
------------
* AC-10: ``test_contract_example_round_trip[*]`` (parametrised over every
  tagged codeblock)
* FR-140: walker discovers and exercises every tagged codeblock
* FR-141: legacy allowlist + baseline integration
"""

from __future__ import annotations

import importlib
import re
import warnings
from pathlib import Path
from typing import Any

import pydantic
import pytest
import yaml

pytestmark = [pytest.mark.contract]

# ---------------------------------------------------------------------------
# Repo root (resolve relative to this file: tests/contract/ -> tests/ -> root)
# ---------------------------------------------------------------------------
_REPO_ROOT: Path = Path(__file__).resolve().parents[2]
_KITTY_SPECS_ROOT: Path = _REPO_ROOT / "kitty-specs"

# ---------------------------------------------------------------------------
# This mission's slug — used to distinguish legacy from Slice F contracts
# ---------------------------------------------------------------------------
_SLICE_F_MISSION_SLUG: str = "slice-f-multi-context-extensibility-01KRX5C8"

# ---------------------------------------------------------------------------
# Legacy contract allowlist (FR-141)
# ---------------------------------------------------------------------------
# Contracts from missions predating the frontmatter convention.  Files in
# this set emit a warning (not a failure) when their YAML codeblocks lack
# ``# pydantic_model:`` frontmatter.  The count is pinned in
# ``tests/architectural/_baselines.yaml``.
#
# Populated by the WP03 discovery sweep.  Each entry is the path relative to
# the repo root (e.g. ``kitty-specs/002-lightweight-pypi-release/contracts/...``).
# ---------------------------------------------------------------------------
_LEGACY_CONTRACT_ALLOWLIST: frozenset[str] = frozenset(
    {
        "kitty-specs/002-lightweight-pypi-release/contracts/release-validation-cli.md",
        "kitty-specs/003-auto-protect-agent/contracts/test-contract.md",
        "kitty-specs/032-identity-aware-cli-event-sync/contracts/event-envelope.md",
        "kitty-specs/033-github-observability-event-metadata/contracts/event-envelope.md",
        "kitty-specs/039-cli-2x-readiness/contracts/lane-mapping.md",
        "kitty-specs/041-enable-plan-mission-runtime-support/contracts/command-template.md",
        "kitty-specs/041-mission-glossary-semantic-integrity/contracts/events.md",
        "kitty-specs/041-mission-glossary-semantic-integrity/contracts/middleware.md",
        "kitty-specs/047-namespace-aware-artifact-body-sync/contracts/push-content-api.md",
        "kitty-specs/048-tracker-publish-resource-routing/contracts/tracker-snapshot-publish.md",
        "kitty-specs/054-constitution-interview-compiler-and-bootstrap/contracts/constitution-cli-contract.md",
        "kitty-specs/058-mission-template-repository-refactor/contracts/mission-template-repository.md",
        "kitty-specs/062-tracker-binding-context-discovery/contracts/bind-confirm.md",
        "kitty-specs/062-tracker-binding-context-discovery/contracts/bind-resolve.md",
        "kitty-specs/062-tracker-binding-context-discovery/contracts/bind-validate.md",
        "kitty-specs/062-tracker-binding-context-discovery/contracts/existing-endpoint-evolution.md",
        "kitty-specs/062-tracker-binding-context-discovery/contracts/resources.md",
        "kitty-specs/064-complete-mission-identity-cutover/contracts/body-sync.md",
        "kitty-specs/064-complete-mission-identity-cutover/contracts/event-envelope.md",
        "kitty-specs/064-complete-mission-identity-cutover/contracts/orchestrator-api.md",
        "kitty-specs/064-complete-mission-identity-cutover/contracts/tracker-bind.md",
        "kitty-specs/068-post-merge-reliability-and-release-hardening/contracts/diff_coverage_policy.md",
        "kitty-specs/068-post-merge-reliability-and-release-hardening/contracts/merge_strategy.md",
        "kitty-specs/068-post-merge-reliability-and-release-hardening/contracts/recovery_extension.md",
        "kitty-specs/068-post-merge-reliability-and-release-hardening/contracts/release_prep.md",
        "kitty-specs/068-post-merge-reliability-and-release-hardening/contracts/stale_assertions.md",
        "kitty-specs/077-mission-terminology-cleanup/contracts/deprecation_warning.md",
        "kitty-specs/077-mission-terminology-cleanup/contracts/grep_guards.md",
        "kitty-specs/077-mission-terminology-cleanup/contracts/selector_resolver.md",
        "kitty-specs/078-planning-artifact-and-query-consistency/contracts/planning-artifact-lifecycle.md",
        "kitty-specs/078-planning-artifact-and-query-consistency/contracts/workspace-resolution.md",
        "kitty-specs/079-post-555-release-hardening/contracts/cli-contracts.md",
        "kitty-specs/079-post-555-release-hardening/contracts/file-format-contracts.md",
        "kitty-specs/079-post-555-release-hardening/contracts/test-contracts.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/api-logout-endpoint.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/api-ws-token-endpoint.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/error-responses.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/oauth-authorize-endpoint.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/oauth-device-endpoint.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/oauth-token-endpoint.md",
        "kitty-specs/080-browser-mediated-oauth-cli-auth/contracts/saas-amendment-refresh-ttl.md",
        "kitty-specs/080-wpstate-lane-consumer-strangler-fig-phase-2/contracts/consumer-interfaces.md",
        "kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/background_daemon_policy.md",
        "kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/hosted_readiness.md",
        "kitty-specs/082-stealth-gated-saas-sync-hardening/contracts/saas_rollout.md",
        "kitty-specs/083-agent-skills-codex-vibe/contracts/skill-renderer.contract.md",
        "kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/ble001-guardrail.md",
        "kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/diagnostic-classification.md",
        "kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/refresh-lock-hermeticity.md",
        "kitty-specs/auth-local-trust-and-multi-process-hardening-01KQW587/contracts/session-hot-path.md",
        "kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/contracts/refresh-replay.md",
        "kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/contracts/revoke-call.md",
        "kitty-specs/auth-tranche-2-5-cli-contract-consumption-01KQEJZK/contracts/session-status-call.md",
        "kitty-specs/backward-transition-cli-emit-01KRV8GC/contracts/auto-promote-backward-emit.md",
        "kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/contracts/ci-job-mypy-availability.md",
        "kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/contracts/golden-path-envelope-assertions.md",
        "kitty-specs/charter-contract-cleanup-tranche-1-01KQATS4/contracts/README.md",
        "kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/dossier-snapshot-ownership.md",
        "kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/next-prompt-file-contract.md",
        "kitty-specs/charter-e2e-827-followups-01KQAJA0/contracts/specify-plan-commit-boundary.md",
        "kitty-specs/charter-golden-path-e2e-tranche-1-01KQ806X/contracts/cli-flow-contract.md",
        "kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/activation-registry.md",
        "kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/charter-facade-modules.md",
        "kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/mission-type-profile.md",
        "kitty-specs/charter-mediated-doctrine-selection-01KRTZCA/contracts/selection-schema.md",
        "kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/contracts/charter-ownership-invariant-contract.md",
        "kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/contracts/charter-public-import-surface.md",
        "kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/contracts/neutrality-lint-contract.md",
        "kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/contracts/README.md",
        "kitty-specs/charter-ownership-consolidation-and-neutrality-hardening-01KPD880/contracts/shim-deprecation-contract.md",
        "kitty-specs/charter-p7-release-closure-01KQF9B9/contracts/validate-json-output.md",
        "kitty-specs/cli-interview-decision-moments-01KPWT8P/contracts/cli-contracts.md",
        "kitty-specs/cli-interview-decision-moments-01KPWT8P/contracts/README.md",
        "kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/contracts/auth-doctor.md",
        "kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/contracts/daemon-singleton.md",
        "kitty-specs/cli-session-survival-daemon-singleton-01KQ9M3M/contracts/refresh-lock.md",
        "kitty-specs/cli-widen-mode-and-write-back-01KPXFGJ/contracts/cli-contracts.md",
        "kitty-specs/cli-widen-mode-and-write-back-01KPXFGJ/contracts/README.md",
        "kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/contracts/drg-shape.md",
        "kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/contracts/step-contracts.md",
        "kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/contracts/removed-cli-surface.md",
        "kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/contracts/resolve-transitive-refs.contract.md",
        "kitty-specs/implement-review-retrospect-reliability-01KQQSCW/contracts/next-routing.md",
        "kitty-specs/implement-review-retrospect-reliability-01KQQSCW/contracts/retrospective-cli.md",
        "kitty-specs/implement-review-retrospect-reliability-01KQQSCW/contracts/review-cycle-domain.md",
        "kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/org-doctrine-source-api-contract.md",
        "kitty-specs/layered-doctrine-org-layer-01KRNPEE/contracts/pack-layout.md",
        "kitty-specs/local-custom-mission-loader-01KQ2VNJ/contracts/mission-run-cli.md",
        "kitty-specs/local-custom-mission-loader-01KQ2VNJ/contracts/validation-errors.md",
        "kitty-specs/merge-review-status-hardening-sprint-01KQFF35/contracts/review-command-interface.md",
        "kitty-specs/migration-shim-ownership-rules-01KPDYDW/contracts/doctor-shim-registry-cli.md",
        "kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/cli_surfaces.md",
        "kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/gate_api.md",
        "kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/retrospective_events_v1.md",
        "kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/retrospective_yaml_v1.md",
        "kitty-specs/mission-retrospective-learning-loop-01KQ6YEG/contracts/synthesizer_hook.md",
        "kitty-specs/p1-dependency-cycle-cleanup-01KQFXVC/contracts/fan-out-adapter.md",
        "kitty-specs/phase-3-charter-synthesizer-pipeline-01KPE222/contracts/topic-selector.md",
        "kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/contracts/host-surface-inventory.md",
        "kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/contracts/profile-invocation-complete.md",
        "kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/contracts/projection-policy.md",
        "kitty-specs/phase6-composition-stabilization-01KQ2JAS/contracts/invocation_executor_invoke.md",
        "kitty-specs/phase6-composition-stabilization-01KQ2JAS/contracts/runtime_bridge_dispatch.md",
        "kitty-specs/phase6-composition-stabilization-01KQ2JAS/contracts/step_contract_executor_lifecycle.md",
        "kitty-specs/private-teamspace-ingress-safeguards-01KQH03Y/contracts/api.md",
        "kitty-specs/quality-devex-hardening-3-2-01KRJGKH/contracts/canonicalization-rule-pipeline.md",
        "kitty-specs/quality-devex-hardening-3-2-01KRJGKH/contracts/stale-lane-auto-rebase-classifier-policy.md",
        "kitty-specs/quality-devex-hardening-3-2-01KRJGKH/contracts/upgrade-probe-and-notifier.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/checklist_surface_removed.contract.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/decision_command_help.contract.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/feature_alias_hidden.contract.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/init_non_git_message.contract.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/mission_create_clean_output.contract.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/status_event_reader_tolerates_decision_events.contract.md",
        "kitty-specs/release-3-2-0a5-tranche-1-01KQ7YXH/contracts/upgrade_post_state.contract.md",
        "kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/contracts/invocation-lifecycle.md",
        "kitty-specs/release-3-2-0a6-tranche-2-01KQ9MKP/contracts/json-envelope.md",
        "kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/contracts/charter-io-chokepoint.md",
        "kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/contracts/encoding-provenance-schema.md",
        "kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/contracts/issue-matrix-schema.md",
        "kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/contracts/merge-state-idempotency.md",
        "kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/contracts/review-mode-resolution.md",
        "kitty-specs/review-merge-gate-hardening-3-2-x-01KRC57C/contracts/status-read-worktree-resolution.md",
        "kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/events_consumer_surface.md",
        "kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/internal_runtime_surface.md",
        "kitty-specs/shared-package-boundary-cutover-01KQ22DS/contracts/tracker_consumer_surface.md",
        "kitty-specs/software-dev-composition-rewrite-01KQ26CY/contracts/runtime-bridge-composition-api.md",
        "kitty-specs/software-dev-composition-rewrite-01KQ26CY/contracts/tasks-step-contract-schema.md",
        "kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/activation.md",
        "kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/charter-context.md",
        "kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/prompt-fragment.md",
        "kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/review-gate.md",
        "kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/events-envelope.md",
        "kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/intake-source-provenance.md",
        "kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/runtime-decision-output.md",
        "kitty-specs/stability-and-hygiene-hardening-2026-04-01KQ4ARB/contracts/tracker-public-imports.md",
        "kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/command-surface-generation.md",
        "kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/review-verdict-consistency.md",
        "kitty-specs/stable-320-p0-cli-stabilization-01KQSNGY/contracts/status-test-boundedness.md",
        "kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/dependency-drift-guard.md",
        "kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/smoke-workflow-contract.md",
        "kitty-specs/stable-320-p1-release-confidence-01KQTPZC/contracts/task-progress-status.md",
        "kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/bundle-validate-cli.contract.md",
        "kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/canonical-root-resolver.contract.md",
        "kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/contracts/chokepoint.contract.md",
        "kitty-specs/workflow-parity-988-989-991-01KRKTT5/contracts/lightweight-review-baseline.md",
        "kitty-specs/workflow-parity-988-989-991-01KRKTT5/contracts/merge-dry-run-review-artifact.md",
        "kitty-specs/workflow-parity-988-989-991-01KRKTT5/contracts/next-json-claimability.md",
        "kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/charter-context-resolver.md",
        "kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/charter-sync-cross-link.md",
        "kitty-specs/wp-prompt-governance-payload-01KRR8HS/contracts/runtime-template-governance-payload-contract.md",
        # CI-wiring YAML snippet (not a Pydantic model payload); added per T031 (#1301)
        "kitty-specs/spec-kitty-3-2-docs-01KS4KSZ/contracts/check_docs_freshness.md",
    }
)

# ---------------------------------------------------------------------------
# Negative-fixture inline examples (T016 / AC-10 sanity check)
# ---------------------------------------------------------------------------
# This list proves the gate catches real divergence. Each entry is a
# (contract_label, model_path, expect, payload, expect_message) tuple.
# These are exercised as extra parametrize cases alongside the discovered ones.
# ---------------------------------------------------------------------------
_INLINE_NEGATIVE_FIXTURES: list[tuple[str, str, str, str, str | None]] = [
    # Sanity: a pydantic model with a required field, given an empty dict.
    # Uses doctrine.drg.models.DRGNode (always available; part of core doctrine).
    (
        "<inline:sanity-negative-fixture>",
        "doctrine.drg.models.DRGNode",
        "invalid",
        "{}",  # Missing required fields -> ValidationError
        None,
    ),
]

# ---------------------------------------------------------------------------
# Frontmatter regexes
# ---------------------------------------------------------------------------
# Matches the pydantic_model and expect lines at the START of a yaml codeblock.
# We search within the block content (not the full file) so anchors work per-block.
_FRONTMATTER_RE: re.Pattern[str] = re.compile(
    r"^# pydantic_model: (?P<model>[\w\.]+)\s*\n"
    r"# expect: (?P<expect>valid|invalid)",
    re.MULTILINE,
)
_EXPECT_MESSAGE_RE: re.Pattern[str] = re.compile(
    r"^# expect_message: (?P<msg>.+)$", re.MULTILINE
)

# Fenced yaml codeblock (triple backtick, NOT preceded on the same line by a
# 4th backtick which would make it a nested illustration inside a markdown fence).
_YAML_BLOCK_RE: re.Pattern[str] = re.compile(
    r"^```yaml\n(?P<body>.*?)^```",
    re.MULTILINE | re.DOTALL,
)

# 4-backtick outer fence used in contracts to illustrate the convention.
# Blocks whose opening ``` is nested inside a ````...```` fence are
# ILLUSTRATION ONLY and must NOT be exercised by the round-trip gate.
_QUAD_FENCE_RE: re.Pattern[str] = re.compile(
    r"^````.*?^````",
    re.MULTILINE | re.DOTALL,
)


# ---------------------------------------------------------------------------
# Discovery helpers
# ---------------------------------------------------------------------------

def _strip_frontmatter_comments(block_body: str) -> str:
    """Remove leading ``# pydantic_model:``, ``# expect:``, ``# expect_message:`` lines."""
    lines = block_body.splitlines(keepends=True)
    stripped: list[str] = []
    for line in lines:
        stripped_line = line.lstrip()
        if (
            stripped_line.startswith("# pydantic_model:")
            or stripped_line.startswith("# expect:")
            or stripped_line.startswith("# expect_message:")
        ):
            continue
        stripped.append(line)
    return "".join(stripped)


def _relative_path(path: Path) -> str:
    """Return path relative to repo root as a forward-slash string."""
    try:
        return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path)


def _is_legacy(contract_path: Path) -> bool:
    """True iff *contract_path* is in the legacy allowlist."""
    return _relative_path(contract_path) in _LEGACY_CONTRACT_ALLOWLIST


def _extract_yaml_blocks(text: str) -> list[str]:
    """Extract ```yaml codeblocks from *text*, skipping those inside 4-backtick fences.

    4-backtick outer fences (````markdown ... ````) are used in contracts to
    ILLUSTRATE the frontmatter convention itself; the inner ```yaml blocks are
    documentation illustrations, not round-trip tested examples.
    """
    # Blank out all 4-backtick fence regions so inner ```yaml blocks are hidden.
    scrubbed = _QUAD_FENCE_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _YAML_BLOCK_RE.findall(scrubbed)


def _parse_expect_message(raw: str) -> str:
    """Parse the expect_message value, stripping optional surrounding quotes.

    The frontmatter line may use YAML-style quoting::

        # expect_message: "unknown kind"   -> returns: unknown kind
        # expect_message: unknown kind     -> returns: unknown kind
    """
    stripped = raw.strip()
    if len(stripped) >= 2 and stripped[0] in ('"', "'") and stripped[-1] == stripped[0]:
        return stripped[1:-1]
    return stripped


def _discover_examples() -> list[tuple[str, str, str, str, str | None]]:
    """Walk every ``kitty-specs/*/contracts/*.md`` and yield tagged examples.

    Yields tuples of:
        (contract_label, model_dotted_path, expect, yaml_payload, expect_message_or_None)

    Codeblocks without ``# pydantic_model:`` are silently skipped.
    Legacy contracts with YAML codeblocks but no frontmatter emit a warning.
    Non-legacy contracts with YAML codeblocks but no frontmatter -> included
    with model_path="<MISSING_FRONTMATTER>" so the parametrised test fails.
    """
    examples: list[tuple[str, str, str, str, str | None]] = []

    if not _KITTY_SPECS_ROOT.exists():
        return examples

    for contract_md in sorted(_KITTY_SPECS_ROOT.glob("*/contracts/*.md")):
        text = contract_md.read_text(encoding="utf-8")
        rel = _relative_path(contract_md)
        is_legacy = _is_legacy(contract_md)

        yaml_blocks = _extract_yaml_blocks(text)
        if not yaml_blocks:
            # No YAML codeblocks at all — just a prose contract. Skip quietly.
            continue

        found_any_frontmatter = False
        for block_idx, block_body in enumerate(yaml_blocks, start=1):
            fm = _FRONTMATTER_RE.search(block_body)
            if fm is None:
                continue
            found_any_frontmatter = True
            model_path = fm.group("model")
            expect = fm.group("expect")
            msg_match = _EXPECT_MESSAGE_RE.search(block_body)
            expect_message: str | None = (
                _parse_expect_message(msg_match.group("msg")) if msg_match else None
            )

            payload = _strip_frontmatter_comments(block_body)

            label = f"{rel}::block-{block_idx}"
            examples.append((label, model_path, expect, payload, expect_message))

        # Warn if a legacy contract has YAML blocks but none had frontmatter.
        if not found_any_frontmatter and is_legacy:
            warnings.warn(
                f"Legacy contract '{rel}' has {len(yaml_blocks)} YAML codeblock(s) "
                f"but none carry ``# pydantic_model:`` frontmatter. "
                f"Consider backfilling the convention to shrink the legacy allowlist "
                f"(tests/architectural/_baselines.yaml::test_example_round_trip"
                f".legacy_contract_allowlist).",
                UserWarning,
                stacklevel=2,
            )
        elif not found_any_frontmatter and not is_legacy:
            # Non-legacy contract with YAML blocks but no frontmatter -> gate failure.
            label = f"{rel}::block-MISSING_FRONTMATTER"
            examples.append(
                (
                    label,
                    "<MISSING_FRONTMATTER>",
                    "valid",
                    "{}",
                    None,
                )
            )

    return examples


# ---------------------------------------------------------------------------
# Collect parametrize cases at module-import time (pytest requires this)
# ---------------------------------------------------------------------------
_DISCOVERED: list[tuple[str, str, str, str, str | None]] = _discover_examples()
_ALL_CASES: list[tuple[str, str, str, str, str | None]] = _DISCOVERED + _INLINE_NEGATIVE_FIXTURES

# ---------------------------------------------------------------------------
# The parametrised gate (AC-10)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "contract_label,model_path,expect,payload,expect_message",
    _ALL_CASES,
    ids=[c[0] for c in _ALL_CASES],
)
def test_contract_example_round_trip(
    contract_label: str,
    model_path: str,
    expect: str,
    payload: str,
    expect_message: str | None,
) -> None:
    """FR-140 round-trip gate: every tagged codeblock validates against its model.

    Outcomes
    --------
    * ``expect: valid``   → ``model_validate`` MUST succeed.
    * ``expect: invalid`` → ``model_validate`` MUST raise ``ValidationError``.

    Failure messages match the shape documented in
    ``kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/
    contract-round-trip-frontmatter.md``.
    """
    # --- Guard: missing frontmatter on a non-legacy contract ---
    if model_path == "<MISSING_FRONTMATTER>":
        pytest.fail(
            f"Contract '{contract_label}' has YAML codeblock(s) but none carry "
            f"``# pydantic_model:`` frontmatter. Add frontmatter per the Slice F "
            f"convention OR move the file to ``_LEGACY_CONTRACT_ALLOWLIST`` in "
            f"``tests/contract/test_example_round_trip.py`` and update "
            f"``tests/architectural/_baselines.yaml``."
        )

    # --- Import the model ---
    module_dotted, _, class_name = model_path.rpartition(".")
    if not module_dotted:
        pytest.fail(
            f"'{contract_label}': ``pydantic_model: {model_path}`` is not a valid "
            f"dotted import path (expected ``module.ClassName``)."
        )

    try:
        module = importlib.import_module(module_dotted)
    except ImportError as exc:
        # Slice F ATDD pattern: contract examples may reference Pydantic
        # models that haven't been landed by their owning WP yet. Skip
        # (don't fail) so the round-trip gate stays honest while future
        # WPs progressively turn each skip into a pass.
        # The owning WP MUST remove the skipif behaviour by landing the
        # named model (per their acceptance criteria, see tasks/WP06,
        # WP09, WP10 task files).
        pytest.skip(
            f"'{contract_label}': module ``{module_dotted}`` not yet "
            f"importable ({exc}). The owning WP turns this case GREEN by "
            f"landing the Pydantic model under that import path. See the "
            f"owning WP's task file for the binding acceptance criterion."
        )

    if not hasattr(module, class_name):
        # Same pattern as ImportError above: the module exists but the
        # specific class doesn't yet. Skip pending the owning WP.
        pytest.skip(
            f"'{contract_label}': ``{module_dotted}`` has no attribute "
            f"``{class_name}`` yet. The owning WP defines this class "
            f"per its acceptance criterion."
        )

    model_cls = getattr(module, class_name)

    # --- Parse the YAML payload ---
    try:
        parsed: Any = yaml.safe_load(payload)
    except yaml.YAMLError as exc:
        pytest.fail(
            f"'{contract_label}' YAML payload failed to parse: {exc}"
        )

    # --- Assert expected outcome ---
    if expect == "valid":
        try:
            model_cls.model_validate(parsed)
        except pydantic.ValidationError as exc:
            pytest.fail(
                f"'{contract_label}' declared ``pydantic_model: {model_path}, "
                f"expect: valid`` but ``model_validate`` raised:\n{exc}"
            )
    else:  # expect == "invalid"
        with pytest.raises(pydantic.ValidationError) as exc_info:
            model_cls.model_validate(parsed)
        if expect_message is not None:
            error_text = str(exc_info.value)
            assert expect_message in error_text, (
                f"'{contract_label}' declared ``expect_message: {expect_message!r}`` "
                f"but the ValidationError text does not contain it.\n"
                f"Actual error:\n{error_text}"
            )
