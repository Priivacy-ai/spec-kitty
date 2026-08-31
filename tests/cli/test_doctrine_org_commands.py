"""CLI tests for ``spec-kitty doctrine org init`` and ``doctrine org validate``.

WP08 / T039 RED tests.  All four tests FAIL on the planning base because the
``org`` subapp does not exist in ``doctrine.py`` yet.

Owner: ``src/specify_cli/cli/commands/doctrine.py``
Mission: slice-f-multi-context-extensibility-01KRX5C8
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands.doctrine import app

runner = CliRunner()

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T039-a: doctrine org init scaffolds a minimal org pack skeleton
# ---------------------------------------------------------------------------


def test_doctrine_org_init_scaffolds_minimal_pack(tmp_path: Path) -> None:
    """``doctrine org init <path>`` creates the three required skeleton files.

    Expected layout::

        <path>/
          org-charter.yaml
          drg/
            fragment.yaml   # carries pydantic_model: + expect: frontmatter
          README.md
    """
    pack_dir = tmp_path / "my-org-pack"

    result = runner.invoke(app, ["org", "init", str(pack_dir)])

    assert result.exit_code == 0, result.output

    # org-charter.yaml must exist and parse as OrgCharterPolicy
    org_charter = pack_dir / "org-charter.yaml"
    assert org_charter.exists(), "org-charter.yaml was not created"

    from ruamel.yaml import YAML

    data = YAML(typ="safe").load(org_charter.read_text(encoding="utf-8"))
    assert data is not None
    from specify_cli.doctrine.org_charter import OrgCharterPolicy

    OrgCharterPolicy.model_validate(data)  # must not raise

    # drg/fragment.yaml must exist and parse as OrgDRGFragment
    fragment = pack_dir / "drg" / "fragment.yaml"
    assert fragment.exists(), "drg/fragment.yaml was not created"

    frag_text = fragment.read_text(encoding="utf-8")
    # Must carry pydantic_model: + expect: frontmatter (FR-140 round-trip)
    assert "# pydantic_model:" in frag_text, "fragment.yaml missing pydantic_model frontmatter"
    assert "# expect: valid" in frag_text, "fragment.yaml missing expect: valid frontmatter"

    # strip frontmatter comment lines before parsing
    payload_lines = [
        line for line in frag_text.splitlines()
        if not line.strip().startswith("#")
    ]
    payload_text = "\n".join(payload_lines)
    frag_data = YAML(typ="safe").load(payload_text)
    assert frag_data is not None
    from charter.drg import OrgDRGFragment

    OrgDRGFragment.model_validate(frag_data)  # must not raise

    # README.md must exist
    readme = pack_dir / "README.md"
    assert readme.exists(), "README.md was not created"


# ---------------------------------------------------------------------------
# T039-b: doctrine org init refuses to overwrite an existing pack
# ---------------------------------------------------------------------------


def test_doctrine_org_init_refuses_to_overwrite_existing(tmp_path: Path) -> None:
    """``doctrine org init`` exits non-zero when the target dir already exists
    (without ``--force``).
    """
    pack_dir = tmp_path / "existing-pack"
    pack_dir.mkdir()

    result = runner.invoke(app, ["org", "init", str(pack_dir)])

    assert result.exit_code != 0, "Expected non-zero exit when target dir exists"
    assert "already exists" in result.output.lower() or "exists" in result.output.lower()


# ---------------------------------------------------------------------------
# T039-c: doctrine org validate accepts a valid pack
# ---------------------------------------------------------------------------


def test_doctrine_org_validate_accepts_valid_pack(tmp_path: Path) -> None:
    """``doctrine org validate <path>`` exits 0 for a pack that passes schema checks."""
    pack_dir = tmp_path / "valid-pack"

    # Scaffold a pack using the init command so we always test against
    # canonically generated content.
    init_result = runner.invoke(app, ["org", "init", str(pack_dir)])
    assert init_result.exit_code == 0, f"init failed: {init_result.output}"

    result = runner.invoke(app, ["org", "validate", str(pack_dir)])

    assert result.exit_code == 0, result.output


# ---------------------------------------------------------------------------
# T039-d: doctrine org validate rejects a pack with invalid kind in fragment
# ---------------------------------------------------------------------------


def test_doctrine_org_validate_rejects_invalid_kind(tmp_path: Path) -> None:
    """``doctrine org validate`` exits non-zero when fragment.yaml has an
    unknown ``kind`` value (not in the 8-kind canonical set).
    """
    pack_dir = tmp_path / "bad-pack"
    pack_dir.mkdir()

    # Write a minimal org-charter.yaml
    (pack_dir / "org-charter.yaml").write_text(
        dedent(
            """\
            schema_version: "1"
            org_name: test-org
            """
        ),
        encoding="utf-8",
    )

    # Write a drg/ fragment with an unknown kind
    drg_dir = pack_dir / "drg"
    drg_dir.mkdir()
    (drg_dir / "fragment.yaml").write_text(
        dedent(
            f"""\
            pack_name: bad-pack
            source_kind: local_path
            source_ref: {pack_dir}
            layer_index: 1
            provenance_marker: org
            nodes:
              - id: bad-node
                kind: not_a_real_kind
                title: Bad node
            edges: []
            """
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["org", "validate", str(pack_dir)])

    assert result.exit_code != 0, "Expected non-zero exit for invalid kind"


# ---------------------------------------------------------------------------
# FR-004 / AC-7 (operator ruling #2, reviews/plan.ruling.md): org_validate's
# internal validate_pack(...) call carries an explicit check_drg_root=True —
# no carve-out. Two cases: (a) a parameter-value assertion mirroring T016's
# assembler assertion (opposite value), and (b) a brand-new positive-fire
# fixture proving `doctrine org validate` now catches the destructive shape
# the dropped carve-out used to suppress.
# ---------------------------------------------------------------------------


def test_doctrine_org_validate_calls_validate_pack_with_check_drg_root_true(
    tmp_path: Path,
) -> None:
    """AC-7(a): ``org_validate``'s internal ``validate_pack(...)`` call passes
    ``check_drg_root=True`` explicitly, not relying on ``validate_pack``'s own
    default. ``validate_pack`` is not bound at module scope in ``doctrine.py``
    — ``org_validate`` does a lazy, function-local import re-run on every
    invocation, so the correct patch target is the source location,
    ``specify_cli.doctrine.pack_validator.validate_pack``.

    Before this WP, ``validate_pack`` has no ``check_drg_root`` keyword
    parameter at all, so asserting it was passed with that value fails.
    """
    from unittest.mock import patch

    from specify_cli.doctrine.pack_validator import ValidationResult

    pack_dir = tmp_path / "valid-pack"
    init_result = runner.invoke(app, ["org", "init", str(pack_dir)])
    assert init_result.exit_code == 0, f"init failed: {init_result.output}"

    with patch(
        "specify_cli.doctrine.pack_validator.validate_pack",
        return_value=ValidationResult(ok=True),
    ) as mock_validate:
        result = runner.invoke(app, ["org", "validate", str(pack_dir)])

    assert result.exit_code == 0, result.output
    mock_validate.assert_called_once_with(pack_dir, check_drg_root=True)


def test_doctrine_org_validate_catches_drg_only_fragment_after_init(
    tmp_path: Path,
) -> None:
    """AC-7(b) — new positive-fire fixture, no precedent in the suite today:
    a pack scaffolded by ``org init``, then given a real
    ``drg/*.graph.yaml`` fragment and no pack-root ``*.graph.yaml``, produces
    the ``drg_root_graph_missing`` diagnostic through ``doctrine org
    validate``. This is the destructive shape the dropped ``org_validate``
    carve-out used to suppress — the whole point of dropping it (operator
    ruling #2).

    Before this WP, no ``drg_root_graph_missing`` diagnostic exists at all,
    so ``doctrine org validate`` exits 0 for this fixture — this is the
    load-bearing proof that the shape was genuinely unguarded before this WP.
    """
    pack_dir = tmp_path / "stub-then-real-drg"
    init_result = runner.invoke(app, ["org", "init", str(pack_dir)])
    assert init_result.exit_code == 0, f"init failed: {init_result.output}"

    # Add a REAL drg/*.graph.yaml fragment (the scaffold's own
    # drg/fragment.yaml never matches this glob) with no pack-root graph.
    (pack_dir / "drg" / "010-security.graph.yaml").write_text(
        dedent(
            """\
            schema_version: "1.0"
            generated_at: STATIC
            generated_by: test
            nodes: []
            edges: []
            """
        ),
        encoding="utf-8",
    )
    assert not sorted(pack_dir.glob("*.graph.yaml"))

    result = runner.invoke(app, ["org", "validate", str(pack_dir)])

    assert result.exit_code != 0, result.output
    assert "drg_root_graph_missing" in result.output
