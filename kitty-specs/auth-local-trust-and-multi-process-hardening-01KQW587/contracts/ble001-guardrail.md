# Contract: Auth/Storage BLE001 Guardrail

## Scope

Guard scoped paths:

- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/auth/`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/auth.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_doctor.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_login.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_logout.py`
- `/Users/robert/spec-kitty-dev/spec-kitty-20260505-085847-6BpmsS/spec-kitty/src/specify_cli/cli/commands/_auth_status.py`

## Passing Suppression

```
except Exception as exc:  # noqa: BLE001 - specific reason that names the safe boundary
```

The reason must explain why the exception is being translated, logged, downgraded, or ignored.

## Failing Suppressions

```
except Exception:  # noqa: BLE001
except Exception:  # noqa: BLE001 - broad catch
except Exception:  # noqa: BLE001 - ignore
```

## Output Contract

On failure, the guard reports:

- File path.
- Line number.
- The problematic suppression text.
- A remediation hint to add a specific safety reason or narrow the exception type.

## Acceptance Fixtures

- One auth/storage sample with a justified suppression passes.
- One auth/storage sample with no reason fails.
- One auth/storage sample with a generic reason fails.
- Unrelated non-auth paths are outside this mission's guard scope unless the existing review command already audits them separately.
