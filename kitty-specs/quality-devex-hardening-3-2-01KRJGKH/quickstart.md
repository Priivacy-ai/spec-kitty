# Quickstart — Quality and DevEx Hardening 3.2

**Mission**: `quality-devex-hardening-3-2-01KRJGKH`
**Branch**: `fix/quality-check-updates`
**Audience**: contributor verifying that the mission's deliverables work.

Each recipe below verifies one Functional Requirement against the running code. Recipes are independent and can run in any order. Run from the repository root checkout.

---

## 1. Mypy strict gate is green (FR-001)

```bash
uv run mypy --strict src/specify_cli src/charter src/doctrine
```

**Expected**: exits 0. The chosen target (option A, decision `DM-01KRJHT7QD7XQMY33Y5TDTQ80V`) is documented in `CHANGELOG.md` and reproduces locally.

If the command shows errors, the gate is not yet green for the WP01 outcome — see `plan.md` Phase 0 §1 for the `re2` strict-drop rationale and WP01 prompt for the typed-code fix list.

---

## 2. Sonar quality gate is OK on `main` (FR-002, FR-003)

Use the snippet committed to this branch — it pulls the live gate via Sonar's public REST API and is reproducible without authentication for public projects:

```bash
bash work/snippets/sonarcloud_branch_review.sh Priivacy-ai_spec-kitty main | head -20
```

**Expected**:

```
=== Quality Gate ===
status: OK

metric                              status   threshold      actual
new_reliability_rating              OK              1            1
new_security_rating                 OK              1            1
new_maintainability_rating          OK              1            1
new_coverage                        OK              80         >=80
...
new_security_hotspots_reviewed      OK             100          100.0
```

If `status: ERROR`, the gate is not yet OK — coverage / hotspot work in WP04–WP07 is incomplete.

---

## 3. Push-time Sonar runs on every push (FR-004)

```bash
gh run list --workflow "CI Quality" --branch main --limit 1 --json conclusion,headSha,event
```

**Expected**: the latest run has `"event": "push"` and `"conclusion": "success"`. Drill into the run:

```bash
gh run view <run_id>
```

The `sonarcloud` step should show `success`, not `skipped`. Before WP07 lands, this step is gated to `schedule || workflow_dispatch` and will appear `skipped` on push runs.

---

## 4. Windows symlink-fallback test runs on every PR (FR-005)

```bash
uv run pytest tests/upgrade/test_m_0_8_0_symlink_windows.py -v
```

**Expected**: both parameterized cases (happy fallback + dual-failure arm) pass on POSIX via the `monkeypatch.setattr(os, "symlink", _raise)` approach documented in WP02.

The test is **not** marked `@pytest.mark.windows_ci` exclusively — that approach restricts execution to Windows runners. Pedro's WP02 prompt instructs using `monkeypatch` so the test runs on every CI pass.

---

## 5. Stale-lane auto-rebase happy path (FR-006)

Set up a two-lane mission with overlapping `pyproject.toml` additions:

```bash
# Setup: two lanes each adding distinct dependencies
spec-kitty agent mission create demo-auto-rebase --friendly-name "Demo Auto-Rebase" \
  --purpose-tldr "Verify auto-rebase classifier" \
  --purpose-context "Smoke test for FR-006" --json | jq -r .mission_slug

# In two lane worktrees, each add a distinct dep to pyproject.toml and commit.
# Merge lane A first (clean).
spec-kitty merge --feature demo-auto-rebase
```

When lane B becomes stale relative to the merged lane A:

**Expected (before this mission lands)**: `spec-kitty merge` fail-stops on lane B with an "overlapping files" error and the actionable manual-merge command.

**Expected (after this mission lands)**: the auto-rebase orchestrator runs `git merge <mission-branch>` in lane B's worktree, classifies the `pyproject.toml` conflict as `R-PYPROJECT-DEPS-UNION`, resolves it, regenerates `uv.lock` under the file lock, and continues the outer merge pipeline. The merge commit message on lane B carries `auto-rebase: 1 conflict resolved by classifier rules [R-PYPROJECT-DEPS-UNION]`.

**Negative case**: introduce a same-package version-specifier conflict (e.g. lane A says `httpx>=0.27`, lane B says `httpx>=0.28`). Expected: classifier falls through to `R-DEFAULT-MANUAL`, orchestrator halts with the original actionable error, no partial auto-resolution remains in the worktree.

---

## 6. No-upgrade notification UX (FR-007)

### Cold cache

```bash
rm -f ~/.cache/spec-kitty/upgrade-check.json
time spec-kitty --version
```

**Expected**: a one-line dim notice appears once. Wall-clock budget is ≤ 300 ms for this cold path. Repeat the command immediately:

```bash
time spec-kitty --version
```

**Expected**: notice is suppressed (identical-channel-within-TTL rule), wall-clock ≤ 100 ms (cache-warm path).

### Off-PyPI build

```bash
# Currently true for this dev install (3.2.0rc7 is not yet on PyPI).
spec-kitty --version
```

**Expected**: the notice reads `spec-kitty-cli 3.2.0rc7 — installed from a non-PyPI build/channel. No PyPI upgrade path is available.`

### Opt-out

```bash
SPEC_KITTY_NO_UPGRADE_CHECK=1 spec-kitty --version
```

**Expected**: no notice, no cache read or write, no probe.

### Probe failure

Block PyPI at the DNS level (e.g. add `127.0.0.1 pypi.org` to `/etc/hosts` temporarily):

```bash
rm -f ~/.cache/spec-kitty/upgrade-check.json
spec-kitty --version
```

**Expected**: no notice. The probe times out at 2 s, falls through to `UNKNOWN`, and the cache records `channel: unknown` with a 1 h TTL. The CLI does not block.

---

## 7. Regex secure-coding regression tests pass (FR-008)

```bash
uv run pytest tests/regressions/test_changelog_regex_redos.py -v --durations=10
```

**Expected**: every test passes, and the slowest test in the output is well under 100 ms wall-clock. Each test feeds an adversarial input (typically 100 000-char run of the ambiguous character + a mismatching tail) and asserts completion within budget.

If a regex change in this mission did not include a wall-clock test, the WP review rejects it (FR-008 + NFR-002).

---

## 8. Canonicalization rule-pipeline behavior preserved (FR-009, FR-011)

```bash
# Characterization tests — captured behavior of _canonicalize_status_row before the refactor.
uv run pytest tests/integration/migration/test_canonicalization_pipeline.py -v

# Per-rule unit tests — added with the refactor.
uv run pytest tests/unit/migration/test_canonicalization_rules.py -v
```

**Expected**: both files pass. The characterization tests use real legacy rows drawn from `.kittify/migrations/mission-state/` fixtures; the per-rule tests are parametrized value-transformer tests.

Verify the refactor preserved behavior:

```bash
git log --oneline -- src/specify_cli/migration/canonicalization.py src/specify_cli/migration/mission_state.py
```

**Expected**: the first commit on `canonicalization.py` is preceded in history by a characterization-test commit that captured `_canonicalize_status_row`'s pre-refactor output (NFR-003).

---

## 9. Code-patterns catalog updated (FR-011 + Success Criterion 7)

```bash
grep -A2 "migration/canonicalization.py" architecture/2.x/04_implementation_mapping/code-patterns.md
```

**Expected**: the rule-pipeline catalog entry cites `src/specify_cli/migration/canonicalization.py` as the canonical Transformer-flavor implementation, alongside the existing pattern description.

---

## 10. Glossary entries land alongside WPs (FR-013)

```bash
yq '.terms[] | select(.surface == "structural debt") | .surface' .kittify/glossaries/spec_kitty_core.yaml
yq '.terms[] | select(.surface == "pipeline-shape") | .surface' .kittify/glossaries/spec_kitty_core.yaml
yq '.terms[] | select(.surface == "characterization test") | .surface' .kittify/glossaries/spec_kitty_core.yaml
yq '.terms[] | select(.surface == "catastrophic backtracking") | .surface' .kittify/glossaries/spec_kitty_core.yaml
```

**Expected**: every canonical term from the spec's Domain Language section is present in the glossary with `status: active`. Reviewers reject WPs whose new canonical term was not landed in the same WP.

---

## 11. Release-stability smoke (NFR-001)

After the mission merges to `main`:

```bash
# In a throwaway directory.
spec-kitty init smoke-test --agent claude
cd smoke-test
spec-kitty agent mission create smoke --friendly-name "Smoke" \
  --purpose-tldr "Verify post-mission release readiness" \
  --purpose-context "NFR-001 smoke run" --json
# Populate spec.md, plan.md, tasks.md per the workflow.
# Walk through: specify → plan → tasks → implement (one trivial WP) → review → merge → PR.
```

**Expected**: the cycle completes without manual state repair, prompt repair, or branch reconstruction. PR opens cleanly on GitHub. If any step requires manual repair, NFR-001 has failed and the mission cannot be marked release-ready.

---

## Acceptance audit

A reviewer running this quickstart end-to-end can answer "is this mission release-ready?" with one of:

- **All 11 recipes pass** → release-ready.
- **Recipes 1, 2, 4–10 pass; recipe 3 (push-time Sonar) is gated to schedule** → mission is **not yet** ready for the gate flip in WP07; this is expected mid-mission.
- **Any other failure pattern** → see the corresponding FR / NFR in `spec.md` and the WP prompt in `tasks/`.
