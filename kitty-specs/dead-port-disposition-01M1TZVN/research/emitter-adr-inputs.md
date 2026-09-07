# Input to PR #3898 — recorded, not executed (C-003)

**Mission** `dead-port-disposition-01M1TZVN` · **WP03 / T015 (FR-011)** · extracted from
`research/29-missionB-research-dossier.md` §3 (verbatim below) and re-verified at the WP03 lane
HEAD `d18b0c98c` (`kitty/mission-dead-port-disposition-01M1TZVN-lane-c`, based on lane-a `4213e000b`)
on 2026-09-06. Intended landing spot: `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md`
(the lane gate refuses `kitty-specs/` commits; the operator copies it in at consolidation).

**Gate state at extraction (gh, 2026-09-06T20:07:02Z):** PR #3898 **MERGED** 2026-09-06T15:59:54Z with the
ADR `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` at `status: Accepted` (title: "Rewire-Ready
Consolidation, Not Retirement"); PR #3899 MERGED 15:59:58Z (its 15 files carry none of the `src/mission_runtime`
residue — OD8 holds); PR #3888 MERGED 10:09:16Z and present in the lane as `c0054153b`. Execution of the ADR is
**WP05** (same lane, after WP03). Nothing below was executed by WP03; the only WP03 touch on the emitter surface
is the `event_emitter.py` module docstring (AST-identical otherwise).

## Dossier §3 (verbatim)

### 3.1 Safe-regardless facts (this dossier's contribution)

- **Name collision (verified):** two classes named `RuntimeEventEmitter` —
  `runtime/next/event_emitter.py:23` (concrete no-op, 88 LOC, `for_feature:43`,
  `seed_from_snapshot:60`) vs `runtime/next/_internal_runtime/events.py:67` (the live Protocol,
  with `NullEmitter`). Every disposition resolves the collision (retire deletes one; rewire/merge
  renames one) — so *documenting* it and pinning the map below is safe; *executing* a rename is
  the ADR's call.
- **The ~29-occurrence `sync_emitter` map (verified at HEAD):** 29 occurrences in `src/`, exactly
  two files — `runtime_bridge_engine.py` × 16 (`:139,166,183,188,198,226,237,270,292,301-307,
  323,344,346,366`) and `runtime_bridge.py` × 13 (`:1215,1231,1472,1552,1614,1647,1976,2187` +
  wrapper plumbing). Plus **10 test files** reference `sync_emitter`. ⚠ VERIFIED-DELTA worth
  recording: `runtime_bridge_engine.py:80` imports the concrete class **under
  `TYPE_CHECKING` only** — all 16 engine occurrences are annotations/parameter names; the sole
  *runtime* coupling to the concrete class is `runtime_bridge.py:195` (import) + `:1552`/`:2739`
  (`for_feature` construction) + `:1614`/`:2745` (`seed_from_snapshot`). Retyping the engine
  against the Protocol is a type-only edit; the bridge is where behavior lives.
- **Both files are Mission-A-adjacent:** `runtime_bridge_engine.py` is one of the four shared
  files; any emitter execution sequences after Mission A regardless of the ADR (§6).
- **`sync_emitter` is retired-transport vocabulary in a live API** (report 20 §3.4#4). A
  parameter rename is *probably* safe under every disposition but touches the same 29 sites the
  ADR's execution will touch — do it as part of the ADR's execution WP, not before (one pass over
  those signatures, not two).

### 3.2 ADR-BLOCKED (do not scope into Mission B until the ADR lands)

- Retire vs rewire vs merge; whether `for_feature` / `seed_from_snapshot` (absent from both the
  Protocol and `NullEmitter` — verified) migrate onto the seam.
- **The buffer flush-target defect (verified live at HEAD):** under the strict retrospective gate
  the buffer replaces the engine emitter (`runtime_bridge.py:2149-2150`) and later flushes into
  `ctx.sync_emitter` (`:2187`) — the **inner no-op**, not `emitter_for_engine` (the
  `DecisionGitLog`-wrapped emitter built at `:1560-1565`), so buffered decision events never reach
  the git log on the gated path. Any deletion silently freezes or silently fixes this; the ADR
  must adjudicate it explicitly (report 24 §4c). Record; don't touch.
- The upstream contract fact anchoring the ADR (verified this session): installed
  `spec_kitty_events` **9.1.6** carries the runtime moments in `VOLATILE_EVENT_TYPES`
  (`MissionRunStarted/Completed`, `NextStepIssued`, `NextStepAutoCompleted`,
  `DecisionInputRequested/Answered`, plus `DecisionPointOpened/Resolved`) with codecs and
  redaction rules — the hosted vocabulary is provisioned and waiting for a producer.
- The parity oracle constraint: `tests/runtime/test_bridge_parity.py:1131-1152`
  (`test_side_effect_sinks_are_actually_reached`) asserts the `sync_emitter` sink is populated by
  ≥1 fixture — a disposition that removes the capture must update this oracle in the same PR.
- `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) is **rollback machinery**, not
  dead code — it structurally implements the Protocol and is the only thing preventing an
  unretractable `MissionRunCompleted` on a rolled-back terminal advance. Not deletable under any
  disposition.

## Verification log lines backing §3 (dossier, verbatim)

- `verification log`: name collision `event_emitter.py:23` vs `_internal_runtime/events.py:67`; `sync_emitter`
  29 sites: engine ×16 incl. TYPE_CHECKING-only import at `:80`, bridge ×13; constructions `:1552,:2739`; seeds
  `:1614,:2745`; buffer swap `:2149-2150`; flush `:2187`; DecisionGitLog wrap `:1560-1565`; parity oracle
  `test_bridge_parity.py:1131-1152`; `spec_kitty_events` 9.1.6 runtime moments.

## Re-verification at WP03 HEAD `d18b0c98c` (every anchor; deltas marked ⚠)

| Anchor (dossier) | State at WP03 HEAD | Delta |
|---|---|---|
| `event_emitter.py:23` concrete `RuntimeEventEmitter`, `for_feature:43`, `seed_from_snapshot:60` | class at **`:37`**, `for_feature` **`:57`**, `seed_from_snapshot` **`:74`** | ⚠ shifted +14 by the WP03 docstring correction (the only change to the file; AST identical). Before WP03 (`4213e000b`) the anchors were exactly `:23/:43/:60`. |
| `_internal_runtime/events.py:67` live Protocol; `NullEmitter` | Protocol `class RuntimeEventEmitter(Protocol)` at `:67`; `NullEmitter` at `:95` | none |
| `runtime_bridge_engine.py:80` `TYPE_CHECKING`-only import | `if TYPE_CHECKING:` `:76`, `from runtime.next.event_emitter import RuntimeEventEmitter` `:80` | none |
| engine `sync_emitter` ×16 (`:139,166,183,188,198,226,237,270,292,301-307,323,344,346,366`) | `:139,166,183,188,198,226,237,270,292,301,304,307,323,344,346,366` = **16** | none |
| `runtime_bridge.py:195` import | `from runtime.next.event_emitter import RuntimeEventEmitter` `:195` | none |
| bridge `sync_emitter` ×13 | `:1215,1231,1472,1552,1560,1563,1614,1647,1976,2187,2739,2745,2754` = **13** (29 total) | none |
| `for_feature` construction `:1552`, `:2739` | `sync_emitter = RuntimeEventEmitter.for_feature(` at `:1552` and `:2739` | none |
| `seed_from_snapshot` `:1614`, `:2745` | `:1614`, `:2745` | none |
| `DecisionGitLog` wrap `:1560-1565` | `emitter_for_engine: Any = _wrap_with_decision_git_log(sync_emitter, …)` `:1560`, plain-`sync_emitter` fallback `:1563` | none |
| buffer swap `:2149-2150` | `buffer = _BufferingRuntimeEmitter()` `:2149`, `engine_emitter = buffer` `:2150` | none |
| flush `:2187` | `buffer.flush(ctx.sync_emitter)` `:2187` — still the inner no-op, not `emitter_for_engine` (defect intact) | none |
| `_BufferingRuntimeEmitter` `runtime_bridge_retrospective.py:69`; `flush` | `:69`; `def flush(self, target)` `:132`; a module-identity subclass at `runtime_bridge.py:526` | none (C-006 untouched) |
| 10 test files reference `sync_emitter` | `grep -rl sync_emitter tests \| wc -l` → **10** | none |
| parity oracle `test_bridge_parity.py:1131-1152` | `def test_side_effect_sinks_are_actually_reached` at `:1131`; `reached["sync_emitter"] \|= bool(se.sync_emitter_calls)` at `:1145`; file untouched by WP03 and green | none |
| `spec_kitty_events` 9.1.6 `VOLATILE_EVENT_TYPES` | `spec_kitty_events.__version__` = `9.1.6` (dist `spec-kitty-events 9.1.6`); `VOLATILE_EVENT_TYPES` ⊇ {MissionRunStarted, MissionRunCompleted, NextStepIssued, NextStepAutoCompleted, DecisionInputRequested, DecisionInputAnswered, DecisionPointOpened, DecisionPointResolved} | none |
| real E3 seam `status/adapters.py:364-366` | module-level default wiring `if not is_truthy(os.environ.get("SPEC_KITTY_SYNC_MINIMAL_IMPORT")): ensure_zeitgeist_moment_handlers()` at `:364-365` | none (the docstring now points here) |
| ADR status | **Accepted** (was `Proposed` when the dossier and plan were written) | ⚠ gate opened; FR-012 executable → WP05 |

## Hand-over

The ADR author's hand-over comment on PR #3898 (analysis finding C1) is an operator action; PR #3898 is merged,
so the record is now input to **WP05** rather than to an open PR.
