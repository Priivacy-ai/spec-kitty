"""Red-first tests for the Contract Registry loader/validator (#2441 / FR-001..004).

The load-bearing contracts pinned here:

* the seeded manifest (``docs/contracts/contract-registry.yaml``) loads + validates,
  yielding BOTH ``retired_literal`` records with their reconstructed literals and
  discovered-then-frozen consumer sets (FR-004);
* a **malformed** record fails validation (structural gate, FR-002);
* a **``file:line``-anchored** record fails validation TWO ways — a positional
  ``file:``/``line:`` field, and a string value shaped like ``path.py:42``
  (NFR-003 / DIR-041). Each negative carries a positive control so it cannot pass
  vacuously.

Forbidden legacy terms are constructed from fragments (``"cere" + "mony"``) so
this test file — which ``test_no_legacy_terminology.py`` scans under ``tests/`` —
does not flag itself, exactly as that sweep does.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest

from specify_cli.contracts.anchoring import is_file_line_anchor
from specify_cli.contracts.registry import (
    ContractRegistryReport,
    ContractRegistrySchemaError,
    check_contract_registry,
    load_registry,
    resolve_contract_registry_path,
    validate_registry,
)

pytestmark = [pytest.mark.fast]


# The two forbidden terms, built from fragments so this file is not self-flagged.
_TERM_PROCESS_NOUN = "cere" + "mony"
_TERM_HYPHENATED = "status" + "-writing"


def _repo_root() -> Path:
    """Resolve the repo root by walking up to a ``.kittify/`` marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _well_formed_record() -> dict[str, Any]:
    """A minimal, schema-valid ``retired_literal`` record (the positive control)."""
    return {
        "id": "test.synthetic-literal",
        "kind": "retired_literal",
        "anchor": {"literals": [{"value": "synthetic_retired_token"}]},
        "status": "retired",
        "owner": "#2441",
        "replaced_by": "specify_cli.something.canonical",
        "retirement": {
            "introduced_in": "3.0.0",
            "removal_target": "3.4.0",
            "tracker_issue": "#2077",
        },
        "consumers": {"scan_roots": ["src"], "exemptions": []},
        "verification": {"enforcement": "advisory"},
    }


# ---------------------------------------------------------------------------
# FR-004 — the seeded manifest loads + validates with both records
# ---------------------------------------------------------------------------


def test_seeded_registry_loads_and_validates() -> None:
    records = load_registry(_repo_root())
    by_id = {r.id: r for r in records}
    assert "terminology.legacy-status-commit-terms" in by_id
    assert "paths.legacy-home-literals-cli-tree" in by_id
    for record in records:
        assert record.kind == "retired_literal"
        assert record.status == "retired"
        # Advisory + additive: seeding enforces nothing new (NFR-002 / NFR-004).
        assert record.verification.enforcement == "advisory"


def test_terminology_record_reconstructs_literals_and_consumer_set() -> None:
    record = {r.id: r for r in load_registry(_repo_root())}[
        "terminology.legacy-status-commit-terms"
    ]
    # Fragments are joined by the loader back to the retired terms.
    assert set(record.anchor.literals) == {_TERM_PROCESS_NOUN, _TERM_HYPHENATED}
    assert record.anchor.symbol is None
    # Consumer set transcribed from test_no_legacy_terminology.py.
    assert record.consumers.scan_roots == ("src", "tests", "docs")
    assert "docs/adr/" in record.consumers.exemptions
    assert "kitty-specs/" in record.consumers.exemptions


def test_path_record_literals_and_scan_scope() -> None:
    record = {r.id: r for r in load_registry(_repo_root())}[
        "paths.legacy-home-literals-cli-tree"
    ]
    assert set(record.anchor.literals) == {"~/.kittify", "~/.spec-kitty"}
    # The CLI-tree literal-grep half scopes to the command tree only.
    assert record.consumers.scan_roots == ("src/specify_cli/cli",)


def test_check_contract_registry_reports_both_records() -> None:
    report = check_contract_registry(_repo_root())
    assert isinstance(report, ContractRegistryReport)
    assert report.record_count == 2
    assert report.advisory_count == 2
    assert report.enforcing_count == 0
    assert report.registry_path == resolve_contract_registry_path(_repo_root())


# ---------------------------------------------------------------------------
# FR-002 — a malformed record fails validation (positive control first)
# ---------------------------------------------------------------------------


def test_well_formed_record_passes_validation() -> None:
    # Positive control: the negatives below cannot pass vacuously.
    validate_registry({"contracts": [_well_formed_record()]})


def test_missing_required_field_fails_validation() -> None:
    record = _well_formed_record()
    del record["retirement"]
    with pytest.raises(ContractRegistrySchemaError) as exc_info:
        validate_registry({"contracts": [record]})
    assert any("retirement" in e for e in exc_info.value.errors)


def test_out_of_range_kind_fails_validation() -> None:
    record = _well_formed_record()
    record["kind"] = "not_a_real_kind"
    with pytest.raises(ContractRegistrySchemaError) as exc_info:
        validate_registry({"contracts": [record]})
    assert any("kind" in e for e in exc_info.value.errors)


def test_retired_literal_without_literals_fails_validation() -> None:
    record = _well_formed_record()
    record["anchor"] = {"literals": []}
    with pytest.raises(ContractRegistrySchemaError):
        validate_registry({"contracts": [record]})


# ---------------------------------------------------------------------------
# NFR-003 / DIR-041 — a ``file:line``-anchored record fails validation
# ---------------------------------------------------------------------------


def test_positional_file_line_field_is_rejected() -> None:
    record = _well_formed_record()
    # A positional anchor via forbidden field names — the rot the registry
    # exists to REPLACE must never be re-introduced.
    record["anchor"] = {"file": "src/specify_cli/foo.py", "line": 42}
    with pytest.raises(ContractRegistrySchemaError) as exc_info:
        validate_registry({"contracts": [record]})
    joined = "\n".join(exc_info.value.errors)
    assert "file:line" in joined or "DIR-041" in joined


def test_file_line_string_value_is_rejected() -> None:
    record = _well_formed_record()
    # A literal value that IS a positional file:line string.
    record["anchor"] = {"literals": [{"value": "src/specify_cli/foo.py:42"}]}
    with pytest.raises(ContractRegistrySchemaError) as exc_info:
        validate_registry({"contracts": [record]})
    assert any("file:line" in e or "DIR-041" in e for e in exc_info.value.errors)


def test_file_line_anchor_detector_positive_and_negative() -> None:
    # Positive: real positional anchors.
    assert is_file_line_anchor("src/specify_cli/foo.py:42")
    assert is_file_line_anchor("tests/architectural/_ratchet_keys.py:229")
    assert is_file_line_anchor("docs/status-model.md:7")
    # Negative: legitimate content anchors and metadata must NOT be flagged.
    assert not is_file_line_anchor("~/.kittify")
    assert not is_file_line_anchor("~/.spec-kitty")
    assert not is_file_line_anchor("specify_cli.status.emit.emit_status_transition")
    assert not is_file_line_anchor("3.4.0")
    assert not is_file_line_anchor("#2077")
    assert not is_file_line_anchor("status commit")


# ---------------------------------------------------------------------------
# Loader edge cases (mirrors compat/registry.py behaviour)
# ---------------------------------------------------------------------------


def test_missing_manifest_raises_file_not_found(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_registry(tmp_path)


def test_malformed_manifest_on_disk_raises_schema_error(tmp_path: Path) -> None:
    registry_path = resolve_contract_registry_path(tmp_path)
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    # A record with a forbidden positional field written to disk.
    bad = copy.deepcopy(_well_formed_record())
    bad["anchor"] = {"file": "x.py", "line": 1}
    import ruamel.yaml

    yaml = ruamel.yaml.YAML(typ="safe")
    with registry_path.open("w") as fp:
        yaml.dump({"contracts": [bad]}, fp)
    with pytest.raises(ContractRegistrySchemaError):
        check_contract_registry(tmp_path)
