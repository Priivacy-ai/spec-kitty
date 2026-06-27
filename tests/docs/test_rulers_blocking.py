"""Ruler-blocking regression gate (WP14 / FR-011, C-005, NFR-006, SC-005).

Mission B flips Mission A's report-only docs rulers to **blocking**. This module
is the per-class RED proof: for every violation class the gate must go RED
**independently**, exercised through the **same CLI invocation path the wired
``.github/workflows/docs-freshness.yml`` uses** — a script-level RED the CI
wiring never calls is the gate-silent-death failure mode (WP14 DoD).

The non-uniform flip:

* **R1 anti-sprawl ratchet** and **R2 related-validator** flip via their wired
  ``--strict`` flag (the workflow now passes it). Each detector class reds on its
  own seeded violation, one class per test so a single always-RED gate cannot
  mask the others.
* **R3 lockfile drift** flips via *code*: the ``INVENTORY-LOCKFILE-DRIFT`` finding
  is now ``error`` severity (was ``warning``) and the check runs default-on, so a
  drifted inventory reds ``check_docs_freshness`` — the aggregate exit keys off
  ``any(f.severity == "error")``. The ``severity == "error"`` assertion is the
  red-first teeth: it fails against the pre-flip ``warning`` code.
* **Description gate** (NFR-003) and the **body-link gate** (WP18) are wired
  blocking too; each reds on its seeded violation.

Each clean-tree counterpart asserts the gate is **green** on a correct tree, so
the RED is attributable to the seeded violation and not a perpetually-red gate.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Final

import pytest

_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.docs import anti_sprawl_ratchet as ratchet  # noqa: E402
from scripts.docs import check_docs_freshness as orchestrator  # noqa: E402
from scripts.docs import description_length_check as desc_gate  # noqa: E402
from scripts.docs import related_validator  # noqa: E402
from scripts.docs import relative_link_fixer  # noqa: E402

pytestmark = pytest.mark.architectural

_GOOD_ADR: Final[str] = (
    "---\ntitle: Example Decision\nstatus: Accepted\ndate: 2026-06-27\n---\n\n"
    "# Example Decision\n\nBody.\n"
)
_GOOD_DESC: Final[str] = "x" * 100


def _write(path: Path, text: str = "# stub\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _build_clean_tree(root: Path) -> Path:
    """A single-root 13-section Common Docs tree with zero ruler violations."""
    docs = root / "docs"
    _write(docs / "index.md")
    for section in ratchet.CANONICAL_SECTIONS:
        if section == "index":
            continue
        _write(docs / section / "index.md")
    _write(docs / "adr" / "3.x" / "2026-06-27-1-example.md", _GOOD_ADR)
    return root


# --------------------------------------------------------------------------- #
# R1 — anti-sprawl ratchet: each detector class reds independently under --strict
# --------------------------------------------------------------------------- #


def test_r1_clean_tree_is_green_under_strict(tmp_path: Path) -> None:
    root = _build_clean_tree(tmp_path / "repo")
    assert ratchet.main(["--root", str(root), "--strict"]) == 0


def test_r1_second_doc_root_reds(tmp_path: Path) -> None:
    root = _build_clean_tree(tmp_path / "repo")
    _write(root / "handbook" / "index.md")  # a competing docs root marker
    assert ratchet.main(["--root", str(root), "--strict"]) == 1


def test_r1_missing_section_index_reds(tmp_path: Path) -> None:
    root = _build_clean_tree(tmp_path / "repo")
    (root / "docs" / "orphaned").mkdir()  # section dir without index.md
    assert ratchet.main(["--root", str(root), "--strict"]) == 1


def test_r1_unfrontmattered_adr_reds(tmp_path: Path) -> None:
    root = _build_clean_tree(tmp_path / "repo")
    _write(root / "docs" / "adr" / "3.x" / "bad.md", "# ADR without frontmatter\n")
    assert ratchet.main(["--root", str(root), "--strict"]) == 1


# --------------------------------------------------------------------------- #
# R2 — related-validator: a dangling related: edge reds under --strict
# --------------------------------------------------------------------------- #


def test_r2_clean_tree_is_green_under_strict(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(root / "docs" / "index.md")
    _write(root / "docs" / "target.md")
    _write(
        root / "docs" / "a.md",
        "---\nrelated:\n- docs/target.md\n---\n# A\n",
    )
    assert (
        related_validator.main(["--docs-root", str(root / "docs"), "--repo-root", str(root), "--strict"])
        == 0
    )


def test_r2_dangling_related_edge_reds(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(root / "docs" / "index.md")
    _write(
        root / "docs" / "a.md",
        "---\nrelated:\n- docs/does-not-exist.md\n---\n# A\n",
    )
    assert (
        related_validator.main(["--docs-root", str(root / "docs"), "--repo-root", str(root), "--strict"])
        == 1
    )


# --------------------------------------------------------------------------- #
# R3 — lockfile drift: error severity reds the orchestrator (the wired path)
# --------------------------------------------------------------------------- #


def _stub_external_subchecks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub leakage + CLI-reference sub-checks to clean so R3 is the only signal."""

    def _clean_leakage(argv: list[str]) -> int:
        Path(argv[argv.index("--report") + 1]).write_text(
            json.dumps({"inventory_rows_count": 0, "findings": [], "exit_code": 0}),
            encoding="utf-8",
        )
        return 0

    def _clean_ref(argv: list[str]) -> int:
        Path(argv[argv.index("--report") + 1]).write_text(
            json.dumps({"findings": []}), encoding="utf-8"
        )
        return 0

    monkeypatch.setattr(orchestrator, "_invoke_version_leakage", _clean_leakage)
    monkeypatch.setattr(orchestrator, "_invoke_cli_reference_freshness", _clean_ref)


def _stage_lockfile_workspace(root: Path, *, drift: bool) -> Path:
    """Stage docs/ + an inventory lockfile; when ``drift`` the two disagree."""
    from scripts.docs import inventory_lockfile as lockfile

    docs = root / "docs"
    _write(docs / "index.md", "---\ntype: how-to\n---\n# Home\n")
    _write(docs / "guides" / "g.md", "---\ntype: how-to\n---\n# Guide\n")
    inventory = root / "inventory.yaml"
    inventory.write_text(
        lockfile.render_lockfile(lockfile.generate_inventory(docs, repo_root=root)),
        encoding="utf-8",
    )
    if drift:
        # Tamper a page's frontmatter so the regeneration != committed lockfile.
        (docs / "guides" / "g.md").write_text(
            "---\ntype: reference\n---\n# Guide\n", encoding="utf-8"
        )
    return root


def test_r3_clean_lockfile_is_green(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _stage_lockfile_workspace(tmp_path / "repo", drift=False)
    _stub_external_subchecks(monkeypatch)
    monkeypatch.setattr(orchestrator, "_SAAS_SYNC_PRESET", True)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    (root / "ref.md").write_text("# ref\n", encoding="utf-8")
    (root / "agent.md").write_text("# agent\n", encoding="utf-8")
    # Run from the repo root with relative paths, exactly as the CI workflow does
    # (the inventory rows are repo-relative, e.g. ``docs/index.md``).
    monkeypatch.chdir(root)
    rc = orchestrator.main(
        [
            "--inventory", "inventory.yaml",
            "--docs-root", "docs",
            "--reference", "ref.md",
            "--agent-reference", "agent.md",
            "--link-check", "none",
            "--ci",
        ]
    )
    assert rc == 0


def test_r3_lockfile_drift_reds_with_error_severity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _stage_lockfile_workspace(tmp_path / "repo", drift=True)
    findings = orchestrator._check_inventory_lockfile_drift(
        root / "inventory.yaml", root / "docs"
    )
    # The flip teeth: drift is reported AND it is error-severity (red-first —
    # fails against the pre-flip warning code).
    assert findings, "expected lockfile drift findings"
    assert all(f.rule_id == "INVENTORY-LOCKFILE-DRIFT" for f in findings)
    assert all(f.severity == "error" for f in findings)

    # And it reds the orchestrator the workflow invokes.
    _stub_external_subchecks(monkeypatch)
    monkeypatch.setattr(orchestrator, "_SAAS_SYNC_PRESET", True)
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    (root / "ref.md").write_text("# ref\n", encoding="utf-8")
    (root / "agent.md").write_text("# agent\n", encoding="utf-8")
    monkeypatch.chdir(root)
    rc = orchestrator.main(
        [
            "--inventory", "inventory.yaml",
            "--docs-root", "docs",
            "--reference", "ref.md",
            "--agent-reference", "agent.md",
            "--link-check", "none",
            "--ci",
        ]
    )
    assert rc == 1


# --------------------------------------------------------------------------- #
# Description gate (NFR-003) + body-link gate (WP18): blocking on their classes
# --------------------------------------------------------------------------- #


def test_description_gate_reds_on_out_of_band(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(
        root / "docs" / "short.md",
        f'---\ndescription: "{"x" * 49}"\n---\n# Short\n',
    )
    assert (
        desc_gate.main(["--docs-root", str(root / "docs"), "--repo-root", str(root), "--strict"])
        == 1
    )


def test_description_gate_green_on_in_band(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(
        root / "docs" / "ok.md",
        f'---\ndescription: "{_GOOD_DESC}"\n---\n# OK\n',
    )
    assert (
        desc_gate.main(["--docs-root", str(root / "docs"), "--repo-root", str(root), "--strict"])
        == 0
    )


def test_description_gate_excludes_content_invariant_adrs(tmp_path: Path) -> None:
    """ADR bodies carry no description (C-002) and must not red the gate."""
    root = tmp_path / "repo"
    _write(root / "docs" / "adr" / "3.x" / "2026-06-27-1-x.md", _GOOD_ADR)
    assert (
        desc_gate.main(["--docs-root", str(root / "docs"), "--repo-root", str(root), "--strict"])
        == 0
    )


def test_body_link_gate_reds_on_dead_link(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(root / "docs" / "index.md", "# Home\n")
    _write(root / "docs" / "page.md", "See [gone](../missing/none.md).\n")
    assert relative_link_fixer.main(["--check", "--repo-root", str(root)]) == 1


def test_body_link_gate_green_when_links_resolve(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    _write(root / "docs" / "index.md", "# Home\n")
    _write(root / "docs" / "target.md", "# Target\n")
    _write(root / "docs" / "page.md", "See [target](target.md).\n")
    assert relative_link_fixer.main(["--check", "--repo-root", str(root)]) == 0
