# Phase 0 Research: Documentation Quality Hardening Gate

Resolves the open architecture decisions the spec/squad flagged. Each entry: **Decision / Rationale / Alternatives considered**. Two scope forks (kitty-specs delink; hidden-checker unification) were already decided by the operator and are recorded here for traceability.

---

> **OBSOLETE (post-rebase, `ccd278061`).** The byte-identity ADR invariance gate was retired upstream in the 3.2.4 cycle. The former FR-010 (comparator pre-image transform) is WITHDRAWN; no comparator exists to keep passing. ADR body edits are now plain edits. Retained below for historical audit only — do **not** implement this. See spec.md "Scope Change".

## R-01 — FR-010: how to keep the byte-invariance comparator passing after the sanctioned ADR-body edits

**Decision**: Extract the FR-008 link migration as a single pure function `migrate_adr_body_links(body, file_path) -> body'` and apply it in **two** places: (a) the live one-time fix of the committed ADR bodies, and (b) inside the comparator, to the recovered git pre-image *before* `convert()` + byte comparison. The comparator then asserts `committed_body == convert(migrate(pre_image))`.

**Rationale**: The invariant is a git-blob proof (`test_adr_content_invariance.py` recovers the merge-base blob, runs `convert()`, asserts byte-equality), not a stored snapshot. Transforming the pre-image with the *same* function keeps the proof non-vacuous: only the sanctioned link edits are tolerated — any *other* body drift still fails. One transform function is the single source of truth, so the live fix and the comparator can never disagree (this is the intended FR-008↔FR-010 coupling). The `compared==116`-style non-vacuity assert continues to hold (count rises to the migrated set, not zero).

**Alternatives considered**:
- *Per-file sanctioned-delta allowlist* (treat each migrated ADR like the existing `_SANCTIONED_SELF_AMENDMENT` reconciliation ADR): rejected — it disables byte-invariance for those 12 files entirely, so future accidental drift in them goes uncaught. Weaker guarantee for the same effort.
- *Re-baseline to post-migration blobs*: rejected — there is no separate stored baseline to re-point; the baseline *is* the pre-move blob, and we must not lose the move-time invariance proof for the other 105 ADRs.

---

> **OBSOLETE (post-rebase, `ccd278061`).** With byte-invariance retired, the 2 non-dated ADRs need no invariance source — FR-011 is now a plain census widen (`_DATE_PREFIX`/`_adr_files_on_disk` include them; `_EXPECTED_CENSUS` 117→119). Retained for audit only. See spec.md "Scope Change".

## R-02 — FR-011: invariance source for the 2 born-in-`docs/` (non-dated) ADRs

**Decision**: For ADRs with no pre-move blob (`adr-connector-auth-binding-separation.md`, `adr-github-app-installation-authority.md`), define the invariance source as the **blob at the file's introduction commit** (`git log --diff-filter=A --follow --format=%H -- <path> | tail -1`, then `git show <sha>:<path>`). The comparator proves "body byte-identical to when the ADR was introduced." Widen `_DATE_PREFIX` handling so `_adr_files_on_disk` includes them (census 117→119) and the comparator routes dated→merge-base-blob, non-dated→introduction-blob.

**Rationale**: Consistent with the existing git-blob approach (no new stored artifact to maintain or drift). The introduction commit is the natural "born" baseline for a doc that never moved. Keeps a single comparator with a branch on baseline-source, not two parallel invariance systems.

**Alternatives considered**:
- *Stored content hash in a lockfile row*: rejected — introduces a maintained artifact and a second invariance mechanism; the git object store already holds the truth.
- *Leave the 2 ADRs uncounted*: rejected — that is the exact blind-spot #2245 asks to close.

---

## R-03 — FR-007: CHANGELOG sync direction & mechanism

**Decision** (operator-confirmed direction): canonical `docs/changelog/CHANGELOG.md` is the **source**; root `CHANGELOG.md` is **generated** from it by a new `scripts/docs/sync_changelog.py`. The generator strips the canonical's YAML frontmatter and emits the body verbatim to root. A blocking test asserts `root == generate(canonical)`; the "shared region" is precisely *the canonical body after its frontmatter block*. FR-006's link fixes are made on the canonical and flow to root via regeneration.

**Rationale**: Matches the existing "relocate-with-alias" contract (root persists for release tooling). Single direction = one owner (Lane B), no two-way reconciliation. Root stays a valid Keep-a-Changelog file for `extract_changelog.py` (reads root at repo cwd, `utf-8-sig`), because it is the canonical body minus frontmatter — still Keep-a-Changelog-shaped. The current 244-byte divergence (frontmatter + a stale `architecture/2.x/05_ownership_map.md` line) is resolved by regeneration after the link fix.

**Alternatives considered**:
- *Two-way sync-assertion only (no generator)*: rejected — leaves both files hand-edited; fails on day-one divergence and doesn't prevent future drift, only detects it.
- *Make root the source*: rejected — canonical lives in the published `docs/` tree (the navigable SSOT); root is the build/release artifact.

---

## R-04 — FR-005: how to retire the 3 hidden parallel checkers

**Decision** (operator-confirmed unify): In IC-05 (after the link fixes land and `EXCLUDE_PREFIXES` is emptied), **remove the link-resolution test functions** `test_architecture_relative_links_resolve`, `test_user_journey_persona_links_resolve` (`test_architecture_docs_consistency.py`), and `test_versioned_docs_relative_links_resolve` (`test_versioned_docs_integrity.py`). Their scopes (`docs/architecture/**`, `docs/plans/user_journey/`, `docs/archive/**`, `docs/index.md`) are all under `docs/`, so the widened `check_dead_body_links` covers them. **Preserve any non-link assertions** those test modules carry (they may validate other invariants) — only the hand-rolled link loops are removed. Add a coverage check confirming the gate visits those subtrees.

**Rationale**: Delivers the mission's stated purpose — exactly one body-link resolver in CI. Removing duplicate hand-rolled `re.compile(r"\[…\]\(…\)")` loops eliminates the maintenance + divergence risk. Routing scope through the single gate is "unify not parity."

**Alternatives considered**:
- *Keep them + document co-existence*: rejected by operator decision — leaves 4 overlapping checkers; "unify" would be only partial.
- *Refactor each to call `check_dead_body_links` with a scope arg*: viable but heavier; deletion is cleaner once the gate covers `docs/` wholesale. Keep this as a fallback only if a subtree needs narrower semantics.

---

## R-05 — NFR-003: emitting `(file, line, target)`

**Decision**: Add `line: int` to the `Unresolvable` dataclass and compute it in `check_dead_body_links` via newline counting at the match offset (`body.count("\n", 0, match.start()) + 1`, accounting for the frontmatter offset already stripped by `split_frontmatter`). Update all `Unresolvable` consumers and `TestLiveTreeGate` assertions.

**Rationale**: This is the existing pattern in `test_architecture_docs_consistency.py` (which already counts newlines); reusing it keeps behavior familiar. Directly satisfies the operator's "list every failed file/line" requirement so a failure is self-diagnosing.

**Alternatives considered**:
- *Report file+target only*: rejected — that is the "something failed to validate" weakness the operator explicitly called out.
- *Byte offset instead of line*: rejected — line numbers are what humans/agents act on.

---

> **PARTIALLY OBSOLETE (post-rebase, `ccd278061`).** The 4 link sub-classes below still correctly describe FR-008's link-repair work. BUT the "single shared `migrate_adr_body_links` transform" framing is WITHDRAWN — with byte-invariance retired there is no comparator to share the transform with, so FR-008 is a plain repair (prefer `relative_link_fixer.py --fix` for the docs-internal classes; manual delink for the `kitty-specs/` class). No new transform module. See spec.md "Scope Change".

## R-06 — ADR link migration sub-classes (FR-008 enumeration)

**Decision**: Treat the 27 links as four mechanical classes, each handled by `migrate_adr_body_links` (R-01): (a) moved-dir rewrites to live `docs/` targets (`docs/development/→docs/guides/`, `docs/how-to/→docs/guides/`, `docs/engineering_notes/→docs/plans/engineering-notes/`); (b) nested-`adr/` segment removal (`../2.x/adr/X → ../2.x/X`); (c) cross-era sibling depth fix (3.x ADR → `../2.x/…`); (d) **delink** the ~9-12 `kitty-specs/` links to a stable ref (merged-PR/commit URL or superseding canonical doc) or remove if purely historical.

**Rationale**: Classes (a)-(c) resolve to live `docs/` targets the gate can validate post-flip. Class (d) is delinked (operator decision) so no `kitty-specs/` target is ever validated and the gate resolver stays `docs/`-scoped. The implementation enumerates the exact live set at execution (count is indicative; verified 27 today).

**Alternatives considered**: depth-fixing the `kitty-specs/` links + repo-wide resolver — rejected by operator decision (ADRs shouldn't pin to transient mission state; avoids a bigger resolver change).

---

## Open items carried to design

None blocking. All NEEDS-CLARIFICATION-class questions are resolved above; data-model.md and contracts/ encode the chosen shapes.
