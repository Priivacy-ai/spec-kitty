---
work_package_id: WP08
title: Org-DRG operator UX — `doctrine org init` + `doctrine org validate` + partial glossary
dependencies:
- WP07
requirement_refs:
- C-010
- FR-006
- NFR-004
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
agent: claude:opus-4-7:python-pedro:implementer
history: []
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/doctrine.py
execution_mode: code_change
owned_files:
- src/specify_cli/cli/commands/doctrine.py
- tests/cli/test_doctrine_org_commands.py
- glossary/contexts/doctrine.md  # WP08 lands `candidate` entries for org-tier terms (T042); WP12 promotes to `canonical` (T065). Both writes land in the single-lane sequence; F-OWN-01 resolution per analysis-report.md.
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Ship the org-pack operator UX (FR-006): `spec-kitty doctrine org init <path>` scaffolds a minimal org-pack skeleton (drg/fragment.yaml, org-charter.yaml, README); `spec-kitty doctrine org validate <path>` validates an org pack's structure independently of the rest of the system (DRG schema + org-charter schema). Add the Slice F org-tier domain terms to `glossary/contexts/doctrine.md` as `candidate` (WP12 promotes them to `canonical` as a pre-acceptance gate per C-010 / NFR-004).

This closes AC-2 (operator UX shipped: init + validate + doctor surfacing).

---

## Context

After WP06 (loader/merge/validator extension) and WP07 (`build_charter_context` + `doctor doctrine` integration), the org-DRG plumbing exists. WP08 is the operator-facing surface: the two new CLI subcommands that let an operator BOOTSTRAP and CHECK an org pack independently.

`doctrine org init`:

- Creates the org-pack directory at the operator-specified path.
- Scaffolds:
  - `org-charter.yaml` — minimal `OrgCharterPolicy` (already supported by Mission B).
  - `drg/fragment.yaml` — minimal `OrgDRGFragment` with one example node + one example edge, plus the FR-140 `pydantic_model:` + `expect:` frontmatter comments.
  - `README.md` — quick reference linking to spec/quickstart docs.
- Refuses to overwrite an existing pack (idempotency-friendly; instructs operator to `--force` or remove the directory first).

`doctrine org validate`:

- Validates the pack's structure by invoking the WP06 loader + schema validation.
- Reports per-file findings with file path + line number when possible.
- Exits non-zero on any schema error (operator-actionable).
- Does NOT require the pack to be configured in any project's `.kittify/config.yaml` — pure standalone validation.

Glossary partial: the 10 Slice F domain terms in spec §"Domain Language" land in `glossary/contexts/doctrine.md` as `Status: candidate`. WP12 (closing) promotes them to `Status: canonical` after the load-bearing work is in place. This split honours C-010 (canonical promotion is a pre-acceptance gate).

References:
- [spec.md FR-006, §"Domain Language"](../spec.md)
- [plan.md §2.12](../plan.md)
- [quickstart.md operator recipes for `doctrine org init`/`validate`](../quickstart.md)
- [atdd-coverage.md AC-2, AC-11](../atdd-coverage.md)

---

## ATDD Discipline

Per **C-011** WP08 lands its failing-first test as its FIRST commit:

1. **Commit A (RED, T039):** `tests/cli/test_doctrine_org_commands.py` exercises `doctrine org init` and `doctrine org validate`. Both fail on planning base (subcommands don't exist). Commit message: `covers: AC-2 (partial — init/validate side) — expected GREEN at: WP08 final commit`.
2. **Commits B..D (GREEN progression, T040-T043):** implement `org init`, implement `org validate`, add glossary candidate entries.

ATDD anchor per [atdd-coverage.md](../atdd-coverage.md):
- AC-2: `test_doctrine_org_init_scaffolds_minimal_pack` AND `test_doctor_doctrine_surfaces_org_layer_state` (the doctor side already passed in WP07; WP08 closes the init/validate side)

---

## Subtasks

### T039 — Land failing-first `tests/cli/test_doctrine_org_commands.py`

**File:** `tests/cli/test_doctrine_org_commands.py` (new)

```python
"""FR-006: operator UX for org packs (doctrine org init/validate)."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.app import app   # adjust import per actual app location


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def test_doctrine_org_init_scaffolds_minimal_pack(runner, tmp_path: Path) -> None:
    pack_path = tmp_path / "my-org-pack"
    result = runner.invoke(app, ["doctrine", "org", "init", str(pack_path)])
    assert result.exit_code == 0, result.stdout
    assert (pack_path / "org-charter.yaml").exists()
    assert (pack_path / "drg" / "fragment.yaml").exists()
    assert (pack_path / "README.md").exists()
    # The scaffolded fragment.yaml MUST carry FR-140 frontmatter
    fragment_text = (pack_path / "drg" / "fragment.yaml").read_text()
    assert "pydantic_model:" in fragment_text
    assert "expect:" in fragment_text


def test_doctrine_org_init_refuses_to_overwrite_existing(runner, tmp_path: Path) -> None:
    pack_path = tmp_path / "existing-pack"
    pack_path.mkdir()
    (pack_path / "org-charter.yaml").write_text("existing: true")
    result = runner.invoke(app, ["doctrine", "org", "init", str(pack_path)])
    assert result.exit_code != 0
    assert "exists" in result.stdout.lower() or "--force" in result.stdout.lower()


def test_doctrine_org_validate_accepts_valid_pack(runner, tmp_path: Path) -> None:
    pack_path = tmp_path / "valid-pack"
    runner.invoke(app, ["doctrine", "org", "init", str(pack_path)])
    result = runner.invoke(app, ["doctrine", "org", "validate", str(pack_path)])
    assert result.exit_code == 0


def test_doctrine_org_validate_rejects_invalid_kind(runner, tmp_path: Path) -> None:
    pack_path = tmp_path / "invalid-pack"
    pack_path.mkdir()
    (pack_path / "drg").mkdir()
    (pack_path / "drg" / "fragment.yaml").write_text(
        "pack_name: invalid\nsource_kind: local_path\nsource_ref: .\n"
        "layer_index: 1\nprovenance_marker: org\n"
        "nodes:\n  - id: foo\n    kind: not-a-real-kind\nedges: []\n"
    )
    result = runner.invoke(app, ["doctrine", "org", "validate", str(pack_path)])
    assert result.exit_code != 0
    assert "not-a-real-kind" in result.stdout or "kind" in result.stdout.lower()
```

**Validation:** `pytest tests/cli/test_doctrine_org_commands.py -v` MUST FAIL on planning base. Commit RED.

### T040 — Implement `spec-kitty doctrine org init <path>`

**File:** `src/specify_cli/cli/commands/doctrine.py`

Add a typer subcommand group `org` with two commands:

```python
import typer
from pathlib import Path

org_app = typer.Typer(help="Manage organisation-tier doctrine packs.")


@org_app.command("init")
def org_init(
    path: Path = typer.Argument(..., help="Target directory for the new org pack."),
    force: bool = typer.Option(False, "--force", help="Overwrite existing pack."),
) -> None:
    """Scaffold a minimal org pack skeleton at PATH."""
    if path.exists() and not force:
        typer.echo(f"Path {path} already exists. Use --force to overwrite.", err=True)
        raise typer.Exit(code=1)
    path.mkdir(parents=True, exist_ok=True)
    (path / "drg").mkdir(exist_ok=True)
    (path / "org-charter.yaml").write_text(_MINIMAL_ORG_CHARTER)
    (path / "drg" / "fragment.yaml").write_text(_MINIMAL_FRAGMENT)
    (path / "README.md").write_text(_MINIMAL_README)
    typer.echo(f"Scaffolded org pack at {path}")


_MINIMAL_ORG_CHARTER = """\
# Minimal org-charter (extend per your organisation's needs)
required_directives: []
required_tactics: []
"""

_MINIMAL_FRAGMENT = """\
# pydantic_model: charter.drg.OrgDRGFragment
# expect: valid
pack_name: my-org
source_kind: local_path
source_ref: .
layer_index: 1
provenance_marker: org
nodes: []
edges: []
"""

_MINIMAL_README = """\
# My Org Pack

This is a minimal organisation-tier doctrine pack. Extend `org-charter.yaml`
and `drg/fragment.yaml` per your organisation's governance needs.

See spec-kitty docs for the full org-tier reference.
"""
```

Wire `org_app` into the existing `doctrine` typer app (`doctrine_app.add_typer(org_app, name="org")`).

### T041 — Implement `spec-kitty doctrine org validate <path>`

**File:** `src/specify_cli/cli/commands/doctrine.py`

```python
@org_app.command("validate")
def org_validate(
    path: Path = typer.Argument(..., help="Org pack directory to validate."),
) -> None:
    """Validate an org pack's structure independently."""
    from charter.drg import OrgDRGFragment
    import yaml

    fragment_path = path / "drg" / "fragment.yaml"
    if not fragment_path.exists():
        typer.echo(f"Missing {fragment_path}", err=True)
        raise typer.Exit(code=1)
    try:
        data = yaml.safe_load(fragment_path.read_text())
        OrgDRGFragment.model_validate(data)
    except Exception as exc:
        typer.echo(f"Validation failed for {fragment_path}: {exc}", err=True)
        raise typer.Exit(code=1)
    # also validate org-charter.yaml if present
    charter_path = path / "org-charter.yaml"
    if charter_path.exists():
        try:
            charter_data = yaml.safe_load(charter_path.read_text())
            # validate via existing OrgCharterPolicy schema (Mission B)
            from specify_cli.doctrine.org_charter import OrgCharterPolicy
            OrgCharterPolicy.model_validate(charter_data)
        except Exception as exc:
            typer.echo(f"Validation failed for {charter_path}: {exc}", err=True)
            raise typer.Exit(code=1)
    typer.echo(f"Org pack at {path} is valid.")
```

### T042 — Glossary partial: org-tier candidate entries

**File:** `glossary/contexts/doctrine.md`

Add the 10 Slice F domain-language terms from spec §"Domain Language" as `Status: candidate` entries. WP12 promotes them to `canonical`.

```markdown
## Three-layer DRG

**Status:** candidate (promoted to canonical at mission close per C-010)
**Introduced:** slice-f-multi-context-extensibility-01KRX5C8

The Doctrine Reference Graph resolved by overlaying shipped → organisation → project tiers...

## Organisation tier (org tier / org pack)

**Status:** candidate
**Introduced:** slice-f-multi-context-extensibility-01KRX5C8

A configured layer of doctrine artefacts between shipped and project, owned by an organisation...

[... 8 more terms: CharterScope, Workflow sequence, Workflow ID, Ratchet baseline,
     Cat-7 grandfathered orphans, Symbol-level dead code, Catalog miss,
     __all__ declaration convention]
```

Each entry MUST include:

- The canonical name (matches spec §"Domain Language" verbatim).
- `Status: candidate` (WP12 changes to `canonical`).
- `Introduced: slice-f-multi-context-extensibility-01KRX5C8`.
- The definition from the spec table.
- A `Notes:` line from the spec table.

### T043 — Confirm AC-2 satisfied; regression sweep clean

```bash
pytest tests/cli/test_doctrine_org_commands.py -v
# EXPECTED: GREEN (4 tests pass; init scaffolds, refuses overwrite, validates valid, rejects invalid)

pytest tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py -v
# EXPECTED: GREEN (already from WP07; AC-2 doctor side)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)

pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
# EXPECTED: 23/23 unchanged (NFR-001)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/cli/test_doctrine_org_commands.py::test_doctrine_org_init_scaffolds_minimal_pack` (was RED on planning base)
- ✅ `tests/cli/test_doctrine_org_commands.py::test_doctrine_org_init_refuses_to_overwrite_existing`
- ✅ `tests/cli/test_doctrine_org_commands.py::test_doctrine_org_validate_accepts_valid_pack`
- ✅ `tests/cli/test_doctrine_org_commands.py::test_doctrine_org_validate_rejects_invalid_kind`
- ✅ `tests/specify_cli/cli/commands/test_doctor_doctrine_org_layer.py` (carried from WP07; AC-2 doctor side)
- ✅ Full architectural sweep exit 0 (NFR-005)
- ✅ 23 governance-contract fixtures unchanged (NFR-001)

FR coverage:

- ✅ FR-006 — `doctrine org init` scaffolds; `doctrine org validate` validates independently

AC coverage:

- ✅ AC-2 — org-pack operator UX shipped: `doctrine org init` + `doctrine org validate` + `doctor doctrine` surfaces org state (doctor side was WP07)
- ✅ Setup for AC-11 — 10 Slice F glossary terms exist as `candidate`; WP12 promotes them

---

## Risks

1. **Scaffolded `fragment.yaml` fails WP03's round-trip gate** if frontmatter isn't right. Mitigation: T040's `_MINIMAL_FRAGMENT` template includes correct `pydantic_model: charter.drg.OrgDRGFragment` + `expect: valid` frontmatter and an empty-but-valid body; verify by manually running `pytest tests/contract/test_example_round_trip.py -v` after scaffolding once.
2. **`OrgCharterPolicy.model_validate` rejects the minimal scaffolded org-charter.yaml** (Mission B may require certain fields). Mitigation: T040's `_MINIMAL_ORG_CHARTER` is the minimum that passes — verify against Mission B's `OrgCharterPolicy` defaults.
3. **`doctrine org init` overwrites a non-pack directory** by accident. Mitigation: T040 refuses if directory exists without `--force`. If directory is empty, `mkdir(exist_ok=True)` is safe.
4. **Glossary file format drift** — `glossary/contexts/doctrine.md` may have a structured format the validator enforces. Mitigation: T042 follows the existing Mission B glossary entry shape verbatim (read an existing entry, mirror it).
5. **`typer.testing.CliRunner` does not capture stderr separately from stdout** in some versions. Mitigation: T039 asserts against `result.stdout` (CliRunner merges by default). If stderr-specific assertion needed, use `subprocess.run` instead.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/cli/test_doctrine_org_commands.py -v
# EXPECTED: failures (subcommands don't exist)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/cli/test_doctrine_org_commands.py -v
# EXPECTED: GREEN (4 tests pass)
```

**Substantive review checks:**

- Confirm `spec-kitty doctrine org init <path>` scaffolds the three required files (`org-charter.yaml`, `drg/fragment.yaml`, `README.md`).
- Confirm scaffolded `fragment.yaml` carries `pydantic_model:` + `expect:` frontmatter (so WP03's round-trip gate accepts it).
- Confirm `spec-kitty doctrine org validate <path>` exits non-zero on schema errors and prints actionable messages.
- Confirm `glossary/contexts/doctrine.md` carries 10 new entries with `Status: candidate` and `Introduced: slice-f-multi-context-extensibility-01KRX5C8`.
- Confirm NO glossary entry is set to `canonical` here (C-010 binds — promotion is a pre-acceptance gate done in WP12).
- Confirm `doctrine.py` declares `__all__` per WP02's convention.
- Confirm full architectural sweep exit 0 (NFR-005).

**FR-304 commit-message check:** T039 RED commit cites `covers: AC-2 (partial — init/validate side) — expected GREEN at: WP08 final commit`.
