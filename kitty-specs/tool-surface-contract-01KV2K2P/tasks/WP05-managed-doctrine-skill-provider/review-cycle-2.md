---
affected_files: []
cycle_number: 2
mission_slug: tool-surface-contract-01KV2K2P
reproduction_command:
reviewed_at: '2026-06-14T11:15:20Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP05
review_artifact_override_at: "2026-06-14T11:28:40Z"
review_artifact_override_actor: "operator"
review_artifact_override_wp_id: "WP05"
review_artifact_override_reason: "Cycle-1 re-review PASSED; supersedes prior review-cycle-2.md rejection. Default --fix now binds verifier.repair_skills (skills.installer has no repair_skills). LIVE no-stub: doctor tool-surfaces --kind doctrine-skill --fix --json on real fixture (5 installed codex doctrine skills, one deleted) -> exit 0, NO AttributeError, deleted skill RESTORED, repair.repaired=[codex.doctrine_skill.SKILL.md] failed=[]. Re-breaking binding to skill_installer made both regression tests FAIL with the original AttributeError; reverted clean. Output conforms to schema (fix+probe); provider=managed_skills. ruff/mypy --strict clean, 101 tool_surface tests pass, no suppressions/feature aliases. --force used only for the known spurious base-ref preflight (tree clean, WP05 commit present, lane ahead of real base kitty/mission-tool-surface-contract-01KV2K2P)."
---

# WP05 Review — Cycle 1: REJECTED

## Verdict: REJECTED (one P0 blocking defect)

The provider is well-structured and delegates correctly in principle, mypy/ruff
are clean, and the read-only `--json` path is fully wired. **However, the live
`--fix` repair path is broken against any real project**: the default installer
collaborator is bound to the wrong module, so `repair()` raises an uncaught
`AttributeError`. The 17 tests pass only because every repair test injects a
`_StubInstaller` synthetic fixture that masks the broken real wiring.

---

## P0 (BLOCKING) — `--fix` crashes on real projects: wrong installer module wired

**File:** `src/specify_cli/tool_surface/providers/managed_skills.py:30-31, 132-134, 283`

The provider imports two modules and binds `self._installer` to the **installer**
module by default:

```python
from specify_cli.skills import installer as skill_installer   # line 30
from specify_cli.skills import verifier as skill_verifier     # line 31
...
self._installer: _InstallerProto = (
    installer if installer is not None else skill_installer   # line 132-134  <-- WRONG MODULE
)
```

and then calls (line 283):

```python
repaired, failed = self._installer.repair_skills(project_root, verify_result, registry)
```

But `repair_skills(project_path, verify_result, registry) -> tuple[int, int]`
**does not exist in `specify_cli.skills.installer`**. It lives in
`specify_cli.skills.verifier` (verifier.py:82, also re-exported from
`specify_cli.skills.__init__`). The `installer` module exposes only
`install_all_skills` / `install_skills_for_agent`.

### Live reproduction (CLI `--fix`, the exact path the WP prompt's T026 DoD requires)

Built a fixture (`.kittify/config.yaml` with `codex`, a `skills-manifest.json`
entry, then deleted the skill file so it is "missing") and ran the production
service path the CLI uses:

```
run_tool_surfaces(Path(fixture), ['codex'], fix=True)
```

Result — uncaught crash, full traceback through the live routing chain:

```
File ".../tool_surface/repair.py", line 123, in _apply
    result = provider.repair(project_root, statuses, dry_run=dry_run)
File ".../tool_surface/providers/managed_skills.py", line 266, in repair
    return self._delegate_repair(project_root, ids)
File ".../tool_surface/providers/managed_skills.py", line 283, in _delegate_repair
    repaired, failed = self._installer.repair_skills(...)
AttributeError: module 'specify_cli.skills.installer' has no attribute 'repair_skills'
```

Note: the provider's `except OSError` on line 286 does **not** catch this —
`AttributeError` propagates and crashes `spec-kitty doctor tool-surfaces --fix`.

### Why the test suite did not catch it (synthetic-fixture masking)

Every repair test (`test_managed_skills_repair_calls_installer`,
`_reports_installer_failures`, `_skips_when_verifier_clean`,
`_fails_without_registry`) constructs `ManagedSkillsProvider(installer=_StubInstaller(...))`,
and `_StubInstaller` defines a `repair_skills` method. No test exercises the
**default** collaborator (`installer=None`), so the broken real wiring is never
executed. This is the anti-pattern checklist item #2 (synthetic fixture) firing:
delete the default-binding line and the tests still pass, so the real `--fix`
path is effectively untested.

### Required fix

Bind the default repair collaborator to the module that actually owns
`repair_skills`. Either:

- Point the default installer at the verifier module:
  `installer if installer is not None else skill_verifier`
  (verifier owns both `verify_installed_skills` and `repair_skills`), **or**
- Import `repair_skills` from `specify_cli.skills.verifier` (or the
  `specify_cli.skills` package re-export) and call that, keeping the injected
  `_InstallerProto` seam for tests.

Pick whichever keeps the DI seam intact; the protocol `_InstallerProto` already
declares the right `repair_skills` signature.

### Required test (must execute the real default path)

Add a test that calls `provider.repair(...)` with **no injected installer/verifier**
(default collaborators) against a fixture with a real canonical skill registry so
`repair_skills` is actually invoked and returns `(repaired, failed)` without
raising. If a full canonical-registry fixture is impractical, at minimum add a
regression test asserting
`callable(getattr(ManagedSkillsProvider()._installer, "repair_skills", None))`
so the wrong-module binding can never silently return.

---

## Note on the Pyright signal

The implementer reported `mypy --strict` clean and dismissed Pyright's line-132
warning. Pyright was correct: it flagged that `repair_skills` "is not present" on
the module assigned to the `_InstallerProto` slot. mypy accepted the module
against the protocol structurally without verifying the attribute and so missed
it. Treat the Pyright finding as the real signal here.

---

## Items that PASSED (for the next cycle — no action needed)

- **Read-only `--json` live wiring**: `doctor tool-surfaces --kind doctrine-skill --json`
  returns a `doctrine_skill` surface with `provider: "managed_skills"`; present
  state ok, missing state emits `generated-surface-missing` (ok=false, exit 1).
  Unfiltered output separates `command_skill` / `doctrine_skill`. Verified via
  live CLI against the fixture.
- **`service.py` registration**: provider added to both `build_providers()` and
  `build_registry()`; `doctrine-skill` token added to `_KIND_TOKENS`; the
  `payload` annotation fix is the only other change. No WP03 behavior altered.
- **Generic dispatch**: `status.py`/`repair.py` route by `can_handle`/`probe`/
  `repair` with no kind special-casing — T025/T026 satisfied via the existing
  generic provider dispatch; `GENERATED_SURFACE_MISSING` / `MANAGED_FILE_DRIFT`
  constants exist in `findings.py`.
- **Delegation (probe side)**: probe delegates hashing to
  `skills.manifest.compute_content_hash` and the verifier; no safety logic
  reimplemented. The `verifier` side of repair is wired correctly.
- **Gates**: `mypy --strict src/specify_cli/tool_surface/` clean (16 files);
  `ruff check` clean; `pytest tests/specify_cli/tool_surface/` = 99 passed
  (WP02 migration-compat + WP03 + 17 WP05).

Fix the P0 installer-module binding and add the default-path regression test;
the rest is ready.
