# Routing manifest — mission `meta-fail-closed-3162-01KZ7FSQ`

**Status**: frozen by `WP01`. Binding on `WP02`–`WP08`.
**Requirements**: `FR-002`, `NFR-002`, `C-001`, `C-003`.

---

## How to read this document

> **Every number here carries the command that produced it and that command's input count**, in the
> form "N candidates in → M dropped for a stated reason → K out". A bare integer in this document is
> a defect. Every probe declares whether it used an **AST walk** or a **regex**; where the answer must
> be exact the authority is the AST walk and the regex appears only as a controlled negative.

> **Counting conventions — declared once, then named inline at every count.**
> - **"call site"** = one `ast.Call` node. The 13 routable sites are **13 call sites**.
> - **"ledger row"** = one `_ACCOUNTED_SITES` entry in
>   `tests/specify_cli/test_meta_fail_closed_full_census_contract.py`. There are **12 ledger rows**,
>   one of which (`specify_cli.missions._read_path_resolver.read_primary_meta`, line `:243`) carries
>   count **2**. 12 rows expand to 13 call sites.
> - **"read expression"** — used only in §3. A read-expression count and a call-site count are
>   **never addable**. Every count below states its convention in the same breath as the number.

> **Citation rule (`C-003`).** Every site is cited by **module-qualified symbol**. Line numbers are
> marked `[shifts — cite the symbol]` because this mission edits every file cited here, so the line
> numbers go stale while this document is still in force. Symbol-alone is **also** insufficient — see
> the `_resolve_mission_id` collision note in §1.

**Regeneration command.** Every number in §1, §2 and §4 is reproduced by the committed script:

```bash
PYTHONPATH=<tree>/src .venv/bin/python scripts/verify_meta_routing_manifest_3162.py [TREE_ROOT]
```

`TREE_ROOT` defaults to the repository root; pass a worktree path to take that tree's numbers. The
script prints the tree and the `PYTHONPATH` it measured, and exits non-zero if any count leaves its
band or any control fails to reproduce its known answer. All output quoted in this document was taken
on tree `/home/jeroennouws/dev/sk-missions/3162` (the repository root — the only tree with a `.venv`;
`.gitignore:31-32` ignores `.venv` / `.venv*/`), `sys.executable`
`/home/jeroennouws/dev/sk-missions/3162/.venv/bin/python`, `PYTHONPATH=/home/jeroennouws/dev/sk-missions/3162/src`.

---

## §1 — The 13 routable call sites: arm, handler, ledger row, by symbol

### 1.1 Ledger row count and the call-site expansion (input counts)

Probe: **regex** for the row count, **AST** for the expansion. Command and output:

```
  grep -c 'pending-batch-a' test_meta_fail_closed_full_census_contract.py: 13 (candidates in)
  legend/prose hits dropped: 1 at line(s) [185]
  ledger ROWS out: 12  (convention: ledger row)
  CALL SITES out: 13  (convention: call site; expanded from row counts)
  multi-count row: src/specify_cli/missions/_read_path_resolver.py::read_primary_meta count=2
```

**The two 13s agree by coincidence, not by construction.** `grep -c 'pending-batch-a'` over
`tests/specify_cli/test_meta_fail_closed_full_census_contract.py` returns **13** because it counts
**12 ledger rows plus one docstring legend line** at `:185`
(`#   ``pending-batch-a``    — a real routing target that is genuinely UNROUTED.`). The row-count
expansion also returns **13** — 11 rows at count 1 plus one row at count 2. Derive from the row
**counts**, never from the grep total: the two numbers are the same integer for unrelated reasons and
either one drifting would silently mask the other.

### 1.2 The AST classifier and its control (control shown first)

The arms are re-derived with an **AST walk**, not a grep: for each censused `(file, function)` pair
the classifier locates every `load_meta` `ast.Call` node, finds every same-function `ast.Try` whose
*body* transitively contains that call, keeps the handlers catching `ValueError` (bare name, a tuple
containing it, or a bare `except`), and classifies each handler body as **REFUSE** (contains an
`ast.Raise`) or **DEGRADE** (does not). No such handler ⇒ **REFUSE-raw**.

Control run first, on two sites whose arm is known by reading. A classifier that has not been
controlled produces a number, not a measurement:

```
== §1 ARMS (AST classifier, not grep) ==
  CONTROL pairs in: 2
  CONTROL src/specify_cli/core/paths.py::load_meta_fail_closed call@676 arm=REFUSE-typed want=REFUSE-typed handler@677
  CONTROL src/specify_cli/mission_metadata.py::load_meta_or_empty call@391 arm=REFUSE-raw want=REFUSE-raw handler@-1
  CONTROL verdict: ALL PASS
```

`specify_cli.core.paths.load_meta_fail_closed` catches `ValueError` and re-raises
`MissionMetaReadError` (`core/paths.py:677-678`), so REFUSE-typed is the known answer.
`specify_cli.mission_metadata.load_meta_or_empty` has no `try` at all, so REFUSE-raw is the known
answer. **Correction to the work-package prompt**: it qualifies this symbol as
`specify_cli.missions.mission_metadata.load_meta_or_empty`. There is no
`src/specify_cli/missions/mission_metadata.py` on this tree; the module is
`src/specify_cli/mission_metadata.py` ⇒ `specify_cli.mission_metadata`. The same misqualification
appears at `_parse_meta_text` (§3.5) and in the predicate pre-list, and is corrected in both places.
The prompt also says "Three sites whose arm is known by reading" and then names two; two controls
were run.

### 1.3 Census output (input count 12 rows, expected 13 call sites)

```
  INPUT rows (ledger pending-batch-a): 12
  SITE src/mission_runtime/resolution.py::_mid8_from_primary_meta call@509 arm=DEGRADE handler@514
  SITE src/mission_runtime/resolution.py::_resolve_coordination_branch call@852 arm=DEGRADE handler@853
  SITE src/mission_runtime/resolution.py::_resolve_mission_id call@1107 arm=DEGRADE handler@1108
  SITE src/runtime/next/_internal_runtime/planner.py::_resolve_workflow_for_mission call@188 arm=REFUSE-raw handler@-1
  SITE src/runtime/next/runtime_bridge_io.py::_workflow_runtime_template call@380 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/bulk_edit/gate.py::_is_bulk_edit_mission call@57 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/bulk_edit/gate.py::ensure_occurrence_classification_ready call@80 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/context/resolver.py::_read_meta_json call@75 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/decisions/service.py::_resolve_mission_id call@134 arm=REFUSE-typed handler@141
  SITE src/specify_cli/missions/_read_path_resolver.py::read_primary_meta call@846 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/missions/_read_path_resolver.py::read_primary_meta call@862 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/missions/_resolve_planning_branch.py::load_mission_target_branch call@116 arm=REFUSE-typed handler@122
  SITE src/specify_cli/upgrade/feature_meta.py::load_feature_meta call@42 arm=DEGRADE handler@43
  DERIVED call sites: 13 / DEGRADE: 4 / REFUSE-raw: 7 / REFUSE-typed: 2
```

**`C-001` / D4=(a) confirmed by measurement: 4 degrade / 2 refuse-typed / 7 refuse-raw, sum 13
call sites.** No site's arm changes in this mission. The inherited split "6 divergent-wrapper / 7"
was wrong: **6** is the count of sites carrying an `except ValueError` (§2), and only **4** of those 6
degrade.

### 1.4 The table (convention: 13 **call sites**; 12 **ledger rows**, one with count 2)

| # | Module-qualified symbol (`C-003`) | `file:line` `[shifts — cite the symbol]` | Read shape | Arm today | Fallback | Fallback kind | Handler `file:line` | Ledger row line | Owning WP |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `mission_runtime.resolution._mid8_from_primary_meta` | `resolution.py:509` | `load_meta(primary_dir, allow_missing=True, on_malformed="raise")` (explicit) | DEGRADE | `return ""` (`:515`) | **constant** | `resolution.py:514` | `:198` | `WP04` |
| 2 | `mission_runtime.resolution._resolve_coordination_branch` | `resolution.py:852` | `load_meta(..., allow_missing=True, on_malformed="raise")` (explicit) | DEGRADE | `return None` (`:856`) | **constant** | `resolution.py:853` | `:199` | `WP04` |
| 3 | `mission_runtime.resolution._resolve_mission_id` | `resolution.py:1107` | `load_meta(..., allow_missing=True, on_malformed="raise")` (explicit) | DEGRADE | `meta = None` (`:1109`) → `return f"legacy-{mission_slug}"` (`:1114`) | **constant** — see 1.6 | `resolution.py:1108` | `:200` | `WP04` |
| 4 | `runtime.next._internal_runtime.planner._resolve_workflow_for_mission` | `planner.py:188` | `load_meta(...)`, `on_malformed` = signature default | REFUSE-raw | — (propagates) | n/a | — (none) | `:201` | `WP02` |
| 5 | `runtime.next.runtime_bridge_io._workflow_runtime_template` | `runtime_bridge_io.py:380` | `load_meta(...)`, signature default | REFUSE-raw | — (propagates) | n/a | — (none) | `:202` | `WP02` |
| 6 | `specify_cli.bulk_edit.gate._is_bulk_edit_mission` | `gate.py:57` | `load_meta(feature_dir)`, signature default | REFUSE-raw | — (propagates) | n/a | — (none) | `:203` | `WP02` |
| 7 | `specify_cli.bulk_edit.gate.ensure_occurrence_classification_ready` | `gate.py:80` | `load_meta(feature_dir)`, signature default | REFUSE-raw | — (propagates) | n/a | — (none) | `:204` | `WP02` |
| 8 | `specify_cli.context.resolver._read_meta_json` | `resolver.py:75` | `load_meta(..., allow_missing=False, on_malformed="raise") or {}` (explicit) | REFUSE-raw | — (propagates); has a **dead** `except FileNotFoundError` at `:76` | n/a | — (no `ValueError` arm) | `:215` | `WP03` |
| 9 | `specify_cli.decisions.service._resolve_mission_id` | `service.py:134` | `load_meta(..., allow_missing=False, on_malformed="raise") or {}` (explicit) | REFUSE-typed | raises `DecisionError(MISSION_NOT_FOUND)` | n/a | `service.py:141` | `:222` | `WP03` |
| 10 | `specify_cli.missions._read_path_resolver.read_primary_meta` (first read) | `_read_path_resolver.py:846` | `load_meta(primary_dir) or {}`, signature default | REFUSE-raw | — (propagates) | n/a | — (none) | `:243` (count 2) | `WP02` |
| 11 | `specify_cli.missions._read_path_resolver.read_primary_meta` (canonicalized re-read) | `_read_path_resolver.py:862` | `load_meta(canonical_dir) or {}`, signature default | REFUSE-raw | — (propagates) | n/a | — (none) | `:243` (count 2) | `WP02` |
| 12 | `specify_cli.missions._resolve_planning_branch.load_mission_target_branch` | `_resolve_planning_branch.py:116` | `load_meta(..., allow_missing=False, on_malformed="raise")` (explicit) | REFUSE-typed | raises `PlanningBranchResolutionFailed` | n/a | `_resolve_planning_branch.py:122` | `:244` | `WP03` |
| 13 | `specify_cli.upgrade.feature_meta.load_feature_meta` | `feature_meta.py:42` | `load_meta(feature_dir)`, signature default | DEGRADE | `return None` (`:44`) | **constant** | `feature_meta.py:43` | `:249` | `WP04` |

*Caption — conventions restated:* the table has **13 rows = 13 call sites**. It maps onto **12 ledger
rows**; rows 10 and 11 are the two calls of the single count-2 ledger row at `:243`. The two totals
are not addable.

**Ledger row → line → symbol pinned by measurement**, not inferred from `plan.md`'s distribution.
`_ACCOUNTED_SITES` rows read (quoting each row's text; input count 12 rows read):

```
198:    ("src/mission_runtime/resolution.py", "_mid8_from_primary_meta"): (1, "pending-batch-a"),
199:    ("src/mission_runtime/resolution.py", "_resolve_coordination_branch"): (1, "pending-batch-a"),
200:    ("src/mission_runtime/resolution.py", "_resolve_mission_id"): (1, "pending-batch-a"),
201:    ("src/runtime/next/_internal_runtime/planner.py", "_resolve_workflow_for_mission"): (1, "pending-batch-a"),
202:    ("src/runtime/next/runtime_bridge_io.py", "_workflow_runtime_template"): (1, "pending-batch-a"),
203:    ("src/specify_cli/bulk_edit/gate.py", "_is_bulk_edit_mission"): (1, "pending-batch-a"),
204:    ("src/specify_cli/bulk_edit/gate.py", "ensure_occurrence_classification_ready"): (1, "pending-batch-a"),
215:    ("src/specify_cli/context/resolver.py", "_read_meta_json"): (1, "pending-batch-a"),
222:    ("src/specify_cli/decisions/service.py", "_resolve_mission_id"): (1, "pending-batch-a"),
243:    ("src/specify_cli/missions/_read_path_resolver.py", "read_primary_meta"): (2, "pending-batch-a"),
244:    ("src/specify_cli/missions/_resolve_planning_branch.py", "load_mission_target_branch"): (1, "pending-batch-a"),
249:    ("src/specify_cli/upgrade/feature_meta.py", "load_feature_meta"): (1, "pending-batch-a"),
```

Command: `grep -n 'pending-batch-a' tests/specify_cli/test_meta_fail_closed_full_census_contract.py`
(**regex**, 13 hits in → 1 legend line at `:185` dropped → 12 rows out). The `WP` column above
agrees with `plan.md`'s line distribution and with `WP02`'s 6 / `WP03`'s 3 / `WP04`'s 4 swap counts:
`:198`–`:200` + `:249` → `WP04` (4 rows, 4 sites); `:201`–`:204` + `:243` → `WP02` (5 rows, **6**
sites, because `:243` carries count 2); `:215`, `:222`, `:244` → `WP03` (3 rows, 3 sites). 4 + 6 + 3 = 13.

### 1.5 `_resolve_mission_id` is ambiguous by symbol alone — module-qualify every citation

`C-003` says cite by symbol. **For this one name, symbol-alone is insufficient.** AST walk over
`src/` (`grep -rn 'def _resolve_mission_id' src/`, **regex** control on the same population, same 4
hits) — 4 defining modules, exact-name matches:

```
src/charter/_io.py:358                              _resolve_mission_id   (inline-read, ALLOW-LISTED — §3.6)
src/mission_runtime/resolution.py:1058              _resolve_mission_id   (row 3, arm DEGRADE)
src/specify_cli/decisions/service.py:112            _resolve_mission_id   (row 9, arm REFUSE-typed)
src/specify_cli/post_merge/retrospective_terminus.py:143  _resolve_mission_id  (not a meta.json read site)
```

Two of the four are **this mission's own sites with opposite arms** — row 3 degrades to a sentinel,
row 9 raises `DecisionError`. A bare `_resolve_mission_id` in a downstream work package is therefore
not just imprecise, it is a coin flip between "keep degrading" and "raise typed". **Every citation in
both contracts is module-qualified.** This is the one place where `C-003` compliance is not
sufficient on its own.

### 1.6 Degrade-site fallbacks: all four are **constant**, none is derived from the malformed file

`FR-002` / `NFR-003` require each degrade site's fallback to be classified, because a *derived*
fallback can produce a plausible-but-wrong value. Read at source, all four are constant:

- **Row 1** — `resolution.py:514-515`: `except ValueError:` / `return ""`. A literal.
- **Row 2** — `resolution.py:853-856`: `except ValueError:` / `# Malformed meta: treat coordination
  topology as undeclared.` / `return None`. A literal.
- **Row 3** — `resolution.py:1108-1114`: `except ValueError:` / `meta = None`, then `if meta:` is
  false, so control reaches `return f"legacy-{mission_slug}"`. **`mission_slug` is the function's own
  parameter** (`_resolve_mission_id(primary_root, mission_slug, *, resolver=...)`,
  `resolution.py:1058-1060`) and `meta` is `None` on this path, so **nothing from the malformed file
  reaches the returned value**. The fallback is **constant with respect to file content**.
  > **Withdrawn claim.** An earlier plan bullet described row 3's `legacy-<slug>` fallback as
  > "derived from the malformed file". That is **false and is struck**: the sentinel is composed from
  > the caller's argument, and `meta` is `None` on the degrade path. Do not reinstate it.
- **Row 13** — `feature_meta.py:43-44`: `except ValueError:` / `return None`. A literal.

**All four degrade fallbacks are constant.** No degrade site can emit a value influenced by the
contents of a malformed `meta.json`.

### 1.7 All 13 sit on the canonical reader's **raise** contract

`specify_cli.mission_metadata.load_meta`'s signature (`mission_metadata.py:280-286`) is:

```python
def load_meta(
    feature_dir: Path,
    *,
    allow_missing: bool = True,
    on_malformed: OnMalformed = "raise",
    encoding: str = _UTF8,
) -> dict[str, Any] | None:
```

`on_malformed` **defaults to `"raise"`**, so a malformed file genuinely produces a `ValueError` at
each of the 13 call sites regardless of whether the keyword is written out. AST keyword inspection
over the 13 (**AST walk**, 13 call sites in → 13 classified → 0 dropped):

- **explicit `on_malformed="raise"`: 6 sites** — rows 1, 2, 3, 8, 9, 12.
- **signature default: 7 sites** — rows 4, 5, 6, 7, 10, 11, 13.

> **Correction to the work-package prompt.** It states "explicit at 7 sites, the signature default at
> 6". Measured on this tree the split is **6 explicit / 7 default** — the two numbers are transposed.
> The substantive claim (all 13 are on the raise contract) is unaffected and holds.

### 1.8 The `:509` / `:512` reconciliation — one call site, not two

`grep -n 'on_malformed' src/mission_runtime/resolution.py` (**regex**) returns exactly three lines:

```
512:            on_malformed="raise",
852:        meta = load_meta(primary_dir, allow_missing=True, on_malformed="raise")
1107:        meta = load_meta(primary_dir, allow_missing=True, on_malformed="raise")
```

`:512` is the **keyword line** of a multi-line call whose `ast.Call` node begins at **`:509`** —
`meta = load_meta(` at `:509`, `primary_dir,` at `:510`, `allow_missing=True,` at `:511`,
`on_malformed="raise",` at `:512`, `)` at `:513`. **Same single call site.** This manifest uses the
**call-node line (`:509`)** for row 1, for consistency with every other row in the table, all of
which are cited at their `ast.Call` node line as reported by the AST classifier.

---

## §2 — The 6 `except ValueError` handlers, and the grep trap that says 9

### 2.1 The authoritative 6 (AST walk)

Probe: **AST walk** — `ast.ExceptHandler` nodes whose `type` resolves to `ValueError` and whose
enclosing `ast.Try` body contains the censused `load_meta` call node. Input: the 12 ledger rows /
13 call sites of §1. Output:

```
== §2 AUTHORITATIVE HANDLERS (AST) ==
  src/mission_runtime/resolution.py:514  (_mid8_from_primary_meta)
  src/mission_runtime/resolution.py:853  (_resolve_coordination_branch)
  src/mission_runtime/resolution.py:1108  (_resolve_mission_id)
  src/specify_cli/decisions/service.py:141  (_resolve_mission_id)
  src/specify_cli/missions/_resolve_planning_branch.py:122  (load_mission_target_branch)
  src/specify_cli/upgrade/feature_meta.py:43  (load_feature_meta)
```

Each `except` line quoted verbatim from source, with its module-qualified enclosing symbol; each
catches **bare** `ValueError`, confirmed by reading:

| Enclosing symbol (module-qualified) | `file:line` `[shifts]` | Verbatim `except` line |
|---|---|---|
| `mission_runtime.resolution._mid8_from_primary_meta` | `resolution.py:514` | `    except ValueError:` |
| `mission_runtime.resolution._resolve_coordination_branch` | `resolution.py:853` | `    except ValueError:` |
| `mission_runtime.resolution._resolve_mission_id` | `resolution.py:1108` | `    except ValueError:` |
| `specify_cli.decisions.service._resolve_mission_id` | `service.py:141` | `    except ValueError as exc:` |
| `specify_cli.missions._resolve_planning_branch.load_mission_target_branch` | `_resolve_planning_branch.py:122` | `    except ValueError as exc:` |
| `specify_cli.upgrade.feature_meta.load_feature_meta` | `feature_meta.py:43` | `    except ValueError:` |

### 2.2 The trap: the naive **regex** returns 9 (and 10 under the fully-derived population)

Probe: **regex** — used *only* as the controlled negative. The authoritative 6 above came from the
AST walk.

```
  [POP-ALL (9 census files, fully derived)] population = 9 files
  [POP-ALL (9 census files, fully derived)] 10 candidates in -> 4 dropped -> 6 out
    DROP src/mission_runtime/resolution.py:420 [UNRELATED-HANDLER] except ValueError as exc:
    DROP src/mission_runtime/resolution.py:491 [COMMENT] # malformed; the ``except ValueError`` below reproduces the historical
    DROP src/specify_cli/bulk_edit/gate.py:71 [UNRELATED-HANDLER] except ValueError:
    DROP src/specify_cli/missions/_read_path_resolver.py:137 [UNRELATED-HANDLER] except ValueError:
  [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] population = 8 files
  [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] 9 candidates in -> 3 dropped -> 6 out
    DROP src/mission_runtime/resolution.py:420 [UNRELATED-HANDLER] except ValueError as exc:
    DROP src/mission_runtime/resolution.py:491 [COMMENT] # malformed; the ``except ValueError`` below reproduces the historical
    DROP src/specify_cli/missions/_read_path_resolver.py:137 [UNRELATED-HANDLER] except ValueError:
  CONTROL 'except ValueError' regex over POP-INHERITED (documented trap = 9): got 9 want 9 -> PASS
  CONTROL 'except ValueError' regex over POP-ALL (fully derived = 10): got 10 want 10 -> PASS
  CONTROL 'except ValueError' AST-authoritative: got 6 want 6 -> PASS
```

**The documented trap: 9 candidates in → 3 dropped (1 comment, 2 unrelated handlers) → 6 out.**
Each dropped item named:

1. **`src/mission_runtime/resolution.py:491` — a comment, not a handler.**
   `# malformed; the ``except ValueError`` below reproduces the historical`. It is prose *about* the
   handler at `:514`, four lines of comment above the `try`.
2. **`src/mission_runtime/resolution.py:420` — an unrelated handler.** It wraps
   `require_explicit_feature(feature, command_hint="--mission <slug>")` and converts its `ValueError`
   into `ActionContextError`. Not a `meta.json` read.
3. **`src/specify_cli/missions/_read_path_resolver.py:137` — an unrelated handler**, inside
   `specify_cli.missions._read_path_resolver.stored_topology_from_meta` (`:120`). It catches the
   enum-coercion `ValueError` from `MissionTopology(raw)` on an **already-parsed** mapping. Not a
   `meta.json` read.

> **The trap's population is under-specified upstream, and a FOURTH spurious hit exists.** "The six
> files" names the six *handlers*, which live in only **four** files. The documented answer **9**
> reproduces over an 8-file population (the 9 distinct census files minus
> `src/specify_cli/bulk_edit/gate.py`). Over the **fully derived** population — all 9 distinct files
> of the 13 census sites — the same regex returns **10**, with a fourth spurious hit no upstream
> artifact names: **`src/specify_cli/bulk_edit/gate.py:71`**, inside
> `specify_cli.bulk_edit.gate._feature_dir_rel` (`:61`), catching `Path.relative_to`'s `ValueError`.
> Both triages are printed above so the number can never be quoted without its population. The
> AST-authoritative answer is **6** under either population.

### 2.3 Why 6, not 4

The inherited scoping was "every degrade handler", which is **4**. The correct count is **6**: rows 9
and 12 are **refuse-typed** and *also* catch `ValueError`. Routing them without widening the handler
leaks `MissionMetaReadError` out of a function contracted to raise `DecisionError`
(`specify_cli.decisions.service`) or `PlanningBranchResolutionFailed`
(`specify_cli.missions._resolve_planning_branch`). Leaving those two unmandated is the **`C-002`
violation the previous slicing shipped**.

### 2.4 The type fact that makes all six load-bearing

`specify_cli.core.paths.MissionMetaReadError` (`core/paths.py:506`) is a **`RuntimeError`**, quoted
from source:

```python
class MissionMetaReadError(RuntimeError):
    """Raised when meta.json exists but cannot be decoded.
```

MRO, printed from the imported class: `MissionMetaReadError -> RuntimeError -> Exception ->
BaseException -> object`; `issubclass(MissionMetaReadError, ValueError)` is **`False`**. So an
`except ValueError` handler **does not** catch it. Every one of the 6 must widen in the same edit as
its routing, or the arm it currently implements silently stops firing.

### 2.5 The `except Exception` ban — over **all six**, not only the two refuse-typed

`specify_cli.missions._read_path_resolver.MissionSelectorAmbiguous` (`_read_path_resolver.py:44`) is
declared `class MissionSelectorAmbiguous(Exception)`; MRO `MissionSelectorAmbiguous -> Exception ->
BaseException -> object`, `issubclass(..., ValueError)` is **`False`**. It is raised *inside* row 1's
`try`, by `_canonicalize_primary_read_handle` — the source comment at `resolution.py:496-497` says so
outright: "``MissionSelectorAmbiguous`` (raised by ``_canonicalize_primary_read_handle``) is NOT a
``ValueError`` and correctly still propagates uncaught." A broadened `except Exception` at any of the
six therefore **silently swallows an ambiguous-handle refusal** (`SC-007`). **`except Exception` is
banned at all six handlers.**

### 2.6 Row 1's handler is **EXTENDED, not narrowed**

Row 1's `try` (`resolution.py:504-513`) wraps three things, not one:

```python
    try:
        primary_dir = _compose_primary_feature_dir(
            repo_root,
            _canonicalize_primary_read_handle(repo_root, mission_slug),
        )
        meta = load_meta(
            primary_dir,
            allow_missing=True,
            on_malformed="raise",
        )
    except ValueError:
        return ""
```

`_compose_primary_feature_dir`'s path-traversal guard (`assert_safe_path_segment`) raises a **real
`ValueError`**, and the source comment at `resolution.py:492-495` records that the handler
deliberately degrades that case to `""` as well. **Target shape:
`except (MissionMetaReadError, ValueError)`.** This is an **extension**, not a narrowing: `WP04` must
not read `US2` scenario 3 as licence to drop `ValueError` here. Dropping it would let an unsafe path
segment escape a function whose contract is to return `""`.

### 2.7 Row 8's handler, and the dead `FileNotFoundError` arms — not one of the 6

`specify_cli.context.resolver._read_meta_json`'s arm is `except FileNotFoundError as exc:`
(`resolver.py:76`), not `except ValueError`, which is why it is **not** one of the 6. Routing makes
it **unreachable**: `specify_cli.core.paths.load_meta_fail_closed` hard-codes `allow_missing=True`
(`core/paths.py:676`, `return load_meta(feature_dir, allow_missing=True, on_malformed="raise")`), so
a missing file yields `None`, never `FileNotFoundError`. Its removal is `FR-013`/`SC-015`, owned by
`WP03`. **The same is true at rows 9 and 12**, which carry *both* a `ValueError` handler (one of the
6) **and** a dead `FileNotFoundError` arm (`service.py:135`, `_resolve_planning_branch.py:117`).

---

## §3 — The bypass set: 5 read expressions / 6 invocation sites

### 3.1 Both totals, in one sentence, with the reason they differ

The reads that reach `meta.json` with **no `load_meta` at all** number **5 read expressions** /
**6 invocation sites**. They differ because
`specify_cli.cli.commands.merge_driver._load_json_object` (`merge_driver.py:167`) is **invoked from
two call sites** — `merge_driver.py:243` and `:244`, quoted from source:

```python
        merged = reconcile_meta_payloads(
            _load_json_object(ours),
            _load_json_object(theirs),
        )
```

Command: `grep -n '_load_json_object' src/specify_cli/cli/commands/merge_driver.py` (**regex**, 3
hits in → 1 dropped as the `def` line at `:167` → 2 invocation sites out). Under the **call-site**
convention the bypass total is **6**; under the **read-expression** convention it is **5**.

### 3.2 The call-site convention is the one this mission uses elsewhere

> **BOXED NOTE — convention is declared inline at every count, in both contracts.** The call-site
> convention is what makes census rows 10/11 count `read_primary_meta` as **2** and the routable set
> total **13 call sites** rather than 12 ledger rows. Both conventions are defensible.
> **Mixing them silently inside one document is the defect this row exists to prevent.** No sentence
> in either contract adds a read-expression count to a call-site count: "13 call sites" and
> "5 read expressions / 6 invocation sites" are **not addable**.

### 3.3 The 5 read expressions, each with its enclosing symbol and its parser

| # | Module-qualified symbol | Read `file:line` `[shifts]` | Parse | Parser |
|---|---|---|---|---|
| B1 | `specify_cli.git.ref_advance._committed_meta_object` (`:192`) | `git show` at `ref_advance.py:203` | `:206` | `_parse_meta_object` (`:181-189`) |
| B2 | `specify_cli.git.ref_advance._meta_change_is_vcs_lock_only` (`:231`) | path built `:242`, `read_text` `:244` | `:247` | `_parse_meta_object` |
| B3 | `specify_cli.cli.commands.implement_cores._committed_meta_mapping` (`:330`) | `show_blob` at `implement_cores.py:335` | `:338` | `_parse_meta_mapping` (`:259`) |
| B4 | `specify_cli.cli.commands.implement_cores._is_self_write_only_diff` | `read_bytes` at `:427` (path built `:422-423`, gated `name == _META_JSON_FILENAME` at `:426`) | `:427` | `_parse_meta_mapping` |
| B5 | `specify_cli.cli.commands.merge_driver._load_json_object` (`:167`) | `read_text` at `merge_driver.py:171` | `:174` | itself (inline `json.loads`) |

Invocation-site convention: B1, B2, B3, B4 contribute one each; B5 contributes **two**
(`:243`, `:244`) ⇒ **6 invocation sites**.

**Correction to the work-package prompt at B4.** It cites "path built at `:421-427`". Read on the
tree, `:421` is the closing `"""` of the docstring; the path is built at `:422-423`
(`name = Path(repo_rel).name` / `source = (repo_root / Path(repo_rel)).resolve()`) and the
`meta.json` gate is at `:426`. `read_bytes` at `:427` is correct.

### 3.4 `plan.md` `[UNVERIFIED]` item 4 reconciled — the hypothesis **holds**

`analysis-report.md` cites `ref_advance.py:203` and `:242`; `research/3162-census.md` cites `:206`
and `:244`. **These are different expressions in the same two functions, not a conflict.** Verified
on the tree, the four source lines quoted verbatim:

```
203:    result = _run_git(worktree, ["show", f"HEAD:{path}"], env=env)      # B1 READ
206:    parsed = _parse_meta_object(result.stdout)                          # B1 PARSE
242:    meta_path = worktree / path                                        # B2 PATH BUILD
244:        worktree_text = meta_path.read_text(encoding="utf-8")           # B2 READ
```

and B2's parse, one line per parse as required:

```
247:    worktree_meta = _parse_meta_object(worktree_text)                   # B2 PARSE
```

`specify_cli.git.ref_advance._meta_change_is_vcs_lock_only` is additionally gated by
`Path(path).name == _META_FILENAME` at `ref_advance.py:315` (`_META_FILENAME = "meta.json"`,
`:45`). **The hypothesis is confirmed; no upstream document was wrong, they cited different lines of
the same functions.**

### 3.5 The three private parsers, and why the architectural gate is blind to each

| Parser (module-qualified) | `file:line` `[shifts]` | Blindness reason |
|---|---|---|
| `specify_cli.git.ref_advance._parse_meta_object` | `ref_advance.py:181` | **Cross-function split** — the read (`:203` / `:244`) and the parse (`:206` / `:247`) are in different functions, so no single scanned function shows a `meta.json` path flowing into a `json.loads`. |
| `specify_cli.cli.commands.implement_cores._parse_meta_mapping` | `implement_cores.py:259` | **Cross-function split** — same shape; the read is at `:335` / `:427`, the parse inside the helper. |
| `specify_cli.cli.commands.merge_driver._load_json_object` | `merge_driver.py:167` | **Path arrives as a bare parameter** — `def _load_json_object(path: Path)`. Nothing in the function body names `meta.json`; the meta-ness lives entirely at the two call sites (`:243`, `:244`). |

The seam-level `_parse_meta_text` referenced in planning is
`specify_cli.mission_metadata._parse_meta_text` (`mission_metadata.py:331`), **not**
`specify_cli.missions.mission_metadata._parse_meta_text` — that module does not exist on this tree
(same misqualification corrected in §1.2).

### 3.6 The triage, with an input count at every step

Probe: **AST walk** for every stage (regex used nowhere in this chain). Reproduced on this tree:

| Stage | Filter | In | Out | Dropped, and why |
|---|---|---|---|---|
| S0 | every `*.py` under `src/` | — | **1 199** files | — |
| S1 | file text contains the literal `"meta.json"` | 1 199 | **172** files | 1 027 never mention `meta.json` |
| S2 | of S1, **zero** routed `load_meta*` calls (`ROUTED_CALLEES` name set, AST) | 172 | **103** files | 69 already route |
| S3 | of S2, ≥1 `.load` / `.loads` attribute call | 103 | **30** files | 73 mention `meta.json` but parse nothing |
| S4 | parse sites inside S3 | 30 files | **41** sites | — |
| S5 | of the 41, **meta-ish** (the parsed bytes come from a `meta.json`) | 41 | **13** sites | 28 parse something else (JSONL event logs, `status.json`, `merge-state.json`, `acceptance-matrix.json`, schema-version YAML, issue-matrix JSON, …) |
| S6 | of the 13: allow-listed inline | 13 | **7** | — |
| S6 | of the 13: ruled out | 13 | **3** | named below |
| S6 | of the 13: **bypass parsers** | 13 | **3** | the §3.5 table |

`7 + 3 + 3 = 13`. **The 3 ruled out, named:**

1. `specify_cli.cli.commands._doctrine_collect._resolve_pack_version` (`_doctrine_collect.py:110`) —
   parses **`pack-manifest.yaml`** (`manifest_path = snapshot_path / "pack-manifest.yaml"`, `:104`),
   not `meta.json`. (The plan's shorthand for this class is "`metadata.yaml`"; the actual filename on
   this tree is `pack-manifest.yaml`.)
2. `specify_cli.orchestrator_api.commands._parse_review_result_json` (`:1299`) — parses the
   `--review-result-json` **CLI string**. Evidence-JSON, never a file read.
3. `specify_cli.orchestrator_api.commands.transition` (`:1386`) — parses the `--evidence-json` CLI
   string. Evidence-JSON, never a file read.

**The 7 allow-listed inline reads** (from `tests/architectural/inline_meta_read_allowlist.yaml`,
`grep -c '^- file:'` → **7**, `inline_meta_read_baseline: 7` at `:19`, shrink-only):
`m_0_13_0_research_csv_schema_check.py::ResearchCSVSchemaCheckMigration.detect` (`:56`) and
`.apply` (`:113`); `m_0_13_5_add_commit_workflow_to_templates.py::AddCommitWorkflowToTemplatesMigration.apply`
(`:73`); `m_0_13_8_target_branch.py::TargetBranchMigration.detect` (`:48`) and `.apply` (`:86`);
`charter._io._resolve_mission_id` (`:380`); `charter.mission_type_profiles._read_meta_mission_type`
(`:650`).

> **Note the intersection with §1.5**: `charter._io._resolve_mission_id` is a **fifth** live
> `_resolve_mission_id`-shaped read in this codebase, and it is an inline read rather than a routable
> site. Another reason no citation in this mission may be a bare symbol.

### 3.7 Closure probes — **5/6 is the current count, not the closure**

> **5 read expressions / 6 invocation sites is what is measurable today. It is not a closure proof.**
> `merge_driver._load_json_object` is blind precisely *because* the path arrives as a bare parameter,
> and no name-based probe can rule out another parser of that shape.

Two probes, each with its denominator:

**Constants-vector probe** (**AST walk**): files carrying a `"meta.json"` string constant **49** →
of those, files with zero routed `load_meta*` calls **22** → minus the 10 files already accounted for
by §3.5 / §3.6 → **15** unaccounted candidate files → of those, `.load` / `.loads` parse calls **8**
→ of those 8, parses whose input traces to a `meta.json` **0**. The 8 are
`acceptance/matrix.py:416` (`acceptance-matrix.json`), `merge/conflict_resolver.py:162` (event-log
lines), `merge/preflight.py:433`, `:486`, `:523` (status events / `status.json`),
`merge/state.py:226` (`merge-state.json`), `migration/runner.py:206` (schema-version YAML),
`tasks/issue_matrix_migration.py:70` (issue-matrix JSON). **Result: 0 new bypass sites.**

**Call-surface probe** (**AST walk**): `ast.Call` nodes over `src/` **64 512** (in 1 199 files; of
which `func` is an `ast.Attribute` at 32 294, an `ast.Name` at 32 158, other 60) → narrowed to
`.load` / `.loads` attribute calls **352** in **240** files → intersected with the S1 `meta.json`
population and the S2 zero-routed filter → the **41** parse sites of S4 → the **13** meta-ish of S5.
**Result: no new site beyond the 5/6.**

> **`[UNVERIFIED]` — two upstream denominators did not reproduce.** `plan.md` / the post-plan pass
> record the call-surface probe as "over **20 276** calls → **70** candidates". Measured here the
> total call surface under `src/` is **64 512** and no narrowing tried reproduces 20 276 or 70. The
> *conclusion* (no new site) reproduces; the denominators do not, so they are **not** restated as
> facts. The reproducible denominators are the ones printed above. Similarly the upstream
> constants-vector probe is recorded only as "**0** new" with no input count; the chain above supplies
> the missing input counts (49 → 22 → 15 → 8 → 0).

### 3.8 Which of the 5 the seam reaches, and on what basis

`C-004`'s original basis was **refuted** — do **not** restate "structurally cannot use the seam".
**2 of the 5 hold real filesystem paths whose parents are feature dirs:**

- **B2**, `specify_cli.git.ref_advance._meta_change_is_vcs_lock_only` — `meta_path = worktree / path`
  at `:242`, under the `Path(path).name == _META_FILENAME` gate at `:315`.
- **B4**, `specify_cli.cli.commands.implement_cores._is_self_write_only_diff` — `source` built at
  `:422-423`, under the `name == _META_JSON_FILENAME` gate at `:426`.

Both are reachable by `specify_cli.core.paths.load_meta_fail_closed` today. **The obstacle at B4 is
the routed budget, not structure** (see `contracts/headroom-allocation.md`: `WP05` spends the single
net routed call on B2's parse at `ref_advance.py:247` per operator ruling **R-1**).

### 3.9 The three-tier seam family

| Tier | Shape | Symbol | Status | Reaches |
|---|---|---|---|---|
| **L1** | pure decode, `text\|bytes → dict\|None`, typed | — | **MISSING — must be filed, not built** (`SC-009`) | would reach B1, B3 (the blob sites) |
| **L2** | path-level | `specify_cli.mission_metadata._parse_meta_text` (`mission_metadata.py:331-349`) | exists | **cannot** serve B1/B3: it takes a `Path` and performs the read itself, so a blob already in memory has no path to hand it |
| **L3** | dir-level | `specify_cli.core.paths.load_meta_fail_closed` (`core/paths.py:638`) | exists | **2 of the 5** — B2 and B4 |

L1 is **filed, not built** in this mission. That is why the four non-routed bypass sites are
diagnosable-only.

---

## §4 — Both live floors, and the two-sided routed band

### 4.1 Live routed = 129, with its command and input count

The gate's own scanner, not a grep. Suite run first, redirected (never piped — the exit status is
needed), and the `N passed` line quoted:

```bash
.venv/bin/python -m pytest tests/architectural/test_inline_meta_read_gate.py -ra > <scratch>/wp01_routed.txt 2>&1
```

```
======================== 40 passed in 90.62s (0:01:30) =========================
```

Exit status `0`; `grep -c '^ERROR tests/'` → `0`. (`-ra`, never `-rf`. Counted `^ERROR tests/`, not
`^ERROR `.) Then the scanner invoked directly, printing the count **and the input file count it
walked**:

```
== §4 LIVE COUNTS (gate's own AST scanners) ==
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 129
  INLINE live (AST walk): 7
```

**Live routed = 129 call sites, over an input population of 1 199 `*.py` files under
`<tree>/src`. Probe: AST walk** (`scan_routed_load_meta_calls`,
`tests/architectural/test_inline_meta_read_gate.py:657`).

### 4.2 The trap: the naive **regex** returns 296

```
  CONTROL routed naive regex (grep -rn 'load_meta' src): got 296 want 296 -> PASS
```

Command: `grep -rn 'load_meta' src --include='*.py' | wc -l` → **296**.

**296 candidates in → 167 dropped → 129 out.** Drop reason: the regex matches **definitions**
(`def load_meta`, `def load_meta_strict`, …), **imports** (`from specify_cli.mission_metadata import
load_meta`), **docstrings and comments** that name the reader, and **non-`meta.json` callees** that
merely share the substring. It counts *text*, not *call nodes*.

**The authoritative 129 came from an AST walk** over the scanner's own file population (1 199 files),
independently reproduced in the post-plan pass over the same 1 199 files. Where the answer must be
exact, this manifest uses the AST walk; the regex appears only as this controlled negative.

### 4.3 The gate constants as they stand today, by symbol and line

```
  const INLINE_META_READ_FLOOR = 7
  const FLOOR_MARGIN = 2
  const ROUTED_LOAD_META_FLOOR = 126
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
```

- `ROUTED_LOAD_META_FLOOR = 126` — `tests/architectural/test_inline_meta_read_gate.py:221`
- `ROUTED_LOAD_META_FLOOR_MARGIN = 4` — `:220`
- `INLINE_META_READ_FLOOR = 7` — `:127`
- `FLOOR_MARGIN = 2` — `:134`
- allow-list `tests/architectural/inline_meta_read_allowlist.yaml` — **7** entries
  (`grep -c '^- file:'` → 7), `inline_meta_read_baseline: 7` at `:19`, shrink-only.

### 4.4 The three assertions of `test_routed_load_meta_floor` (`:1084`), quoted verbatim

```python
    routed = scan_routed_load_meta_calls(SRC_ROOT)
    assert len(routed) >= ROUTED_LOAD_META_FLOOR, (
        f"routed load_meta*() census dropped to {len(routed)}; expected "
        f">= {ROUTED_LOAD_META_FLOOR}. A drop means call sites stopped routing "
        "through the canonical reader family."
    )
    assert len(routed) > ROUTED_LOAD_META_FLOOR, (
        "ROUTED_LOAD_META_FLOOR must be a concrete census integer strictly below "
        "the live routed count, not '>= len(routed)' (anti-vacuous)."
    )
    assert len(routed) - ROUTED_LOAD_META_FLOOR <= ROUTED_LOAD_META_FLOOR_MARGIN, (
        f"ROUTED_LOAD_META_FLOOR ({ROUTED_LOAD_META_FLOOR}) is more than "
        f"ROUTED_LOAD_META_FLOOR_MARGIN ({ROUTED_LOAD_META_FLOOR_MARGIN}) below the "
        f"live routed count ({len(routed)}); tighten the floor."
    )
```

The test's own docstring states the intent: *"both bounds are enforced (``live - MARGIN <= floor <
live``) so the floor is a concrete census integer, never a tautological ``>= len(routed)``."*

**Band derived from the quoted text, not copied from anywhere.** Clause 1 gives
`len(routed) >= FLOOR`. Clause 2 gives `len(routed) > FLOOR` — **strict, and explicitly
anti-vacuous** — which dominates clause 1, so the low bound is `FLOOR + 1`. Clause 3 gives
`len(routed) - FLOOR <= MARGIN`, so the high bound is `FLOOR + MARGIN`. With the constants read off
`:221` and `:220`:

```
  DERIVED routed band: [127, 130] (two-sided; 126 is RED)
```

low bound = `126 + 1`; high bound = `126 + 4`. The admissible band is **`[127, 130]`** — **not**
`[126, 130]`. Three earlier artifacts stated `[126, 130]`; that is wrong, because clause 2 is strict.

> Every appearance of the integer `127` in this document is the **low bound of the derived band**
> `[127, 130]`. It is **never** a `ROUTED_LOAD_META_FLOOR` value. See §4.7.

### 4.5 **126 is RED.**

126 is RED. A live routed count of exactly 126 fails clause 2 (`len(routed) > ROUTED_LOAD_META_FLOOR`
is `126 > 126`, false), even though it passes clause 1.

**The constraint is two-sided, and the downward direction is the one this programme keeps losing.**
A routing pass that **collapses** two calls into one reds this gate **from below**, exactly as one
that adds too many reds it from above. The concrete temptation is in this document's own §1 table:
**census rows 10 and 11 are two `load_meta` calls inside one function**,
`specify_cli.missions._read_path_resolver.read_primary_meta` (`:846` first read, `:862`
canonicalized re-read). Folding those two reads into one during routing is a natural-looking
tidy-up; it takes routed from 129 to 128, and a second such fold anywhere takes it to 126 — RED.
This programme has already had **three floor mismatches caused by folds that collapsed call sites**
(§4.6). **A document that records only a ceiling reintroduces the failure mode.** Both bounds are
binding.

### 4.6 The attribution machinery, and the three prior false reds

`ROUTED_CALLEES` (`tests/architectural/test_inline_meta_read_gate.py:105`) matches callee **names**
over the whole of `src/`, not the call graph:

```python
ROUTED_CALLEES: frozenset[str] = frozenset(
    {
        "load_meta",
        "load_meta_strict",
        "load_meta_or_empty",
        "load_meta_fail_closed",
        "_load_meta_fail_closed",
        "_require_meta",
    }
)
```

It counts `specify_cli.doc_analysis.doc_state._require_meta` (`doc_state.py:68`) — a **locally
defined** function that happens to share the name. The census is **global over `src/`**, so any
unrelated commit anywhere that adds a call named `load_meta*` moves the number. The gate header's own
record of the third recurrence, quoted from `:200-217`:

> "…neither helper name was added to :data:`ROUTED_CALLEES`, so the census mechanically dropped even
> though routing coverage did not regress — this is the SAME shape as the PR #3155 drop two
> paragraphs above (the **THIRD recurrence of this exact census/floor mismatch**).
> ``ROUTED_LOAD_META_FLOOR`` (117) was left unmoved across this drop, which is what turned it into a
> **false-red CI failure**: measured directly … on 2026-08-04, live == 110 < 117."

**This is why the command and its input count are part of the anchor.** A mid-mission deviation from
129 must be **attributable** — to this mission's routing, or to an unrelated landing — *before*
anyone "fixes" it. The anchor is: `scan_routed_load_meta_calls` over **1 199** files under
`<tree>/src` on the repository root, `PYTHONPATH=<tree>/src`.

### 4.7 No re-derived floor value here — the prohibition

> **PROHIBITION (binding on every downstream work package).**
> **The change that moves `ROUTED_LOAD_META_FLOOR` (`WP06`) MUST print the measured live routed count
> and derive the new floor from it. Copying a floor value or a band from `plan.md`, from
> `analysis-report.md`, or from any other planning artifact is FORBIDDEN.**
> `plan.md` `[UNVERIFIED]` item 1 offers a candidate floor and a resulting band. **Both are derived
> from `R-1`'s stated rule, not measured**, and neither is restated in this document. This hole is
> deliberate: filling it here would pre-empt a measurement `WP06` owes.

**The rule, recorded as a rule and not as a value**: on 2026-08-04, `ROUTED_LOAD_META_FLOOR` was
raised **117 → 126** "to restore the established 3-below-live gap (mechanic 2) against the corrected
129" (gate header, `:215-217`). That is the precedent — *the gap-restoring operation*, applied to a
freshly measured live count. Not a number to copy.

`NFR-002`'s **immovable-floor clause is STRUCK** under `R-1` and must not be restated as live. See
`contracts/headroom-allocation.md` §6.

### 4.8 Live inline = 7, and the four mutually-locking assertions

```
  INLINE live (AST walk): 7
  inline 7 <= 7 and gap <= 2: OK
```

**Live inline = 7 call sites**, input population **1 199** `*.py` files under `<tree>/src`. **Probe:
AST walk** (`scan_inline_meta_reads`, `test_inline_meta_read_gate.py:589`). Same suite run as §4.1,
`40 passed`.

The assertions that lock it, by symbol and line:

| Test | Line | What it asserts |
|---|---|---|
| `test_inline_meta_read_floor` | `:1061` | `count <= INLINE_META_READ_FLOOR` **and** `INLINE_META_READ_FLOOR - count <= FLOOR_MARGIN` |
| `test_inline_meta_read_gate_green_against_seeded_allowlist` | `:1109` | `check_inline_meta_read_gate(SRC_ROOT, allowlist) == []` |
| **`test_allowlist_matches_floor`** | **`:1116`** | **`len(load_allowlist(ALLOWLIST_PATH)) == INLINE_META_READ_FLOOR` — an EQUALITY** |
| `test_allowlist_shrink_only` | `:1125` | `len(keys) <= baseline` (`inline_meta_read_baseline`, shrink-only) |
| `test_allowlist_entries_are_still_live` | `:1166` | every allow-list entry matches a live site (no stale entry masking a completed drain) |

**`test_allowlist_matches_floor` (`:1116`) is an EQUALITY**, and it is the assertion that **forecloses
the `floor→8 / allowlist→7` escape**: you cannot raise the inline ceiling to absorb a new inline read
without adding an allow-list entry, and you cannot add an allow-list entry without breaching
`test_allowlist_shrink_only` against a baseline of 7. **No earlier mission artifact mentioned this
equality.**

### 4.9 Expected trajectory (each work package checks itself against this row)

Convention: every number below is a **routed call-site count**.

| Stage | Routed | Net delta | Inline | Notes |
|---|---|---|---|---|
| pre-mission (this freeze) | **129** | — | **7** | in `[127, 130]`; floor 126 |
| `WP02` | 129 | **0-net** | 7 | 6 swaps; `load_meta` and `load_meta_fail_closed` are both in `ROUTED_CALLEES` |
| `WP03` | 129 | **0-net** | 7 | 3 swaps |
| `WP04` | 129 | **0-net** | 7 | 4 swaps |
| `WP05` | **130** | **+1** | 7 | routes `ref_advance.py:247`; the mission's single net routed call (R-1) |
| `WP06` | 130 | **0-net** | 7 | re-derives `ROUTED_LOAD_META_FLOOR` from the **measured** live count |
| `WP07` | 130 | **0-net** | 7 | test + tracker only |
| `WP08` | 130 | **0-net** | 7 | re-derives on the **integrated** tree, not by summing lane numbers |

Inline stays **7** throughout: `WP05` routes `ref_advance.py:247`, which is a **bypass parse**, not an
allow-listed inline read, so the inline census is untouched — and `test_allowlist_matches_floor`
(`:1116`) would red immediately if it were not.

### 4.10 Full regeneration output

The complete verbatim output of `scripts/verify_meta_routing_manifest_3162.py` on this tree, exit
status `0`, `VERDICT: PASS` — this is the single command that reproduces every number in §1, §2 and
§4:

```
==============================================================================
verify_meta_routing_manifest_3162 — mission meta-fail-closed-3162-01KZ7FSQ
==============================================================================
TREE measured : /home/jeroennouws/dev/sk-missions/3162
SRC_ROOT      : /home/jeroennouws/dev/sk-missions/3162/src
PYTHONPATH    : /home/jeroennouws/dev/sk-missions/3162/src
sys.executable: /home/jeroennouws/dev/sk-missions/3162/.venv/bin/python
== §1 LEDGER ROWS ==
  grep -c 'pending-batch-a' test_meta_fail_closed_full_census_contract.py: 13 (candidates in)
  legend/prose hits dropped: 1 at line(s) [185]
  ledger ROWS out: 12  (convention: ledger row)
  CALL SITES out: 13  (convention: call site; expanded from row counts)
  multi-count row: src/specify_cli/missions/_read_path_resolver.py::read_primary_meta count=2
== §1 ARMS (AST classifier, not grep) ==
  CONTROL pairs in: 2
  CONTROL src/specify_cli/core/paths.py::load_meta_fail_closed call@676 arm=REFUSE-typed want=REFUSE-typed handler@677
  CONTROL src/specify_cli/mission_metadata.py::load_meta_or_empty call@391 arm=REFUSE-raw want=REFUSE-raw handler@-1
  CONTROL verdict: ALL PASS
  INPUT rows (ledger pending-batch-a): 12
  SITE src/mission_runtime/resolution.py::_mid8_from_primary_meta call@509 arm=DEGRADE handler@514
  SITE src/mission_runtime/resolution.py::_resolve_coordination_branch call@852 arm=DEGRADE handler@853
  SITE src/mission_runtime/resolution.py::_resolve_mission_id call@1107 arm=DEGRADE handler@1108
  SITE src/runtime/next/_internal_runtime/planner.py::_resolve_workflow_for_mission call@188 arm=REFUSE-raw handler@-1
  SITE src/runtime/next/runtime_bridge_io.py::_workflow_runtime_template call@380 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/bulk_edit/gate.py::_is_bulk_edit_mission call@57 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/bulk_edit/gate.py::ensure_occurrence_classification_ready call@80 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/context/resolver.py::_read_meta_json call@75 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/decisions/service.py::_resolve_mission_id call@134 arm=REFUSE-typed handler@141
  SITE src/specify_cli/missions/_read_path_resolver.py::read_primary_meta call@846 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/missions/_read_path_resolver.py::read_primary_meta call@862 arm=REFUSE-raw handler@-1
  SITE src/specify_cli/missions/_resolve_planning_branch.py::load_mission_target_branch call@116 arm=REFUSE-typed handler@122
  SITE src/specify_cli/upgrade/feature_meta.py::load_feature_meta call@42 arm=DEGRADE handler@43
  DERIVED call sites: 13 / DEGRADE: 4 / REFUSE-raw: 7 / REFUSE-typed: 2
== §2 AUTHORITATIVE HANDLERS (AST) ==
  src/mission_runtime/resolution.py:514  (_mid8_from_primary_meta)
  src/mission_runtime/resolution.py:853  (_resolve_coordination_branch)
  src/mission_runtime/resolution.py:1108  (_resolve_mission_id)
  src/specify_cli/decisions/service.py:141  (_resolve_mission_id)
  src/specify_cli/missions/_resolve_planning_branch.py:122  (load_mission_target_branch)
  src/specify_cli/upgrade/feature_meta.py:43  (load_feature_meta)
== TRAPS (regex probes, controlled negatives) ==
  CONTROL routed naive regex (grep -rn 'load_meta' src): got 296 want 296 -> PASS
  [POP-ALL (9 census files, fully derived)] population = 9 files
  [POP-ALL (9 census files, fully derived)] 10 candidates in -> 4 dropped -> 6 out
    [POP-ALL (9 census files, fully derived)] DROP src/mission_runtime/resolution.py:420 [UNRELATED-HANDLER] except ValueError as exc:
    [POP-ALL (9 census files, fully derived)] DROP src/mission_runtime/resolution.py:491 [COMMENT] # malformed; the ``except ValueError`` below reproduces the historical
    [POP-ALL (9 census files, fully derived)] DROP src/specify_cli/bulk_edit/gate.py:71 [UNRELATED-HANDLER] except ValueError:
    [POP-ALL (9 census files, fully derived)] DROP src/specify_cli/missions/_read_path_resolver.py:137 [UNRELATED-HANDLER] except ValueError:
  [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] population = 8 files
  [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] 9 candidates in -> 3 dropped -> 6 out
    [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] DROP src/mission_runtime/resolution.py:420 [UNRELATED-HANDLER] except ValueError as exc:
    [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] DROP src/mission_runtime/resolution.py:491 [COMMENT] # malformed; the ``except ValueError`` below reproduces the historical
    [POP-INHERITED (8 files = POP-ALL minus src/specify_cli/bulk_edit/gate.py)] DROP src/specify_cli/missions/_read_path_resolver.py:137 [UNRELATED-HANDLER] except ValueError:
  CONTROL 'except ValueError' regex over POP-INHERITED (documented trap = 9): got 9 want 9 -> PASS
  CONTROL 'except ValueError' regex over POP-ALL (fully derived = 10): got 10 want 10 -> PASS
  CONTROL 'except ValueError' AST-authoritative: got 6 want 6 -> PASS
== §4 LIVE COUNTS (gate's own AST scanners) ==
  INPUT .py files walked: 1199
  ROUTED live (AST walk): 129
  INLINE live (AST walk): 7
  const INLINE_META_READ_FLOOR = 7
  const FLOOR_MARGIN = 2
  const ROUTED_LOAD_META_FLOOR = 126
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band: [127, 130] (two-sided; 126 is RED)
== BOUNDS ==
  routed 129 in [127, 130]: OK
  inline 7 <= 7 and gap <= 2: OK
  CONTROL routed AST authoritative: got 129 want 129 -> PASS
==============================================================================
VERDICT: PASS
```

### 4.11 The script's fail path, exercised

The band is not decorative: the script **reads the four constants off
`tests/architectural/test_inline_meta_read_gate.py` and re-derives the band from them**, then exits
non-zero when the live count leaves it. Exercised against a **scratch tree** whose `src/` is a symlink
to this tree's `src/` and whose `tests/` is a copy with `ROUTED_LOAD_META_FLOOR` patched to `100`
(`src/` and `tests/` on the real tree untouched — `git status --porcelain src/ tests/` empty):

```
  const ROUTED_LOAD_META_FLOOR = 100
  const ROUTED_LOAD_META_FLOOR_MARGIN = 4
  DERIVED routed band: [101, 104] (two-sided; 100 is RED)
== BOUNDS ==
  routed 129 in [101, 104]: OUT OF BAND
  inline 7 <= 7 and gap <= 2: OK
==============================================================================
VERDICT: FAIL
SCRIPT EXIT (out-of-band scratch tree) = 1
```

The derived band tracked the patched constant (`[101, 104]` from floor `100`), the bound check
reported `OUT OF BAND`, and the process exit status was **1**. The same non-zero path fires when any
control fails to reproduce its known answer — observed during development when the `except ValueError`
trap population was wrong and the run exited `1` rather than reporting a number whose control had
failed.

---

## Appendix A — corrections this manifest carries, and what is struck

1. **`legacy-<slug>` is constant.** Row 3's fallback is composed from the caller's `mission_slug`
   **argument** at `resolution.py:1114`, with `meta` set to `None` at `:1109`. The earlier claim that
   it is "derived from the malformed file" is **withdrawn**. All four degrade fallbacks are constant
   (§1.6).
2. **Census row 8's sole behavioural pin is
   `tests/specify_cli/context/test_resolver.py:256`** —
   `with pytest.raises(MissingIdentityError, match="meta.json not found"):`, read and confirmed as a
   real assertion. **`tests/integration/test_coord_loop_workspace.py:611` and `:627` are docstring
   prose, not assertions** — `:611` is a class docstring
   (`TestResolveContextReadsFromPrimary`, `:606`) and `:627` a method docstring
   (`test_resolve_context_reads_wp_from_primary`, `:620`). Both were read on the tree. This mission
   has had docstring prose propagate as a load-bearing claim through eight references; **a cited line
   number is not evidence that the line asserts anything.**
3. **`on_malformed` split is 6 explicit / 7 default**, not 7/6 (§1.7).
4. **The module is `specify_cli.mission_metadata`**, not `specify_cli.missions.mission_metadata`
   (§1.2, §3.5).
5. **The `except ValueError` trap has a fourth spurious hit** and its population is under-specified
   upstream (§2.2).
6. **`NFR-002`'s immovable-floor clause is STRUCK.** The one-call budget stands; the immovability
   does not (§4.7, and `contracts/headroom-allocation.md` §6).
7. **`plan.md`'s "31 candidates / 30 rejected at clause 3"** was refuted by the post-plan squad and
   is not carried here; the measured chain is `19 → 17 at clause 2 → 1 at clause 3 → 1 accepted`, and
   clause **2** — not clause 3 — is what holds gate false positives at zero.
