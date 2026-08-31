"""CR-02 compat shim: `spec-kitty doctrine` CLI group -> canonical
`spec-kitty charter` (mission `charter-code-topology-01M152G1` S4).

Precedent for every CR shim in this mission: `charter.sync` CR-01
(`src/charter/sync.py:245-311`) -- read-both / canonical-wins / warn-once.
CR-02 is a CLI-surface variant of that shape: the legacy group still WORKS
(delegates to the exact same implementation) and warns; it is additionally
hidden from top-level `--help` so it stops advertising itself as the
front door.

`doctrine mission-type list` (activation-blind: every registered type,
regardless of activation) and `charter mission-type list` (activation-
filtered: only types active for this project) are NOT the same command --
CR-02 explicitly forbids folding one into the other. The canonical route for
the activation-blind listing is `charter mission-type list
--include-inactive`, not a straight alias.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.cli.commands.charter import charter_app
from specify_cli.cli.commands.doctrine import app as doctrine_app

runner = CliRunner()
pytestmark = [pytest.mark.unit, pytest.mark.fast]


def _write_single_activation(repo: Path, mission_type_id: str) -> None:
    """Minimal ``.kittify/config.yaml`` activating exactly one built-in type.

    Mirrors ``tests/core/test_mission_create_activation_gate.py``'s
    ``_write_activations`` helper -- the ``mission_type_activations:`` shape
    is the sole activation authority (``PackContext.activated_mission_types``,
    WP04); no git init needed, only ``resolve_layered_roster`` /
    ``existing_mission_types`` read this file.
    """
    kittify = repo / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    (kittify / "config.yaml").write_text(
        f"mission_type_activations:\n  - {mission_type_id}\n",
        encoding="utf-8",
    )


def test_doctrine_group_hidden_alias_warns() -> None:
    """`spec-kitty doctrine <x>` still runs, prints a deprecation notice,
    and no longer appears in the top-level `--help` command list."""
    top_level_help = runner.invoke(app, ["--help"])
    assert top_level_help.exit_code == 0, top_level_help.output
    assert "doctrine" not in top_level_help.output

    result = runner.invoke(app, ["doctrine", "mission-type", "list", "--json"])
    assert result.exit_code == 0, result.output
    # The deprecation notice writes to stderr (`err=True`) -- it must never
    # land inside stdout's JSON payload (Click 8.2+ separates `.stdout` from
    # the combined `.output`; see the CR-02 note on the sibling assertion in
    # tests/cli/test_charter_mission_type_commands.py).
    assert "deprecated" in result.stderr.lower()
    assert "spec-kitty charter" in result.stderr

    # Delegation: the subcommand's own real output (a JSON row list) is
    # still produced on stdout, untouched by the stderr warning.
    rows = json.loads(result.stdout)
    assert rows
    assert {"id", "source_layer", "display_name"} <= rows[0].keys()

    # Directly invoking the (still-registered, just hidden) sub-app works
    # identically -- "hidden" means absent from the parent's listing, not
    # unreachable.
    direct = runner.invoke(doctrine_app, ["mission-type", "list", "--json"])
    assert direct.exit_code == 0, direct.output


def test_charter_group_canonical_routes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`charter mission-type list --include-inactive` is the canonical
    replacement for the retired `doctrine mission-type list` -- listing
    every registered type, not only the activated subset -- WITHOUT folding
    the two distinct semantics into one (activation state is still visible
    per row)."""
    _write_single_activation(tmp_path, "software-dev")
    monkeypatch.chdir(tmp_path)

    activated_only = runner.invoke(charter_app, ["mission-type", "list", "--json"])
    assert activated_only.exit_code == 0, activated_only.output
    activated_rows = json.loads(activated_only.output)
    assert activated_rows
    assert all(row["action_sequence"] for row in activated_rows)

    everything = runner.invoke(charter_app, ["mission-type", "list", "--include-inactive", "--json"])
    assert everything.exit_code == 0, everything.output
    all_rows = json.loads(everything.output)

    # --include-inactive strictly grows the roster: every activated id is
    # still present, plus (at least) the non-activated ones.
    activated_ids = {row["id"] for row in activated_rows}
    all_ids = {row["id"] for row in all_rows}
    assert activated_ids <= all_ids
    assert len(all_rows) >= len(activated_rows)

    # The distinguishing signal CR-02 requires: a non-activated row is
    # tagged, not silently presented as if it were fully resolved.
    inactive_rows = [row for row in all_rows if row["id"] not in activated_ids]
    assert inactive_rows, "expected at least one registered-but-inactive mission type"
    for row in inactive_rows:
        assert row["activated"] is False
        assert row["action_sequence"] == "(not activated)"
    for row in all_rows:
        if row["id"] in activated_ids:
            assert row["activated"] is True
