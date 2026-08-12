---
affected_files:
- path: tests/architectural/_home_pin_scan.py
- path: tests/architectural/test_home_pin_scan_limbs.py
cycle_number: 1
mission_slug: isolated-home-pin-guard-r1a-01KZNMA3
reproduction_command: /home/jeroennouws/dev/sk-missions/3157/.venv/bin/python -m pytest
  tests/architectural -q -p no:cacheprovider
reviewed_at: '2026-08-11T16:53:05+02:00'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP01
---

# WP01 review — cycle 1

**Reviewer**: reviewer-renata · **Verdict**: **REJECT** (narrow — one required change, one recommended)
**Under review**: `5068b8cbd` on `kitty/mission-isolated-home-pin-guard-r1a-01KZNMA3-lane-a`
**Files**: `tests/architectural/_home_pin_scan.py`, `tests/architectural/test_home_pin_scan_limbs.py` (only these two; `git diff --stat` confirms)

Directives applied: DIR-001 (architectural integrity), DIR-024 (locality), DIR-030 (test/typecheck gate),
DIR-032 (conceptual alignment), DIR-041 (tests as scaffold, not friction).
Tactics: code-review-incremental, reverse-speccing, language-driven-design, architectural-gate-non-vacuity.

The reject is **not** about the code's behaviour, which I could not break in eleven of twelve independent
mutations. It is about one unmechanised constant whose failure mode is silent, catastrophic and two lines
from being closed.

---

## Required change (blocking)

### [HIGH] `tests/architectural/_home_pin_scan.py:310-315` — FR-010's limb is asserted-inert in fact and presented as live

`OWNER_PARAM_NAMES = {"tmp_path", "canonical_home", "runtime_home"}`. **Constructed, not reasoned:**

| Mutation | Result |
|---|---|
| Remove `runtime_home` entirely | **69/69 still pass.** The entry has zero effect on anything. |
| Remove both `runtime_home` and `canonical_home` | 2 fail — **both from this module's own synthetic `_MEMBER_TREE`**, no real-tree assertion moves. |
| Rename `canonical_home` → `isolated_home` (the WP03 risk) | same 2 fail, same synthetic origin. |

Direct construction of the cited site `tests/audit/test_no_legacy_path_literals.py:94`:

```
chain-union params (normalised) = ['argv', 'module_name', 'tmp_path']
silhouette ['monkeypatch', 'tmp_path'] satisfied?  False
resolved value = '<tmp_path>'   (member needs '<tmp_path>/home')
attribution = None
```

The `runtime_home` normalisation fires (`runtime_home` → `tmp_path` is visible in the union) but the site is
refused on **two independent limbs**, so the entry's real-tree member population is **0**. The docstring cites
it as "the live population-1 shape", which is a correct citation of FR-010's *shape* claim but reads as an
anchor the measurement does not support.

`canonical_home` is worse: its only operand is a string the author wrote in `_MEMBER_TREE` and the same string
in production. A rename renames both and stays green. **Nothing outside this module constrains it** —
`contracts/canonical-home-owner.md` does not exist yet, and I checked WP03's prompt, DoD and `not_done_if`:
T012 binds the contract to `tests/conftest.py`'s fixture and **never to `_home_pin_scan.OWNER_PARAM_NAMES`**.

This WP applies FR-007's rule — *"a limb matching nothing must be known to match nothing, or it will be read
as enforcement"* — to fifteen ids, with a positive control each. It does not apply it to its own sixteenth
limb, the one whose stated purpose is *"without this limb the guard goes blind in proportion to R1b's
adoption"*. If this ships as-is and WP03 names the fixture anything else, FR-010's limb goes permanently
inert, every adopting definition becomes invisible, and the **shrink-only census ratchet greens on every
disappearance**. Nothing reds, ever.

**Required (docstring only, no behaviour change):** state in `OWNER_PARAM_NAMES`'s comment that
(a) the measured real-tree member population contributed by `runtime_home` and `canonical_home` is **0** —
`:94` fails the silhouette (no `monkeypatch`) and resolves to `<tmp_path>`, not `<tmp_path>/home`; and
(b) `canonical_home` is a **provisional** name that **no operand outside this module constrains** until
`contracts/canonical-home-owner.md` exists, and that WP03/T012 must assert the contract's declared name
∈ `OWNER_PARAM_NAMES`.

WP01 cannot mechanise this itself: the contract does not exist, `dependencies: []`, and WP03 may not edit
this module. The docstring is the only artefact WP03's implementer is guaranteed to read, because they
import it. Prose in a review file is exactly the handoff `_sole_door_scan.py:13-27` records as having failed.

## Recommended (not blocking)

### [MEDIUM] `test_home_pin_scan_limbs.py` — give FR-010's limb the FR-007 treatment the WP gives the other fifteen

Cheapest honest form, ~6 lines, no production change: assert over the real tree that the FR-010-cited site is
**not** a member and name both reasons (silhouette failure and value mismatch), with `_MEMBER_TREE`'s
`# M4 FR-010 owner param` already serving as the positive control that the limb bites where the shape exists.
That converts a prose claim into a measured population with a control, which is this module's own standard.

---

## Adjudications requested (all three resolved in the implementer's favour)

**1. `key_member(site, chain) -> Member | None` is unsatisfiable — SOUND, substitution FAITHFUL.**
`Member` carries `relpath` (unavailable from `site`/`chain`) and `key`; the same contract's key section says
the key is formed *"Never inside `find_write_sites` or `key_member`."* Both cannot hold. Keeping the positional
signature and narrowing the return to `Attribution`, with `member_key` composing at the boundary in
`discover`, preserves every behavioural clause of the contract's `key_member` row and satisfies C-012(5).
**→ `contracts/home-pin-scan-seam.md` needs amending** (not WP01's to edit): `-> Attribution | None`, and add
`Attribution` to the public surface.

**2. C-012(5)'s literal mechanism is measurably false — CONFIRMED, and worse than reported.**
I applied `assert_descriptor_unique_within_qualname` per member over the real tree. It raises on **11 of 40
members**, not one: `cli/commands/test_sync_commands.py:55`, `test_sync_doctor_consent_health_3030.py:109`,
`test_sync_doctor_per_project_3030.py:99`, `test_sync_doctor_tracker_egress_3108.py:124`,
`test_sync_purge_3030.py:129`, `test_sync_report_label_is_a_purge_selector_3030.py:84`,
`test_sync_status_per_project_3030.py:108`, `sync/test_consent_fault_vocabulary_3030.py:62`,
`sync/test_consent_field_fault_3030.py:82`, `sync/test_consent_write_refusal_3030.py:75`,
`sync/tracker/test_tracker_egress_refusal_3108.py:194`. Cause is as the implementer states —
`code_tokens_by_line` strips string literals, so consecutive `setenv` calls on different keys collapse to one
normalised token line. The substitution (member-level key uniqueness over `discover()`'s own output, raising
`DuplicateMemberKeyError`, `ContentDescriptor` kept as the diagnostic vehicle) **is** the property the contract
actually argues for. **→ contract needs amending** to restate the mechanism at member level.

**3. `NEEDLE_BYTES` with the text derived — SOUND, and self-enforcing.**
Mutating the module back to `NEEDLE = "SPEC_KITTY_HOME"` reds
`test_every_inert_sub_form_has_population_zero_over_the_real_tree[SC-002b]` with
`('architectural/_home_pin_scan.py', 105)`. The guard's own artefact is inside the guard's own population and
the empty-set assertion is a live constraint on this module — not a promise. I found **no equivalent hazard**
in either file: the synthetic sources are string constants (invisible to the AST matchers), `NEEDLE = scan.NEEDLE`
is an `Attribute` not a `Constant`, the 229/98 denominator is unmoved, and all fifteen population-0 assertions
run over a `tests/` tree that includes both new files and return `set()`.

---

## Non-blocking findings

- **[MEDIUM] Baseline-red classification is under-reported.** Apples-to-apples, `tests/architectural` at
  `-n auto --dist loadfile`: **merge-base** = 1 failed / 1850 passed (975s), the failure being
  `test_wp_prompt_build_latency::…implement…` at 6.08s vs a 6.0s budget, with
  `test_ci_quality_path_filters::test_core_misc_shards_plus_e2e_owner_cover_legacy_selection` **passing**.
  **Lane** = 3 failed / 1917 passed (922s): the `ci_quality_path_filters` red **plus** the `implement` budget
  red **plus** a second `…review…` budget red at 7.21s. The named test passes alone on the lane branch
  (221s at `-n0`) and is untouched by this WP, and its failure mode (`_collect_nodes` subprocess wall-clock
  timeout) is documented in that module's own comment as a concurrency artefact — so it is **not a semantic
  regression**. But "resource contention, not theirs" is incomplete: the lane adds ~140s of single-worker
  work and 69 tests to the shard and measurably raises the pressure that produces this failure class.
  Route to the **operator** as a TG-item. Per C-013 no `gh issue create` was run; this is the DIR-013 tension
  the WP's own Risks row anticipates, and the issue is the operator's to open.
- **[LOW] `Member.relpath` is walk-root-relative; `members.json`'s `path` is repo-root-relative.**
  `data-model.md:15` records the semantics normatively ("POSIX, relative to the walk root"), so the
  information exists — but WP05/T023 step 4 does not name the `tests/` prefix at the point of use, and the
  cheapest wrong repair for a symdiff of 40 is to edit the C-011 anchor, which the seam contract forbids.
  Carry the prefix note into WP05's prompt. A one-line note on the `relpath` field would help.
- **[LOW] `_corpus` `lru_cache((root, prefilter))`** holds parsed trees for the session; re-writing the same
  root mid-session yields stale results. No test hits it and no consumer path reaches it (WP02's two
  `git archive` extractions use distinct temp roots). Does not need closing now — a one-line docstring caveat
  would be enough. Note `discover()` does **not** share the cache while `inert_hits()` does.
- **[LOW] `DuplicateMemberKeyError`'s docstring** cites `tests/paths/test_runtime_root_spec_kitty_home.py:91,93`
  as a live counterexample. Verified: those two sites resolve to `tmp_path/"one"` and `tmp_path/"two"`, so
  neither is a member and the member-level check has real-tree population **0**. Site-level non-injectivity is
  real (the contract's own framing); member-level is not. The check has a genuine positive control
  (`_COLLIDING_TREE`), so it is not a vacuous green — the wording just overstates.
- **[INFO] No `record.md`.** WP01 could not write one: `record.md` is WP06's `owned_files` and C-006 confines
  this WP to two files. The three findings are recorded in module docstrings, which is the right substitute.
  **The obligation to carry findings 1–3 and the residuals into WP06/T030 is currently unowned** — route it.
- **[INFO] Zero golden-count headroom.** `tests/architectural` is now at **25 convert sites against a ceiling
  of 25**. This WP contributes **0** (its remaining `len(matches) == 1` classifies `keep`), and the baseline
  JSON is untouched — but WP02–WP05 have no room and must convert on sight.
- **[INFO] Silhouette limb has no real-tree discriminating power.** Removing the `monkeypatch` half, or the
  silhouette check entirely, leaves both real-tree distribution assertions green; only the synthetic M3
  chain-union witness catches it. That matches spec §0.1b's own measurement (the silhouette limb excludes 0
  real sites) and the permanent witness is WP04/T017's. Recorded so it is not rediscovered.
- **[INFO] `__all__` exports 43 names; 17 are never touched by the WP's own tests.** All have internal
  callers, so none is dead — and the seam contract's anti-drift row explicitly asks for a complete surface.
  Noted, not objected to. (`OWNER_PARAM_NAMES` being exported is what makes the WP03 repair possible.)

---

## What I verified, and how

**Everything below was constructed, not read.**

*Gates.* `ruff check` clean. `mypy --strict` clean on both files. 69/69 pass at `-n0` (100s) **and** at
`-n auto --dist loadfile` (140s) — NFR-003 holds for the WP's own suite. pytest **9.0.3** (NFR-006).
`test_golden_count_ban`, `test_ratchet_positional_anchor_ban` and `test_gate_coverage` (the orphan ratchet):
**83 passed**. `_golden_count_baseline.json` **untouched** (`git diff` empty, last commit predates the WP).
No escape hatches (`# golden-count:`, `# diagnostic-locator`) in either file. Zero `except` statements in the
module. No `subprocess`/git surface. `pytestmark = pytest.mark.architectural` at module top level; all 69
tests selected by `-m '(git_repo or integration or architectural) and not timing'`. Three
`# noqa: TID251` on `sha256`, each with an inline justification — squarely inside `pyproject.toml`'s own
carve-out text ("body/file-integrity checksums"), which requires exactly this form. Blast radius: two files.
Terminology canon: no `--feature`/`Feature` in added lines. `time` is not used at all, so the
`perf_counter` gate is N/A here.

*Mutation battery — 12 independent mutations, 11 red.*

| # | Mutation | Result |
|---|---|---|
| A | Attribute at the **innermost** def | 3 red, incl. **both** synthetic and real-tree `kind_distribution` |
| B1 | Rename `SKH-VAL-CONCAT` in **spec.md**'s FR-007 table | quadruple **red** |
| B2 | Add a 15th row to spec.md's table | quadruple **red** |
| B3 | Break the table header so the parser sees nothing | **red** on "the instrument can see" |
| B4 | Parser returns the author's own set | **green** — the mission's acknowledged residual, see below |
| B5 | Drop one id from `INLINE_EXPECTED` only | quadruple **red** |
| D1 | `NEEDLE = "SPEC_KITTY_HOME"` written the obvious way | SC-002b **red** at `_home_pin_scan.py:105` |
| D2 | Empty `_UNFILTERED_IDS` | **5 controls red** — the HOME denominator is mechanised by the controls |
| E1 | Key identity at the **attributed** def | 2 red |
| E2 | `byte_prefilter` → pass-through | red |
| E3 | Collision guard neutered | red (`DID NOT RAISE`) |
| E4 | `_key_set_payload` separator `\t` → `\|` | red — the test **reconstructs** the payload, not just "a hash" |
| E5 | Production stops recognising `CONCAT` | 2 controls red |
| E6/E7 | Silhouette weakened / removed | red on the synthetic M3 witness only (see INFO above) |

B4 is the only survivor and it is unclosable in principle — B1/B2/B3 prove the parser genuinely reads
`spec.md`, which is the property the fourth operand exists to establish.

*The quadruple.* `INLINE_EXPECTED` is enumerated **literally** at `test_home_pin_scan_limbs.py:527-545` and
never imported from the module under test. `CONTROL_IDS = frozenset(_CONTROLS)` is derived from the shipped
controls, so the fourth operand is not written twice. The FR-007 row count is **printed, never asserted**
(line 682); the id column's injectivity **is** asserted (line 679) and the parser's non-emptiness is asserted
before anything is trusted about what it did not find. All **fifteen** ids carry both arms — an empty-set
assertion over the real tree (parametrised, line 719) and a positive control (line 728) that asserts **which**
site the production matcher found via a content-derived `# the-shape` marker, not how many. D2 and E5 prove
the controls bite.

*Red-first honesty (T004/T005).* I cannot audit authoring order — the WP is one squashed commit — so
"recovered red" is unverifiable as evidence. The mutation battery above supersedes it: whatever the order,
T004's quadruple and T005's baseline reconstruction demonstrably fail on mechanism removal, and E4 shows the
baseline test pins the actual payload rather than merely asserting a hash exists.

*Populations.* Not re-derived — the operator had already reproduced 40 members / 36 files, 40 distinct triples
vs 19 bare pairs, A=27/B1=11/B2=2, kind 30/10/0 keyed vs 30/9/1 innermost, symdiff 0 against the C-011 anchor.
I confirmed 40 members incidentally while constructing the C-012(5) probe.

## What I could not check

- Whether the real member set is the *right* one — that anchor is external (C-011) and lands in WP05/T023.
- Authoring order / red-first sequence for any subtask (single squashed commit).
- Whether `contracts/canonical-home-owner.md` will name the owner `canonical_home` — it does not exist.
- Full-repo `pytest tests/` (out of budget); I ran the complete `tests/architectural` shard on both the lane
  and the merge-base under `-n auto --dist loadfile`.
