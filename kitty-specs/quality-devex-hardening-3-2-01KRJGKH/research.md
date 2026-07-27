# Phase 0 Research — Quality and DevEx Hardening 3.2

**Mission**: `quality-devex-hardening-3-2-01KRJGKH`
**Spec**: [spec.md](spec.md)
**Plan**: [plan.md](plan.md)

This Phase 0 research is **deliberately focused**. Pre-mission research is comprehensive — see `/work/findings/00-summary.md`, `refactor-audit.md`, `rule-pipeline-pattern-survey.md`, and the six per-ticket findings. This file covers only the gaps that surfaced during plan-phase elaboration; it does not re-litigate decisions already taken (e.g. the resolved Decision Moment on mypy scope).

## 1. `re2` typing strategy under strict mypy

### Decision

**Drop strict on `re2` import sites only.** Mark the import with `type: ignore[import-untyped]` and a comment that references this decision.

### Rationale

- The `re2` package (Google RE2 Python bindings) ships no `.pyi` stubs and no Type Information PEP-561 marker.
- Authoring a stub set for the `re2` surface is a non-trivial side mission; the surface includes compile/search/match/replace + flag constants. Pedro estimates 1–2 hours of stubs work, all of which is throwaway when `re2` upstream ships its own stubs (already discussed in the upstream tracker, no ETA).
- Replacing `re2` usage with the stdlib `re` module is not safe: `re2` is specifically used as the escape hatch in the `secure-regex-catastrophic-backtracking` tactic for callers that cannot rewrite to a linear pattern. Removing it widens the catastrophic-backtracking surface.
- The `re2` call sites are narrow (handful of imports) and Pedro can localize the `type: ignore` so the rest of the codebase remains strict.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| Author `.pyi` stubs for the `re2` surface used in this repo | Non-trivial effort; thrown away when upstream ships stubs; pulls scope out of this mission's structural-debt focus. |
| Replace `re2` calls with stdlib `re` | Removes the linear-time escape hatch documented in the secure-regex tactic. Net regression. |
| Drop `re2` entirely as a dependency | Same as above — removes the option of using a non-backtracking engine where rewrites are infeasible. |
| Vendor `re2` stubs from a third-party package (e.g. `types-re2` if it existed) | No such package on PyPI as of this research; option not available. |

### Implementation note for WP01

Each `re2` import site gets:

```python
import re2  # type: ignore[import-untyped]  # see research.md §1; upstream stubs pending
```

Mission's CHANGELOG entry mentions the localized ignore and references this research file.

---

## 2. Sonar new-code baseline reset evidence

### Decision

**Do not reset the baseline.** Produce the evidence the release owner needs to make the call themselves, but Pedro recommends keeping the current baseline because resetting hides the debt the mission is actively paying down.

### Rationale

- The current "previous version" baseline anchors the `new_coverage` and `new_security_hotspots_reviewed` metrics to a real diff window that the team is held accountable for.
- Resetting the baseline (to e.g. the latest 3.2.0rcN tag) would mathematically zero out the gap *without* the team writing any new tests — the gate would flip green by definition, not by improved coverage.
- Pedro's research lens: a release-stability outcome cannot be claimed by moving the goalposts. Issue #595's spirit is "the new release-path coverage debt is real; pay it down". A baseline reset would silently invert that intent.

### Evidence package for the release owner

To support the decision (whoever makes it), the following data lives in this research file:

- Current Sonar gate status on `main`: ERROR; `new_coverage` 58.8 %; `new_security_hotspots_reviewed` 0 %; total hotspots 6; total code-smells on new code 724.
- New-code window: anchored to the previous version baseline (Sonar default). Exact baseline tag visible in the Sonar `Priivacy-ai_spec-kitty` project's Administration → New Code panel.
- Files with the largest uncovered new-code surfaces (top 10): `cli/commands/charter.py` (645/891), `cli/commands/doctor.py` (418/464), `next/_internal_runtime/engine.py` (303/502), `doc_analysis/gap_analysis.py` (273/339), `drg/migration/extractor.py` (239/261), dashboard JS (192/192 — out of scope, not Python), `cli/commands/charter_bundle.py` (177/208), `orchestrator_api/commands.py` (176/203), `cli/commands/agent/config.py` (171/187), `cli/commands/implement.py` (167/267).
- These surfaces are all release-path CLI code; the new-code window correctly captures the recent expansion that drove the gap. Resetting would re-anchor to a snapshot that no longer reflects the codebase's current breadth.

### Acceptance for this research item

The release owner reads this section before WP07 (Sonar gate flip) lands and either confirms "do not reset" (recommended) or directs the mission to reset and update CHANGELOG accordingly.

---

## 3. Auto-rebase classifier rule corpus

### Decision

**Use the following file-pattern rules in the ADR draft**, validated against real conflict shapes observed in `.worktrees/` history and in the issue body of #771:

| File pattern | Conflict shape | Rule | Example |
|---|---|---|---|
| `pyproject.toml` `[project.dependencies]` array | Two sides add distinct entries to the dependency list | Auto-union: keep both entries, dedup by name | Lane A added `httpx`, Lane B added `freezegun` |
| `pyproject.toml` `[dependency-groups.dev]` | Same shape as above | Auto-union: keep both entries, dedup by name | Same |
| `uv.lock` | Regeneration outcome of `pyproject.toml` merge | Regenerate via `uv lock --no-upgrade` after pyproject merge succeeds; global file lock to prevent concurrent regenerations across lanes | n/a — regenerated, not merged textually |
| `__init__.py` import block | Both sides added distinct `from foo import bar` lines, no overlap on existing imports | Auto-union: union of import lines, preserve sort order | Lane A added `from .auth import AuthFlow`, Lane B added `from .sync import SyncClient` |
| `urls.py` URL list (or similar list-of-strings constants) | Both sides added distinct list entries | Auto-union: keep both entries; preserve order if order is significant (TBD per file) | Lane A added a callback URL, Lane B added a webhook URL |
| Any other file pattern | Either side or both modified existing logic | **Manual** — halt with current actionable error | n/a — fail-safe default |

### Rationale

- The four patterns above cover 100 % of the 30-minute rote-merge cost called out in the issue body and observed in the Pedro audit of past missions.
- The fail-safe default (`Manual` for anything unmatched) means a wrong-classified semantic conflict is impossible: the classifier opts out rather than guessing.
- `uv.lock` regeneration is the only non-trivial post-merge step; it MUST be serialized with `specify_cli.core.file_lock` so two lanes do not stomp on each other's regeneration.

### Open question for the ADR

Whether the auto-union driver for `__init__.py` import blocks should also re-run `ruff --fix` on the merged file to canonicalize import order. Pedro recommends **yes** because the existing import order is already ruff-driven; otherwise the auto-resolved file may fail a subsequent `ruff check`. Documented in the ADR draft.

---

## 4. `charter.py` testability triage

### Decision

**Three buckets** of functions in `src/specify_cli/cli/commands/charter.py` (645 uncovered new lines of 891 total):

| Bucket | Approximate fraction | Test strategy |
|---|---|---|
| **A. Pure orchestration of small helpers** | ~40 % | Typer-runner integration tests at the command boundary; assert on stdout/exit-code outcomes. No internal mocking. Driven by realistic fixture charters in `tests/_factories/charters/`. |
| **B. Filesystem-heavy IO with branching** | ~35 % | Use `tmp_path` + real file I/O with small handcrafted fixtures; assert on resulting file content and side effects. Avoid `unittest.mock` patches of `Path.read_text` etc. (over-mocking pattern). |
| **C. Diagnostic / report-rendering** | ~25 % | Snapshot-style assertions on rendered output (the message strings ARE the contract because they're operator-facing); kept as behavior tests by asserting on stable substrings rather than the full Rich-rendered surface. |

### Rationale

- Bucket A is the easiest win and drives the largest coverage delta with the least implementation churn. Land Bucket A first.
- Bucket B requires care to avoid the "test the file-system mock, not the behavior" anti-pattern. Pedro recommends real `tmp_path` IO over patches.
- Bucket C is the highest-risk for `function-over-form-testing` violations — assertions on exact rendered output are brittle. Use substring assertions on stable message content, not on layout / formatting.

### Implementation note for WP05

`tests/cli/commands/test_charter_coverage.py` is split into three sibling files following the bucket boundaries: `test_charter_orchestration.py`, `test_charter_io.py`, `test_charter_rendering.py`. Each follows the AAA structure mandated by NFR-002.

---

## 5. PyPI probe failure-mode taxonomy (for FR-007)

### Decision

The probe in `src/specify_cli/core/upgrade_probe.py` returns a `UpgradeProbeResult` with one of four `channel` values: `already_current`, `ahead_of_pypi`, `no_upgrade_path`, `unknown`. Failure modes map as follows:

| Failure mode | `channel` value | Cache TTL |
|---|---|---|
| HTTP 200 with installed == latest | `already_current` | 24 h |
| HTTP 200 with installed > latest (e.g. dev/rc build) | `ahead_of_pypi` | 24 h |
| HTTP 200 with installed not in `releases` (off-PyPI build) | `no_upgrade_path` | 24 h |
| HTTP 4xx / 5xx | `unknown` | 1 h (shorter retry window) |
| Network timeout / DNS failure / connection refused | `unknown` | 1 h |
| `SPEC_KITTY_NO_UPGRADE_CHECK=1` set | (probe not run) | (n/a — opt-out path) |

### Rationale

- The four-channel taxonomy maps 1:1 to the issue's acceptance criteria (#740 AC #2 + #3).
- Two cache TTLs (24 h for successful probes, 1 h for `unknown`) means transient PyPI outages don't wedge a user into "no notice for a day" while a successful probe still gives a sensible re-check cadence.
- All failure modes resolve to `channel = unknown` with no exception bubbling to the CLI — NFR-001 requires that the CLI never blocks on the probe.

### Implementation note for WP09

Cache file: `~/.cache/spec-kitty/upgrade-check.json` (POSIX path; Windows: `%LOCALAPPDATA%\spec-kitty\upgrade-check.json`). Schema captured in `data-model.md::UpgradeProbeResult`.

---

## Research summary (Phase 0 complete)

All four research items resolved with documented decisions and acceptance criteria. No remaining `[NEEDS CLARIFICATION]` markers in plan.md. Phase 1 (data-model + contracts + quickstart) can proceed.
