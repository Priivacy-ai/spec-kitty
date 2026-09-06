---
affected_files: []
cycle_number: 1
mission_slug: upgrade-preview-mission-health-01M1V6E1
reproduction_command:
reviewed_at: '2026-09-06T17:22:22Z'
reviewer_agent: codex
wp_id: WP07
---

# WP07 Independent Adversarial Review

Verdict: **REJECT** for the scoped WP07 implementation. Four independently
reproduced defects below require correction. This verdict does not depend on
the separate canonical agent-config defect.

Reviewer: Reviewer Renata, independently resolved through
`spec-kitty agent profile show reviewer-renata`; review-only correctness,
security, preservation and standards boundary. No implementation, product
decision, lifecycle management or self-integration performed.

## Reviewed Revision and Authority

- ROOT: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc`
- LANE: `/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g`
- BASE: `5b0992a8acaf3993166503ef57e576a5e246f5a1`
- Original RED: `3f50b533e71b29842f86edaf81dfa6a9ed49358d`
- GREEN implementation: `51bbf50f32f3152240f60de8ac6766e4116a58dc`
- Observed checkout HEAD: `0d72b954fb20a9fa73f786b2976a138d173ca516`.
  GREEN-to-HEAD changes are mission lifecycle/review artifacts, not source.
  All 13 owned files passed the delivered SHA-256 manifest verification.
  Tracked worktree remained clean.

Review used the full WP07 T034-T038 contract, parent handoff, actual charter,
spec/plan/data model and mission contracts, delivered WP02 selection/dispatch
implementation, and WP01 filesystem oracle. All eight modified production
modules and five modified test files were included in the review scope.
No CodeGraph directory exists in this lane.

Canonical `charter context --action review --json` reproduced #3908:
success envelope, zero references, empty directives/tactics, and explicit
unresolved-directive diagnostic. This is degraded governance resolution, not
successful resolution or absence of governance. Fallback authority is the
actual charter and CLI-resolved Renata profile under
[spk-doctrine-profile-load](/Users/robert/.agents/skills/spk-doctrine-profile-load/SKILL.md).
Applied locality, canonical authority, test/implementation independence,
real filesystem evidence and actionable implementer handoff.

## Findings

### R1 [P1] Planned native writes invalidate the session batch in the same dispatch

Location:
[session_presence.py:274](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g/src/specify_cli/tool_surface/providers/session_presence.py:274),
with the parent observation constructed at
[markdown_rules.py:75](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g/src/specify_cli/session_presence/writers/markdown_rules.py:75).

Both owners retain the root directory's mtime as a strict precondition.
Through the actual delivered service, a valid project configured for Vibe and
missing both native config and AGENTS.md assesses two complete batches:
native creates `.vibe` and `.vibe/config.toml`; session creates `AGENTS.md`.
The dispatcher applies native first. Its authorized directory creation changes
the root mtime. Session then refuses its retained batch with
`Session input changed: .`, although no external actor changed any input.
The planned AGENTS.md is absent after application.

Fresh actual-service reproduction in `wp07-independent-controls.py`:
`run_tool_surfaces(project, ["vibe"], kinds=[NATIVE_CONFIG, CONTEXT_FILE],
assessment_inputs=...automatic consent...)`, followed by
`SurfaceRepairService(build_providers()).apply_assessments(...)`.
Config is real `agents:\n  available: [vibe]\n`.
Observed outcomes: native `applied`, session `precondition_changed`.
Positive control differs only by creating the empty `.vibe` parent before
assessment: both batches apply and AGENTS.md exists.

Impact: ordinary combined repair requires another invocation and violates
FR-003's plan/apply agreement on an otherwise unchanged fixture. Isolated
single-owner tests do not exercise this failure.

Correction must distinguish legitimate assessed sibling effects from hostile
parent replacement while retaining whole-batch byte/type/mode/inode checks and
external-race refusal. Do not simply suppress precondition errors or silently
rerender. Add an actual combined native/session service regression.

### R2 [P2] Native partial-failure reporting claims the wrong final directory mode succeeded

Location:
[native_config.py:227](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g/src/specify_cli/tool_surface/providers/native_config.py:227).

The exception path classifies a directory effect as succeeded merely because
the destination is a nonsymlink directory. It never checks its promised final
mode. With an absent `.vibe`, umask `077`, and a low-level directory
`os.fchmod` failure after real mkdir, disk contains a `0700` directory.
The result nevertheless places the `.vibe` effect, whose after.mode is
`0755`, in `succeeded`.

Fresh reproduction retains real assessment, mkdir and filesystem observation;
only the directory fchmod syscall boundary raises
`OSError("independent directory fchmod fault")`.
Output: actual_mode `0o700`; MODE_DECLARED_SUCCEEDED
`[('.vibe', '0o755')]`. The config file was not written.

Impact: T037's physical success IDs disagree with actual postconditions.
Determine success from the complete declared final state or retain explicit
per-operation completion evidence. A created-but-incompletely-configured
directory must not be called a successfully completed `0755` effect.
Add this negative partial-I/O control alongside the second-replace fault test.

### R3 [P2] An unrelated valid TOML NaN blocks native repair

Location:
[vibe_config.py:54](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g/src/specify_cli/skills/vibe_config.py:54).

`parsed != expected` compares independently parsed values using ordinary
Python equality. NaN is unequal to itself. A valid config containing
`skill_paths = ["custom"]\nthreshold = nan\n` is therefore rejected as
`Native config preparation changed an unowned TOML key`, although the
unowned threshold text was preserved.

Fresh `tomllib.loads` accepts the original; real native assessment returns
complete=False with that diagnostic. A finite-value positive control
(`threshold = 1.0`) assesses successfully. Snapshot equality confirms the
refused case preserves bytes; this is a false refusal, not observed data loss.

Keep preservation validation, but account for legal non-reflexive TOML values
without weakening byte preservation. Cover nested NaN values as well.

### R4 [P2] Valid multiline scalar paths with trailing quotes are parsed at the wrong boundary

Location:
[vibe_config.py:118](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g/src/specify_cli/skills/vibe_config.py:118).

The hand-written scanner treats the first three quotes in a closing run as
the complete delimiter and returns immediately. TOML permits a quote adjacent
to the closing triple delimiter. Real `tomllib` accepts both:

~~~toml
skill_paths = """custom""""
~~~

~~~toml
skill_paths = '''custom''''
~~~

Their scalar values are respectively `custom"` and `custom'`. Preparation
leaves one quote outside the replacement span, then rejects its own rendered
TOML with `Expected newline or end of document after a statement`
(columns 45 and 44 in the recorded fixtures).
Both original configs are valid, string-compatible input. No file mutation
occurred during refusal.

Correct the format-aware boundary handling and add exact-byte preservation
controls for four/five closing-quote runs in multiline basic and literal
strings. Keep the owner helper authoritative; no provider-local TOML policy.

## Separate Unresolved Acceptance Dependency

Canonical
[core/agent_config.py:69](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/spec-kitty/.worktrees/upgrade-preview-mission-health-01M1V6E1-lane-g/src/specify_cli/core/agent_config.py:69)
uses `yaml.load(f) or {}`. Fresh controls confirm `[]`, `false`, `0`
and an empty-string scalar each yield successful empty configuration, so
session assessment is complete=True, effects=(), not_applicable for selected
Codex. This is not malformed-config contract compliance.

Parent reports [#3917](https://github.com/Priivacy-ai/spec-kitty/issues/3917)
and supporting Op `01M1VV3PYTR3HESCVHEXG9W7TQ` OPEN; no fix is integrated.
The cross-owner malformed-config acceptance requirement remains **unresolved**.
The parent owns canonical loader/test repair and integration. Independent
post-integration controls are required before approving the full requirement.
No loader/dependency changes or provider-local schema were introduced here.

## Fresh Verification

All commands used the inspected external `wp07-evidence/run` wrapper and
the existing warm lane interpreter. No uv sync, install, global credentials,
source changes or network-backed tooling was used.

The wrapper clears inherited environment, binds home/config/cache/temp externally,
disables bytecode/cacheprovider, and loads the inspected external offline policy.
The policy pins sync=0 despite conftest resets and forces child sync=0.
A fresh explicit reset-to-1 control verified parent 0 and child 0.
Shared conftest remained enabled in the pytest run; its test_venv fixture was
bound externally to the warm lane venv by the existing supplied plugin.

Fresh targeted command, cwd LANE:

~~~sh
sh "$ROOT/wp07-evidence/run" .venv/bin/pytest \
  tests/specify_cli/tool_surface/providers/test_native_config.py \
  tests/specify_cli/tool_surface/providers/test_session_presence.py \
  tests/specify_cli/session_presence/test_markdown_rules_writer.py \
  tests/specify_cli/session_presence/test_claude_code_writer.py \
  tests/specify_cli/session_presence/test_manager.py \
  -k wp07 -p no:cacheprovider -q
~~~

Result: **62 passed, 79 deselected, 5.83s**, exit 0. Selection was deliberate
focused verification, not a claim that every test in those files ran.
Includes genuine owner writes, exact physical effects, preserved foreign
Markdown/JSON/TOML, shared owners, selected policies, late-input refusal,
transient-write denial, retained T1 bytes at T2, partial I/O and repeat snapshots.

Original RED replay:

~~~sh
sh "$ROOT/wp07-evidence/run" .venv/bin/python "$ROOT/wp07-independent-controls.py" red
~~~

All three original test functions loaded verbatim from RED Git objects failed
at their intended assertions against BASE production module bytes:
TOML preservation; Markdown second-write snapshot; malformed Claude sibling
preservation. No missing-new-API failure counted. Source modules were loaded
from immutable Git objects in memory; the checkout was not reverted or edited.
Original test functions were invoked directly with disposable directories,
rather than claiming a full baseline pytest/conftest run.
The corresponding GREEN tests passed in the focused pytest run.

Initial external-script attempts lacked LANE on sys.path: one TOML RED
assertion ran, then `ModuleNotFoundError: No module named 'tests'` stopped
execution. This harness error was not counted as RED. Adding LANE to the
external script's sys.path enabled the complete recorded replay.

Fresh source mutations, separate processes using disposable in-memory source
copies, all **killed by assertions**:

- `mutation-settings`: omit the settings physical effect.
- `mutation-parent`: omit directory effects.
- `mutation-overwrite`: discard preexisting foreign Markdown on append.
- `mutation-churn`: force changed=True and bypass the same-byte atomic guard.

Invocation:
`sh "$ROOT/wp07-evidence/run" .venv/bin/python
"$ROOT/wp07-independent-controls.py" mutation-<name>`.
These are actual production-code mutations, not only weakened expected sets.
Unmutated matching cases passed in the focused run. No on-disk source copy
or production writer was replaced with a mock success.

Fresh rerun of inspected `wp07-evidence/capture.py` produced
[10 raw oracle records](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp07-independent-oracle.jsonl):
two equivalent fixtures each for missing native, mixed native, Claude, Cursor,
and shared AGENTS.md. Every record verifies nonempty exact
root/path/action/kind/mode/hash equality, exact retained bytes, all scanned
directories, foreign file/link, and two unchanged subsequent applies.
No timestamp/content normalization is used for these owner outputs.
Execution-artifact patterns are retained in those records.

Additional independent controls and findings:
[script](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp07-independent-controls.py),
[output](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp07-independent-controls.log),
[original RED output](/var/folders/gj/bxx0438j003b20kn5b6s7bsh0000gn/T/spec-kitty-20260906-130341-7O3Frc/wp07-independent-red.log).
Script exit 0 means the observations completed; its finding cases deliberately
print defective outcomes and do not claim acceptance.

SHA-256:
- controls.py: c7cb80063ced08bd410179dbf8b2343d6c333a7fe408883c25a8f87242ca7009
- controls.log: 7074b4c602231b6d3348184889456c1e1d29a0bd258777bf0c2d98fe997e4ce7
- red.log: f5d57bf1f1849943d269db6a3e75ea3df2698fb35a17183d4f8a904f9b90917c
- oracle.jsonl: 425f1611e1f3abfb8b580b0bb9924425715a0a495fa401749f2280bdd98dc574

## Contract and Anti-Pattern Disposition

| Check | Verdict | Evidence / limit |
| --- | --- | --- |
| T034 original existing-entry RED | PASS | Three intended failures replayed; matching GREEN passed |
| T035 native preparation | FAIL | R3/R4 reject legal TOML; common fixtures preserve bytes |
| T036 session preparation | PASS scoped | Real Markdown/JSON, full Claude sibling batch, sharing and pure content controls |
| T037 application | FAIL | R1 combined dispatch; R2 inaccurate physical success |
| T038 verification | FAIL acceptance | Useful non-vacuous tests, but gaps above and #3917 remain |
| Dead code | PASS | New preparation/apply values and helpers have production callers; no new modules |
| Synthetic-fixture tests | PASS | Relevant tests exercise real owners; mutations kill actual behavior |
| Silent empty return | FAIL full contract | External #3917 remains; owned exception paths diagnose failures |
| FR coverage | FAIL acceptance | FR-003 contradicted by R1/R2; malformed input dependency unresolved |
| Frozen surface | PASS | No diff to loader, WP02 operations/repair, shared conftest, oracle or dependency files |
| Locked decisions | FAIL | Complete promised effects and honest final physical outcomes are not met |
| Shared-file ownership | PASS scoped | Exact 13 owned paths; no dependency/neighbor source changes |
| Production fragility | FAIL | Valid-input failures R3/R4; portability concern below |

No manifest/refcount owner was added or changed. Shared AGENTS.md coalesces
logical owners into one physical effect in the tested cases. Existing exact
hook commands remain the owned JSON entries; unknown content is preserved.
No existing native/session lock acquisition was found to retain; recheck
contexts perform observations and atomic application holds parent descriptors.

## Limits and Parent Handoff

The worker's **1289-test delivery suite**, **1642 fast tests**, Ruff/mypy,
architecture and coverage results are supplied evidence, not my fresh runs.
They were not broadly duplicated. The prior open-ops timing failure remains
parent-disposition evidence; these focused results do not erase it.

Darwin is the only actual filesystem platform exercised. Additional portability
concern: the new atomic path unconditionally opens directory descriptors and
uses dir_fd plus os.fchmod without a platform branch
(markdown_rules.py:232-268). This requires a concrete Windows-compatible
implementation/control before claiming existing Windows support. I did not
run Windows or Linux and do not present emulation as capable-platform evidence.

Public CLI startup, installed wheel, aggregate composition, mission-state
repair and full acceptance matrices remain parent/WP10/WP13 responsibilities.
The per-owner oracle's success is not public-upgrade acceptance, and R1 already
demonstrates why that distinction matters.

Parent should route R1-R4 back to the WP07 implementer, retain #3917 as a
separate unresolved requirement, and request independent follow-up controls
against the integrated revisions. This report is the review artifact only;
the parent owns durable verdict/lifecycle recording. No lifecycle/Op/root
coordination files, commits, pushes or self-integration were performed.

