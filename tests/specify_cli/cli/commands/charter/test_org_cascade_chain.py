"""WP02 (mission ``cascade-org-inert-01M07E9P``): org-roots threading into the
three ``load_validated_graph`` cascade call sites (``activate.py``:226/317,
``deactivate.py``:139) plus ``_layer_roots.py``'s ID-mapping chain widening.

The defect this WP fixes (FR-001, NFR-001/002, C-001/002): before this WP,
``charter activate/deactivate --cascade`` walked the merged DRG with **no org
roots at all**, so a ``requires``/``suggests`` edge that lived in (or targeted)
an org pack was invisible to the cascade engine — dependent org-pack artifacts
were silently neither activated nor reported as skipped. Separately,
``_layer_roots.resolve_layer_roots`` only ever registered the FIRST org root
into its single-value ``roots["org"]`` slot, so even once the DRG walk saw
pack 2..N, the DRG-bare-ID -> config-stem-ID mapping (``_drg_id_to_config_id``)
still only consulted pack 1 -- an org-pack-2..N cascade target would resolve to
its raw DRG ID (unresolvable by ``CharterPackManager.activate``) instead of its
real config stem.

Covers T011 (red-first single-pack + two-pack chain), T012 (non-vacuity: the
ID-mapping widening specifically, not just DRG visibility), T013
(``charter list --all`` back-compat regression -- the third consumer the spec
squad caught), T014 (no-org-pack regression), T015
(``referenced_but_not_cascaded`` names org-pack artifacts), T016 (malformed
pack -- loud failure is acceptable, no degrade logic is this WP's job).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from specify_cli.cli.commands.charter import charter_app
from specify_cli.cli.commands.charter import activate as activate_mod
from specify_cli.cli.commands.charter._layer_roots import resolve_layer_roots

runner = CliRunner()

pytestmark = [pytest.mark.integration]

# ---------------------------------------------------------------------------
# Fixture builders (no reusable conftest helper exists for this shape --
# module-level helpers, matching the established cross-module pattern e.g.
# tests/specify_cli/mission_step_contracts/test_executor.py's
# write_org_pack_config / write_two_pack_org_config).
# ---------------------------------------------------------------------------


def _write_org_pack_config(project_root: Path, packs: list[tuple[str, str]]) -> None:
    """Write ``.kittify/config.yaml`` with a declaration-ordered org-pack chain.

    Carries ``mission_type_activations`` (WP04, C-A1): ``PackContext.from_config``
    fails closed without it.
    """
    lines: list[str] = ["doctrine:", "  org:", "    packs:"]
    for name, local_path in packs:
        lines.append(f"      - name: {name}")
        lines.append(f"        local_path: {local_path}")
    lines.append("mission_type_activations:")
    lines.append("  - software-dev")
    config_path = project_root / ".kittify" / "config.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_directive(pack_root: Path, stem: str, declared_id: str) -> None:
    """Write a flat-layout directive artifact: ``<pack>/directives/<stem>.directive.yaml``.

    The config-stem (``stem``, what ``charter activate directive <stem>`` and
    config.yaml's activation lists key off) is deliberately distinct from the
    DRG ``id:`` field (``declared_id``, what DRG edges/nodes reference) --
    matching the established convention in
    ``tests/specify_cli/cli/commands/charter/test_activation_layout.py`` and
    ``tests/charter/test_org_scan_dirs_activation_regression.py`` -- a fixture
    that makes stem == id cannot catch a stem/id-confusion bug.
    """
    directives_dir = pack_root / "directives"
    directives_dir.mkdir(parents=True, exist_ok=True)
    (directives_dir / f"{stem}.directive.yaml").write_text(
        f"id: {declared_id}\ntype: directive\ntitle: {stem}\n", encoding="utf-8"
    )


def _write_graph_fragment(
    pack_root: Path,
    filename: str,
    *,
    nodes: list[tuple[str, str]],
    edges: list[tuple[str, str, str]],
) -> None:
    """Write a root-level ``*.graph.yaml`` DRG fragment for *pack_root*.

    ``nodes``: ``(urn, kind)`` pairs. ``edges``: ``(source_urn, target_urn,
    relation)`` triples -- full URN endpoints (never bare ids), so an edge may
    validly target a node declared in a DIFFERENT pack's own fragment once the
    merge folds both in (this is exactly what the two-pack chain test needs).
    """
    node_lines = "\n".join(f'  - urn: "{urn}"\n    kind: {kind}' for urn, kind in nodes)
    nodes_section = f"nodes:\n{node_lines}" if nodes else "nodes: []"

    edge_lines = "\n".join(
        f'  - source: "{src}"\n    target: "{tgt}"\n    relation: {rel}'
        for src, tgt, rel in edges
    )
    edges_section = f"edges:\n{edge_lines}" if edges else "edges: []"

    body = (
        'schema_version: "1.0"\n'
        'generated_at: "2026-08-17T00:00:00Z"\n'
        'generated_by: "test"\n'
        f"{nodes_section}\n"
        f"{edges_section}\n"
    )
    (pack_root / filename).write_text(body, encoding="utf-8")


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """A minimal project with an empty ``.kittify/config.yaml`` (no org packs)."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n", encoding="utf-8"
    )
    return tmp_path


def _config(project_root: Path) -> dict:
    raw = (project_root / ".kittify" / "config.yaml").read_text(encoding="utf-8")
    return yaml.safe_load(raw) or {}


def _activate(project_root: Path, *args: str, catch_exceptions: bool = False) -> object:
    return runner.invoke(
        charter_app,
        ["activate", "--repo-root", str(project_root), *args],
        catch_exceptions=catch_exceptions,
    )


def _deactivate(project_root: Path, *args: str) -> object:
    return runner.invoke(
        charter_app,
        ["deactivate", "--repo-root", str(project_root), *args],
        catch_exceptions=False,
    )


# ---------------------------------------------------------------------------
# T011 (1/2) — single healthy org pack (FR-001 AC1)
# ---------------------------------------------------------------------------


class TestSingleOrgPackCascade:
    def test_cascade_all_activates_requires_edge_within_same_org_pack(
        self, project_root: Path
    ) -> None:
        """``A requires B``, both in one org pack: ``--cascade all`` activates B too.

        This is the baseline positive case for this call site -- previously
        untested here since org roots were never threaded at all before this
        WP (T011 item 1).
        """
        pack_root = project_root / "org-packs" / "pack1"
        _write_directive(pack_root, "a-directive", "DIRECTIVE_A")
        _write_directive(pack_root, "b-directive", "DIRECTIVE_B")
        _write_graph_fragment(
            pack_root,
            "fixture.graph.yaml",
            nodes=[
                ("directive:DIRECTIVE_A", "directive"),
                ("directive:DIRECTIVE_B", "directive"),
            ],
            edges=[("directive:DIRECTIVE_A", "directive:DIRECTIVE_B", "requires")],
        )
        _write_org_pack_config(project_root, [("pack1", "org-packs/pack1")])

        result = _activate(
            project_root, "--cascade", "all", "directive", "a-directive"
        )
        assert result.exit_code == 0, result.output

        data = _config(project_root)
        activated = data.get("activated_directives") or []
        assert "a-directive" in activated
        assert "b-directive" in activated, (
            f"org-pack requires edge did not cascade-activate; output:\n{result.output}"
        )
        assert "Cascade-activated" in result.output


# ---------------------------------------------------------------------------
# T011 (2/2) — two-pack chain (FR-001 AC2 / User Story 1 AC2)
# ---------------------------------------------------------------------------


def _write_two_pack_chain(project_root: Path) -> None:
    """Pack 1's ``a-directive`` requires pack 2's ``c-directive``.

    Node C is declared only in pack 2's own fragment; the requires edge is
    declared in pack 1's fragment, referencing C's full URN. This is only
    resolvable once BOTH packs are folded into the merged DRG (proving the
    full-chain widening, not just pack 1) AND ``resolve_config_id`` receives
    the full org-root chain (proving the ID-mapping widening, not just DRG
    visibility) -- a test that only carried one pack would prove nothing about
    the pack-2..N defect class this mission's core bug lives in (#3525's
    "one layer down" analogue).
    """
    pack1_root = project_root / "org-packs" / "pack1"
    pack2_root = project_root / "org-packs" / "pack2"
    _write_directive(pack1_root, "a-directive", "DIRECTIVE_A")
    _write_graph_fragment(
        pack1_root,
        "fixture.graph.yaml",
        nodes=[("directive:DIRECTIVE_A", "directive")],
        edges=[("directive:DIRECTIVE_A", "directive:DIRECTIVE_C", "requires")],
    )
    _write_directive(pack2_root, "c-directive", "DIRECTIVE_C")
    _write_graph_fragment(
        pack2_root,
        "fixture.graph.yaml",
        nodes=[("directive:DIRECTIVE_C", "directive")],
        edges=[],
    )
    _write_org_pack_config(
        project_root,
        [("pack1", "org-packs/pack1"), ("pack2", "org-packs/pack2")],
    )


class TestTwoPackChainCascade:
    def test_cascade_all_activates_requires_edge_reaching_second_pack(
        self, project_root: Path
    ) -> None:
        """``charter activate directive a-directive --cascade all`` activates
        pack-2's ``c-directive`` too -- the pack-2..N chain case (T011 item 2).
        """
        _write_two_pack_chain(project_root)

        result = _activate(
            project_root, "--cascade", "all", "directive", "a-directive"
        )
        assert result.exit_code == 0, result.output

        data = _config(project_root)
        activated = data.get("activated_directives") or []
        assert "a-directive" in activated
        assert "c-directive" in activated, (
            "cascade did not reach the second org pack in the chain; "
            f"output:\n{result.output}"
        )
        # The config-stem ID must be used, never the raw DRG bare ID -- a
        # fallback to the raw ID is exactly the ID-mapping-widening failure
        # mode T012 proves separately.
        assert "DIRECTIVE_C" not in activated

    def test_cascade_deactivate_reaches_second_pack(self, project_root: Path) -> None:
        """Symmetric coverage for ``deactivate --cascade`` (T010) over the same chain."""
        _write_two_pack_chain(project_root)

        activate = _activate(
            project_root, "--cascade", "all", "directive", "a-directive"
        )
        assert activate.exit_code == 0, activate.output
        assert "c-directive" in (_config(project_root).get("activated_directives") or [])

        result = _deactivate(
            project_root, "--cascade", "all", "directive", "a-directive"
        )
        assert result.exit_code == 0, result.output
        data = _config(project_root)
        remaining = data.get("activated_directives") or []
        assert "a-directive" not in remaining
        assert "c-directive" not in remaining, (
            f"cascade-deactivation did not reach the second org pack; output:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# T012 — revert-test: ID-mapping widening matters, not just DRG visibility
# ---------------------------------------------------------------------------


class TestIdMappingWideningNonVacuous:
    def test_two_pack_cascade_fails_without_id_mapping_org_roots(
        self, project_root: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Simulates reverting ONLY T008 (the ID-mapping half) while T009's
        DRG-visibility org-roots threading stays intact, and proves T011's
        two-pack test goes RED again.

        Monkeypatches ``activate.resolve_config_id`` to drop the ``org_roots``
        keyword before delegating -- i.e. exactly ``_drg_id_to_config_id``'s
        pre-T008 call shape (``layer_roots`` only). ``load_validated_graph``'s
        own ``org_roots=`` argument (T009) is left completely untouched, so
        the cascade engine still WALKS into pack 2 and reports
        ``DIRECTIVE_C`` as a target -- proving the DRG-visibility half alone
        is not sufficient and this test is not vacuous with respect to it.
        """
        _write_two_pack_chain(project_root)

        real_resolve_config_id = activate_mod.resolve_config_id

        def _resolve_config_id_without_org_roots(urn, *, doctrine_root, org_roots=None, layer_roots=None):
            del org_roots  # pre-T008 shape: never received the chain.
            return real_resolve_config_id(
                urn, doctrine_root=doctrine_root, layer_roots=layer_roots
            )

        monkeypatch.setattr(
            activate_mod, "resolve_config_id", _resolve_config_id_without_org_roots
        )

        result = _activate(
            project_root, "--cascade", "all", "directive", "a-directive"
        )
        assert result.exit_code == 0, result.output

        data = _config(project_root)
        activated = data.get("activated_directives") or []
        assert "c-directive" not in activated, (
            "expected the pack-2 target to FAIL to cascade-activate once ID "
            "mapping is reverted to pre-T008 (layer_roots-only) behaviour -- "
            "if this assertion fails, the two-pack test above is vacuous "
            "with respect to the ID-mapping widening.\n"
            f"output:\n{result.output}"
        )
        # The DRG-visibility half (T009) is still intact -- the cascade
        # engine still reached pack 2 and tried (and failed) to map its raw
        # DRG id back, surfaced as a cascade warning naming the raw id.
        assert "DIRECTIVE_C" in result.output, (
            "expected the raw DRG id to surface in a cascade warning, proving "
            f"the DRG walk (T009) still reached pack 2 on its own; output:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# T013 — charter list --all back-compat regression (the third consumer)
# ---------------------------------------------------------------------------


class TestListAllLayersBackCompat:
    def test_resolve_layer_roots_org_key_stays_single_path_over_a_chain(
        self, project_root: Path
    ) -> None:
        """Direct proof: over a two-pack chain, ``resolve_layer_roots``'s
        ``roots["org"]`` is still exactly pack 1's single ``Path`` -- the
        literal FR-001 AC7 assertion, established BEFORE trusting any CLI
        behaviour built on top of it.
        """
        _write_two_pack_chain(project_root)

        roots = resolve_layer_roots(project_root)
        assert roots["org"] == project_root / "org-packs" / "pack1"
        assert isinstance(roots["org"], Path)

    def test_list_all_does_not_crash_over_a_two_pack_chain(
        self, project_root: Path
    ) -> None:
        """``charter list --all`` over the same two-pack chain does not crash
        or type-error (User Story 3 AC4, FR-001 AC7) -- the exact consumer
        the original issue missed.
        """
        _write_two_pack_chain(project_root)

        result = runner.invoke(
            charter_app,
            ["list", "--repo-root", str(project_root), "--all"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output

    def test_list_all_shows_pack_one_but_not_pack_two_unchanged(
        self, project_root: Path
    ) -> None:
        """Pack 1's artifact is listed (pre-existing, single-org-root behaviour);
        pack 2's is not -- proving ``list --all``'s own display is genuinely
        UNCHANGED by this WP (widening its display to pack 2+ is explicitly
        out of scope, FR-001 AC7), not merely untested.
        """
        _write_two_pack_chain(project_root)

        result = runner.invoke(
            charter_app,
            ["list", "--repo-root", str(project_root), "--all"],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        squashed = "".join(result.output.split())
        assert "a-directive" in squashed
        assert "c-directive" not in squashed


# ---------------------------------------------------------------------------
# T014 — no-org-pack regression (FR-001 AC4)
# ---------------------------------------------------------------------------


class TestNoOrgPackRegression:
    """Built-in-only cascade behaviour is byte-for-byte unchanged (no org
    packs configured at all -- ``resolve_org_root_chain`` returns ``[]``,
    identical to the pre-fix no-org-roots-threaded call)."""

    _CASCADE_SOURCE_KIND = "agent-profile"
    _CASCADE_SOURCE_ID = "architect-alphonso"

    def test_activate_cascade_all_unaffected_by_org_roots_threading(
        self, project_root: Path
    ) -> None:
        result = _activate(
            project_root,
            "--cascade",
            "all",
            self._CASCADE_SOURCE_KIND,
            self._CASCADE_SOURCE_ID,
        )
        assert result.exit_code == 0, result.output
        data = _config(project_root)
        assert self._CASCADE_SOURCE_ID in (data.get("activated_agent_profiles") or [])
        assert data.get("activated_directives"), result.output
        assert data.get("activated_tactics"), result.output

    def test_deactivate_cascade_all_unaffected_by_org_roots_threading(
        self, project_root: Path
    ) -> None:
        activate = _activate(
            project_root,
            "--cascade",
            "all",
            self._CASCADE_SOURCE_KIND,
            self._CASCADE_SOURCE_ID,
        )
        assert activate.exit_code == 0, activate.output

        result = _deactivate(
            project_root,
            "--cascade",
            "all",
            self._CASCADE_SOURCE_KIND,
            self._CASCADE_SOURCE_ID,
        )
        assert result.exit_code == 0, result.output
        data = _config(project_root)
        assert self._CASCADE_SOURCE_ID not in (
            data.get("activated_agent_profiles") or []
        )

    def test_no_cascade_warning_unaffected_by_org_roots_threading(
        self, project_root: Path
    ) -> None:
        result = _activate(
            project_root, self._CASCADE_SOURCE_KIND, self._CASCADE_SOURCE_ID
        )
        assert result.exit_code == 0, result.output
        assert "not activated" in result.output.lower()


# ---------------------------------------------------------------------------
# T015 — referenced_but_not_cascaded names org-pack artifacts (FR-001 AC5)
# ---------------------------------------------------------------------------


class TestNoCascadeWarningNamesOrgPackArtifacts:
    def test_absent_cascade_warns_about_org_pack_requires_target(
        self, project_root: Path
    ) -> None:
        """Without ``--cascade``, an org-pack ``requires`` target is reported
        by its config-stem ID in the warning -- proving the DRG this warning
        walks now contains org-pack nodes at all (pre-fix it structurally
        could not, since org roots were never loaded here either).
        """
        pack_root = project_root / "org-packs" / "pack1"
        _write_directive(pack_root, "a-directive", "DIRECTIVE_A")
        _write_directive(pack_root, "b-directive", "DIRECTIVE_B")
        _write_graph_fragment(
            pack_root,
            "fixture.graph.yaml",
            nodes=[
                ("directive:DIRECTIVE_A", "directive"),
                ("directive:DIRECTIVE_B", "directive"),
            ],
            edges=[("directive:DIRECTIVE_A", "directive:DIRECTIVE_B", "requires")],
        )
        _write_org_pack_config(project_root, [("pack1", "org-packs/pack1")])

        result = _activate(project_root, "directive", "a-directive")
        assert result.exit_code == 0, result.output

        data = _config(project_root)
        assert "a-directive" in (data.get("activated_directives") or [])
        assert "b-directive" not in (data.get("activated_directives") or [])
        assert "b-directive" in result.output, (
            f"no-cascade warning did not name the org-pack requires target "
            f"by its config-stem ID; output:\n{result.output}"
        )
        assert "not activated" in result.output.lower()


# ---------------------------------------------------------------------------
# T016 — malformed org pack: loud failure acceptable, no degrade logic here
# ---------------------------------------------------------------------------


class TestMalformedOrgPackLoudFailure:
    def test_malformed_org_pack_does_not_silently_succeed(
        self, project_root: Path
    ) -> None:
        """A configured org pack that exists but carries no ``*.graph.yaml``
        fragment MAY raise ``DRGLoadError`` uncaught (Out of Scope / C-006 --
        #3401's territory, not duplicated here). What this test forbids is
        the OTHER outcome: silently succeeding with wrong/partial data
        (NFR-002). Either the command errors, or the cascade target is simply
        absent -- never present under a bogus ID.
        """
        pack_root = project_root / "org-packs" / "malformed-pack"
        # Artifact file present, but deliberately no *.graph.yaml at the pack
        # root -- has_graph_files(pack_root) is False.
        _write_directive(pack_root, "a-directive", "DIRECTIVE_A")
        _write_org_pack_config(project_root, [("malformed-pack", "org-packs/malformed-pack")])

        result = _activate(
            project_root,
            "--cascade",
            "all",
            "directive",
            "a-directive",
            catch_exceptions=True,
        )

        if result.exit_code == 0:
            # Graceful path is not required, but if the command didn't
            # error, it must not have silently activated a non-existent
            # cascade target under the malformed pack's authority.
            data = _config(project_root)
            activated = data.get("activated_directives") or []
            assert activated == ["a-directive"] or activated == []
        else:
            # Loud failure: an exception propagated (DRGLoadError, per
            # load_graph_or_dir's contract for a pack with no graph
            # fragment) -- acceptable per spec's Out of Scope / C-006.
            assert result.exception is not None
