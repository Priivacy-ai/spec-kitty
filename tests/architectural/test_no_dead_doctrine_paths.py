"""Architectural gate: doctrine paths named in guidance must exist on disk.

Mission ``doctrine-silence-guards-01KYFV7Q`` WP07 (FR-008, FR-009, NFR-003).

Three defect classes, one shared shape: a source site tells a reader to look
at, edit, or link to a doctrine path that is not there.

``A`` -- the DRG monolith ``src/doctrine/graph.yaml``, sharded out of
existence by #2680 into one ``<kind>.graph.yaml`` fragment per kind.

``B`` -- the ``<kind>/shipped/`` pack layer, which has never existed on disk;
the shipped pack layer is ``<kind>/built-in/``.

``C`` -- relative cross-links in built-in doctrine markdown.

Each gate carries **discriminators**: semantic exclusions that keep it from
false-redding on correct code. A gate that flags every mention of a string is
not a gate, it is a spell-checker, and the first correct site it flags gets it
deleted. NFR-003 therefore requires every discriminator be proven by a fixture
that would false-red *without* it -- the ``*_would_false_red_without_*`` tests
below are those proofs. Each also pins the discriminator's **effect set**
positively (the exact excluded sites and their count), so widening a
discriminator to silence an inconvenient site is a visible diff here rather
than a quiet regex tweak.

There is no violation allowlist. Discriminators exclude sites that are
*correct*; they never excuse a site that is wrong.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_DOCTRINE_ROOT = _SRC_ROOT / "doctrine"

#: Text suffixes worth scanning for path-shaped guidance.
_TEXT_SUFFIXES = frozenset({".py", ".md", ".yaml", ".yml", ".json", ".toml", ".txt"})

#: Mission-tier templates are copied into a mission directory before anyone
#: reads them, so their sibling links resolve at the destination and never at
#: the source. Gate C scopes them out wholesale rather than allowlisting each
#: link; the exclusion is asserted by ``test_cross_link_scope_is_pinned``.
_DEPLOYMENT_RELATIVE_SUBTREE = "missions"


@dataclass(frozen=True, order=True)
class Site:
    """One matched occurrence, addressed repo-relatively."""

    path: str
    line: int
    text: str


def _rel(path: Path, root: Path) -> str:
    """Repo-relative address, falling back to *root* for scanner unit tests."""
    try:
        return path.relative_to(_REPO_ROOT).as_posix()
    except ValueError:
        return path.relative_to(root).as_posix()


def _read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


@lru_cache(maxsize=8)
def _text_files(root: Path) -> tuple[tuple[Path, tuple[str, ...]], ...]:
    """Read every scannable text file under *root* once per root."""
    found: list[tuple[Path, tuple[str, ...]]] = []
    for candidate in sorted(root.rglob("*")):
        if candidate.is_file() and candidate.suffix in _TEXT_SUFFIXES:
            found.append((candidate, tuple(_read_lines(candidate))))
    return tuple(found)


# ---------------------------------------------------------------------------
# Gate A -- the dead DRG monolith path
# ---------------------------------------------------------------------------

#: Any slash-joined literal naming a ``graph.yaml`` directly inside a
#: ``doctrine`` directory. Deliberately broader than the exact built-in
#: string: the defect class is "names a doctrine graph monolith", and a gate
#: keyed only on ``src/doctrine/graph.yaml`` is evaded by rewording the prefix.
_GRAPH_MONOLITH_RE = re.compile(r"[\w./<>-]*doctrine/graph\.yaml")

#: Discriminator A1. The project tier really does write a single
#: ``graph.yaml`` under ``.kittify/doctrine/``; that path is live, not dead.
_PROJECT_TIER_PATH = ".kittify/doctrine/graph.yaml"

#: Discriminator A2. An agent profile's avoidance boundary names a path in
#: order to *forbid* it. Rewriting such a mention inverts the sentence.
_FORBIDDING_FIELD = "avoidance-boundary:"


@dataclass(frozen=True)
class GraphMonolithScan:
    """Gate A result, split by discriminator."""

    violations: tuple[Site, ...]
    project_tier: tuple[Site, ...]
    forbidding_mentions: tuple[Site, ...]

    @property
    def naive(self) -> tuple[Site, ...]:
        """Every match, as a gate with no discriminators would report it."""
        return tuple(sorted(self.violations + self.project_tier + self.forbidding_mentions))


def _forbidding_span(path: Path, lines: tuple[str, ...]) -> tuple[int, int] | None:
    """Return the 1-based inclusive line span of an agent profile's
    ``avoidance-boundary`` block, or ``None`` when the file has no such block.

    The span is derived from YAML block structure (key indentation), not from
    prose matching, so it cannot be widened by wording.
    """
    if not path.name.endswith(".agent.yaml"):
        return None
    for index, line in enumerate(lines):
        stripped = line.lstrip()
        if not stripped.startswith(_FORBIDDING_FIELD):
            continue
        key_indent = len(line) - len(stripped)
        end = len(lines)
        for follow in range(index + 1, len(lines)):
            following = lines[follow]
            if not following.strip():
                continue
            if len(following) - len(following.lstrip()) <= key_indent:
                end = follow
                break
        return (index + 1, end)
    return None


def scan_graph_monolith_paths(root: Path) -> GraphMonolithScan:
    """Classify every ``doctrine/graph.yaml`` mention under *root*."""
    violations: list[Site] = []
    project_tier: list[Site] = []
    forbidding: list[Site] = []
    for path, lines in _text_files(root):
        span = _forbidding_span(path, lines)
        for number, line in enumerate(lines, start=1):
            for match in _GRAPH_MONOLITH_RE.finditer(line):
                site = Site(_rel(path, root), number, match.group(0))
                if _PROJECT_TIER_PATH in match.group(0):
                    project_tier.append(site)
                elif span is not None and span[0] <= number <= span[1]:
                    forbidding.append(site)
                else:
                    violations.append(site)
    return GraphMonolithScan(
        violations=tuple(sorted(violations)),
        project_tier=tuple(sorted(project_tier)),
        forbidding_mentions=tuple(sorted(forbidding)),
    )


# ---------------------------------------------------------------------------
# Gate B -- the `<kind>/shipped/` pack layer that never existed
# ---------------------------------------------------------------------------

#: Discriminator B1 is the leading path segment: ``shipped/`` only counts as a
#: pack-layer reference when a directory segment precedes it. English prose
#: ("the shipped/packaged artifact", "a shipped/custom step") has no such
#: segment and is not a path.
_SHIPPED_PATH_RE = re.compile(r"(?:<[A-Za-z_][\w-]*>|[A-Za-z_][\w-]*)/shipped/")

#: The same class with B1 removed -- used only to prove B1 does work.
_SHIPPED_NAIVE_RE = re.compile(r"shipped/")


@dataclass(frozen=True)
class ShippedLayerScan:
    """Gate B result, split by discriminator."""

    violations: tuple[Site, ...]
    prose: tuple[Site, ...]

    @property
    def naive(self) -> tuple[Site, ...]:
        return tuple(sorted(self.violations + self.prose))


def scan_shipped_pack_paths(root: Path) -> ShippedLayerScan:
    """Classify every ``shipped/`` occurrence under *root*."""
    violations: list[Site] = []
    prose: list[Site] = []
    for path, lines in _text_files(root):
        for number, line in enumerate(lines, start=1):
            for match in _SHIPPED_NAIVE_RE.finditer(line):
                start = match.start()
                window = line[:start]
                as_path = any(hit.end() == match.end() for hit in _SHIPPED_PATH_RE.finditer(line))
                site = Site(_rel(path, root), number, (window[-24:] + match.group(0)).strip())
                (violations if as_path else prose).append(site)
    return ShippedLayerScan(
        violations=tuple(sorted(violations)),
        prose=tuple(sorted(prose)),
    )


# ---------------------------------------------------------------------------
# Gate C -- relative cross-links in built-in doctrine markdown
# ---------------------------------------------------------------------------

_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "#", "<")
#: Discriminator C2: an unfilled template slot is not a broken link.
_PLACEHOLDER_RE = re.compile(r"[{}]")


@dataclass(frozen=True)
class CrossLinkScan:
    """Gate C result, split by discriminator."""

    unresolved: tuple[Site, ...]
    code_examples: tuple[Site, ...]
    placeholders: tuple[Site, ...]


def _link_targets(line: str) -> list[str]:
    return [match.group(1).strip() for match in _LINK_RE.finditer(line)]


def _resolves(md_path: Path, target: str) -> bool:
    bare = target.split("#", 1)[0].strip()
    if not bare:
        return True
    return (md_path.parent / bare).exists()


def _classify_link(md_path: Path, number: int, target: str, root: Path) -> tuple[str, Site] | None:
    if target.startswith(_EXTERNAL_PREFIXES):
        return None
    site = Site(_rel(md_path, root), number, target)
    if _PLACEHOLDER_RE.search(target):
        return ("placeholder", site)
    if _resolves(md_path, target):
        return None
    return ("unresolved", site)


def scan_doctrine_cross_links(root: Path) -> CrossLinkScan:
    """Resolve every relative markdown cross-link under *root*.

    Discriminator C1 drops links that live inside a fenced code block or an
    inline code span: those are *illustrations of link syntax*, not
    navigation. Discriminator C2 drops targets carrying a ``{placeholder}``.
    """
    unresolved: list[Site] = []
    code_examples: list[Site] = []
    placeholders: list[Site] = []
    skipped = root / _DEPLOYMENT_RELATIVE_SUBTREE
    for md_path in sorted(root.rglob("*.md")):
        if skipped in md_path.parents:
            continue
        in_fence = False
        for number, line in enumerate(_read_lines(md_path), start=1):
            if _FENCE_RE.match(line):
                in_fence = not in_fence
                continue
            raw_targets = _link_targets(line)
            if in_fence:
                live_targets: list[str] = []
            else:
                live_targets = _link_targets(_INLINE_CODE_RE.sub("", line))
            for target in raw_targets:
                if target in live_targets:
                    continue
                if target.startswith(_EXTERNAL_PREFIXES):
                    continue
                code_examples.append(Site(_rel(md_path, root), number, target))
            for target in live_targets:
                verdict = _classify_link(md_path, number, target, root)
                if verdict is None:
                    continue
                bucket, site = verdict
                (placeholders if bucket == "placeholder" else unresolved).append(site)
    return CrossLinkScan(
        unresolved=tuple(sorted(unresolved)),
        code_examples=tuple(sorted(code_examples)),
        placeholders=tuple(sorted(placeholders)),
    )


def _render(sites: tuple[Site, ...]) -> str:
    return "\n".join(f"  {site.path}:{site.line}: {site.text}" for site in sites)


# ---------------------------------------------------------------------------
# Gate A assertions
# ---------------------------------------------------------------------------


def test_no_source_site_names_the_dead_drg_monolith() -> None:
    """FR-008 / SC-007: nothing under ``src/`` points at the sharded-away
    ``src/doctrine/graph.yaml``."""
    scan = scan_graph_monolith_paths(_SRC_ROOT)
    assert not scan.violations, (
        "These sites name a doctrine graph monolith that #2680 deleted. "
        "Point them at the per-kind fragment (src/doctrine/<kind>.graph.yaml):\n" + _render(scan.violations)
    )


def test_the_migration_hint_names_a_fragment_that_exists() -> None:
    """FR-008: the hint an operator is handed must be followable -- the file
    it names must be on disk for every artifact kind that can raise it."""
    from doctrine.shared.errors import build_migration_hint

    kinds = (
        "directive",
        "tactic",
        "procedure",
        "paradigm",
        "styleguide",
        "toolguide",
        "agent_profile",
    )
    unfollowable: list[str] = []
    for kind in kinds:
        hint = build_migration_hint(forbidden_field="tactic_refs", source_kind=kind, source_id="example")
        named = [token for token in hint.split() if token.endswith(".graph.yaml")]
        if len(named) != 1 or not (_REPO_ROOT / named[0]).is_file():
            unfollowable.append(f"{kind}: {hint}")
    assert not unfollowable, "Migration hints naming a file that is not on disk:\n" + "\n".join(unfollowable)


def test_project_tier_graph_path_would_false_red_without_its_discriminator() -> None:
    """NFR-003 proof for discriminator A1, with its effect set pinned."""
    scan = scan_graph_monolith_paths(_SRC_ROOT)
    assert scan.project_tier, (
        "A1 excludes nothing, so it cannot be proven. Either the live project-tier path is gone (delete A1) or the pattern stopped matching it."
    )
    naive_paths = {site.path for site in scan.naive}
    kept_paths = {site.path for site in scan.violations} | {site.path for site in scan.forbidding_mentions}
    excluded = sorted(naive_paths - kept_paths)
    assert excluded == [
        "src/charter/synthesizer/manifest.py",
        "src/charter/synthesizer/project_drg.py",
        "src/doctrine/drg/merge.py",
        "src/glossary/drg_builder.py",
        "src/specify_cli/charter_runtime/freshness/computer.py",
        "src/specify_cli/state/contract.py",
    ], f"A1's effect set moved -- widening it needs a reason, not a regex tweak: {excluded}"


def test_forbidding_mention_would_false_red_without_its_discriminator() -> None:
    """NFR-003 proof for discriminator A2, with its effect set pinned."""
    scan = scan_graph_monolith_paths(_SRC_ROOT)
    paths = sorted({site.path for site in scan.forbidding_mentions})
    assert paths == ["src/doctrine/agent_profiles/built-in/doctrine-daphne.agent.yaml"], f"A2's effect set moved: {paths}"
    assert len(scan.forbidding_mentions) == 1, f"A2 now excludes more than the single forbidding mention it was written for: {_render(scan.forbidding_mentions)}"


def test_gate_a_rejects_a_planted_violation(tmp_path: Path) -> None:
    """Self-mutation: the gate must catch the regression it exists to catch."""
    planted = tmp_path / "guidance.md"
    planted.write_text("Add the edge to src/doctrine/graph.yaml.\n", encoding="utf-8")
    scan = scan_graph_monolith_paths(tmp_path)
    assert [site.text for site in scan.violations] == ["src/doctrine/graph.yaml"]


def test_gate_a_discriminators_do_not_swallow_a_planted_violation(tmp_path: Path) -> None:
    """A1/A2 must not become blanket escapes: a dead path inside an agent
    profile but *outside* its avoidance boundary is still a violation."""
    profile = tmp_path / "example.agent.yaml"
    profile.write_text(
        "specialization:\n"
        "  primary-focus: >\n"
        "    Edit src/doctrine/graph.yaml to add the edge.\n"
        "  avoidance-boundary: >\n"
        "    Does not tell an operator to edit src/doctrine/graph.yaml.\n",
        encoding="utf-8",
    )
    scan = scan_graph_monolith_paths(tmp_path)
    assert [site.line for site in scan.violations] == [3]
    assert [site.line for site in scan.forbidding_mentions] == [5]


# ---------------------------------------------------------------------------
# Gate B assertions
# ---------------------------------------------------------------------------


def test_no_source_site_references_the_shipped_pack_layer() -> None:
    """FR-009 / SC-008: ``<kind>/shipped/`` has never existed; the shipped
    pack layer is ``<kind>/built-in/``."""
    scan = scan_shipped_pack_paths(_SRC_ROOT)
    assert not scan.violations, "These sites reference a `shipped/` pack layer that is not on disk. The shipped pack layer is `<kind>/built-in/`:\n" + _render(
        scan.violations
    )


def test_shipped_prose_would_false_red_without_the_path_shape_discriminator() -> None:
    """NFR-003 proof for discriminator B1, with its effect set pinned."""
    scan = scan_shipped_pack_paths(_SRC_ROOT)
    excluded = sorted({site.path for site in scan.prose})
    assert excluded == [
        "src/doctrine/model_task_routing/catalog/model-to-task_type.yaml",
        "src/runtime/next/_internal_runtime/planner.py",
    ], f"B1's effect set moved: {excluded}"
    assert len(scan.prose) == 2, f"B1 now excludes more than the two prose sites it was written for: {_render(scan.prose)}"


def test_gate_b_rejects_a_planted_violation(tmp_path: Path) -> None:
    """Self-mutation: a planted pack-layer path must be flagged, and the
    adjacent prose form must not be."""
    planted = tmp_path / "guide.md"
    planted.write_text(
        "Artifacts live in src/doctrine/tactics/shipped/.\nThe shipped/packaged catalogue is generated.\n",
        encoding="utf-8",
    )
    scan = scan_shipped_pack_paths(tmp_path)
    assert [site.line for site in scan.violations] == [1]
    assert [site.line for site in scan.prose] == [2]


def test_gate_b_flags_the_placeholder_pack_layer_form(tmp_path: Path) -> None:
    """``<kind>/shipped/`` is the operator-facing form and must not slip
    through on account of its angle brackets."""
    planted = tmp_path / "guide.md"
    planted.write_text("Shipped artifacts: src/doctrine/<kind>/shipped/\n", encoding="utf-8")
    scan = scan_shipped_pack_paths(tmp_path)
    assert len(scan.violations) == 1


# ---------------------------------------------------------------------------
# Gate C assertions
# ---------------------------------------------------------------------------


def test_every_built_in_doctrine_cross_link_resolves() -> None:
    """SC-008: relative cross-links in built-in doctrine markdown resolve."""
    scan = scan_doctrine_cross_links(_DOCTRINE_ROOT)
    assert not scan.unresolved, "Broken relative cross-links in doctrine markdown:\n" + _render(scan.unresolved)


def test_code_example_links_would_false_red_without_their_discriminator() -> None:
    """NFR-003 proof for discriminator C1, with its effect set pinned."""
    scan = scan_doctrine_cross_links(_DOCTRINE_ROOT)
    excluded = sorted({(site.path, site.text) for site in scan.code_examples})
    assert excluded == [
        ("src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md", "../spec.md#x"),
        ("src/doctrine/toolguides/built-in/MERMAID_DIAGRAMMING.md", "diagram.svg"),
        ("src/doctrine/toolguides/built-in/PLANTUML_DIAGRAMMING.md", "diagram.svg"),
    ], f"C1's effect set moved: {excluded}"


def test_placeholder_links_would_false_red_without_their_discriminator() -> None:
    """NFR-003 proof for discriminator C2, with its effect set pinned."""
    scan = scan_doctrine_cross_links(_DOCTRINE_ROOT)
    excluded = sorted({(site.path, site.text) for site in scan.placeholders})
    assert excluded == [
        ("src/doctrine/templates/guides/HOW-TO.template.md", "../explanation/{topic}.md"),
        ("src/doctrine/templates/guides/HOW-TO.template.md", "../reference/{file}.md"),
        ("src/doctrine/templates/guides/HOW-TO.template.md", "./{related-guide}.md"),
    ], f"C2's effect set moved: {excluded}"


def test_cross_link_scope_is_pinned() -> None:
    """The one scope exclusion is the mission-tier template subtree, whose
    links resolve at the mission directory they are copied into."""
    skipped = _DOCTRINE_ROOT / _DEPLOYMENT_RELATIVE_SUBTREE
    assert skipped.is_dir()
    in_scope = {_rel(path, _DOCTRINE_ROOT) for path in _DOCTRINE_ROOT.rglob("*.md") if skipped not in path.parents}
    assert not any(path.startswith("src/doctrine/missions/") for path in in_scope)
    assert len(in_scope) >= 20


def test_gate_c_rejects_a_planted_broken_link(tmp_path: Path) -> None:
    """Self-mutation: a broken link must be flagged, while its code-span and
    placeholder neighbours must not be."""
    (tmp_path / "sibling.md").write_text("ok\n", encoding="utf-8")
    planted = tmp_path / "page.md"
    planted.write_text(
        "See [gone](./missing.md).\nSee [here](./sibling.md).\nWrite `[see spec](../spec.md#x)` like this.\nFill in [topic]({topic}.md).\n",
        encoding="utf-8",
    )
    scan = scan_doctrine_cross_links(tmp_path)
    assert [site.text for site in scan.unresolved] == ["./missing.md"]
    assert [site.text for site in scan.code_examples] == ["../spec.md#x"]
    assert [site.text for site in scan.placeholders] == ["{topic}.md"]


def test_gate_c_fence_discriminator_does_not_swallow_live_links(tmp_path: Path) -> None:
    """A closed fence must restore checking; otherwise one stray fence
    silences the rest of a file."""
    planted = tmp_path / "page.md"
    planted.write_text(
        "```\n[in fence](./nope.md)\n```\n[after fence](./also-nope.md)\n",
        encoding="utf-8",
    )
    scan = scan_doctrine_cross_links(tmp_path)
    assert [site.text for site in scan.unresolved] == ["./also-nope.md"]
    assert [site.text for site in scan.code_examples] == ["./nope.md"]
