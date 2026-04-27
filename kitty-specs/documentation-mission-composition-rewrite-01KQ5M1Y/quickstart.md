# Quickstart — Documentation Mission Dogfood Smoke

This is the operator-facing sequence the `mission-review` skill executes to prove SC-001 / SC-006. It is also the documented "drive a real documentation mission" recipe.

**Critical**: use `uv --project <spec-kitty-repo>` — never `uv --directory <spec-kitty-repo>`. `--directory` pollutes the source repo and corrupts JSON output (per #735). The mission-review verdict is downgraded to UNVERIFIED on any `--directory` hit in the smoke evidence.

## Prerequisites

- `uv` installed.
- `python 3.13` available (`uv run --python 3.13 …`).
- `git` installed.
- A clean shell session.
- The `spec-kitty` source tree merged with the #502 changes (this mission's deliverables).

## Smoke command sequence

```bash
# 1. Set absolute paths.
SPEC_KITTY_REPO="/path/to/spec-kitty"   # <-- the merged spec-kitty repo
TMP_REPO="$(mktemp -d -t docs-smoke-XXXXXX)/repo"

# 2. Initialize a fresh temp repo OUTSIDE the spec-kitty source tree (C-010).
mkdir -p "$TMP_REPO"
cd "$TMP_REPO"
git init --initial-branch=main >/dev/null
git config user.email "smoke@test.local"
git config user.name  "Smoke"
echo "# smoke repo" > README.md
git add README.md
git commit -m "init" >/dev/null

# 3. Create a documentation mission via the spec-kitty CLI from the temp repo.
#    Use --project (not --directory) per #735.
uv run --project "$SPEC_KITTY_REPO" \
    spec-kitty agent mission create demo-docs --mission-type documentation --json \
    > create.json

# 4. Inspect the mission_id / mission_slug.
MISSION_HANDLE="$(python3 -c 'import json; print(json.load(open("create.json"))["mission_slug"])')"
echo "mission handle: ${MISSION_HANDLE}"

# 5a. Query mode — read-only probe; no result advances yet.
uv run --project "$SPEC_KITTY_REPO" \
    spec-kitty next --agent claude --mission "${MISSION_HANDLE}" --json \
    > next.json

# 5b. Author spec.md (and the rest of the documentation gate artifacts) so the
#     discover step's post-execution guard chain has no missing-artifact failure.
echo "# spec" > "kitty-specs/${MISSION_HANDLE}/spec.md"

# 5c. Issue the action by reporting --result success. The first call issues the
#     first composed step (discover); a second --result success drives the
#     composition dispatch and writes paired trail records.
uv run --project "$SPEC_KITTY_REPO" \
    spec-kitty next --agent claude --mission "${MISSION_HANDLE}" --result success --json \
    > next-issue.json
uv run --project "$SPEC_KITTY_REPO" \
    spec-kitty next --agent claude --mission "${MISSION_HANDLE}" --result success --json \
    > next-advance.json

# 6. Verify the decision is documentation-native. Tolerates both kind=query
#    (with preview_step) and kind=step (with step_id).
python3 - <<'PY'
import json
d = json.load(open("next.json"))
print("decision_kind:", d.get("kind"))
step = d.get("step_id") or d.get("preview_step")
print("step:", step)
print("mission:", d.get("mission"))
assert d["mission"] == "documentation", f"expected documentation, got {d['mission']}"
assert step in {"discover", "audit", "design", "generate", "validate", "publish"}, \
    f"unexpected step: {step}"
PY

# 7. Inspect the invocation trail. After issuance, the trail dir holds paired
#    started+completed records whose action ∈ {discover, ...}.
ls -la "${TMP_REPO}/.kittify/events/profile-invocations/" | head -10

# 8. Cleanup.
cd /
rm -rf "$(dirname "$TMP_REPO")"
```

Expected outcomes:

- Step 3 prints JSON ending with `"result": "success"` and a documentation `mission_type`.
- Step 5a returns a JSON `Decision` with `kind == "query"`, `mission == "documentation"`, and `preview_step == "discover"` (no action issued yet — query mode is read-only).
- Step 5c's first `--result success` returns `kind == "step"` with `step_id == "discover"`; the second `--result success` advances to `step_id == "audit"` and the composition dispatch writes invocation-trail records.
- Step 7 lists ≥ 1 `*.jsonl` file under `<TMP_REPO>/.kittify/events/profile-invocations/` (NOT under `~/.kittify/`). Each file contains a `started` line paired with a `completed` line whose `outcome` ∈ {`done`, `failed`}, and whose `action` is documentation-native (`discover`, `audit`, ...).
- No `MissionRuntimeError` anywhere.

## What the mission-review skill records

The mission-review skill must include in its evidence section:

1. The exact commands above (verbatim, with the actual `SPEC_KITTY_REPO` substituted).
2. The full stdout of step 3 (`create.json`).
3. The full stdout of step 5 (`next.json`).
4. The output of step 7 (invocation trail listing).
5. A grep proving no `--directory` invocation appears anywhere in the recorded smoke session.

If any of (1)..(5) is missing, the verdict downgrades to UNVERIFIED per NFR-005 / SC-006 / C-008.

## Tolerance for #735 sync noise

If `next.json` contains trailing lines after the JSON payload (e.g. `Not authenticated, skipping sync`), the smoke parser MUST extract only the leading JSON object. The shell snippet above (`python3 -c 'import json; print(json.load(open("create.json"))["mission_slug"])'`) tolerates whole-file JSON; if the CLI ever emits trailing-noise stdout, the smoke command sequence prepends a `head -n -1` filter or uses `python -c "import json,sys; print(json.loads(open('create.json').read().split('\\n')[0])['mission_slug'])"` — but documenting #735 noise as evidence is the responsibility of #735, not #502.
