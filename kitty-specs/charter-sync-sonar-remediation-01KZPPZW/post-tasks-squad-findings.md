# Tracer: Post-Tasks Squad Findings (2026-08-10) — AUTHORITATIVE

Two profile-loaded lenses (architect-alphonso empirically read/timed/fuzzed the risky items; reviewer-renata
audited discipline + caller-safety). Implementers MUST honor these; they supersede conflicting WP wording.
Coverage confirmed SOUND: all 80 findings map to the 6 disjoint-owner WPs, no orphan, no double-owned file.

## WP01 — S8786 ReDoS regex (token_budget.py:308) — REFRAMED

- The pattern is `_HEADING_LINE_RE = re.compile(r"^###\s+(.+?)\s*$")`. It is **NOT catastrophic** — worst case
  is quadratic and the real input is a single short heading line; timing proofs show the OLD pattern is
  already fast. **Do NOT try to prove "adversarial input slow on old, fast on new" — it doesn't exist.**
- Reframe NFR-003 as: **remove the static `.`/`\s` overlap** (the ambiguous-partition Sonar flags).
- **Recommended rewrite:** `^###\s+(\S.*?)\s*$` (require the captured group to start non-space → linear, no
  `.`/`\s` ambiguity). **Match-equivalence is the acceptance proof** (not timing).
- **One intentional divergence to document:** on the degenerate input `"###    "` (marker + only whitespace),
  the OLD pattern captures `' '` (a single space); the rewrite returns `None`. No real `### ` heading is
  whitespace-only (`None` just skips the chunk, arguably more correct). The characterization test MUST cover
  `"###    "` and document this single-space→None divergence as an intentionally-dropped dead input.
- `:365` (S3776/28): standard tested helper extraction; characterize-first if its coverage is thin.

## WP05 — corrections

- **S8572 (dossier_pipeline.py:83,:194):** the WP's "(e.g. decorator/staticmethod)" guess is WRONG. Actual:
  "Use `logging.exception()`". Fix = `logger.error(msg, e)` → `logger.exception(msg)` (drop the `e` arg).
  `logging.exception` ADDS a traceback to the record — behavior-preserving ONLY if no test asserts exact log
  text; check the sync log-assertion tests first.
- **S3776 dossier_pipeline.py:38 (33):** decompose by the 4 sequential `try/except`-wrapped steps —
  `_emit_artifact_events(...)`, `_emit_snapshot(...) -> (snapshot|None, int)`, `_emit_drift(...)`,
  `_prepare_bodies(...)`. **CARE:** each step's `try/except` isolates failure so one step's exception never
  aborts the others — each extracted helper MUST retain its own try/except (or the caller keeps them) and the
  running `events_emitted` counter / `errors` list must be threaded back. Behavior-preserving only if that
  isolation is kept.
- **orphan_sweep.py:705 / background.py:776 (daemon/port-sensitive):** extract ONLY the decision/partition
  branches (`_classify_reset_action(record, ...)`, `_skipped_entry(record)`; `_partition_window(window,
  granted)`). **Leave the port/timing I/O byte-identical** — `_sweep_one_with_path`, `_assert_safe_to_sweep`,
  the HTTP-shutdown→terminate→kill escalation, `_body_queue.drain`, and any sleeps/timeouts must NOT be
  touched, so `tests/sync/test_orphan_sweep.py` (real-port, run `-n0`) stays timing-stable.
- Add inline: "read+run each function's existing tests before/after; characterize-first where coverage is thin."

## WP06 — corrections

- **S107 (emitter.py:1581, events.py:283,:513): "or keyword-only" is WRONG** — S107 counts total params
  regardless of keyword-only. ONLY a params-object reduces the count. Remove the keyword-only option.
  - `emit_token_usage_recorded` (14): 4 refs, 1 test — tractable, but it's a **two-layer** signature (events
    wrapper threads into `get_emitter().emit_token_usage_recorded(...)`); a params-object must be threaded
    through BOTH layers or the finding just moves.
  - `emit_wp_status_changed` (15): **103 test call-sites** (~26 pass optional metadata kwargs) — **NOT
    mechanical.** Bundle only the OPTIONAL metadata tail (`policy_metadata, force, reason, review_ref,
    execution_mode, evidence, occurred_at, causation_id`) into ONE optional params object with a default,
    keeping the core positional args — this drops the count under 13 while most call-sites (core args only)
    stay untouched. Give this its own tested slice; do not treat as a mechanical lump.
- **S5779 (events.py:78, `_ensure_dashboard_sync_daemon`):** the code `raise AssertionError("intent_local_only…")`
  inside `try/…except Exception` is a genuinely-unreachable defensive guard that gets swallowed into
  warning-and-continue. **Characterize first** (confirm no control-flow relies on the catch), then the
  behavior-preserving fix is: replace the `raise AssertionError(...)` with a direct `logger.warning(...)` in
  that branch (same observable outcome). Pure control-flow, daemon-adjacent but no timing impact.
- **S1172 (restart.py):** before removing an unused param, check whether the function is an override,
  implements a Protocol/ABC, or is a registered callback/handler — grep sibling implementations, not just
  direct callers. If it's a contract slot, `_`-prefix (keep the slot); do NOT remove.
- Restate the #3232 gotcha inline: an explanatory/rationale comment must NOT contain a `# noqa:` literal
  (ruff re-flags it).

## WP03 — corrections

- **S3516 (pack_manager.py:559, `deactivate`) is likely STALE/FALSE-POSITIVE:** the method already has a
  single `return result` + an inline "(S3516 → single return)" comment from a prior refactor, and `result`
  is a freshly-constructed input-varying `ActivationResult`. There is **no clean behavior-preserving code
  change left**. Disposition: re-run Sonar; if it persists, it's a false-positive → mark won't-fix in the
  SonarCloud UI with rationale and call it out in the PR body (per CLAUDE.md). Do NOT contort correct code.
- **S1172 (pack_manager):** same Protocol/ABC/callback caution as WP06 above. Grep sibling impls.
- Add inline (this is the biggest complexity lane — 12 functions): "read+run each function's existing tests
  before/after; add a characterization test first where coverage is thin"; and the `# noqa:`-literal gotcha.

## WP04 — corrections

- **S5890 (synthesizer/manifest.py:89) is a Pydantic PrivateAttr FALSE-POSITIVE:**
  `_raw_field_names: frozenset[str] | None = PrivateAttr(default=None)` is idiomatic Pydantic v2; Sonar
  mis-infers the RHS type. **No behavior-preserving code fix** that keeps both typing and Pydantic semantics.
  Disposition: UI won't-fix with rationale + PR-body callout (SC-001's "documented residual" clause). Do NOT
  mandate a code edit. (Same pattern recurs 5× in out-of-scope `core/wps_manifest.py` — correctly excluded.)
- **S1172 (preflight/runner.py, activation_block.py):** Protocol/ABC/callback caution before removing.

## Spec/SC implication (both FP items)

SC-001/SC-002 "0 open findings" is achievable via CODE for all but **S3516 (pack_manager)** and **S5890
(manifest)**, which are false-positives requiring **SonarCloud UI won't-fix** (no clean code fix). The PR body
MUST list these two as remaining Sonar UI work (per the CLAUDE.md Sonar-expectations rule). FR-005 is read as
"resolve OR document as FP" for these two.

## SOUND (confirmed, no action)

- Heaviest complexity `code_reader.py:182` (33) cleanly decomposable: `_scan_tree`, `_detect_frameworks`,
  `_detect_test_frameworks`, `_build_stack_id` (all pure, unit-testable).
- All other items (S1192 literals→constants, S7632 suppression-comment fixes, S5713, S6353 re.ASCII, S7503,
  the ≤29 complexity funcs) are mechanical/low-risk and proven in #3232.
- Regex match-equivalence discipline carried by WP01 (oracle + edge) and WP06 (S6353 re.ASCII, #3232 lesson).
