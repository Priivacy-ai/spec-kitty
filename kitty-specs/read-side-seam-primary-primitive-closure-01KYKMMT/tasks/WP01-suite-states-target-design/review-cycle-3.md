---
affected_files:
- path: tests/architectural/test_gate_read_literal_ban.py
- path: tests/architectural/test_trio_seam_only.py
cycle_number: 3
mission_slug: read-side-seam-primary-primitive-closure-01KYKMMT
reproduction_command: |
  cd /home/stijn/Documents/_code/SDD/fork/spec-kitty/.worktrees/read-side-seam-primary-primitive-closure-01KYKMMT-lane-a
  uv run python -c '
  import ast, sys; sys.path.insert(0, ".")
  from tests.architectural.test_gate_read_literal_ban import _WRITE_ARM_SURFACES, _find_function, write_arm_anchors
  def sub(kind):
      class T(ast.NodeTransformer):
          def visit_Call(self, n):
              self.generic_visit(n)
              f = n.func
              nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute) else None)
              if nm == "primary_feature_dir_for_mission":
                  return ast.copy_location(ast.parse("placement_seam(r, s).read_dir(MissionArtifactKind.%s)" % kind, mode="eval").body, n)
              return n
      return T()
  for kind in ("PRIMARY_METADATA", "STATUS_STATE"):
      for surf in _WRITE_ARM_SURFACES:
          tree = sub(kind).visit(ast.parse(open(surf.rel_path).read()))
          ast.fix_missing_locations(tree)
          print(kind, surf.func, write_arm_anchors(_find_function(tree, surf.func)))
  '
reviewed_at: '2026-07-28T12:16:30Z'
reviewer_agent: reviewer-renata
verdict: approved
wp_id: WP01
---

# WP01 Review — APPROVED (cycle 3)

Commits `13ed4a279` + `333614aa8` + the cycle-1 fix `6c9ec7f7e`. **B1 is closed.** Nothing
regressed, and the specific way this fix could have been wrong in a new direction — broadening
the write-arm anchor branch without preserving kind discipline — does not occur.

## Why this artifact exists

`review-cycle-2.md` is **not** an independent second rejection. Its body is byte-identical to
`review-cycle-1.md` (verified by `diff`; only a leading blank line differs), wrapped in
synthetic frontmatter: `reviewer_agent: unknown`, `verdict: rejected`, empty `affected_files`
and `reproduction_command`. It is the tooling's copy of the cycle-1 feedback file, written when
WP01 was moved back to `planned` with `--review-feedback-file` pointing at cycle-1. There is
exactly **one** genuine rejection — mine, cycle 1 — and the fix below addresses it.

`_guard_rejected_verdict`
(`src/specify_cli/cli/commands/agent/tasks_transition_core.py:365`) resolves only the
**highest-numbered** `review-cycle-N.md` (`src/specify_cli/agent_utils/status.py:41`). This
artifact therefore supersedes by **being the latest**, not by erasing anything: cycles 1 and 2
are left byte-for-byte intact, and no override flag was used.

**Timestamp note (record honesty).** Cycle-1's self-recorded `reviewed_at: 2026-07-28T12:20:00Z`
was a rounded value written *ahead* of wall clock. Its real write time was `11:47:48Z` — the
value the tooling captured in cycle-2's frontmatter, consistent with the file mtime and with the
fix commit at `11:58:02Z` (which would otherwise appear to predate the review it answers). This
artifact's `reviewed_at` is the true wall-clock time and is genuinely after cycle-1's *actual*
time. Recorded rather than back-dated to make the numbers line up.

---

## B1 — CLOSED

`_primary_partition_seam_invoked_in` is the seam-idiom counterpart of `_anchor_invoked_in`:
**kind**-discriminated via `_is_primary_partition_read_dir_call` (which resolves the `kind`
argument through the real `is_primary_artifact_kind` predicate — never a bare callee name), and
it recognises a PRIMARY-partition `<seam>.read_dir(kind)` call anywhere in the function, bound
or inline. That is the actual post-WP08 shape of all three real write-arm surfaces, which are
thin adapters over `read_target_branch_from_meta` and never build the literal
`<dir> / "meta.json"` join `_builds_meta_path_from_primary_seam` requires.

### Mutation table — re-run independently, not taken on report

I rebuilt the harness at **AST level** (an `ast.NodeTransformer` replacing every
`primary_feature_dir_for_mission` **Call node**) rather than reusing cycle-1's textual
`#(`-comment trick, which produces an `IndentationError` on the multi-line call in
`core/paths.py`. No repository file was modified. Three real surfaces × five mutants:

| Mutant | Required | `get_feature_target_branch` | `resolve_target_branch` | `finalize_tasks` |
|---|---|---|---|---|
| baseline | green | `(F, T)` GREEN ✅ | `(F, T)` GREEN ✅ | `(F, T)` GREEN ✅ |
| → candidate resolver | bites | `(F, F)` REDS ✅ | `(F, F)` REDS ✅ | `(F, F)` REDS ✅ |
| → unrelated third resolver (M8 case) | bites | `(F, F)` REDS ✅ | `(F, F)` REDS ✅ | `(F, F)` REDS ✅ |
| **→ post-migration seam idiom** | **GREEN** | **`(F, T)` GREEN ✅** | **`(F, T)` GREEN ✅** | **`(F, T)` GREEN ✅** |
| → `read_dir(STATUS_STATE)`, same shape | bites | `(F, F)` REDS ✅ | `(F, F)` REDS ✅ | `(F, F)` REDS ✅ |

The row that had to flip did flip — the post-migration idiom is now GREEN on all three surfaces
(it was `(F, F)` in cycle 1, the B1 defect). **And the row that must not regress did not**: a
`read_dir(STATUS_STATE)` call in the identical shape still fails to satisfy `reads_via_primary`
on all three. A STATUS read cannot satisfy a PRIMARY-anchor assertion. Kind discipline survived
the broadening, so the outcome that would have been *worse* than the original B1 does not exist.

---

## Over-broadening — real, and specifically NOT a loosening

`_primary_partition_seam_invoked_in` is `any(PRIMARY read_dir anywhere in func)`, so I probed it
adversarially with four synthetic functions:

| Probe | Result |
|---|---|
| compliant post-WP08 thin adapter | GREEN (intended) |
| unrelated `read_dir(SPEC)` early + meta read via a third unrecognised construct | **GREEN — the over-broad case** |
| unrelated `read_dir(LANE_STATE)` early + candidate **literal join** | REDS (`cand=True`) — negative arm still bites |
| unrelated `read_dir(LANE_STATE)` early + candidate **thin adapter** | GREEN — the pre-existing N1 deferral, unchanged |
| **control: unrelated `primary_feature_dir_for_mission(...)` call + third-construct meta read** | **GREEN *pre-fix* as well** |

So the answer to "can a function that merely *touches* a PRIMARY seam satisfy the write-arm
anchor assertion without anchoring its meta read there" is **yes** — but that is **not a
regression introduced by this fix**, and it is not grounds for rejection:

1. **The control row is decisive.** The "anywhere in the function" granularity is exactly
   `_anchor_invoked_in`'s pre-existing shape. A function calling the wrapper for an unrelated
   reason and resolving meta via a third construct passed the gate *before* this fix too. The
   fix mirrors an accepted shape at the seam; it does not invent a weaker one.
2. **Cycle-1 feedback named this shape as acceptable**, verbatim: "*or a PRIMARY-partition
   `read_dir` call occurring in the function at all*". The implementer took an option the
   reviewer offered. Rejecting for that would be moving the goalposts.
3. **NFR-005's widening-plus-bite-test pairing holds.** `_WRITE_UNANCHORED_OTHER_CONSTRUCT`
   carries no PRIMARY `read_dir`, so the M8 anti-vacuity test still bites (verified under
   mutation, below).
4. The candidate-literal-join negative arm is untouched and still fires.

Recorded as a non-blocking hardening for successors, below — not as a defect.

---

## Both new self-tests bite

I mutated each test's **subject** (the predicate), not its fixture, and called the tests
directly:

| Mutation of the predicate | thin-adapter test | kind-discipline test | M8 anti-vacuity test |
|---|---|---|---|
| none (baseline) | PASS | PASS | PASS |
| new signal stubbed to `False` | **FAILS** | PASS | PASS |
| `_is_primary_partition_read_dir_call` made callee-name-blind (`read_dir`, any kind) | PASS | **FAILS** | PASS |
| seam predicate matches any call at all | PASS | **FAILS** | **FAILS** |

Each test fails on precisely the mutation it exists to catch, and neither is satisfiable
independently of its subject. This WP already shipped one vacuous assertion (that *was* B1);
these two are not it.

---

## Record honesty — the claims now match the code

- `write_arm_anchors`' docstring labels shape (2) as "*a shape NONE of the three real write-arm
  surfaces uses today or after WP08*". The false "surviving spelling" claim is gone.
- The one surviving `"surviving spelling"` phrase in the tree
  (`test_gate_read_literal_ban.py:749`) attaches to shape (4), where it is **true**.
- The pre-existing literal-join test is renamed
  `test_write_arm_recognises_primary_seam_idiom_literal_join_spelling`, with a docstring stating
  it covers a shape no real surface uses.
- The `reads_via_candidate` literal-join-only deferral is stated explicitly, including that it
  makes the negative arm vacuous for a hypothetical candidate-anchored thin adapter.
- The `unanchored` failure message now names the **target** anchor alongside today's, so it no
  longer instructs an implementer to resurrect a deleted primitive.
- `research/expected-reds.md` `## WP01` carries the corrected narrative and mutation table.
- Non-blocking N2/N3 folded into `test_trio_seam_only.py`: the two imports the trio assertion
  depends on staying live are named (`cli/commands/agent/workflow.py:356`,
  `acceptance/__init__.py:722`), and the
  `test_allowed_read_path_resolver_names_are_currently_used` node-id misnomer is recorded as
  deliberate naming debt kept stable for the gate-coverage baseline.

No remaining claim that a dead branch is live.

---

## Reconciliation — verified, not accepted on report

Six C-008 gates, targeted node set only (never the full `tests/architectural/` suite, per
C-008): **168 passed / 3 failed / 0 collection errors** — net **+2** from the two new
self-tests, matching cycle-1's 166. The three reds are node-for-node identical to cycle 1 and to
the `## WP01` ledger, all **assertion** failures about behaviour, each FR-traceable:

| Node id | FR | Greened by |
|---|---|---|
| `test_coord_read_residuals_closeout.py::test_fr007_arm_live_identity_scan_is_clean` | FR-014 | WP04 |
| `test_trio_seam_only.py::test_trio_imports_route_only_through_seam_wrappers` | FR-004 / FR-005 | WP05 |
| `test_trio_seam_only.py::test_allowed_read_path_resolver_names_are_currently_used` | FR-004 / FR-012 | WP05 |

No unpredicted red. `ruff check` exit 0 on all four changed modules; `mypy` clean; **0** new
`# noqa` / `# type: ignore` / `skip` / `xfail` anywhere in the diff. **Zero `src/` changes**,
confirmed by `git diff <base>..<lane> --name-only | grep '^src/'` → 0. The foreign honest-red P0
`tests/sync/test_sync_consent_default_deny.py` (#3031, ADR `2026-07-17-1`) is untouched (C-010).

### Anti-pattern checklist

1. Dead code — **N/A/PASS**: `_primary_partition_seam_invoked_in` has a live caller
   (`write_arm_anchors`); no production code added.
2. Synthetic-fixture test — **PASS**: the gate assertions scan real `src/` modules; the
   synthetic snippets are self-tests of the gate's own predicate and provably bite under
   subject mutation.
3. Silent empty return — **PASS**: no new effect-free handler or bare empty return.
4. FR coverage — **PASS**.
5. Frozen surface — **PASS**: zero `src/` changes, the WP's own hard constraint.
6. Locked decision — **PASS**.
7. Shared-file ownership — **PASS**: both changed files are in WP01's `owned_files`.
8. Production fragility — **N/A**: no production `raise` added.

---

## Non-blocking — recommendations for successors, not conditions of this approval

**R1. Tighten the positive arm so the bound name must reach a meta-read consumer.** Require the
name bound from the PRIMARY `read_dir` to actually reach the meta read — a
`read_target_branch_from_meta` argument, or the left operand of a `/ "meta.json"` join — using
the existing `_names_bound_from_primary_read_dir` primitive. The predicate is currently **looser
than its own new fixture**, which already has exactly that shape. This matters most for
**WP06**: `_PRIMARY_ARTIFACT_KINDS` includes `SPEC`, `LANE_STATE`, `TASKS_INDEX` and
`WORK_PACKAGE_TASK`, and `finalize_tasks` is ~200 lines
(`mission_finalize.py:1589-1788`), so once WP06 routes its reads through the seam the positive
arm is likely to be satisfied by an incidental `read_dir` and go **near-tautological for that
one surface**. Do not read the positive arm as protection it is not providing there.

**R2. The N1 `reads_via_candidate` deferral is unchanged.** It stays literal-join-only, so a
candidate-anchored *thin adapter* remains invisible to the negative arm. Coverage is preserved
indirectly (the candidate-rename mutation is caught by the positive arm), and the deferral is
now stated honestly in the docstring. A future widening pass should close it symmetrically.

**R3. Lane `kitty-specs/` delta is merge staleness, not data loss.** The
`status.events.jsonl` / `status.json` changes in the lane diff are the lane being *behind* the
mission branch: all 5 absent event lines carry `"wp_id": "WP02"` and are present on the mission
branch, and `status.json` differs only in WP02's lane state. Zero WP01 events lost; resolves on
the next merge. No action for WP01.

**R4. Tooling observation for the orchestrator.** The rejected-artifact guard cannot distinguish
a duplicated feedback copy from a fresh independent verdict, so an ordinary cycle-2 approve is
blocked until a superseding artifact is authored. Worth an upstream issue: the copy written by
the rejection path should not carry a `verdict: rejected` frontmatter that later reads as a
second reviewer's ruling.

## Verdict

**APPROVED.** B1 closed and independently re-verified by mutation; kind discipline preserved
under the broadening; both new self-tests bite; the record now matches the code; reconciliation
reproduced exactly at 168/3/0 with zero `src/` changes. R1–R4 are carried forward as
non-blocking notes for WP04/WP05/WP06/WP08 and the orchestrator.
