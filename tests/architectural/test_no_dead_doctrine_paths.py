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
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pytest

#: Without this the CI shard that selects ``-m architectural`` collects none of
#: these tests, and the gate silently never runs.
pytestmark = [pytest.mark.architectural, pytest.mark.git_repo]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC_ROOT = _REPO_ROOT / "src"
_DOCTRINE_ROOT = _SRC_ROOT / "doctrine"

#: Relocated built-in pack root (mission ``relocate-builtin-doctrine-packs-01KYT87F``).
#: The shipped built-in doctrine content that names paths -- agent profiles,
#: glossary packs, toolguide markdown, and the per-kind ``*.graph.yaml`` fragments
#: -- moved out of ``src/doctrine/`` into this top-level pack root. The dead-path
#: defect class now spans BOTH trees (consuming code under ``src/``; authored pack
#: content under ``packs/built-in/``), so every shipped gate below scans the pair
#: and merges the result. ``_rel`` addresses each site repo-relatively, so a merged
#: site keeps its true ``src/...`` or ``packs/...`` prefix.
_PACKS_ROOT = _REPO_ROOT / "packs" / "built-in"

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

#: The whole dead path, not just its ``<segment>/shipped/`` core. Discriminator
#: B2 compares this token against the frozen seed, so a pack that *invented* a
#: sibling dead path under the same segment cannot ride the seed's coat-tails.
_SHIPPED_FULL_PATH_RE = re.compile(
    r"[\w./<>-]*(?:<[A-Za-z_][\w-]*>|[A-Za-z_][\w-]*)/shipped/[\w./-]*"
)

#: Discriminator B2 -- built-in glossary packs mirroring a hash-pinned seed.
#:
#: ``src/doctrine/glossary_packs/built-in/<pack-id>.glossary-pack.yaml`` is a
#: field-for-field migration of the read-only seed
#: ``.kittify/glossaries/<pack-id>.yaml`` (the ``{scope.value}.yaml`` layout
#: ``glossary.scope.load_seed_file`` resolves). Two standing gates make the pack
#: text non-editable in BOTH directions: ``test_glossary_pack_parity`` requires
#: every seed-present field to round-trip byte-identically, and
#: ``test_glossary_pack_no_regression`` pins the seed's sha256 under C-003 ("the
#: seed is READ, never modified"). A stale doctrine path quoted inside that prose
#: is therefore a *frozen historical inaccuracy*, not a live defect: it cannot be
#: corrected on the pack side without breaking parity, nor on the seed side
#: without breaking the C-003 content pin. Dead path, frozen artefact -- different
#: problems, and a dead-path sweep owns only the first.
#:
#: The exclusion is derived, not declared: it fires only for a token that is
#: present VERBATIM in the seed the pack mirrors. It is also self-retiring --
#: when Mission C retires the seed, the token stops resolving and every pack site
#: reverts to a violation with no edit here.
# Relocated to the flattened pack root (mission relocate-builtin-doctrine-packs-01KYT87F):
# the built-in glossary packs now live at ``packs/built-in/glossary_packs/`` (the
# inner ``built-in`` segment is dropped). Matched as a parent-path substring.
_GLOSSARY_PACK_SUBTREE = "built-in/glossary_packs"
_GLOSSARY_PACK_SUFFIX = ".glossary-pack.yaml"
_GLOSSARY_SEED_DIR = _REPO_ROOT / ".kittify" / "glossaries"


@lru_cache(maxsize=8)
def _frozen_seed_text(seed_path: Path) -> str:
    return seed_path.read_text(encoding="utf-8")


def _frozen_seed_for_pack(path: Path) -> Path | None:
    """The hash-pinned migration seed *path* mirrors, or ``None``.

    Anchored at ``_REPO_ROOT`` rather than the scan root on purpose: the seed
    lives under ``.kittify/``, outside every root gate B is pointed at.
    """
    if not path.name.endswith(_GLOSSARY_PACK_SUFFIX):
        return None
    if _GLOSSARY_PACK_SUBTREE not in path.parent.as_posix():
        return None
    pack_id = path.name[: -len(_GLOSSARY_PACK_SUFFIX)]
    seed = _GLOSSARY_SEED_DIR / f"{pack_id.replace('-', '_')}.yaml"
    return seed if seed.is_file() else None


def _full_path_token(line: str, naive: re.Match[str]) -> str | None:
    """The whole path literal enclosing a bare ``shipped/`` match."""
    for hit in _SHIPPED_FULL_PATH_RE.finditer(line):
        if hit.start() <= naive.start() and naive.end() <= hit.end():
            return hit.group(0)
    return None


@dataclass(frozen=True)
class ShippedLayerScan:
    """Gate B result, split by discriminator."""

    violations: tuple[Site, ...]
    prose: tuple[Site, ...]
    frozen_mirrors: tuple[Site, ...]

    @property
    def naive(self) -> tuple[Site, ...]:
        return tuple(sorted(self.violations + self.prose + self.frozen_mirrors))


def scan_shipped_pack_paths(root: Path) -> ShippedLayerScan:
    """Classify every ``shipped/`` occurrence under *root*."""
    violations: list[Site] = []
    prose: list[Site] = []
    frozen_mirrors: list[Site] = []
    for path, lines in _text_files(root):
        for number, line in enumerate(lines, start=1):
            for match in _SHIPPED_NAIVE_RE.finditer(line):
                start = match.start()
                window = line[:start]
                as_path = any(hit.end() == match.end() for hit in _SHIPPED_PATH_RE.finditer(line))
                site = Site(_rel(path, root), number, (window[-24:] + match.group(0)).strip())
                if not as_path:
                    prose.append(site)
                    continue
                token = _full_path_token(line, match)
                seed = _frozen_seed_for_pack(path)
                if token is not None and seed is not None and token in _frozen_seed_text(seed):
                    # Site.text is the full path token here (not the prose window
                    # the other buckets carry): it is what B2 actually matched on,
                    # so it is stable identity for the effect-set pin below.
                    frozen_mirrors.append(Site(_rel(path, root), number, token))
                    continue
                violations.append(site)
    return ShippedLayerScan(
        violations=tuple(sorted(violations)),
        prose=tuple(sorted(prose)),
        frozen_mirrors=tuple(sorted(frozen_mirrors)),
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
# Two-tree shipped scans (mission relocate-builtin-doctrine-packs-01KYT87F)
# ---------------------------------------------------------------------------
# The shipped assertions walk BOTH ``src/`` (consuming code) and
# ``packs/built-in/`` (relocated authored pack content), because the dead-path
# defect class now spans the two. The mutation-proof tests keep calling the
# single-root scanners against a ``tmp_path`` fixture and are untouched by this.
#
# NOTE (#3036): this is a scope widening, not a re-framing. #3036 tracks the
# fuller rework of this suite (canonical pack-root discovery in place of a
# hard-coded root pair); that reframing is deliberately NOT attempted here.


def scan_graph_monolith_shipped() -> GraphMonolithScan:
    """Gate A over the shipped trees: ``src/`` merged with ``packs/built-in/``."""
    src, pack = (
        scan_graph_monolith_paths(_SRC_ROOT),
        scan_graph_monolith_paths(_PACKS_ROOT),
    )
    return GraphMonolithScan(
        violations=tuple(sorted(src.violations + pack.violations)),
        project_tier=tuple(sorted(src.project_tier + pack.project_tier)),
        forbidding_mentions=tuple(sorted(src.forbidding_mentions + pack.forbidding_mentions)),
    )


def scan_shipped_pack_shipped() -> ShippedLayerScan:
    """Gate B over the shipped trees: ``src/`` merged with ``packs/built-in/``."""
    src, pack = (
        scan_shipped_pack_paths(_SRC_ROOT),
        scan_shipped_pack_paths(_PACKS_ROOT),
    )
    return ShippedLayerScan(
        violations=tuple(sorted(src.violations + pack.violations)),
        prose=tuple(sorted(src.prose + pack.prose)),
        frozen_mirrors=tuple(sorted(src.frozen_mirrors + pack.frozen_mirrors)),
    )


def scan_doctrine_cross_links_shipped() -> CrossLinkScan:
    """Gate C over the shipped doctrine markdown: ``src/doctrine/`` merged with
    ``packs/built-in/``."""
    src, pack = (
        scan_doctrine_cross_links(_DOCTRINE_ROOT),
        scan_doctrine_cross_links(_PACKS_ROOT),
    )
    return CrossLinkScan(
        unresolved=tuple(sorted(src.unresolved + pack.unresolved)),
        code_examples=tuple(sorted(src.code_examples + pack.code_examples)),
        placeholders=tuple(sorted(src.placeholders + pack.placeholders)),
    )


# ---------------------------------------------------------------------------
# Gate A assertions
# ---------------------------------------------------------------------------


def test_no_source_site_names_the_dead_drg_monolith() -> None:
    """FR-008 / SC-007: nothing under the shipped trees (``src/`` +
    ``packs/built-in/``) points at the sharded-away ``src/doctrine/graph.yaml``."""
    scan = scan_graph_monolith_shipped()
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
            continue
        # Existence alone is too weak: every per-kind fragment exists, so a hint
        # hard-coded to any one of them passes an is_file() check for all seven.
        # Review proved it by replacing the interpolation with a constant
        # "tactic.graph.yaml" -- 61 tests stayed green while an operator holding
        # a directive-sourced edge was sent to the tactic shard. Edges shard by
        # SOURCE kind (extractor._partition_by_kind), verified against all 774
        # shipped edges, so the named fragment must be the source kind's own.
        # Relocated (mission relocate-builtin-doctrine-packs-01KYT87F): the shipped
        # per-kind fragments moved from ``src/doctrine/`` to the ``packs/built-in/``
        # pack root, so the followable hint names the fragment there.
        expected = f"packs/built-in/{kind}.graph.yaml"
        if named[0] != expected:
            unfollowable.append(f"{kind}: names {named[0]}, but its edges shard into {expected}")
    assert not unfollowable, (
        "Migration hints that do not name the fragment the operator must open:\n"
        + "\n".join(unfollowable)
    )


def test_project_tier_graph_path_would_false_red_without_its_discriminator() -> None:
    """NFR-003 proof for discriminator A1, with its effect set pinned."""
    scan = scan_graph_monolith_shipped()
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
    scan = scan_graph_monolith_shipped()
    # (path, matched text) rather than a path set plus a count: a second
    # forbidding mention in the SAME file collapses out of a path set, and a
    # different mention swapped in for this one keeps any count unchanged.
    # ``Site.text`` is gate A's raw ``match.group(0)`` -- the path itself, so it
    # is stable identity rather than surrounding prose.
    #
    # Relocated (mission relocate-builtin-doctrine-packs-01KYT87F): doctrine-daphne's
    # profile moved to the flattened pack root, so her avoidance-boundary mention
    # of the retired monolith now addresses as ``packs/built-in/agent_profiles/``.
    excluded = sorted((site.path, site.text) for site in scan.forbidding_mentions)
    assert excluded == [
        (
            "packs/built-in/agent_profiles/doctrine-daphne.agent.yaml",
            "src/doctrine/graph.yaml",
        )
    ], f"A2's effect set moved -- widening it needs a reason: {_render(scan.forbidding_mentions)}"


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
    scan = scan_shipped_pack_shipped()
    assert not scan.violations, "These sites reference a `shipped/` pack layer that is not on disk. The shipped pack layer is `<kind>/built-in/`:\n" + _render(
        scan.violations
    )


def test_shipped_prose_would_false_red_without_the_path_shape_discriminator() -> None:
    """NFR-003 proof for discriminator B1, with its effect set pinned."""
    scan = scan_shipped_pack_shipped()
    # A list, not a set: duplicates survive, so a second prose match appearing in
    # any of these three files goes red instead of collapsing into the same path.
    # Unlike gate A, ``Site.text`` here is a 24-char prose window built for the
    # failure message, so it is not part of the pinned identity.
    #
    # 2026-07-29 (PR #3070 landing pass, WP05 doctrine-delivery-reachability):
    # widened by one entry for `src/specify_cli/cli/commands/_doctrine_asset.py`
    # — its module docstring reads "...resolve shipped/overlay doctrine assets",
    # genuine English prose (no `<segment>/` immediately precedes `shipped/`),
    # not a `<kind>/shipped/` pack-layer path reference.
    excluded = sorted(site.path for site in scan.prose)
    assert excluded == [
        "src/doctrine/model_task_routing/catalog/model-to-task_type.yaml",
        "src/runtime/next/_internal_runtime/planner.py",
        "src/specify_cli/cli/commands/_doctrine_asset.py",
    ], f"B1's effect set moved -- widening it needs a reason: {_render(scan.prose)}"


def test_frozen_seed_mirror_would_false_red_without_its_discriminator() -> None:
    """NFR-003 proof for discriminator B2, with its effect set pinned.

    A list of ``(path, token)`` pairs, duplicates intact: the pack quotes the
    same dead path twice (once in the term's ``definition`` prose, once in its
    ``see_also`` entry) and both must stay excluded. Collapsing to a set would
    let one of the two silently become a violation.
    """
    scan = scan_shipped_pack_shipped()
    excluded = sorted((site.path, site.text) for site in scan.frozen_mirrors)
    # Relocated (mission relocate-builtin-doctrine-packs-01KYT87F): the built-in
    # glossary pack moved to the flattened ``packs/built-in/glossary_packs/`` home.
    pack = "packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml"
    dead_path = "src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml"
    assert excluded == [(pack, dead_path), (pack, dead_path)], (
        "B2's effect set moved. It may only exclude a pack site whose dead path "
        "is verbatim in the hash-pinned seed it mirrors -- widening it needs a "
        f"reason, not a regex tweak: {_render(scan.frozen_mirrors)}"
    )


def test_frozen_seed_mirror_discriminator_is_anchored_in_the_live_seed() -> None:
    """B2 is only sound while the seed really does carry the dead path.

    Reads the seed directly rather than trusting the scan: if the seed were
    edited to "fix" the path (the C-003 violation this discriminator exists to
    make unnecessary), B2 would go quietly inert and the pack sites would flip
    to violations with no explanation. This fails first, and says why.
    """
    seed = _GLOSSARY_SEED_DIR / "spec_kitty_core.yaml"
    assert seed.is_file(), f"the mirrored migration seed is missing: {seed}"
    dead_path = "src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml"
    assert dead_path in _frozen_seed_text(seed), (
        f"the seed no longer carries {dead_path!r}. The seed is READ, never "
        "modified (C-003, pinned by test_glossary_pack_no_regression) -- if it "
        "was legitimately retired, drop discriminator B2 and fix the pack."
    )


def test_gate_b_frozen_mirror_discriminator_requires_the_seed_to_carry_the_path(
    tmp_path: Path,
) -> None:
    """B2 must not degrade into a subtree escape for the glossary-pack dir.

    Three planted sites in the pack subtree, one excluded: only the path the
    real seed actually carries. A sibling dead path under the same
    ``tactics/shipped/`` segment, and a pack whose id maps to no seed at all,
    both stay violations.
    """
    # Flattened pack home (mission relocate-builtin-doctrine-packs-01KYT87F):
    # ``packs/built-in/glossary_packs/`` (the inner ``built-in`` is dropped).
    pack_dir = tmp_path / "packs" / "built-in" / "glossary_packs"
    pack_dir.mkdir(parents=True)
    mirrored = "src/doctrine/tactics/shipped/secure-regex-catastrophic-backtracking.tactic.yaml"
    (pack_dir / "spec-kitty-core.glossary-pack.yaml").write_text(
        f"a: {mirrored}\nb: src/doctrine/tactics/shipped/invented.tactic.yaml\n",
        encoding="utf-8",
    )
    (pack_dir / "no-such-seed.glossary-pack.yaml").write_text(
        f"a: {mirrored}\n", encoding="utf-8"
    )
    scan = scan_shipped_pack_paths(tmp_path)
    assert [(site.path, site.line) for site in scan.frozen_mirrors] == [
        ("packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml", 1)
    ]
    assert [(site.path, site.line) for site in scan.violations] == [
        ("packs/built-in/glossary_packs/no-such-seed.glossary-pack.yaml", 1),
        ("packs/built-in/glossary_packs/spec-kitty-core.glossary-pack.yaml", 2),
    ]


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
    scan = scan_doctrine_cross_links_shipped()
    assert not scan.unresolved, "Broken relative cross-links in doctrine markdown:\n" + _render(scan.unresolved)


def test_code_example_links_would_false_red_without_their_discriminator() -> None:
    """NFR-003 proof for discriminator C1, with its effect set pinned."""
    scan = scan_doctrine_cross_links_shipped()
    excluded = sorted({(site.path, site.text) for site in scan.code_examples})
    # Relocated (mission relocate-builtin-doctrine-packs-01KYT87F): the toolguide
    # markdown moved to the flattened ``packs/built-in/toolguides/`` home; the
    # SKILL.md stays under ``src/doctrine/skills/`` (skills did not move).
    assert excluded == [
        ("packs/built-in/toolguides/MERMAID_DIAGRAMMING.md", "diagram.svg"),
        ("packs/built-in/toolguides/PLANTUML_DIAGRAMMING.md", "diagram.svg"),
        ("src/doctrine/skills/spec-kitty-spdd-reasons/SKILL.md", "../spec.md#x"),
    ], f"C1's effect set moved: {excluded}"


def test_placeholder_links_would_false_red_without_their_discriminator() -> None:
    """NFR-003 proof for discriminator C2, with its effect set pinned."""
    scan = scan_doctrine_cross_links_shipped()
    excluded = sorted({(site.path, site.text) for site in scan.placeholders})
    assert excluded == [
        ("src/doctrine/templates/guides/HOW-TO.template.md", "../explanation/{topic}.md"),
        ("src/doctrine/templates/guides/HOW-TO.template.md", "../reference/{file}.md"),
        ("src/doctrine/templates/guides/HOW-TO.template.md", "./{related-guide}.md"),
    ], f"C2's effect set moved: {excluded}"


def test_cross_link_scope_is_pinned() -> None:
    """The one scope exclusion is the mission-tier template subtree, whose
    links resolve at the mission directory they are copied into.

    Relocated (mission relocate-builtin-doctrine-packs-01KYT87F): Gate C now
    covers BOTH shipped trees, so the in-scope corpus is the union of
    ``src/doctrine/`` markdown (skills, templates, package READMEs — the
    ``missions`` subtree still lives here and is still excluded) and the
    relocated ``packs/built-in/`` markdown (toolguides, pack READMEs).
    """
    in_scope: set[str] = set()
    for root in (_DOCTRINE_ROOT, _PACKS_ROOT):
        skipped = root / _DEPLOYMENT_RELATIVE_SUBTREE
        in_scope |= {
            _rel(path, root)
            for path in root.rglob("*.md")
            if skipped not in path.parents
        }
    assert _DOCTRINE_ROOT.is_dir() and _PACKS_ROOT.is_dir()
    assert not any(path.startswith("src/doctrine/missions/") for path in in_scope)
    # Pinned near the live combined count (159 = 141 under src/doctrine + 18 under
    # packs/built-in), not at a token floor. The exclusion is subtree-shaped, so
    # this assertion is the only thing standing between Gate C and a silencing
    # move: at a floor of 20, most files could be relocated under a skipped
    # subtree before anything noticed. Re-measured 2026-07-30 after the built-in
    # pack relocation; the gap to 159 is slack for ordinary authoring, not for a
    # migration.
    assert len(in_scope) >= 150, (
        f"Gate C's in-scope set fell to {len(in_scope)} from a measured 159. "
        "Moving files under a skipped `missions/` subtree removes them from link "
        "checking entirely — if that is intended, say why and re-pin."
    )


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


# ---------------------------------------------------------------------------
# Gate D -- live documentation must not name a pre-move built-in path
# (mission relocate-builtin-doctrine-packs-01KYT87F, T024 / FR-011)
# ---------------------------------------------------------------------------

#: The two path shapes the relocation retired from ``src/doctrine/``: the
#: per-kind built-in content home ``src/doctrine/<kind>/built-in`` and the
#: sharded per-kind fragments ``src/doctrine/<kind>.graph.yaml``. Both now live
#: under ``packs/built-in/``.
_MOVED_BUILTIN_DOC_RE = r"src/doctrine/[a-z_]+/built-in|src/doctrine/[a-zA-Z0-9_.-]*\.graph\.yaml"

#: Documentation subtrees excluded from the live-reference guard, each because
#: its references are NOT live pointers to where doctrine currently lives:
#:  * ``docs/adr`` -- immutable decision snapshots (the Terminology Canon keeps
#:    historical wording frozen; an ADR records the world as it was).
#:  * ``docs/plans`` -- point-in-time mission planning and adversarial-squad
#:    analysis (line-numbered ``*.graph.yaml`` citations, and hypothetical paths
#:    such as ``src/doctrine/values/built-in/…`` that never existed on disk).
#:  * the generated retrieval index -- a derived aggregate that mirrors the
#:    ``docs/plans`` headings it indexes, so it carries their frozen wording and
#:    is regenerated, never hand-edited.
#:  * the relocation migration note -- its whole job is to document the move, so
#:    its old->new mapping table NAMES the retired ``src/doctrine/.../built-in``
#:    paths as the "from" column. That is a record of where content used to live,
#:    not a live pointer to where it lives now (same rationale as ``docs/adr``).
_GUARD_DOC_EXCLUSIONS = (
    ":(exclude)docs/adr",
    ":(exclude)docs/plans",
    ":(exclude)docs/development/3-2-docs-retrieval-index.yaml",
    ":(exclude)docs/migrations/relocate-builtin-doctrine-packs.md",
)


def test_no_live_doc_names_a_pre_move_builtin_path() -> None:
    """FR-011 committed guard: the T024 live-reference sweep is observable, not
    eyeballed. ``git grep`` of live ``docs/`` (minus the snapshot/derived subtrees
    pinned above) for a retired ``src/doctrine/`` built-in path must return zero;
    a hit means a live doc still sends a reader to a home that moved to
    ``packs/built-in/`` (see docs/migrations/relocate-builtin-doctrine-packs.md)."""
    result = subprocess.run(
        ["git", "grep", "-nE", _MOVED_BUILTIN_DOC_RE, "--", "docs", *_GUARD_DOC_EXCLUSIONS],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode not in (0, 1):
        pytest.skip(f"git grep unavailable ({result.returncode}): {result.stderr.strip()}")
    # git grep exit status: 0 == matches found (dead refs present); 1 == clean.
    assert result.returncode == 1, (
        "Live documentation still names a pre-move built-in path. Repoint each to "
        "packs/built-in/ (drop the inner `built-in` segment):\n" + result.stdout
    )
