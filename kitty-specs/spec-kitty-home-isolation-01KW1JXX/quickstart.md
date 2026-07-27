# Quickstart: Verify SPEC_KITTY_HOME State Isolation

Manual verification recipe matching the issue #2171 reproduction. Run against the built CLI
from this branch.

## 1. Isolation holds (the bug, inverted)

```bash
tmp_home="$(mktemp -d)"
tmp_skh="$(mktemp -d)"

HOME="$tmp_home" \
SPEC_KITTY_HOME="$tmp_skh" \
SPEC_KITTY_ENABLE_SAAS_SYNC=1 \
spec-kitty sync server https://example.invalid

echo "--- default home (must be EMPTY of config) ---"
find "$tmp_home" -maxdepth 3 -type f | sort
echo "--- SPEC_KITTY_HOME (must contain config.toml) ---"
find "$tmp_skh" -maxdepth 3 -type f | sort
```

**Expected**: `config.toml` appears under `$SPEC_KITTY_HOME`; `$HOME/.spec-kitty/config.toml`
does **not** exist.

## 2. Backward compatibility (unset = unchanged on POSIX)

```bash
tmp_home="$(mktemp -d)"
HOME="$tmp_home" spec-kitty sync server https://example.invalid
test -f "$tmp_home/.spec-kitty/config.toml" && echo "OK: legacy POSIX layout preserved"
```

## 3. Doctor agrees with runtime

```bash
HOME="$(mktemp -d)" SPEC_KITTY_HOME="$(mktemp -d)" spec-kitty state doctor
# The reported global-sync root must equal $SPEC_KITTY_HOME.
```

## 4. Automated equivalent

```bash
PWHEADLESS=1 .venv/bin/pytest \
  tests/kernel/test_paths.py \
  tests/paths/ \
  tests/audit/test_no_legacy_path_literals.py \
  -q
```

## Acceptance mapping

| Step | Spec criterion |
|------|----------------|
| 1 | SC-001, SC-002, FR-001 |
| 2 | SC-003, NFR-001 |
| 3 | SC-004, FR-009 |
| 4 | FR-010..FR-012, NFR-001/003 |
