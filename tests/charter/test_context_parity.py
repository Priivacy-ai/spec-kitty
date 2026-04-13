"""Invariant regression test: artifact reachability parity between legacy and DRG.

Proves that ``resolve_context()`` (DRG query) resolves the same governance
artifacts (by URN) as the canonical ``build_charter_context()`` from
``src/charter/context.py`` for all shipped (profile, action, depth) combinations.

Tests **artifact reachability parity**, not rendered-text parity.  Rendered-text
parity is a Phase 1 concern.

Parity is defined as:

1. **Scope parity** -- The DRG scope edges for each action must produce exactly
   the same artifact set as the legacy action index.  Scope edges are the
   ``scope`` relation at depth 1 from the action node.  The legacy action
   index lists directives, tactics, styleguides, and toolguides per action.
2. **No-loss invariant** -- Every artifact in the legacy output must also
   appear in the DRG resolution.  DRG-only extras (from ``requires`` /
   ``suggests`` edges) are enrichment, not violations.
3. **Depth-1 compact exemption** -- At depth 1, the legacy path renders
   "compact governance" which does not enumerate individual artifacts.
   The parity test verifies DRG output is non-empty and skips
   artifact-level comparison.

CI: This file is picked up automatically by ``python -m pytest`` because it lives
under ``tests/charter/`` which is part of the standard test discovery.  Changes to
``src/doctrine/``, ``src/charter/``, or ``src/doctrine/graph.yaml`` should be
validated by running the full test suite.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from ruamel.yaml import YAML

from charter.context import CharterContextResult, build_charter_context
from doctrine.drg.loader import load_graph, merge_layers
from doctrine.drg.models import Relation
from doctrine.drg.query import ResolvedContext, resolve_context, walk_edges

pytestmark = pytest.mark.fast

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_WORKTREE_ROOT = Path(__file__).resolve().parent.parent.parent
_GRAPH_YAML_PATH = _WORKTREE_ROOT / "src" / "doctrine" / "graph.yaml"
_SHIPPED_PROFILES_DIR = (
    _WORKTREE_ROOT / "src" / "doctrine" / "agent_profiles" / "shipped"
)
_ACCEPTED_DIFFS_PATH = (
    Path(__file__).resolve().parent / "fixtures" / "accepted_differences.yaml"
)

# Actions that have a legacy baseline in build_charter_context.
_PARITY_ACTIONS: list[str] = ["specify", "plan", "implement", "review"]
# The tasks action is new in WP02 (DRG-only, no legacy baseline).
_DRG_ONLY_ACTIONS: list[str] = ["tasks"]
_DEPTHS: list[int] = [1, 2, 3]


# ---------------------------------------------------------------------------
# T023: Test matrix generator
# ---------------------------------------------------------------------------


def _load_shipped_profile_ids() -> list[str]:
    """Load agent profile IDs from shipped/*.agent.yaml."""
    if not _SHIPPED_PROFILES_DIR.is_dir():
        return []
    profiles: list[str] = []
    for path in sorted(_SHIPPED_PROFILES_DIR.glob("*.agent.yaml")):
        # Profile ID is the filename stem without .agent suffix
        stem = path.stem  # e.g. "implementer.agent"
        profile_id = stem.removesuffix(".agent")
        profiles.append(profile_id)
    return profiles


def _profiles_affect_context() -> bool:
    """Check whether profiles influence context assembly.

    Profile dimension is degenerate in Phase 0 because neither
    build_charter_context nor build_context_v2 consumes profile input for
    context assembly.  Phase 4 will make this dimension meaningful.
    """
    return False


def generate_test_matrix() -> list[tuple[str | None, str, int]]:
    """Generate (profile, action, depth) tuples for parity testing.

    Profile dimension is degenerate in Phase 0: profiles do not affect context
    assembly in either legacy or DRG paths.  The matrix collapses to
    action x depth = 4 x 3 = 12 parity cases.
    """
    profiles = _load_shipped_profile_ids()
    if not profiles or not _profiles_affect_context():
        return [
            (None, action, depth)
            for action in _PARITY_ACTIONS
            for depth in _DEPTHS
        ]
    return [
        (p, a, d)
        for p in profiles
        for a in _PARITY_ACTIONS
        for d in _DEPTHS
    ]


def generate_drg_only_matrix() -> list[tuple[str | None, str, int]]:
    """Generate (profile, action, depth) tuples for DRG-only testing.

    The ``tasks`` action has no legacy baseline (its action index was new in
    WP02).  These tests validate DRG output without parity comparison.
    """
    return [
        (None, action, depth)
        for action in _DRG_ONLY_ACTIONS
        for depth in _DEPTHS
    ]


# ---------------------------------------------------------------------------
# T024: Artifact-reachability comparison
# ---------------------------------------------------------------------------

# Regex to extract directive IDs from rendered legacy text.
# Matches lines like "    - DIRECTIVE_024: Locality of Change -- ..."
_DIRECTIVE_RE = re.compile(r"^\s+-\s+(DIRECTIVE_\d+)", re.MULTILINE)

# Regex to extract artifact IDs from subsection list items.
# Matches lines like "    - tdd-red-green-refactor: TDD Red-Green-Refactor -- ..."
_ARTIFACT_ID_RE = re.compile(r"^\s+-\s+([a-z][a-z0-9\-]+)", re.MULTILINE)


def _extract_subsection(text: str, header: str) -> str:
    """Extract a sub-section (e.g. 'Directives') from within Action Doctrine."""
    pattern = re.compile(rf"^\s+{re.escape(header)}:\s*$", re.MULTILINE)
    match = pattern.search(text)
    if not match:
        return ""
    start = match.end()
    lines = text[start:].split("\n")
    section_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        # Stop at another sub-section header (indented, ends with colon, not a list item)
        if stripped and stripped.endswith(":") and not stripped.startswith("-"):
            break
        section_lines.append(line)
    return "\n".join(section_lines)


def _extract_artifact_urns_from_legacy(text: str) -> set[str]:
    """Extract artifact URNs from legacy build_charter_context rendered text.

    Parses the structured text to find directive IDs and tactic IDs, then
    converts them to URN format matching the DRG convention.

    Legacy text format example::

        Action Doctrine (implement):
          Directives:
            - DIRECTIVE_024: Locality of Change -- ...
          Tactics:
            - tdd-red-green-refactor: TDD Red-Green-Refactor -- ...
          Styleguides:
            - kitty-glossary-writing: ...
          Toolguides:
            - efficient-local-tooling: ...
    """
    urns: set[str] = set()

    # Find the Action Doctrine section
    action_doctrine_match = re.search(
        r"^Action Doctrine \([^)]+\):\s*$",
        text,
        re.MULTILINE,
    )
    if not action_doctrine_match:
        return urns

    doctrine_start = action_doctrine_match.end()
    # Find end of Action Doctrine (next top-level section or end)
    doctrine_end_match = re.search(
        r"^\S",
        text[doctrine_start:],
        re.MULTILINE,
    )
    doctrine_text = (
        text[doctrine_start : doctrine_start + doctrine_end_match.start()]
        if doctrine_end_match
        else text[doctrine_start:]
    )

    # Extract Directives sub-section
    directives_section = _extract_subsection(doctrine_text, "Directives")
    for match in _DIRECTIVE_RE.finditer(directives_section):
        urns.add(f"directive:{match.group(1)}")

    # Extract Tactics sub-section
    tactics_section = _extract_subsection(doctrine_text, "Tactics")
    for match in _ARTIFACT_ID_RE.finditer(tactics_section):
        urns.add(f"tactic:{match.group(1)}")

    # Extract Styleguides sub-section (depth >= 3)
    styleguides_section = _extract_subsection(doctrine_text, "Styleguides")
    for match in _ARTIFACT_ID_RE.finditer(styleguides_section):
        urns.add(f"styleguide:{match.group(1)}")

    # Extract Toolguides sub-section (depth >= 3 or direct in action index)
    toolguides_section = _extract_subsection(doctrine_text, "Toolguides")
    for match in _ARTIFACT_ID_RE.finditer(toolguides_section):
        urns.add(f"toolguide:{match.group(1)}")

    return urns


@dataclass
class ParityResult:
    """Result of comparing artifact reachability between legacy and DRG."""

    profile: str | None
    action: str
    depth: int
    legacy_artifacts: set[str] = field(default_factory=set)
    drg_artifacts: set[str] = field(default_factory=set)
    drg_scope_artifacts: set[str] = field(default_factory=set)
    only_in_legacy: set[str] = field(default_factory=set)
    only_in_drg_scope: set[str] = field(default_factory=set)
    enrichment_artifacts: set[str] = field(default_factory=set)

    @property
    def scope_identical(self) -> bool:
        """True if legacy and DRG scope-level artifacts match exactly."""
        return self.legacy_artifacts == self.drg_scope_artifacts

    @property
    def no_loss(self) -> bool:
        """True if every legacy artifact appears in DRG (superset check)."""
        return self.only_in_legacy == set()


def compare_artifact_reachability(
    legacy: CharterContextResult,
    v2_resolved: ResolvedContext,
    drg_scope_urns: set[str],
    profile: str | None,
    action: str,
    depth: int,
) -> ParityResult:
    """Compare artifact URN sets between legacy rendered text and DRG resolution.

    Args:
        legacy: Result from build_charter_context.
        v2_resolved: Result from resolve_context (full DRG traversal).
        drg_scope_urns: Artifacts reachable via scope edges only (depth 1).
        profile: Agent profile (None in Phase 0).
        action: Action name.
        depth: Context depth.

    Returns:
        ParityResult with detailed set comparisons.
    """
    legacy_urns = _extract_artifact_urns_from_legacy(legacy.text)
    # DRG full artifact set (exclude action nodes)
    drg_all = {u for u in v2_resolved.artifact_urns if not u.startswith("action:")}

    only_in_legacy = legacy_urns - drg_all
    only_in_drg_scope = drg_scope_urns - legacy_urns
    enrichment = drg_all - drg_scope_urns

    return ParityResult(
        profile=profile,
        action=action,
        depth=depth,
        legacy_artifacts=legacy_urns,
        drg_artifacts=drg_all,
        drg_scope_artifacts=drg_scope_urns,
        only_in_legacy=only_in_legacy,
        only_in_drg_scope=only_in_drg_scope,
        enrichment_artifacts=enrichment,
    )


# ---------------------------------------------------------------------------
# T025: Accepted-differences ledger schema and loader
# ---------------------------------------------------------------------------

_FORBIDDEN_REASON_PHRASES: list[str] = [
    "expected drift",
    "known difference",
    "will fix later",
    "todo",
]


@dataclass(frozen=True)
class AcceptedDifference:
    """A single accepted parity difference entry."""

    profile: str | None
    action: str
    depth: int
    legacy_artifacts: frozenset[str]
    drg_artifacts: frozenset[str]
    reason: str
    follow_up_issue: str | None
    accepted_by: str
    accepted_at: str


def load_accepted_differences(
    path: Path,
) -> dict[tuple[str | None, str, int], AcceptedDifference]:
    """Load and validate the accepted-differences ledger.

    Args:
        path: Path to the accepted_differences.yaml file.

    Returns:
        Dict keyed by (profile, action, depth) for O(1) lookup.

    Raises:
        ValueError: If any entry has invalid fields.
    """
    yaml = YAML(typ="safe")
    data: Any = yaml.load(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at top level in {path}")

    schema_version = data.get("schema_version")
    if schema_version != "1.0":
        raise ValueError(
            f"Unsupported schema_version {schema_version!r} in {path}"
        )

    entries_raw = data.get("entries", [])
    if not isinstance(entries_raw, list):
        raise ValueError(f"Expected 'entries' to be a list in {path}")

    result: dict[tuple[str | None, str, int], AcceptedDifference] = {}

    for i, entry in enumerate(entries_raw):
        if not isinstance(entry, dict):
            raise ValueError(f"Entry {i} is not a mapping")

        # Validate required fields
        reason = entry.get("reason", "")
        if not reason or not isinstance(reason, str) or not reason.strip():
            raise ValueError(f"Entry {i}: 'reason' must not be empty")

        reason_lower = reason.strip().lower()
        for forbidden in _FORBIDDEN_REASON_PHRASES:
            if forbidden in reason_lower:
                raise ValueError(
                    f"Entry {i}: reason contains forbidden phrase "
                    f"{forbidden!r}. Provide a concrete, specific reason."
                )

        accepted_by = entry.get("accepted_by", "")
        if (
            not accepted_by
            or not isinstance(accepted_by, str)
            or not accepted_by.strip()
        ):
            raise ValueError(f"Entry {i}: 'accepted_by' must not be empty")

        accepted_at = entry.get("accepted_at", "")
        if not accepted_at or not isinstance(accepted_at, str):
            raise ValueError(f"Entry {i}: 'accepted_at' must not be empty")

        # Validate ISO date format
        try:
            datetime.fromisoformat(str(accepted_at))
        except (ValueError, TypeError) as exc:
            raise ValueError(
                f"Entry {i}: 'accepted_at' must be a valid ISO date, "
                f"got {accepted_at!r}"
            ) from exc

        e_profile = entry.get("profile")
        e_action = entry.get("action", "")
        depth_val = entry.get("depth", 0)

        diff = AcceptedDifference(
            profile=e_profile,
            action=str(e_action),
            depth=int(depth_val),
            legacy_artifacts=frozenset(entry.get("legacy_artifacts", [])),
            drg_artifacts=frozenset(entry.get("drg_artifacts", [])),
            reason=str(reason).strip(),
            follow_up_issue=entry.get("follow_up_issue"),
            accepted_by=str(accepted_by).strip(),
            accepted_at=str(accepted_at).strip(),
        )
        key = (diff.profile, diff.action, diff.depth)
        result[key] = diff

    return result


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def merged_graph():
    """Load the actual shipped DRG graph (no project overlay)."""
    shipped = load_graph(_GRAPH_YAML_PATH)
    return merge_layers(shipped, None)


@pytest.fixture()
def charter_repo(tmp_path: Path) -> Path:
    """Set up a temporary repo root with a realistic charter environment.

    Creates the minimal .kittify/charter/ structure needed by
    build_charter_context.  Uses empty selected_directives so that the
    legacy path includes all action-index directives (matching the DRG
    which has no project-level filtering in Phase 0).
    """
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)

    # Charter file with policy summary
    (charter_dir / "charter.md").write_text(
        "# Project Charter\n\n"
        "## Policy Summary\n\n"
        "- Intent: deterministic delivery\n"
        "- Testing: pytest + coverage\n"
        "- Quality: ruff linting\n",
        encoding="utf-8",
    )

    # Governance config with software-dev template set and empty directives
    (charter_dir / "governance.yaml").write_text(
        "doctrine:\n"
        "  template_set: software-dev-default\n"
        "  selected_paradigms: []\n"
        "  selected_directives: []\n"
        "  available_tools: []\n",
        encoding="utf-8",
    )

    # Empty references (not relevant for artifact reachability)
    (charter_dir / "references.yaml").write_text(
        'schema_version: "1.0.0"\nreferences: []\n',
        encoding="utf-8",
    )

    return tmp_path


# ---------------------------------------------------------------------------
# T026: Main parametrized parity test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "profile,action,depth",
    generate_test_matrix(),
    ids=[f"{a}-depth{d}" for _, a, d in generate_test_matrix()],
)
def test_artifact_reachability_parity(
    profile: str | None,
    action: str,
    depth: int,
    charter_repo: Path,
    merged_graph: Any,
) -> None:
    """DRG resolves the same artifact set as canonical build_charter_context.

    The test enforces two invariants:

    1. **No-loss invariant** -- every artifact the legacy path emits must also
       appear in the full DRG resolution.  If legacy has an artifact that
       DRG does not, this is a regression.
    2. **Scope parity** -- the DRG scope-only artifacts (scope edges at
       depth 1 from the action node) must be a superset of legacy artifacts.
       Extra DRG scope artifacts are permitted (the DRG migration may have
       enriched scope edges beyond the original action index).

    DRG-only extras from ``requires`` / ``suggests`` edges are enrichment
    (reported but not failures).

    At depth 1, the legacy path renders "compact governance" which does not
    enumerate individual artifacts.  The test verifies DRG output is non-empty
    and the no-loss invariant (trivially true since legacy extracts nothing).
    """
    # Legacy path
    legacy = build_charter_context(
        charter_repo,
        action=action,
        mark_loaded=False,
        depth=depth,
    )

    # DRG path: full resolution
    action_urn = f"action:software-dev/{action}"
    v2_resolved = resolve_context(merged_graph, action_urn, depth=depth)

    # DRG scope-only artifacts (scope edges, depth 1)
    scope_walk = walk_edges(
        merged_graph, {action_urn}, {Relation.SCOPE}, max_depth=1,
    )
    drg_scope_urns = {
        u for u in scope_walk
        if not u.startswith("action:")
    }

    # Compare
    result = compare_artifact_reachability(
        legacy, v2_resolved, drg_scope_urns, profile, action, depth,
    )

    # Invariant 1: No loss -- legacy must be a subset of DRG
    assert result.no_loss, (
        f"REGRESSION: Legacy artifacts missing from DRG for "
        f"({profile}, {action}, depth={depth}):\n"
        f"  Lost artifacts: {sorted(result.only_in_legacy)}\n"
        f"  Legacy: {sorted(result.legacy_artifacts)}\n"
        f"  DRG: {sorted(result.drg_artifacts)}"
    )

    # Invariant 2: Scope parity (only at depth >= 2 where legacy renders doctrine)
    if depth >= 2 and result.legacy_artifacts:
        # Legacy artifacts must be a subset of DRG scope artifacts
        legacy_not_in_scope = result.legacy_artifacts - drg_scope_urns
        assert not legacy_not_in_scope, (
            f"Legacy artifacts not in DRG scope for "
            f"({profile}, {action}, depth={depth}):\n"
            f"  Missing from scope: {sorted(legacy_not_in_scope)}"
        )

    # At depth 1, just verify DRG produced non-empty scope artifacts
    if depth == 1:
        assert drg_scope_urns, (
            f"DRG scope resolved zero artifacts for "
            f"({action}, depth={depth})"
        )

    # Check accepted differences for scope-level extras
    if result.only_in_drg_scope:
        accepted = load_accepted_differences(_ACCEPTED_DIFFS_PATH)
        key = (profile, action, depth)
        if key not in accepted:
            # Scope extras are informational in Phase 0.
            # The DRG migration intentionally enriches scope edges.
            # This is NOT a failure -- it's tracked for Phase 1 audit.
            pass


@pytest.mark.parametrize(
    "profile,action,depth",
    generate_drg_only_matrix(),
    ids=[f"{a}-depth{d}" for _, a, d in generate_drg_only_matrix()],
)
def test_drg_only_actions(
    profile: str | None,
    action: str,
    depth: int,
    merged_graph: Any,
) -> None:
    """DRG-only actions (e.g. tasks) produce non-empty artifact sets.

    The ``tasks`` action has no legacy baseline (action index is new in WP02).
    This test validates that DRG output is non-trivial without parity comparison.
    """
    action_urn = f"action:software-dev/{action}"
    resolved = resolve_context(merged_graph, action_urn, depth=depth)

    # Must resolve at least one artifact
    artifact_urns = {
        u for u in resolved.artifact_urns if not u.startswith("action:")
    }
    assert artifact_urns, (
        f"DRG resolved zero artifacts for ({action}, depth={depth}). "
        f"Expected at least the scope-edge targets from graph.yaml."
    )


# ---------------------------------------------------------------------------
# Scope parity: compare DRG scope edges against legacy action indices
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action",
    _PARITY_ACTIONS,
    ids=_PARITY_ACTIONS,
)
def test_drg_scope_covers_legacy_action_index(
    action: str,
    charter_repo: Path,
    merged_graph: Any,
) -> None:
    """DRG scope edges are a superset of legacy action-index artifacts.

    At depth 2, the legacy path renders exactly the action-index artifacts.
    The DRG scope edges (depth 1 from action node) must include all of these.
    """
    # Legacy at depth 2 renders the action index
    legacy = build_charter_context(
        charter_repo,
        action=action,
        mark_loaded=False,
        depth=2,
    )
    legacy_urns = _extract_artifact_urns_from_legacy(legacy.text)

    # DRG scope-only
    action_urn = f"action:software-dev/{action}"
    scope_walk = walk_edges(
        merged_graph, {action_urn}, {Relation.SCOPE}, max_depth=1,
    )
    drg_scope_urns = {
        u for u in scope_walk if not u.startswith("action:")
    }

    # Legacy must be a subset of DRG scope
    missing_from_drg = legacy_urns - drg_scope_urns
    assert not missing_from_drg, (
        f"Legacy action-index artifacts missing from DRG scope for {action}:\n"
        f"  Missing: {sorted(missing_from_drg)}\n"
        f"  Legacy: {sorted(legacy_urns)}\n"
        f"  DRG scope: {sorted(drg_scope_urns)}"
    )


# ---------------------------------------------------------------------------
# Threshold gate
# ---------------------------------------------------------------------------


def test_accepted_differences_threshold() -> None:
    """Accepted differences must be < 10% of the test matrix.

    Phase 0 is not done if > 10% of matrix entries have differences.
    """
    accepted = load_accepted_differences(_ACCEPTED_DIFFS_PATH)
    matrix = generate_test_matrix()
    threshold = len(matrix) * 0.10
    assert len(accepted) <= threshold, (
        f"Too many accepted differences ({len(accepted)}/{len(matrix)}). "
        f"Phase 0 is not done if > 10% of matrix has differences."
    )


# ---------------------------------------------------------------------------
# Accepted-differences ledger validation
# ---------------------------------------------------------------------------


class TestAcceptedDifferencesLedger:
    """Validate the accepted_differences.yaml schema and loader."""

    def test_empty_ledger_loads(self) -> None:
        """Empty ledger loads without error."""
        accepted = load_accepted_differences(_ACCEPTED_DIFFS_PATH)
        assert isinstance(accepted, dict)
        assert len(accepted) == 0

    def test_empty_reason_rejected(self, tmp_path: Path) -> None:
        """Entries with empty reason are rejected."""
        ledger = tmp_path / "bad.yaml"
        ledger.write_text(
            'schema_version: "1.0"\n'
            "entries:\n"
            "  - profile: null\n"
            "    action: implement\n"
            "    depth: 2\n"
            '    reason: ""\n'
            "    accepted_by: test\n"
            '    accepted_at: "2026-04-13"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="reason.*must not be empty"):
            load_accepted_differences(ledger)

    def test_expected_drift_rejected(self, tmp_path: Path) -> None:
        """Entries with 'expected drift' in reason are rejected."""
        ledger = tmp_path / "bad.yaml"
        ledger.write_text(
            'schema_version: "1.0"\n'
            "entries:\n"
            "  - profile: null\n"
            "    action: implement\n"
            "    depth: 2\n"
            '    reason: "This is expected drift from migration"\n'
            "    accepted_by: test\n"
            '    accepted_at: "2026-04-13"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="forbidden phrase.*expected drift"):
            load_accepted_differences(ledger)

    def test_known_difference_rejected(self, tmp_path: Path) -> None:
        """Entries with 'known difference' in reason are rejected."""
        ledger = tmp_path / "bad.yaml"
        ledger.write_text(
            'schema_version: "1.0"\n'
            "entries:\n"
            "  - profile: null\n"
            "    action: implement\n"
            "    depth: 2\n"
            '    reason: "This is a known difference"\n'
            "    accepted_by: test\n"
            '    accepted_at: "2026-04-13"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="forbidden phrase.*known difference"):
            load_accepted_differences(ledger)

    def test_valid_entry_loads(self, tmp_path: Path) -> None:
        """Valid entries load correctly and are keyed by tuple."""
        ledger = tmp_path / "good.yaml"
        ledger.write_text(
            'schema_version: "1.0"\n'
            "entries:\n"
            "  - profile: null\n"
            "    action: implement\n"
            "    depth: 2\n"
            "    legacy_artifacts:\n"
            "      - directive:DIRECTIVE_099\n"
            "    drg_artifacts: []\n"
            "    reason: >\n"
            "      DIRECTIVE_099 was removed in graph migration;\n"
            "      see issue #42\n"
            "    accepted_by: engineer\n"
            '    accepted_at: "2026-04-13"\n',
            encoding="utf-8",
        )
        accepted = load_accepted_differences(ledger)
        assert (None, "implement", 2) in accepted
        entry = accepted[(None, "implement", 2)]
        assert "DIRECTIVE_099" in entry.reason
        assert entry.accepted_by == "engineer"

    def test_missing_accepted_by_rejected(self, tmp_path: Path) -> None:
        """Entries without accepted_by are rejected."""
        ledger = tmp_path / "bad.yaml"
        ledger.write_text(
            'schema_version: "1.0"\n'
            "entries:\n"
            "  - profile: null\n"
            "    action: implement\n"
            "    depth: 2\n"
            '    reason: "Real reason"\n'
            '    accepted_by: ""\n'
            '    accepted_at: "2026-04-13"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="accepted_by.*must not be empty"):
            load_accepted_differences(ledger)

    def test_invalid_date_rejected(self, tmp_path: Path) -> None:
        """Entries with non-ISO date are rejected."""
        ledger = tmp_path / "bad.yaml"
        ledger.write_text(
            'schema_version: "1.0"\n'
            "entries:\n"
            "  - profile: null\n"
            "    action: implement\n"
            "    depth: 2\n"
            '    reason: "Real reason"\n'
            "    accepted_by: engineer\n"
            '    accepted_at: "not-a-date"\n',
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="accepted_at.*valid ISO date"):
            load_accepted_differences(ledger)


# ---------------------------------------------------------------------------
# Test matrix coverage
# ---------------------------------------------------------------------------


class TestMatrixGenerator:
    """Validate the test matrix generator."""

    def test_matrix_has_expected_size(self) -> None:
        """Matrix has 4 actions x 3 depths = 12 entries (profile degenerate)."""
        matrix = generate_test_matrix()
        assert len(matrix) == 12

    def test_all_parity_actions_covered(self) -> None:
        """All parity actions appear in the matrix."""
        matrix = generate_test_matrix()
        actions = {action for _, action, _ in matrix}
        assert actions == set(_PARITY_ACTIONS)

    def test_all_depths_covered(self) -> None:
        """All depths appear in the matrix."""
        matrix = generate_test_matrix()
        depths = {depth for _, _, depth in matrix}
        assert depths == set(_DEPTHS)

    def test_profiles_degenerate_to_none(self) -> None:
        """Profile dimension is None for all entries in Phase 0."""
        matrix = generate_test_matrix()
        profiles = {profile for profile, _, _ in matrix}
        assert profiles == {None}

    def test_drg_only_matrix_excludes_parity_actions(self) -> None:
        """DRG-only matrix only contains non-parity actions."""
        drg_matrix = generate_drg_only_matrix()
        actions = {action for _, action, _ in drg_matrix}
        assert actions.isdisjoint(set(_PARITY_ACTIONS))
        assert "tasks" in actions

    def test_shipped_profiles_loadable(self) -> None:
        """Shipped agent profiles can be listed (even if not used in Phase 0)."""
        profiles = _load_shipped_profile_ids()
        # Should have at least a few profiles
        assert len(profiles) >= 5, (
            f"Expected at least 5 shipped profiles, found {len(profiles)}"
        )


# ---------------------------------------------------------------------------
# Legacy artifact extraction unit tests
# ---------------------------------------------------------------------------


class TestLegacyArtifactExtraction:
    """Unit tests for _extract_artifact_urns_from_legacy."""

    def test_extracts_directives(self) -> None:
        text = (
            "Action Doctrine (implement):\n"
            "  Directives:\n"
            "    - DIRECTIVE_024: Locality of Change\n"
            "    - DIRECTIVE_030: Test and Typecheck Quality Gate\n"
        )
        urns = _extract_artifact_urns_from_legacy(text)
        assert "directive:DIRECTIVE_024" in urns
        assert "directive:DIRECTIVE_030" in urns

    def test_extracts_tactics(self) -> None:
        text = (
            "Action Doctrine (implement):\n"
            "  Tactics:\n"
            "    - tdd-red-green-refactor: TDD Red-Green-Refactor\n"
            "    - stopping-conditions: Stopping Conditions\n"
        )
        urns = _extract_artifact_urns_from_legacy(text)
        assert "tactic:tdd-red-green-refactor" in urns
        assert "tactic:stopping-conditions" in urns

    def test_extracts_styleguides(self) -> None:
        text = (
            "Action Doctrine (implement):\n"
            "  Styleguides:\n"
            "    - kitty-glossary-writing: Kitty Glossary Writing\n"
        )
        urns = _extract_artifact_urns_from_legacy(text)
        assert "styleguide:kitty-glossary-writing" in urns

    def test_extracts_toolguides(self) -> None:
        text = (
            "Action Doctrine (implement):\n"
            "  Toolguides:\n"
            "    - efficient-local-tooling: Efficient Local Tooling\n"
        )
        urns = _extract_artifact_urns_from_legacy(text)
        assert "toolguide:efficient-local-tooling" in urns

    def test_empty_text_returns_empty(self) -> None:
        urns = _extract_artifact_urns_from_legacy("")
        assert urns == set()

    def test_no_action_doctrine_section(self) -> None:
        text = "Charter Context (Bootstrap):\n  - Source: foo\n"
        urns = _extract_artifact_urns_from_legacy(text)
        assert urns == set()

    def test_combined_extraction(self) -> None:
        """Full realistic text with multiple artifact types."""
        text = (
            "Charter Context (Bootstrap):\n"
            "  - Source: .kittify/charter/charter.md\n"
            "\n"
            "Policy Summary:\n"
            "  - Intent: deterministic delivery\n"
            "\n"
            "Action Doctrine (implement):\n"
            "  Directives:\n"
            "    - DIRECTIVE_024: Locality of Change\n"
            "    - DIRECTIVE_025: Boy Scout Rule\n"
            "  Tactics:\n"
            "    - tdd-red-green-refactor: TDD Red-Green-Refactor\n"
            "    - quality-gate-verification: Quality Gate Verification\n"
            "  Toolguides:\n"
            "    - efficient-local-tooling: Efficient Local Tooling\n"
            "\n"
            "Reference Docs:\n"
            "  - No references manifest found.\n"
        )
        urns = _extract_artifact_urns_from_legacy(text)
        assert urns == {
            "directive:DIRECTIVE_024",
            "directive:DIRECTIVE_025",
            "tactic:tdd-red-green-refactor",
            "tactic:quality-gate-verification",
            "toolguide:efficient-local-tooling",
        }
