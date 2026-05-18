---
work_package_id: WP09
title: ADR-8 + `CharterScope` abstraction (single-project default + monorepo seam)
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-008
- FR-009
- FR-010
- FR-011
- NFR-001
- NFR-003
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T044
- T045
- T046
- T047
- T048
- T049
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: src/charter/scope.py
execution_mode: code_change
owned_files:
- src/charter/scope.py
- src/charter/scope_router.py
- architecture/adrs/2026-05-18-1-monorepo-charter-scope.md
- tests/charter/test_charter_scope.py
- tests/integration/test_monorepo_charter_scope.py
role: implementer
tags: []
shell_pid: "2771878"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Land **Axis 2 of Slice F** (cross-repo / monorepo charter visibility, per #522 / ADR-8): finalise ADR-8 documenting the design; introduce the `CharterScope` abstraction at the charter layer; provide single-project byte-stable default (`CharterScope.default(repo_root)`) and monorepo-aware resolver (`CharterScope.resolve(repo_root, feature_dir)`); thread scope through the rendering pipeline via a NEW thin wrapper `src/charter/scope_router.py` (avoids signature change to `build_charter_context`, which is owned by WP07).

Single-project repositories (no monorepo configuration) MUST behave identically to today — the 23 `test_wp_prompt_governance_contract.py` fixtures pass unchanged (NFR-001 binding).

---

## Context

Per spec §1.2 and ADR-8 (draft):

- `CharterScope.default(repo_root)` — single-project default. `root = repo_root`, `name = None`, `config_source = "repo_root_default"`. Byte-identical to today.
- `CharterScope.resolve(repo_root, feature_dir)` — reads `.kittify/config.yaml::charter_scopes:` list (if present); walks upward from `feature_dir` and returns the nearest enclosing configured scope. If `charter_scopes:` is absent, returns `CharterScope.default(repo_root)`.

Monorepo config shape (`.kittify/config.yaml`):

```yaml
charter_scopes:
  - root: packages/auth
    name: auth
  - root: packages/web
    name: web
```

Exceptions:

- `CharterScopeConflict` — two `.kittify/charter/` directories at incompatible nesting depths configured.
- `CharterScopeNotFound` — `feature_dir` is not under any configured scope's `root`.

Per **NFR-001** binding: the 23 fixtures pass unchanged because their `build_charter_context(repo_root, feature_dir)` calls route via `CharterScope.default(repo_root)`, which produces byte-identical output to today.

References:
- [spec.md §"Scenario 2 — Monorepo charter scoping"](../spec.md)
- [spec.md FR-008..FR-011](../spec.md)
- [plan.md §1.2, §2.2, §2.10](../plan.md)
- [contracts/charter-scope-resolution.md](../contracts/charter-scope-resolution.md)
- [data-model.md §4 CharterScope](../data-model.md#4-charterscope-fr-009-fr-010)
- [atdd-coverage.md Scenario 2, AC-3](../atdd-coverage.md)

**Ownership coordination with WP07:** WP07 owns `src/charter/context.py` and intentionally does NOT change `build_charter_context`'s signature. WP09 introduces a NEW wrapper module `src/charter/scope_router.py` that resolves the scope and calls into `build_charter_context`. The prompt builder calls `scope_router.build_with_scope(...)` instead of calling `build_charter_context` directly. This avoids cross-WP file ownership conflict on `context.py`.

**Lane D dependency on Lane A:** WP09 cannot start until WP01 merges (RR-1). WP02 requires `__all__` on the new `scope.py` and `scope_router.py` modules.

---

## ATDD Discipline

Per **C-011** WP09 is the lane-opening WP for Lane D and lands its failing-first tests as its FIRST commit:

1. **Commit A (RED, T044):** `tests/integration/test_monorepo_charter_scope.py` (happy path + malformed config exception) + `tests/charter/test_charter_scope.py` (unit suite). All RED on planning base. Commit message: `covers: Scenario 2, Scenario 2 exception, AC-3 — expected GREEN at: WP09 final commit`.
2. **Commits B..F (GREEN progression, T045-T049):** ADR-8, `CharterScope` class, `scope_router.py`, prompt builder wiring, regression sweep.

ATDD anchors per [atdd-coverage.md](../atdd-coverage.md):
- Scenario 2: `test_nearest_enclosing_charter_resolves_from_deep_subdirectory`
- Scenario 2 exception: `test_malformed_monorepo_config_reports_conflicting_paths`
- AC-3: `test_default_scope_is_byte_identical_to_today` + the 23 governance-contract fixtures unchanged

---

## Subtasks

### T044 — Land failing-first monorepo scope tests + unit suite

**Files (all new):**
- `tests/integration/test_monorepo_charter_scope.py`
- `tests/charter/test_charter_scope.py`

```python
# tests/integration/test_monorepo_charter_scope.py
import pytest

def test_nearest_enclosing_charter_resolves_from_deep_subdirectory(tmp_monorepo):
    """From packages/auth/some/deep/dir/, charter status returns packages/auth charter."""
    from charter.scope import CharterScope
    feature_dir = tmp_monorepo / "packages" / "auth" / "some" / "deep" / "dir"
    scope = CharterScope.resolve(tmp_monorepo, feature_dir)
    assert scope.name == "auth"
    assert scope.root == tmp_monorepo / "packages" / "auth"

def test_malformed_monorepo_config_reports_conflicting_paths(tmp_malformed_monorepo):
    from charter.scope import CharterScope, CharterScopeConflict
    feature_dir = tmp_malformed_monorepo / "packages" / "ambiguous" / "deep"
    with pytest.raises(CharterScopeConflict) as exc_info:
        CharterScope.resolve(tmp_malformed_monorepo, feature_dir)
    assert "packages/auth" in str(exc_info.value)
    assert "packages/auth/sub" in str(exc_info.value)

def test_default_scope_is_byte_identical_to_today(tmp_single_project):
    """NFR-001: single-project repos behave identically."""
    from charter.scope import CharterScope
    scope = CharterScope.resolve(tmp_single_project, tmp_single_project)
    assert scope.config_source == "repo_root_default"
    assert scope.root == tmp_single_project
    assert scope.name is None
```

```python
# tests/charter/test_charter_scope.py
def test_default_scope_constructs_with_repo_root():
    from charter.scope import CharterScope
    scope = CharterScope.default(Path("/tmp/repo"))
    assert scope.root == Path("/tmp/repo")
    assert scope.name is None
    assert scope.config_source == "repo_root_default"

def test_resolve_without_config_returns_default(tmp_repo_without_config):
    from charter.scope import CharterScope
    scope = CharterScope.resolve(tmp_repo_without_config, tmp_repo_without_config)
    assert scope.config_source == "repo_root_default"

def test_resolve_with_config_walks_upward(tmp_monorepo):
    from charter.scope import CharterScope
    deep = tmp_monorepo / "packages" / "auth" / "src" / "internal"
    scope = CharterScope.resolve(tmp_monorepo, deep)
    assert scope.name == "auth"

def test_charter_scope_not_found_when_feature_dir_outside_any_scope(tmp_monorepo):
    from charter.scope import CharterScope, CharterScopeNotFound
    outside = tmp_monorepo / "not-a-package" / "deep"
    with pytest.raises(CharterScopeNotFound) as exc_info:
        CharterScope.resolve(tmp_monorepo, outside)
    assert "auth" in str(exc_info.value)
    assert "web" in str(exc_info.value)
```

**Validation:** `pytest tests/integration/test_monorepo_charter_scope.py tests/charter/test_charter_scope.py -v` MUST FAIL on planning base (ImportError — `charter.scope` doesn't exist yet). Commit RED.

### T045 — Author ADR-8

**File:** `architecture/adrs/2026-05-18-1-monorepo-charter-scope.md` (new)

ADR template sections:

- **Title:** Monorepo charter scope
- **Status:** Accepted
- **Context:** Why per-package charter resolution is needed (per #522 + spec §1.2)
- **Decision:** Introduce `CharterScope` abstraction at the charter layer; single-project default preserves byte-stability; monorepo config opts in.
- **Consequences:**
  - + per-package charter scoping unblocked for monorepo teams
  - + single-project repos completely unaffected (NFR-001)
  - − operators must learn the `charter_scopes:` config shape
- **Alternatives considered:** repo-root-only forever; per-mission `charter_root:` field; auto-discovery of `.kittify/charter/` directories.
- **Related:** #522, spec.md FR-008..FR-011, contracts/charter-scope-resolution.md

### T046 — Create `src/charter/scope.py`

**File:** `src/charter/scope.py` (new)

Per data-model §4:

```python
"""CharterScope abstraction (FR-009).

Resolves "which charter applies to this filesystem path" given an optional
monorepo layout. Single-project repos (no charter_scopes: config) use
CharterScope.default(repo_root), which is byte-identical to today's
repo-root-only resolution (NFR-001 binding).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

__all__ = [
    "CharterScope",
    "CharterScopeConflict",
    "CharterScopeNotFound",
]


@dataclass(frozen=True)
class CharterScope:
    root: Path
    name: str | None
    config_source: Literal["repo_root_default", "monorepo_config"]

    @classmethod
    def default(cls, repo_root: Path) -> "CharterScope":
        return cls(root=repo_root, name=None, config_source="repo_root_default")

    @classmethod
    def resolve(cls, repo_root: Path, feature_dir: Path) -> "CharterScope":
        config_path = repo_root / ".kittify" / "config.yaml"
        if not config_path.exists():
            return cls.default(repo_root)
        config = yaml.safe_load(config_path.read_text()) or {}
        scopes_config = config.get("charter_scopes", []) or []
        if not scopes_config:
            return cls.default(repo_root)
        # validate no incompatible nesting
        _validate_no_incompatible_nesting(scopes_config, repo_root)
        # walk upward from feature_dir; return nearest enclosing scope
        feature_dir_abs = feature_dir.resolve()
        matches = []
        for entry in scopes_config:
            scope_root = (repo_root / entry["root"]).resolve()
            if scope_root in feature_dir_abs.parents or scope_root == feature_dir_abs:
                matches.append((scope_root, entry.get("name")))
        if not matches:
            available = [entry["root"] for entry in scopes_config]
            raise CharterScopeNotFound(
                f"feature_dir {feature_dir} not under any configured scope. "
                f"Available scopes: {available}"
            )
        # nearest enclosing = deepest path
        matches.sort(key=lambda m: len(m[0].parts), reverse=True)
        scope_root, name = matches[0]
        return cls(root=scope_root, name=name, config_source="monorepo_config")


def _validate_no_incompatible_nesting(scopes_config, repo_root: Path) -> None:
    roots = [(repo_root / e["root"]).resolve() for e in scopes_config]
    # if two roots are at incompatible nesting depths (one ancestor of another),
    # report conflict per Scenario 2 exception
    for a in roots:
        for b in roots:
            if a == b:
                continue
            if a in b.parents:
                raise CharterScopeConflict(
                    f"Charter scope roots have incompatible nesting: "
                    f"{a} is an ancestor of {b}"
                )


class CharterScopeConflict(Exception):
    pass


class CharterScopeNotFound(Exception):
    pass
```

### T047 — Create `src/charter/scope_router.py`

**File:** `src/charter/scope_router.py` (new)

Thin wrapper that combines scope resolution + `build_charter_context` call. Avoids changing `context.py`'s signature (WP07 ownership boundary).

```python
"""Thin wrapper combining CharterScope.resolve + build_charter_context.

Routes prompt-builder calls through the scope resolver so single-project repos
use CharterScope.default(repo_root) (byte-identical to today) and monorepo
repos use the nearest-enclosing scope.
"""
from __future__ import annotations

from pathlib import Path

from charter.context import build_charter_context
from charter.scope import CharterScope

__all__ = ["build_with_scope"]


def build_with_scope(repo_root: Path, feature_dir: Path, **kwargs):
    """Resolve the scope, then build the charter context against scope.root."""
    scope = CharterScope.resolve(repo_root, feature_dir)
    # Use scope.root as the effective repo_root for build_charter_context.
    # For the single-project default, scope.root == repo_root (byte-stable).
    return build_charter_context(scope.root, feature_dir, **kwargs)
```

### T048 — Wire `prompt_builder.build_prompt` to use `scope_router`

**File:** `src/specify_cli/next/prompt_builder.py`

Locate the existing call to `build_charter_context`. Replace with:

```python
from charter.scope_router import build_with_scope

# ... inside build_prompt:
context = build_with_scope(repo_root, feature_dir, ...)
```

For single-project repos, this routes via `CharterScope.default(repo_root)` and produces byte-identical output. Verify by running the 23-fixture suite.

### T049 — Confirm AC-3 + NFR-001; regression sweep clean

```bash
pytest tests/integration/test_monorepo_charter_scope.py tests/charter/test_charter_scope.py -v
# EXPECTED: GREEN (Scenario 2 + exception + AC-3 byte-stability + unit suite)

pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v
# EXPECTED: 23/23 unchanged (NFR-001 binding)

PWHEADLESS=1 pytest tests/architectural/ -v
# EXPECTED: exit 0 (NFR-005)

pytest tests/architectural/test_layer_rules.py -v
# EXPECTED: pass unchanged (NFR-003)
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/integration/test_monorepo_charter_scope.py::test_nearest_enclosing_charter_resolves_from_deep_subdirectory` (was RED)
- ✅ `tests/integration/test_monorepo_charter_scope.py::test_malformed_monorepo_config_reports_conflicting_paths` (was RED)
- ✅ `tests/integration/test_monorepo_charter_scope.py::test_default_scope_is_byte_identical_to_today` (was RED — AC-3)
- ✅ `tests/charter/test_charter_scope.py::*` (full unit suite)
- ✅ 23 governance-contract fixtures pass unchanged (NFR-001 — verified via `pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v`)
- ✅ Full architectural sweep exit 0 (NFR-005)
- ✅ Layer-rule sweep unchanged (NFR-003)
- ✅ **`tests/contract/test_example_round_trip.py` case `charter.scope.CharterScopeConfig` flips from SKIPPED to PASSED** — WP03 cycle-2 remediation left this case skip-decorated pending the WP09 model. Landing `CharterScopeConfig` (with its real field shape + validators in `src/charter/scope.py`) MUST turn the case green. This is a binding pre-approval acceptance criterion: the reviewer rejects if the case still shows `SKIPPED` after WP09 lands.

FR coverage:

- ✅ FR-008 — ADR-8 lands documenting monorepo charter scope design
- ✅ FR-009 — `CharterScope` abstraction exists
- ✅ FR-010 — `build_with_scope` (the wrapper) accepts scope-resolved root; default is byte-identical
- ✅ FR-011 — single-project repos behave identically; 23 fixtures unchanged

AC coverage:

- ✅ AC-3 — ADR-8 lands; `CharterScope` exists; single-project repos byte-stable; monorepo unblocked

---

## Risks

1. **`build_with_scope` is called instead of `build_charter_context` in some site we missed** — would mean monorepo support is partial. Mitigation: T048 greps `rg "build_charter_context\(" src/specify_cli/` and migrates every site. The function signature didn't change, so legacy direct calls continue to work for single-project — they just don't get monorepo support. Document which sites were migrated in commit message.
2. **`CharterScope.resolve` reads `.kittify/config.yaml` on every prompt build** — perf overhead. Mitigation: NFR-002 caps regression at 20%; verify via `test_wp_prompt_build_latency.py`. If latency surfaces, add a module-level cache keyed by `repo_root`.
3. **Two scopes at the same nesting depth but different siblings** (`packages/auth` and `packages/web`) — the walker matches based on parent chain, so `feature_dir = packages/auth/x` only matches `auth`, not `web`. Mitigation: `_validate_no_incompatible_nesting` only catches ancestor-of cases, not sibling cases. Sibling cases are normal monorepo layouts; the walker correctly picks the matching one.
4. **`feature_dir` is a relative path** — `feature_dir.resolve()` may yield surprising results. Mitigation: assert `feature_dir.is_absolute()` at the top of `resolve()` or normalise explicitly via `(repo_root / feature_dir).resolve()`.
5. **WP07 (already merged at this point) changed `context.py` and the scope_router import breaks** — circular import risk. Mitigation: `scope_router.py` imports `charter.context.build_charter_context` and `charter.scope.CharterScope`; both are leaf modules. No circular dependency. Verify by `python -c "from charter.scope_router import build_with_scope"`.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/integration/test_monorepo_charter_scope.py tests/charter/test_charter_scope.py -v
# EXPECTED: ImportError (charter.scope doesn't exist)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/integration/test_monorepo_charter_scope.py tests/charter/test_charter_scope.py -v
# EXPECTED: GREEN
```

**Substantive review checks:**

- Confirm `src/charter/scope.py` declares `__all__` per WP02's convention (C-007).
- Confirm `CharterScope.default(repo_root)` returns the byte-stable single-project shape.
- Confirm `CharterScope.resolve` returns `default(repo_root)` when no `charter_scopes:` config — this is the NFR-001 byte-stability path.
- Confirm `src/charter/scope_router.py` is a thin wrapper (no business logic beyond scope resolution + delegation).
- Confirm `build_charter_context`'s signature is UNCHANGED in `src/charter/context.py` (WP07 ownership boundary).
- Confirm `prompt_builder.py` calls `build_with_scope` (not `build_charter_context` directly).
- Confirm ADR-8 lands at `architecture/adrs/2026-05-18-1-monorepo-charter-scope.md` with all required sections.
- Confirm 23 fixtures pass unchanged (NFR-001 binding — REJECT if any fixture's output differs).
- Confirm layer-rule unchanged (NFR-003).
- Confirm full architectural sweep exit 0 (NFR-005).

**FR-304 commit-message check:** T044 RED commit cites `covers: Scenario 2, Scenario 2 exception, AC-3 — expected GREEN at: WP09 final commit`.

## Activity Log

- 2026-05-18T16:52:07Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2508041 – Started implementation via action command
- 2026-05-18T18:50:57Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2734405 – Assigned agent via action command
- 2026-05-18T19:13:34Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2734405 – CharterScope abstraction (FR-008-FR-011) + ADR-8 + scope_router wrapper; CharterScopeConfig round-trip flipped SKIPPED->PASSED; NFR-001 23/23; single-project default byte-stable.
- 2026-05-18T19:14:27Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2771878 – Started review via action command
- 2026-05-18T19:32:02Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2771878 – WP09 approved: CharterScope (FR-008–FR-011) + ADR-8 + scope_router wrapper; 18 ATDD GREEN; CharterScopeConfig round-trip flipped SKIPPED→PASSED; NFR-001 23/23; single-project byte-stable. Category C allowlist verified as truly WP11-pending (no premature gate-papering). No regressions.
