---
affected_files: []
cycle_number: 2
mission_slug: doctrine-consumer-surface-missions-extraction-01KZ6G6H
reproduction_command:
reviewed_at: '2026-08-04T19:04:38Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP03
---

# WP03 review — cycle 1 — REJECTED (additive remediation only)

**Reviewer**: reviewer-renata
**Artifact**: `docs/plans/doctrine/missions-reader-inventory-01KZ6G6H.md` (commit `21238a8d5`)
**Verdict**: reject — the inventory is materially incomplete in the one way that matters: three
files that require a code change in WP05 are absent from it, and therefore absent from WP05's
`owned_files`. Everything else in the artifact is verified correct and must **not** be reworked.

---

## Part 1 — verified correct (do not touch)

I re-derived these independently rather than taking the document's word for them:

- **SC-007 invariant holds.** 46 data rows across four tables; **zero** rows with an empty cell.
  Every row carries a non-empty `decision` and `rationale`.
- **All four mandated inclusions are present and accurate**, including keeping
  `kernel.paths.get_package_asset_root()` (R-01) and `specify_cli.runtime.home.get_package_asset_root()`
  (R-09) as **separate rows**. I read both bodies: they are genuinely distinct implementations.
  Not conflated. Correct.
- **The `.py`-vs-data split is exactly right.** I opened all 11 modules and grepped each for path
  construction. The four marked `repoint` genuinely need it — `repository.py:98-110`,
  `mission_type_repository.py:74-77`, `mission_step_repository.py:219`, `step_contracts.py:194-199`
  — and the other seven genuinely construct nothing (`action_index.py` takes `missions_root` as a
  parameter; `glossary_hook.py` only receives `repo_root`; `models.py`/`primitives.py`/
  `step_projection.py`/`step_offer_seam.py`/`__init__.py` have no filesystem access at all).
  This is a better reading than WP03's own prompt ("expected: all of them") and `data-model.md`
  explicitly licenses it.
- **The `m_2_1_3_restore_prompt_commands.py` zero-literal claim is TRUE.**
  `grep -n "doctrine\.missions\|doctrine/missions"` on that file exits 1 — no match anywhere —
  while `_get_runtime_command_templates_dir()` at lines 87-96 really does build
  `Path(doctrine.__file__).parent / "missions" / "mission-steps" / _MISSION_NAME`. The method
  claim is not overstated for this site.
- **The "live finding" against WP04's lane-b is accurate to the letter.** Read from
  `git show c681a8910`: `_MISSION_ASSETS_SIBLING_PATTERN = PurePosixPath("src") / "*" / "missions"`,
  `_MISSIONS_ROOT_SIBLING_PATTERN = PurePosixPath("missions")`, and
  `kernel/sibling_paths.py::_first_match` returns `sorted(...)[0]` of glob matches with **no
  content sniff**. Both self-match traps are real, precisely as described.
- **R-07 is real and high-severity, as claimed.** `_scan_layer_dirs` sets
  `roots = {"built-in": _SRC_ROOT}` (line 670) and the non-layered branch does
  `candidate = root / base_dir` guarded by `candidate.is_dir()` (lines 703-709) — so post-move the
  built-in layer is silently dropped from `charter pack list mission-type` /
  `mission-step-contract`. No error signal. Confirmed.
- **R-13 is the default `spec-kitty init` path, as claimed.** `init.py:792` →
  `copy_specify_base_from_package` → `manager.py:100-109`, first candidate
  `files("doctrine").joinpath("missions")`, `_resource_exists()`, `break`. Confirmed.
- **The two named must-fix-together pairs are real.** `catalog.py:185` is
  `_get_package_asset_root().parent` and is the only production consumer of the kernel function;
  `init.py:320-321` is `get_package_asset_root().parent / "templates"` off the `runtime.home`
  implementation. Repointing either resolver to `packs/built-in/missions` moves what `.parent`
  yields. This is load-bearing guidance and WP05 must keep it.
- **No source file changed.** The diff is the inventory plus two added lines in `research.md`.
- **Issue matrix**: all 14 rows carry verdicts; nothing left `unknown`.

## Part 2 — BLOCKING: three missed readers that need a code change

Each is a `repoint`-class site absent from the inventory **and** from WP05's `owned_files`.
All three literally match the inventory's own stated resolution-shape sweep keywords
(`get_package_asset_root`, `Path(doctrine.__file__).parent / "missions"`), so the method was
right and the triage of its output was incomplete.

### B-1 `src/specify_cli/runtime/agent_commands.py::_get_command_templates_dir()` (lines 95-98, 100-108)

```python
loaded_file = getattr(sys.modules.get("doctrine"), "__file__", None)
if isinstance(loaded_file, str) and loaded_file:
    return Path(loaded_file).parent / "missions" / "mission-steps" / DEFAULT_MISSION_KEY
...
return doctrine_path / "missions" / "mission-steps" / DEFAULT_MISSION_KEY
```

Two independent constructions of `<doctrine pkg>/missions/mission-steps/<mission>`, **both
returned unguarded** — no `.is_dir()` check on either. Same class as R-11/M-01/M-02 but strictly
worse, because M-01/M-02 at least fail closed onto a fallback chain. Reached from
`ensure_global_agent_commands()` (line 312 → 328), i.e. global agent-command installation.
Post-move both branches return a nonexistent directory.

### B-2 `src/specify_cli/migration/rewrite_shims.py::_get_command_templates_dir()` (lines 45-57)

Byte-identical shape to M-01/M-02 (`Path(doctrine.__file__).parent / "missions" / "mission-steps"
/ _MISSION_NAME`, `.is_dir()`-guarded, then falling through to
`specify_cli.runtime.home.get_package_asset_root()` — i.e. straight into R-09's bug). By the
inventory's own M-01 standard ("the primary `doctrine.__file__`-relative construction should also
be repointed to avoid depending on a broken fallback") this is a `repoint`. It was missed because
the deliberate migration sweep was **directory-scoped** to `src/specify_cli/upgrade/migrations/*.py`
and this module lives in `src/specify_cli/migration/`. Worth saying so in the Method section — it
is a second, sharper lesson than the one M-02 already carries.

### B-3 `src/specify_cli/runtime/bootstrap.py::_stage_package_assets()` (lines 97-110)

```python
asset_root = get_package_asset_root()
...
shutil.copytree(missions_src, missions_dst)      # missions_src = asset_root
scripts_src = asset_root.parent / "scripts"
```

Two distinct problems, both in classes the inventory itself elevates:

1. `copytree(asset_root, target / "missions")` is a **third instance of the R-12/R-13
   silent-wrong-content class** — it stages the data-less `src/doctrine/missions` into the runtime
   asset tree with zero error signal. It belongs in the "would silently resolve to the data-less
   package directory" enumeration, which currently lists five entries.
2. `asset_root.parent / "scripts"` is a **third `.parent`-coordination site** alongside R-08 and
   R-14. Repointing R-09 to `packs/built-in/missions` makes `.parent` yield `packs/built-in`, and
   `packs/built-in/scripts` does not exist — scripts silently stop staging. This is a **third
   must-fix-together pair (R-09 ↔ `bootstrap.py`)**, and the summary's "two required-together
   pairs" line currently loses it.

## Part 3 — required additions: rows that may legitimately be `stay`, but must not be silence

The document explicitly credits itself for recording ruled-out sites ("Recorded to show they were
checked and explicitly ruled out, not silently skipped"). These match the same
`get_package_asset_root` keyword and appear nowhere in it. Each is downstream of R-09, so
`stay`/`repoint` is your call — but the post-move behaviour is a silent degradation worth naming:

- **`src/specify_cli/runtime/show_origin.py:68, 89, 114`** — `pkg_root / <mission> /
  "command-templates"`, `pkg_root / "mission-steps" / <mission>`, `pkg_root / <mission> /
  "templates"`, plus `_discover_mission_names()` iterating `pkg_root.iterdir()` for `mission.yaml`.
  Post-move silently degrades onto `builtin_mission_type_ids()` / `_FALLBACK_COMMAND_NAMES`.
- **`src/specify_cli/runtime/migrate.py:177`** — `package_root` is the comparison baseline for
  `classify_asset`; against a data-less root nothing is ever `IDENTICAL`/`SUPERSEDED`, so
  `spec-kitty migrate` silently stops reclaiming assets.
- **`src/specify_cli/upgrade/migrations/m_2_0_7_fix_stale_overrides.py:40, 72`** — same baseline
  problem; `detect()` returns `False` and the migration becomes a silent no-op. This one matters
  for the method claim specifically: the inventory names 15 migrations across its two migration
  `stay` rows and asserts a 25-file sweep, and `m_2_0_7` is the *one* migration in that directory
  that reads missions content via `get_package_asset_root()`.
- **`src/runtime/`** — layer `runtime` is in your legend and in `data-model.md`'s enum, yet has
  zero rows. I swept it: both `builtin_roots` producers
  (`src/runtime/next/runtime_bridge_io.py:238` and `src/specify_cli/mission_loader/command.py:196`)
  point at `specify_cli/missions`, so it is genuinely unaffected. That conclusion belongs on the
  page as one ruled-out row.
- **Three more legacy-tree migrations**, unlisted, all `Path(specify_cli.__file__).parent /
  "missions"` and correctly `stay`: `m_0_10_6_workflow_simplification.py:100`,
  `m_0_11_1_improved_workflow_templates.py:68`, `m_0_11_2_improved_workflow_templates.py:68`.

## Part 4 — row-accuracy defects in the consolidated `stay` rows

These do not hide a `repoint`, but each asserts something the code contradicts. WP05 will read
these rows as authority, so they need correcting rather than deleting:

1. **`src/specify_cli/runtime/resolver.py`** is described as a "re-export shim". It is the
   641-line 5-tier resolver, and it consumes `get_package_asset_root()` at **:317** and **:631** to
   build the `PACKAGE_DEFAULT` tier. `stay` is the right decision; the `current_path_assumption`
   is wrong.
2. **`src/charter/activation/compiler.py`**, inside the consolidated charter row whose rationale reads "No
   independent path/root construction in any of these files": line **1316** is
   `mission_path = repo._mission_config_path(mission) or (doctrine_root / "missions" / mission /
   "mission.yaml")` — a stale `or`-fallback that post-move yields a nonexistent path into a
   `CharterReference`'s `source_path`. Low severity, but it is an independent construction and
   `compiler.py` is not in WP05's `owned_files`.
3. **`src/specify_cli/mission_loader/command.py`**, same claim in the `specify_cli` row: lines
   **195-197** construct `Path(runtime_bridge.__file__).resolve().parent.parent / "missions"`.
   `stay` is correct (legacy tree), the "no independent path construction" claim is not.
4. **`src/specify_cli/cli/commands/charter/list_cmd.py`**, same row: lines **66** and **79**
   construct `project_root / "doctrine" / "missions"` and `org_root / "doctrine" / "missions"`.
   Correctly unaffected (project/org layers), same false claim.
5. **`src/specify_cli/cli/commands/init.py`** — R-14 names only line 320. Line **361**
   (`package_root / mission / "command-templates"` in `_resolve_mission_command_templates_dir`) is
   a second missions-data read in the same file. No scope loss (file already owned), but the row
   should name both sites.
6. **`src/doctrine/drg/migration/extractor.py`** is missing from the "would silently resolve to
   the data-less package directory" enumeration. Post-move `_is_pack_root(packs/built-in)` is
   still `True` (it tests `directives/*.directive.yaml`, which does not move), so
   `_missions_root()` still takes the redirect branch and returns
   `doctrine_package_dir() / "missions"` — the data-less directory. It is caught loudly by
   `test_regen_roundtrip.py`, but by exactly this mechanism, and the row's own text ("resolves via
   `files("doctrine")`") understates it: the trap is that the pack-root branch's premise inverts
   while the predicate that selects it does not.

## Part 5 — scope

`owned_files` is the inventory markdown only; the diff also adds two lines to
`kitty-specs/.../research.md`. I judge this **acceptable rationale-backed leeway, not a violation**:
it is a forward cross-reference at the tail of R9, touches no other WP's owned file, changes no
decision, and improves traceability from the mission's research to its deliverable. One fix
required: that sentence asserts "**14 files** require repoint", a count this remediation will
change. Drop the number and let the artifact carry it.

## What "done" looks like for cycle 2

Purely additive. Do not restructure, do not re-verify what Part 1 confirms:

1. Add `repoint` rows for **B-1, B-2, B-3**, and add all three to WP05's `owned_files`.
2. Add `bootstrap.py`'s `copytree` to the silent-data-less enumeration; promote
   **R-09 ↔ `bootstrap.py`** to a third must-fix-together pair in the summary; update the
   "14 distinct files" count.
3. Add the Part 3 ruled-out rows (including a `src/runtime/` row).
4. Correct the four false "no independent path construction" claims in Part 4 and add the
   extractor to the dangerous-class list.
5. Drop the hard-coded count from the `research.md` pointer.

The method (symbol/shape tracing) is right and the six grep-invisible claims hold. What failed is
exhaustive triage of that method's own output: six files matching `get_package_asset_root` were
never adjudicated. Widening the sweep from "the keyword found it" to "every hit of the keyword has
a row" closes this.
