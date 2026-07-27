# Renata — DoD Rigor Review (post-tasks adversarial)

**Reviewer:** reviewer-renata · **Date:** 2026-06-16 · **Lens:** Is each WP's Definition of Done
OBJECTIVE, NON-GAMEABLE, and INDEPENDENTLY REVIEWABLE from the diff alone?

**Scope verification (grounding the review in code):**
- Confirmed `branch_naming.py` exposes `mid8` (raises, line 122) + `resolve_mid8` (line 169) + the
  `_legacy_failover_warned`/`reset_legacy_failover_warning` seam — WP01's premise is real.
- Confirmed `tests/architectural/test_no_worktree_name_guess.py` today detects *composes* (idiom 3,
  `_is_bare_mid8_dir_compose`), has NO `[:8]` slice detector, and carries an `_ALLOWED_SITES` frozenset
  — WP02's "new detector, not a tweak" framing is honest.
- Confirmed `invocation_id[:8]` lives at `invocation/executor.py:469` — WP02 non-target is real.

---

## Overall verdict

**DoDs NEED-HARDENING.** The mission's *test discipline* (function-over-form, verification-by-deletion,
TDD-first, byte-parity tables) is unusually well-specified — this is a strong tasks decomposition. But
the DoDs lean on the **word** "byte-parity"/"characterization" without **mechanically forbidding the
single most likely gaming move: capturing the golden value AFTER the edit.** Six of seven WPs share this
gap, and three carry additional reviewability/precision holes. None are fatal; all are one-line prompt
additions.

**Count: 6 DoD checkboxes are gameable as written; 2 are vague/unreviewable in isolation.**
(Gameable: WP01 byte-parity, WP03 characterization, WP04 byte-parity, WP05 byte-parity, WP02 "shrank",
WP06 #1971-tail "converge". Vague/cross-WP: WP02 allow-list-shrank claim, WP06 #1888 over-reject.)

---

## The one systemic anti-gaming gap (applies to WP01/03/04/05)

Every "byte-parity"/"characterization" DoD can PASS WITHOUT PROVING THE CONTRACT via the classic move:
**write the test AFTER routing, snapshotting the new (already-routed) output, or asserting
`resolve_mid8(x) == resolve_mid8(x)` (tautology) instead of comparing to the pre-change literal.**
The spec's C-003/C-004 say "characterization test lands before the change" but the WP DoDs do not make
that *checkable from the diff*.

**Required addition to WP01/WP03/WP04/WP05 DoD (verbatim, anti-gaming):**
> - [ ] Golden values are **literals captured from HEAD BEFORE any edit** — the characterization/byte-parity
>   test asserts `actual == "<hard-coded expected string>"`, NOT `==` between two live calls of the new code.
>   Reviewer can confirm by checking the test commit predates (or the test literals match) the pre-routing
>   output. A test whose expected side is a function call into the routed seam is REJECTED.

Reviewer-checkable signal: in the diff, the assertion RHS must be a string/None/`""` literal, not a
`resolve_mid8(...)`/`mid8(...)` call. This is the difference between a real characterization test and a
self-referential tautology.

---

## Per-WP assessment

### WP01 — Seam SSOT entrypoint (`mid8` → `_mid8`)
- **Objective?** Mostly. "`mid8` is private; not in `__all__`; 3 internal callers updated" is fully
  diff-checkable. "mission-id-only equivalence holds + tested" is objective (a named assertion).
- **Gameable?** YES — "composed names byte-identical (NFR-001)" is gameable: the WP authors the test in
  the SAME diff, so the implementer can snapshot post-rename output. (The rename is behavior-preserving so
  risk is low, but the DoD shouldn't *rely* on that.)
- **Reviewable in isolation?** YES — it's the foundation, no upstream deps.
- **Anti-gaming requirement to ADD:**
  - The systemic literal-from-HEAD requirement above.
  - Make the public-surface check **negative and mechanical:** *"a test asserts `from ...branch_naming
    import mid8` raises ImportError / `mid8 not in branch_naming.__all__` AND `_mid8` not in `__all__`."*
    "ensure `_mid8` is not exported" (T002) is currently prose, not a checkbox artifact.

### WP02 — Ratchet AST short-id detector
- **Objective?** Partial. "AST detector catches the 5 shapes incl. dashboard/scanner.py" IS objective IF
  the self-test (T021) enumerates all 5 shapes. "Allow-list empty/minimal & justified" is objective.
  "Honesty note present" is objective.
- **Gameable?** YES, two ways:
  1. **"catches the 5 var-name-independent shapes"** — gameable unless the guard self-test plants ALL FIVE
     concrete shapes (`str(x)[:8]`, `mid[:8]`, `raw_mid[:8]`, `*_id_meta[:8]`, intermediate-var). T021 as
     written plants only "a bare `mission_id[:8]`" — a detector that catches ONLY that one shape would pass
     T021's literal text while missing the 4 harder shapes that are the whole point of FR-004.
  2. **"allow-list actually shrank"** — needs a concrete before-count. "Confirm the allow-list shrank vs the
     pre-mission baseline" has no pinned baseline number, so it's an unverifiable claim.
- **Reviewable in isolation?** PARTIALLY — this is the cross-WP risk. WP02 depends on WP03/04/05 having
  deleted the sites for the allow-list to be empty. If reviewed before those land, "allow-list empty" is
  unprovable. The dep ordering (WP02 lands last) mitigates this, but the DoD should state the precondition.
- **Anti-gaming requirement to ADD:**
  - **"The guard self-test plants ALL FIVE shapes from FR-004/paula-missed-paths as separate fixtures and
    asserts EACH is flagged; a self-test covering fewer than 5 shapes is REJECTED."** (Closes the
    catches-only-one-shape gaming move.)
  - **"DoD records the pre-mission allow-list entry count as a committed literal in the test (or PR body),
    and asserts the new count is strictly less; NFR-003's `mission_id[:8]`-class entries → 0 is asserted by
    name."** (Makes "shrank" objective.)
  - Add precondition note: *"reviewable only after WP03/04/05 sites are deleted (this WP's dep order
    guarantees that)."*

### WP03 — Route contract-sensitive sites (the 4 byte-parity landmines)
- **Objective?** YES — the per-site contract table (status/aggregate `""`, scanner `None`, doctor
  try/except, implement.py `meta["mid8"]` pref) gives reviewer concrete expected behaviors per site.
- **Gameable?** YES — "Characterization tests written first and green before & after" is the highest-value
  but most gameable DoD in the mission. The `None`-vs-`""` distinction is exactly the kind of thing a
  post-hoc snapshot would silently lock in WRONG (capture after a bug, test stays green forever).
- **Reviewable in isolation?** YES (depends only on WP01).
- **Anti-gaming requirement to ADD:**
  - The systemic literal-from-HEAD requirement, **with explicit per-contract literals**: *"the
    characterization test asserts the literal `""` for aggregate-absent, literal `None` for scanner-pseudo,
    the literal tolerant short-id display for doctor, and `None` for implement.py-no-meta — each as a
    hard-coded expected value captured from HEAD, not a re-call of the routed code."*
  - For T007 (doctor dead `try/except`): add *"a test exercises the short-id input path and asserts the
    SAME tolerant output as before removal — proving the removed `except` was genuinely dead, not silently
    changing behavior."* Right now "decision documented" is satisfiable by a comment alone with no proof
    the tolerance survived.

### WP04 — Route direct + 5 missed sites
- **Objective?** YES for the routing checklist. "Each addition confirmed mission-identity (not a foreign
  id)" is objective IF a reviewer can see the confirmation — but the DoD doesn't say WHERE that
  confirmation is recorded.
- **Gameable?** YES — same byte-parity gaming as WP03 ("outputs byte-identical (NFR-001)"). Also: **FR-002
  verification test (T013)** is gameable into a tautology — "no `ExecutionContext`-held re-derivation"
  could be "asserted" by a test that simply doesn't exercise any ExecutionContext path.
- **Reviewable in isolation?** YES (depends only on WP01).
- **Anti-gaming requirement to ADD:**
  - Systemic literal-from-HEAD requirement.
  - **For the 5 missed sites:** *"the WP handoff note records, per site, the evidence that the sliced value
    is `mission_id`-derived (the variable's provenance), not `invocation_id`/sha — a reviewer must be able
    to confirm without re-tracing."* (T012 says "confirm each is a mission-identity derivation" but the
    DoD doesn't require the evidence be written down — it's currently a trust-me.)
  - **For T013/FR-002:** *"the FR-002 test must construct a real `ExecutionContext`/`ActionContext` and
    assert mid8 is read from `IdentityFragment.mid8` (not re-derived) — a test that asserts a count of
    zero sites without exercising a context object is REJECTED."*

### WP05 — #2000 compose-routing
- **Objective?** YES — "no inline `<human>-<mid8>` f-string or bare `_mid8` remains in these files" is
  fully grep-able from the diff. Strong DoD.
- **Gameable?** YES — only the byte-parity test (same systemic gap). The risk here is the HIGHEST-stakes
  (these are worktree/branch CREATE paths — a wrong golden = mis-named worktrees forever), so the
  literal-from-HEAD discipline matters most here.
- **Reviewable in isolation?** YES (depends only on WP01).
- **Anti-gaming requirement to ADD:**
  - Systemic literal-from-HEAD requirement, emphasized: *"byte-parity test golden values for the composed
    dir AND branch names are literals captured from HEAD before edit, covering the NNN-strip and
    embedded-mid8 dedup edge cases the reviewer guidance names; a golden captured post-routing is REJECTED."*

### WP06 — #1888 existence-check fix + #1971-tail verify
- **#1888 (FR-007):** Objective and well-guarded — TDD-first repro, and the DoD names the precise
  over-reject trap ("future `create_intent` files NOT rejected; zero-match `**` globs still warn-not-fail").
  This is the CORRECT level of precision for the create_intent/future-file trap — **not vague.** Minor:
  add the positive artifact — *"a test asserts a declared owned path that is a legitimate `create_intent`
  future file VALIDATES (does not fail), and a zero-match `**` glob WARNS (asserts the warning, not just
  absence of failure)."* Currently the checkbox says it but no named test is required.
- **#1971-tail (FR-006):** **VAGUE/gameable.** "test proves the 3 entries converge under
  env-var/worktree/`.kittify` conditions" — a tautological "3 entries exist" or "all return the same
  type" test could pass this. The spec is explicit that the test must **DISPROVE the split-brain**, but
  the DoD doesn't forbid the weak form.
  - **Anti-gaming requirement to ADD:** *"the convergence test asserts all three entrypoints return the
    SAME resolved path for the SAME input under EACH of the three conditions (SPECIFY_REPO_ROOT set;
    worktree `.git`-file pointer; `.kittify` walk) — asserting equality of actual resolved Path values, not
    merely that three callables exist or share a return type. A test that does not exercise a divergent
    input (where a split-brain WOULD show) is REJECTED."*
- **Reviewable in isolation?** YES (no deps).

### WP07 — #2007 command-drift guard (doc-path/process correctness — Renata's blocking lens)
- **Doc-path correctness (THE blocking check per project review doctrine):** CORRECT. The WP repeatedly and
  prominently instructs **SOURCE-only** edits (`src/doctrine/...`) and explicitly forbids the generated
  agent copies (`.claude/`, `.codex/`). `owned_files` are all SOURCE + the architectural test + the typer
  walker. Test location (`tests/architectural/`) is correct. This is doctrine-compliant — **not blocking.**
- **Objective?** YES — "15 SOURCE drift refs repointed to registered surfaces" is checkable; "guard
  added, path-level, empty-frozenset ratchet, in existing docs-contract gate (no new CI job)" is
  diff-checkable.
- **Gameable?** PARTIALLY — "repointed commands actually exist in the Typer registry" is the key
  correctness claim and is well-guarded by the guard self-test itself (the guard validates against the
  registry). Good — the guard checks its own repoints. One gap: **T027** allows "if absent in SOURCE …
  record that finding and skip" — a lazy implementer could claim "absent, skipped" without grepping. Add:
  *"if the worktree-repair hint is skipped, the WP note must quote the grep command + its empty output as
  evidence."*
- **Reviewable in isolation?** YES (no deps).
- **Note:** T028's finding-code requirement (`unregistered-path`/`unknown-flag`/`internal-as-public`) +
  T029's self-test (plant nonexistent snippet → fails; clean → passes) is the right non-gameable shape —
  the self-test proves the guard isn't a no-op. Keep it.

---

## Top remediations to apply to the WP prompts (priority order)

1. **(WP01/03/04/05) Add the literal-from-HEAD anti-gaming checkbox** (verbatim text in the systemic
   section above). This single addition closes the dominant gaming move across the whole mission. The
   reviewer-checkable rule: assertion RHS is a literal, never a re-call of the routed seam.
2. **(WP02) Require the guard self-test to plant ALL FIVE shapes** (not just `mission_id[:8]`), and **pin
   the pre-mission allow-list count as a committed literal** so "shrank" is objective. Add the
   "reviewable only after WP03/04/05" precondition note.
3. **(WP06) Harden the #1971-tail DoD** to require asserting EQUAL resolved Path values under each of the
   three named conditions with a divergent input — explicitly REJECT the "3 entries exist / same type"
   tautology.
4. **(WP03 T007 + WP04 T012/T013)** Require the *evidence* to be written down: doctor short-id tolerance
   preserved (a test, not just a comment); the 5 missed sites' mission-identity provenance recorded; the
   FR-002 test must construct a real context object.
5. **(WP07 T027)** Require grep-evidence if the worktree-repair hint is "skipped."

---

## One-line verdict

**DoDs NEED-HARDENING** — strong decomposition and honest scoping, but 6 byte-parity/characterization
checkboxes are gameable by capturing goldens post-edit, and the WP02 "5 shapes"/"allow-list shrank" and
WP06 "#1971 converge" claims are not objectively reviewable as written; all are closable with the
five one-line prompt additions above.
