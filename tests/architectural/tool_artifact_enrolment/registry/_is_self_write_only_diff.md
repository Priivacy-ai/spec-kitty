# Exemption mechanism -- `_is_self_write_only_diff`

<!-- Machine-readable exemption-registry row (R-014). Parsed by
     tests/architectural/test_exemption_registry_ratchet.py. ONE mechanism per
     file, so a retirement WP deletes ONLY its own row and never collides with a
     sibling retirement editing a shared file (squad-mandated design; the plan's
     stated reason for rejecting golden-count mode). The registry only SHRINKS:
     when a mechanism is retired onto the owner, its literal(s)/symbol vanish from
     src/ and the overcount / symbol-presence arm goes RED until this row file is
     deleted (red -> green per retirement). -->


- mechanism: `_is_self_write_only_diff`
- module: `src/specify_cli/cli/commands/implement_cores.py`
- literals: `_WP_SELF_WRITE_FILENAME_RE`
- symbol: `_is_self_write_only_diff`
- retirement-wp: `WP14`
- retirement-ref: `IC-07d`
- owner-route: `is_toolchain_generated_churn`
- status: `justified-survivor`

**WP14 (IC-07d) genuine must-keep, not a silent survivor.** The plan's IC-07d
retirement double-listed `_drop_vcs_lock_only_meta` and
`_drop_runtime_frontmatter_only_wp` as owner-routable (like their sibling
`_exclude_coord_owned`, which DOES route fully onto the owner-exposed
`is_status_state_path` leg -- its row was deleted, not replaced). Implementation
found the vcs-lock/frontmatter pair cannot make that same move: they are
structural twins of EACH OTHER (same "keep unless the predicate flags a
runtime self-write" shape, now merged into one `_drop_if`-consumed predicate),
but their filename gate is a `meta.json`/`WP##.md` DIFF comparison, not a
`MissionArtifactKind` classification -- `is_toolchain_generated_churn` answers
"is this file's *kind* toolchain-generated" (a whole-file verdict; `meta.json`
is unconditionally self-bookkeeping there, `WP##.md` is unconditionally
PRIMARY/never churn), while this predicate must answer "is THIS DIFF only the
runtime's own claim-time self-write", which requires reading both the working
tree and the committed baseline and comparing the changed keys/body. Forcing
the owner's kind-based verdict in here would either (a) always-drop `meta.json`
regardless of content -- silently swallowing a genuine non-lock operator edit,
regressing `test_non_lock_dirty_meta_still_blocks_auto_commit_false_claim` -- or
(b) never drop `WP##.md` at all (it is never toolchain-generated churn by
kind), regressing every runtime-frontmatter-only-diff test. Both are C6
violations. Registered here -- with real justification prose, `status:
justified-survivor`, and a live `_is_self_write_only_diff` symbol -- rather
than silently retained, per plan.md's "if implementation finds a genuine
must-keep, it becomes an explicit, justified registry row, never a silent
survivor" (WP15 precedent).

**Mission `meta-fail-closed-3162-01KZ7FSQ` (WP05 / IC-05) made the `meta.json`
arm diagnosable and did NOT retire the mechanism.**

*Line-number convention for this row: every coordinate below is **post-edit** --
it names the line on the tree this row is committed with, not the pre-edit line
it replaced. (Review cycle 1 MINOR: the first version of this paragraph cited
`implement_cores.py:426-431`, a pre-edit coordinate that post-edit lands inside
the `_is_self_write_only_diff` docstring -- a registry row pointing at prose
instead of at the branch it describes.)*

The predicate's `meta.json` branch (`implement_cores.py:455-466`) reads and
parses `meta.json` without reaching the canonical fail-closed seam, so a corrupt
file returned `False` silently -- indistinguishable from "this is a genuine
operator edit".

That branch now **appends** a message naming `meta.json` and the resolved
`source` path to the caller-supplied `diagnostics` sink (`:461-465`) before
returning `False`. It does not print: this module is deliberately free of
console/typer side effects, so the operator-visible half is the executor's --
`implement._ensure_planning_artifacts_committed_git` allocates the sink, passes
it through `resolve_planning_artifact_staging`, and prints what comes back
before the generic "Planning artifacts not committed" listing. Both halves are
required and both are present; the sink alone reaches no operator, and review
cycle 1 rejected an earlier version of this row that claimed the branch "emits"
when only the append existed. The end-to-end path is pinned by
`TestSitesCandDReachTheOperator` in
`tests/specify_cli/cli/commands/test_meta_bypass_diagnosability.py`, which
drives the executor -- not this predicate -- and goes red if the sink stops
being threaded from the production caller.

The return contract, the filename gate, the `literals:`/`symbol:` above and
`status: justified-survivor` are all unchanged, and the WP14/IC-07d
justification above still stands in full.

**The mechanism was NOT routed onto the seam, and the reason is the routed
budget -- not structure.** `C-004`'s original claim that these sites
"structurally cannot use the seam" is **refuted and struck**: `source` at
`implement_cores.py:452` is a real resolved filesystem path under a
`name == _META_JSON_FILENAME` gate (`:455`) and its parent IS a feature dir, so
`specify_cli.core.paths:load_meta_fail_closed` fits here today. The mission's
admissible routed band is two-sided (`[127, 130]`, derived from
`test_routed_load_meta_floor`), and its single net routed call was spent
routing `specify_cli.git.ref_advance:_meta_change_is_vcs_lock_only` instead.
Full routing of this site is deferred to issue **#3230** (the `Q2` residue).
