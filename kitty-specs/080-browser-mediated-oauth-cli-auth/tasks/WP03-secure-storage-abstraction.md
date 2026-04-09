---
work_package_id: WP03
title: Secure Storage Abstraction + Multi-Backend Implementation
dependencies: []
requirement_refs:
- FR-017
- FR-018
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T017
- T018
- T019
- T020
- T021
- T022
- T023
- T024
history: []
authoritative_surface: src/specify_cli/auth/secure_storage/
execution_mode: code_change
owned_files:
- src/specify_cli/auth/secure_storage/**
- tests/auth/test_secure_storage.py
status: pending
tags: []
---

# WP03: Secure Storage Abstraction + Multi-Backend Implementation

**Objective**: Build pluggable secure credential storage supporting OS keychains (macOS, Windows, Linux) with file fallback for degraded environments.

**Context**: Foundation for WP04 (TokenManager). Must complete before any token management code.

**Acceptance Criteria**:
- [ ] SecureStorage ABC allows swappable backends
- [ ] Keychain backend works on macOS (using keyring library)
- [ ] Credential Manager backend works on Windows
- [ ] Secret Service backend works on Linux
- [ ] File backend stores JSON with 0600 permissions
- [ ] Auto-detection selects appropriate backend
- [ ] File fallback prompts user ("Secure storage unavailable; save to file?")
- [ ] All tests pass (100% coverage per backend)

---

## Subtask Guidance

### T017: Create SecureStorage ABC

```python
class SecureStorage(ABC):
    @abstractmethod
    async def read(self) -> Optional[StoredSession]:
        """Load session; return None if missing/corrupt."""
    
    @abstractmethod
    async def write(self, session: StoredSession):
        """Save session securely."""
    
    @abstractmethod
    async def delete(self):
        """Delete session from storage."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Backend name (keychain, credential_manager, secret_service, file)."""
```

**Files**: `src/specify_cli/auth/secure_storage/abstract.py` (~50 lines)

---

### T018-T020: Implement OS-Specific Backends

**Keychain (macOS)**:
- Use keyring library: `keyring.get_password(service, account)`
- Service: "spec-kitty-cli", Account: "session"
- JSON encode StoredSession, save as password

**Credential Manager (Windows)**:
- Use ctypes + Windows API (or pywin32)
- Target: spec-kitty-cli/session
- Store JSON-encoded StoredSession

**Secret Service (Linux)**:
- Use secretstorage library
- Collection: "default"
- Label: "spec-kitty-cli session"
- Secret: JSON-encoded StoredSession

**Files**:
- `src/specify_cli/auth/secure_storage/keychain.py` (~60 lines)
- `src/specify_cli/auth/secure_storage/credential_manager.py` (~60 lines)
- `src/specify_cli/auth/secure_storage/secret_service.py` (~60 lines)

---

### T021: Implement File Backend

Save to `~/.config/spec-kitty/credentials.json`:
```python
{
  "version": "1.0",
  "backend": "file",
  "session": { /* StoredSession JSON */ }
}
```

Requirements:
- Create file with 0600 permissions
- Verify permissions on read (fail if not 0600)
- Handle JSON parsing errors gracefully

**Files**: `src/specify_cli/auth/secure_storage/file_fallback.py` (~80 lines)

---

### T022: Create Platform Detector + Factory

```python
def get_default_storage() -> SecureStorage:
    """Auto-detect platform, return appropriate backend."""
    system = platform.system()
    
    if system == "Darwin":
        return SecureStorageKeychain()
    elif system == "Windows":
        return SecureStorageCredentialManager()
    elif system == "Linux":
        return SecureStorageSecretService()
    else:
        # Unknown platform, fall back to file
        return SecureStorageFile()
```

**Files**: `src/specify_cli/auth/secure_storage/factory.py` (~50 lines)

---

### T023: Implement File Fallback Workflow

If primary backend unavailable, prompt user:
```
Secure storage (macOS Keychain) is unavailable.
Would you like to save credentials in a local file?
(file will be protected with 0600 permissions)
> yes/no
```

If user declines: session not persisted, will need re-login on exit.

**Files**: `src/specify_cli/auth/secure_storage/factory.py` (update ~30 lines)

---

### T024: Write Backend Tests

For each backend:
- [ ] write() saves session
- [ ] read() retrieves identical session
- [ ] delete() removes session
- [ ] read() returns None if not exists
- [ ] Serialization round-trip is correct

**Files**: `tests/auth/test_secure_storage.py` (~150 lines)

---

## Definition of Done

- [ ] All backends tested on their respective platforms (or mocked)
- [ ] File backend has correct 0600 permissions
- [ ] Factory auto-detects platform correctly
- [ ] File fallback prompt works
- [ ] No secrets logged or exposed in error messages

