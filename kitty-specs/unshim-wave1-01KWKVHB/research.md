# Research — unshim-wave1-01KWKVHB (Phase 0)

All decisions derive from the pre-spec 4-lens squad (debugger-debbie, planner-priti, architect-alphonso, randy-reducer) and the post-spec 3-agent pass (reviewer-renata, paula-patterns, randy-reducer related-surfaces), all run 2026-07-03 against main @ cf2e91e17 / branch tip. Divergences were adjudicated from primary sources, not averaged.

## D1 — Census authority: spec rev 2 tables override the issue bodies

#2289's body carries 4 wrong canonical-home cells (`core.identity` → real home `specify_cli.identity.aliases`; the three `doc_*` shims → real home `specify_cli.doc_analysis.*`; the body's `missions.documentation.*` does not exist) and a ~3× re-anchor undercount ("~15" vs verified ~45–50 sites / ~19 files / 36 sites in tasks_support alone incl. 10 `patch()` strings — renata re-verified 35 refs + 10 patch strings exactly). Every LOC cell in the spec tables matches `wc -l` exactly (renata). **Decision**: C-005 — re-anchor targets come only from the spec table.

## D2 — auth.transport: documented-DELETE, deferred to Robert (not #614/#391)

Three-way squad divergence resolved by reading the ADR: `docs/adr/3.x/2026-05-18-2-delete-specify-cli-auth-transport.md` is **Accepted**, recommends DELETE, and **binds execution to Robert** (HiC §5a.3; its own C-005: `auth/transport.py` + `test_auth_transport_singleton.py` MUST NOT be modified). #2292's "#614/#391 blocker" is a misattribution → corrected via issue comment (FR-007). The live `from .transport import` hits resolve to the *different* module `auth/http/transport.py` — a sibling-name trap recorded so nobody re-greps it wrong.

## D3 — tracker_client_glue: DELETE (defer premise was stale)

randy's DEFER rested on "active mission #2124/#2131 reworking the domain" — adjudicated against the tracker: #2124 CLOSED, #2131 MERGED; the landed rework touched the file (`3994e9bba`) and still left it caller-less. Superseded → clean delete. This flip makes the executed-deletion count 4 (meets #2292's ≥4 AC) without sacrificing policy.audit.

## D4 — policy.audit: keep, adopt-as-follow-up

The one orphan with a live future seam (append-only `policy-audit.jsonl` governance evidence; intended emission points: commit_guard_hook, risk override, merge gate). Wiring = design work = follow-up issue (operator default: the wave stays pure deletion/triage). Both randy (steelmanned) and alphonso (maps any transport/port adoption to epic #2173) converge.

## D5 — Gate mechanics: atomic delete+drain, and the category_b −13 split

`test_no_dead_modules.py:590` asserts `_ALLOWLIST - actual_orphans == ∅` — deletion cannot ship without its allowlist drain in the same tip (and vice versa). Hence C-006: no standalone gate-drain WP. Arithmetic trap (renata): `identity_aliases::with_tracked_mission_slug_aliases` is BOTH the category_4 symbol-allowlist row AND a `_CATEGORY_B` member — so category_b's 237→224 = −1 (IC-01) + −12 (IC-03). An implementer draining only the 12 and writing 224 reds the count gate; the split is now stated in FR-003/FR-005.

## D6 — patch() interception proofs (the silent-no-op class)

The 10 `patch("specify_cli.tasks_support...")` sites are bare return-value redirects — no `assert_called*` exists at the exact sites where the silent-no-op risk lives. AC 1.2 therefore requires per rewritten site: an added call assertion OR a red-first bogus-target flip proof. Trap recorded: the correct patch target is the **consumer's lookup namespace** after re-anchoring, not necessarily the definition module `task_utils.support`.

## D7 — Scope verdict: legitimately thin; no-fold #2290/#2291; ~13 LOC doc hygiene folds

Operator flagged thin scope → dedicated related-surfaces sweep (randy) + fold adjudication (paula). Convergent verdict: **do not pad**. Structural proof: `test_no_dead_modules` is a bidirectional ratchet and passes green on main → no uncategorized dead module exists by construction. `_baselines.yaml` full enumeration: category_1 (87 migrations, live via pkgutil), category_2/3 (live), category_5 (0), category_6 (3 — #2291 territory per C-003), symbol categories not drainable-now beyond mission scope. #2290/#2291 are live-caller re-point migrations — categorically different risk class (paula: folding #2291 ~doubles the mission and injects delete-before-re-point ordering hazards). Folds accepted: `documentation-mission.md:899-901` re-point (~3 LOC, live doc) + `degod-unshim-inventory.md` strike-through (~10 LOC, closeout). New untracked debt classes surfaced → FR-008 files fresh issues (pre-3.0 migration retirement; legacy-contract allowlist backfill), operator may veto.

## D8 — Deletion set is closed (cascade + residue checks)

- Cascade-orphaning: deleting the 4 orphans strands no sibling (replay/glue import nothing first-party; task_profile imports only heavily-used core; lifecycle imports only the package-wide `ActorRef`).
- No empty packages result; no migration imports any target (zero grep hits across `upgrade/migrations/`); no doctrine YAML / skills manifest / pyproject entry-point references any target; docs-freshness gates read page inventories, not in-body code paths → no LEAK risk.
- Zero Design-P `resolution_gate_allowlist.yaml` keys and zero audit-inventory rows point into targets — the content-pinned gates do not engage.
- ~12 string-literal `workspace_context.py` path refs in historical mission-fixture `owned_files` lists: leave as-is (disposition recorded in spec edge cases).

## Pre-mission op record

#2258 (`record_merge`/`finalize_merge` prune) executed as governed op `01KWKWQC58KWSN3VDCZ3VZB2GR` before planning: deadness verified (zero src callers; `merge_history` has no reader — TypedDict field + preservation docstring intentionally retained as legacy on-disk audit-trail compat), 2 functions + 4 test classes deleted (−248 LOC), gates green, commit `c194f8d`, evidence commented on #2258, closes via this mission's PR.
