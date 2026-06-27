# Approach Trace — coord-read-residuals-merge-lanes-and-identity-routing-01KW2M8V

**Purpose:** a running log of the approach/strategy decisions taken while running this
mission — the "how we chose to work" record (distinct from `design-trace.md`, which records
the "what the fix looks like" decisions). Seeded at spec→plan; **append during implement**;
assessed at close.

> Format per entry: `[date] [phase] DECISION — rationale — alternative rejected`

---

## Seeded during spec → plan (2026-06-26)

1. **[spec] One mission, two lanes — not two missions.** #2185 (merge/lanes) and #2186
   (identity) are kept as one mission with Lane A / Lane B. Rationale: shared resolver family,
   shared gate file (`test_gate_read_literal_ban.py`), shared canonicalizer-floor file, and a
   shared coord fixture — two missions would contend on the *same* test/gate files. Alternative
   rejected: split into two missions (worse — concurrent edits to one ratchet file + floor).

2. **[spec] Sequence the landing AFTER the implement-loop sibling; spec/plan in parallel now.**
   Rationale: the implement-loop mission deposits the #2185 `_DIR_READ_KNOWN_RESIDUALS` pins and
   widens the dir-read scanner to whole-`src`; this mission inherits both and drains Lane A pins.
   Source line numbers in the owned surfaces are stable across the sibling's merge (C-009 forbids
   it from editing them), so spec/plan can proceed in parallel. Alternative rejected: land first
   (would force this mission to duplicate the sibling's scanner-widening → guaranteed conflict).

3. **[research] 3-agent code-state research before authoring the spec.** Rationale: the tickets
   listed exact files/lines but the kind labels were suspect; parallel readers (Lane A sites,
   Lane B sites, implement-loop strategy) grounded the spec in verified facts. Payoff: caught **6
   mislabeled artifact kinds** + 3 undercounted mixed sites + the gate-blindness fact. Alternative
   rejected: spec straight from the ticket text (would have propagated the wrong kinds).

4. **[spec→plan] Post-spec adversarial squad before /plan (4 profile-loaded lenses).** Rationale:
   planning point-cut cadence; squads reliably catch undersizing/false-greens. Payoff: caught the
   **CRITICAL `build_coord` false-green** (non-divergent husk), the FR-006/C-SEQ incoherence, the
   broken Lane B pin-drain narrative, and the identity-arm blast radius — all folded into the spec
   before planning. Alternative rejected: straight to /plan on the first-draft spec.

5. **[env] Isolated fresh clone + worktree discipline.** All work runs in dedicated clones/worktrees
   off `upstream/main`; the primary clone (live implement-loop mission) and the doctrine-qol #2083
   clone are never touched. Rationale: parallel missions must not disturb in-flight work.

## Appended during implement (2026-06-27)

6. **[post-rebase] 4-lens rescoping squad on the analyze BLOCK (F1).** The analyze gate blocked on the vacuous "#2185 pin-drain" premise; a profile-loaded squad (priti/alphonso/renata/debbie) re-scoped Lane A from "drain an empty pin set" to "route + prove via a real static call-shape arm + the divergent FR-009 fixture." Payoff: confirmed the empty-set, corrected T009's false-STOP, deleted the no-op drains (T015/T021), kept #2187 as the sole genuine drain, and surfaced the dependency inversion + wrong-fixture false-green. Alternative rejected: implement Lane A on the vacuous premise.

7. **[rescope→regen] Operator course-correction: regenerate, don't patch.** Rather than trust the in-place struggle-patch, the chosen flow was **3-lens spec/plan review → apply 11 precise corrections → delete the WP layer → canonical `/spec-kitty.tasks` regen**. Rationale: the durable reframe lives in spec/plan; the WP layer is generated and should be regenerated from a validated foundation, not hand-surgered. Payoff: analyze `ready`, clean deps, the regen even fixed an unrouted-site gap. Lesson (folds into [[feedback_canonical_sources_discipline]]): a thrashing in-place planner is the signal to regenerate canonically.

8. **[scope] Adopted the lanes.json call-shape arm (unification, not parity).** Operator-approved: alphonso found the #2185 "permanent ratchet vocabulary gap" was closeable — generalize the identity call-shape arm to also flag `read_lanes_json`/`require_lanes_json` off coord-aware resolvers. So #2185 gets a REAL static ratchet, not fixture-only coverage. Alternative rejected: fixture-only backstop (fragile to future unrouted lanes.json reads).

9. **[implement] Per-WP review with C-001 trace as the priority adversarial check.** WP01 routed identity reads that happened to be censused by the coord-authority WRITE floor → the review's first duty is verifying no STATUS-write leg was dragged to PRIMARY (#2155). Rationale: the one regression that must not slip on this mission class is a status-leg swap.

<!-- append during implement: rebase-onto-post-implement-loop-main, WP sequencing decisions,
     any approach pivots, the pre-merge full-gate dry run. -->

## Close-out assessment (2026-06-27)

The **regenerate-don't-patch** course-correction (entry 7) was the pivotal call: after the in-place reframe thrashed, deleting the WP layer + regenerating canonically from a 3-lens-validated spec/plan produced a foundation so clean that **all 5 WPs approved first-pass with zero rejection cycles**. The **C-001-trace-first** review discipline (entry 9) caught no violations — every routing was correct — so it paid off as *confidence* (an auditable per-WP STATUS-leg-stayed-coord verdict), not as catches. The **lanes.json-arm** decision (entry 8) is realized: the live FR-007 arm gates the real tree (0 un-pinned). Net: the squad-heavy front-load (rescope + spec/plan review) bought a frictionless implement loop.
