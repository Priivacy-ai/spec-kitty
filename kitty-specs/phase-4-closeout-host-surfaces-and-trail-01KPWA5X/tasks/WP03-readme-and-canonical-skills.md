---
work_package_id: WP03
title: README + Canonical Skills Terminology Sweep
dependencies:
- WP01
requirement_refs:
- FR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T010
- T011
- T012
- T013
- T014
agent: "claude:sonnet-4-6:implementer:implementer"
shell_pid: "14904"
history:
- event: created
  at: '2026-04-23T05:10:00Z'
  note: Initial generation from /spec-kitty.tasks
authoritative_surface: README.md
execution_mode: code_change
owned_files:
- README.md
- .agents/skills/spec-kitty.advise/SKILL.md
- src/doctrine/skills/spec-kitty-runtime-next/SKILL.md
- tests/specify_cli/docs/test_readme_governance.py
tags: []
---

# WP03 — README + Canonical Skills Terminology Sweep

## Objective

Ship a `Governance layer` subsection in `README.md` that points new operators at the advise/ask/do surface, `docs/trail-model.md`, and `docs/host-surface-parity.md` (the last doc is created by WP05; WP03 may ship with a forward link that resolves once WP05 merges). Audit the two canonical skill packs for terminology consistency with the Phase 4 runtime vocabulary and with WP02's Mission Run rename.

This is a small, well-bounded documentation WP. No runtime code is modified.

## Context

The README currently has no explicit entry point for the Phase 4 governance layer. Operators discover advise/ask/do by reading skill packs, CHANGELOG, or `docs/trail-model.md`. Adding a README pointer satisfies FR-005 (rendering-contract consistency on the README surface) and raises first-contact discoverability.

The two canonical skill packs were updated in 3.2.0a5 and use current vocabulary. WP03's sweep is a consistency pass — most rows should be "no change needed." WP03 still earns its keep because the Mission Run rename (WP02) may surface terminology drift in the canonical skills' examples or prose.

## Branch Strategy

- **Planning base**: `main`.
- **Final merge target**: `main`.
- **Execution worktree**: allocated from `lanes.json` at implement time. WP03 depends on WP01 (inventory informs vocabulary scope) but can run in parallel with WP02 and WP04.

## Subtask Guidance

### T010 — README governance-layer subsection

**Purpose**: Add a subsection that names the governance layer and links to the two operator-facing docs.

**Steps**:
1. Open `README.md` and locate the top-level structure (likely sections like "Installation", "Usage", "Commands", "Architecture", "Contributing").
2. Add a new subsection titled **"Governance layer"** at a logical position (typically after "Usage" and before deeper architecture sections).
3. Subsection content — keep to ~10 lines:

   ```markdown
   ## Governance layer

   Spec Kitty routes, records, and projects every profile-governed invocation. Host LLMs call `spec-kitty advise`, `spec-kitty ask <profile>`, or `spec-kitty do` to open a governed invocation; Spec Kitty assembles governance context, writes a local JSONL audit trail, and additively projects to SaaS when sync is enabled. See:

   - [docs/trail-model.md](docs/trail-model.md) — the shipped trail contract (modes of work, trail tiers, correlation links, SaaS read-model policy).
   - [docs/host-surface-parity.md](docs/host-surface-parity.md) — parity matrix for the 15 supported host surfaces.
   ```

4. The `docs/host-surface-parity.md` link is a forward reference — WP05 creates the doc. Link will resolve once Tranche A is merged.

### T011 — `.agents/skills/spec-kitty.advise/SKILL.md` consistency pass

**Purpose**: Audit the Codex/Vibe canonical skill pack for Mission Run vocabulary consistency.

**Steps**:
1. Open `.agents/skills/spec-kitty.advise/SKILL.md`.
2. Search for the token `feature` (case-insensitive). Record every hit.
3. Judge each hit:
   - **Keep**: uses of `feature` that refer to code-level identifiers (JSON field names like `feature.name`, variable names in example code) — these are backend terms and stay per FR-004.
   - **Rename**: uses of `feature` that refer to the user-facing concept that is now a Mission Run (e.g., "select a feature from the dashboard", "after the feature completes").
4. If any rename target is found, update to `mission run` or `mission` as appropriate.
5. The shipped SKILL.md at baseline does not appear to need renames, but the audit is still mandatory.

**Special case**: the SKILL.md has a "When to use" table with examples. If any example refers to "implement the feature", rephrase to "implement the mission" or a more specific noun.

### T012 — `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` consistency pass

**Purpose**: Same sweep for Claude Code's canonical runtime-next skill.

**Steps**:
1. Open `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`.
2. Grep for the token `feature`. At baseline, occurrences include:
   - Line 171 (comment): `Feature-level worktree display remains obsolete.` — keep; describes historical state accurately.
   - Line 172 (comment): `No-op: feature-level worktrees are obsolete in the lane model.` — keep; historical reference.
   - Line 181: `function switchFeature(featureId)` — N/A, this is the dashboard doc; not present in the runtime-next SKILL.md. Confirm by re-reading.
   - Line 355: `--feature is a hidden deprecated alias for --mission` — keep verbatim; this is correct historical documentation of a deprecated flag.
   - Any references to "feature slug" used as a synonym for mission slug — these are now inconsistent and should be renamed to "mission slug" or "mission handle".
3. Update any inconsistent instance. Preserve historical references and flag-alias documentation.

### T013 — Snapshot test for README structure

**Purpose**: Regression guard that the Governance layer subsection stays present and its links stay valid.

**File**: `tests/specify_cli/docs/test_readme_governance.py` (new).

**Test structure**:

```python
"""WP03 — README Governance layer subsection regression tests."""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
README = REPO_ROOT / "README.md"


def test_readme_has_governance_layer_section() -> None:
    content = README.read_text()
    assert "## Governance layer" in content, (
        "README.md must contain a '## Governance layer' subsection "
        "(WP03 / FR-005)."
    )


def test_governance_section_links_to_trail_model() -> None:
    content = README.read_text()
    gov_idx = content.index("## Governance layer")
    # Next top-level section or EOF
    next_h2 = content.find("\n## ", gov_idx + 1)
    section = content[gov_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "docs/trail-model.md" in section, (
        "Governance layer subsection must link to docs/trail-model.md."
    )


def test_governance_section_links_to_host_surface_parity() -> None:
    content = README.read_text()
    gov_idx = content.index("## Governance layer")
    next_h2 = content.find("\n## ", gov_idx + 1)
    section = content[gov_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "docs/host-surface-parity.md" in section, (
        "Governance layer subsection must link to docs/host-surface-parity.md."
    )


def test_governance_section_mentions_advise_ask_do() -> None:
    content = README.read_text()
    gov_idx = content.index("## Governance layer")
    next_h2 = content.find("\n## ", gov_idx + 1)
    section = content[gov_idx : next_h2 if next_h2 != -1 else len(content)]
    assert "spec-kitty advise" in section
    assert "spec-kitty ask" in section
    assert "spec-kitty do" in section
```

### T014 — Link-target regression test for canonical skill packs

**Purpose**: Assert that references from the canonical skill packs resolve to actual files in the repo.

**Add to** `tests/specify_cli/docs/test_readme_governance.py` (or a sibling test file, at implementer's choice — owned_files covers both):

```python
import re


def test_advise_skill_references_resolve() -> None:
    """Every relative link in .agents/skills/spec-kitty.advise/SKILL.md
    resolves to an existing file in the repo."""
    skill = REPO_ROOT / ".agents/skills/spec-kitty.advise/SKILL.md"
    content = skill.read_text()
    # Match markdown links with relative targets (not http/https)
    links = re.findall(r"\]\(([^)#]+\.md)\)", content)
    for link in links:
        if link.startswith("/") or link.startswith("http"):
            continue
        target = (skill.parent / link).resolve()
        assert target.exists(), f"Broken link in spec-kitty.advise/SKILL.md: {link}"


def test_runtime_next_skill_references_resolve() -> None:
    skill = REPO_ROOT / "src/doctrine/skills/spec-kitty-runtime-next/SKILL.md"
    content = skill.read_text()
    links = re.findall(r"\]\(([^)#]+\.md)\)", content)
    for link in links:
        if link.startswith("/") or link.startswith("http"):
            continue
        target = (skill.parent / link).resolve()
        assert target.exists(), f"Broken link in runtime-next/SKILL.md: {link}"
```

If a link is known-deferred (e.g., a doc WP05 creates), mark it with an `xfail` and leave a comment referencing the creating WP.

## Definition of Done

- [ ] `README.md` contains a `## Governance layer` subsection with the prescribed content and links.
- [ ] `.agents/skills/spec-kitty.advise/SKILL.md` and `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` pass the consistency audit; any renames are applied; unchanged files are noted as "audited, no changes needed" in the commit message.
- [ ] `tests/specify_cli/docs/test_readme_governance.py` exists and passes.
- [ ] `pytest tests/specify_cli/docs/test_readme_governance.py -v` returns green.

## Risks

- **Forward link on `docs/host-surface-parity.md`**: if WP03 merges before WP05, the link is 404 temporarily. Mitigation: WP05 is the Tranche A closeout WP; README's broken link is present only between WP03 merge and WP05 merge. Acceptable under the WP-dependency model. Alternatively, WP03 can use a placeholder text ("linked after WP05") and a follow-up commit replaces the placeholder with the live link when WP05 merges. Prefer the direct link since WP03 and WP05 both merge before the mission ships.
- **Over-renaming**: an agent may aggressively rename code-level `feature` identifiers in skill-pack examples, violating FR-004. Mitigation: T011 / T012 checklist explicitly distinguishes "code-level identifiers stay" from "user-facing prose renames".

## Reviewer Guidance

Reviewer should:
- Read the new README Governance layer subsection end-to-end; verify it is accurate and concise.
- Run `git diff .agents/skills/spec-kitty.advise/SKILL.md src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` and confirm any renames are user-facing prose only.
- Run the test file and confirm the four README assertions pass plus both link-resolution tests.
- Confirm no backend identifiers were renamed in either skill-pack file.

## Activity Log

- 2026-04-23T05:36:21Z – claude:sonnet-4-6:implementer:implementer – shell_pid=14904 – Started implementation via action command
- 2026-04-23T05:39:34Z – claude:sonnet-4-6:implementer:implementer – shell_pid=14904 – README governance section added; canonical skills audit complete (2 changes in advise SKILL.md, 1 change in runtime-next SKILL.md); 6 tests pass
