# Data Model: CLI Authentication Module

This document describes the data entities used by the CLI authentication system.

---

## Overview

The CLI authentication system manages three types of tokens and stores credentials locally in TOML format. The data model is intentionally simple - no database, just file-based storage with appropriate permissions.

---

## Entities

### Entity: CredentialStore

- **Description**: Local file-based storage for authentication tokens
- **Location**: `~/.spec-kitty/credentials`
- **Format**: TOML
- **Permissions**: 600 (owner read/write only)

**Schema**:
```toml
[tokens]
access = "eyJ..."           # JWT access token
refresh = "eyJ..."          # JWT refresh token
access_expires_at = "ISO8601"   # Access token expiry timestamp
refresh_expires_at = "ISO8601"  # Refresh token expiry timestamp

[user]
username = "user@example.com"   # Authenticated user's email/username

[server]
url = "https://spec-kitty-dev.fly.dev"  # Server URL at time of auth
```

**Lifecycle**:
- Created: On successful `auth login`
- Updated: On token refresh
- Deleted: On `auth logout` or credential clear

---

### Entity: AccessToken

- **Description**: Short-lived JWT for API authentication
- **TTL**: 15 minutes
- **Source**: SaaS `/api/v1/token/` or `/api/v1/token/refresh/`

**Attributes**:
| Field | Type | Description |
|-------|------|-------------|
| value | string | JWT token string |
| expires_at | datetime | Expiration timestamp |

**State Transitions**:
```
[Not Exists] --obtain_tokens()--> [Valid]
[Valid] --time passes--> [Expired]
[Expired] --refresh_tokens()--> [Valid]
[Expired] --refresh fails--> [Invalid] --clear()--> [Not Exists]
```

---

### Entity: RefreshToken

- **Description**: Long-lived JWT for obtaining new access tokens
- **TTL**: 7 days
- **Source**: SaaS `/api/v1/token/` or `/api/v1/token/refresh/`
- **Rotation**: New refresh token issued on each use (old one invalidated)

**Attributes**:
| Field | Type | Description |
|-------|------|-------------|
| value | string | JWT token string |
| expires_at | datetime | Expiration timestamp |

**State Transitions**:
```
[Not Exists] --obtain_tokens()--> [Valid]
[Valid] --refresh_tokens()--> [New Valid] (rotated)
[Valid] --time passes (7 days)--> [Expired]
[Expired] --any use--> [Invalid] --clear()--> [Not Exists]
```

---

### Entity: WebSocketToken

- **Description**: Ephemeral token for WebSocket authentication
- **TTL**: 15 minutes
- **Source**: SaaS `/api/v1/ws-token/`
- **Storage**: NOT stored locally (obtained on-demand)

**Attributes**:
| Field | Type | Description |
|-------|------|-------------|
| ws_token | string | UUID token string |
| expires_at | datetime | Expiration timestamp |
| expires_in | integer | Seconds until expiry |

**Lifecycle**:
- Obtained when WebSocket connection is needed
- Used immediately in WebSocket Authorization header
- Discarded after use (not persisted)

---

## Relationships

```
CredentialStore
    ├── AccessToken (1:1, stored)
    ├── RefreshToken (1:1, stored)
    └── User metadata (1:1, stored)

AccessToken
    └── WebSocketToken (1:N, derived on-demand, not stored)
```

---

## Validation Rules

### CredentialStore File

- MUST have 600 permissions on Unix systems
- MUST be valid TOML format
- MUST contain [tokens] section with access and refresh
- SHOULD contain [user] section for status display
- SHOULD contain [server] section for multi-server scenarios

### Token Validity

- Access token is valid if: `current_time < access_expires_at`
- Refresh token is valid if: `current_time < refresh_expires_at`
- Authentication is valid if: access token valid OR refresh token valid

### Auto-Refresh Logic

```python
def get_access_token():
    if access_token_valid():
        return access_token
    elif refresh_token_valid():
        new_tokens = refresh_tokens(refresh_token)
        save_credentials(new_tokens)
        return new_tokens.access
    else:
        raise AuthenticationRequired("Please run 'spec-kitty auth login'")
```

---

## Security Considerations

| Concern | Mitigation |
|---------|------------|
| Token theft | 600 file permissions, tokens never logged |
| Stale tokens | Automatic expiry checking, clear on 401 |
| Race conditions | File locking via `filelock` library |
| Password storage | Never stored - only tokens |
| Token exposure | Never displayed in CLI output |

---

## File Locking Strategy

```python
from filelock import FileLock

CREDENTIALS_PATH = Path.home() / ".spec-kitty" / "credentials"
LOCK_PATH = CREDENTIALS_PATH.with_suffix(".lock")

def save_credentials(tokens):
    with FileLock(LOCK_PATH):
        # Read-modify-write is atomic within lock
        write_toml(CREDENTIALS_PATH, tokens)
        set_permissions(CREDENTIALS_PATH, 0o600)
```

---

## Cross-Platform Notes

| Platform | Permissions | Lock File |
|----------|-------------|-----------|
| macOS | chmod 600 | filelock (flock) |
| Linux | chmod 600 | filelock (flock) |
| Windows | ACL-based | filelock (msvcrt) |

The `filelock` library handles platform differences automatically.

---

**END OF DATA MODEL**
