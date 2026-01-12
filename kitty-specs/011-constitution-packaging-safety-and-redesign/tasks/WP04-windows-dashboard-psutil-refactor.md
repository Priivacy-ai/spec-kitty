---
work_package_id: "WP04"
subtasks:
  - "T022"
  - "T023"
  - "T024"
  - "T025"
  - "T026"
  - "T027"
title: "Windows Dashboard psutil Refactor"
phase: "Feature - Track 2 UX Improvements"
lane: "doing"
assignee: ""
agent: ""
shell_pid: ""
review_status: ""
reviewed_by: ""
history:
  - timestamp: "2026-01-12T11:30:00Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP04 – Windows Dashboard psutil Refactor

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review. If you see feedback here, treat each item as a must-do before completion.]*

---

## Objectives & Success Criteria

**Goal**: Replace POSIX-only signal handling with cross-platform psutil library to fix Windows dashboard ERR_EMPTY_RESPONSE issue (#71).

**Success Criteria**:
1. `psutil>=5.9.0` added to `pyproject.toml` dependencies
2. All `os.kill(pid, 0)` replaced with `psutil.Process(pid).is_running()`
3. All `signal.SIGKILL` usage replaced with `psutil.Process(pid).kill()` (6 locations)
4. All `signal.SIGTERM` usage replaced with `psutil.Process(pid).terminate()` (1 location)
5. Proper exception handling for `psutil.NoSuchProcess`, `psutil.TimeoutExpired`, `psutil.AccessDenied`
6. Imports updated (remove `signal`, add `psutil`)
7. Dashboard starts successfully on Windows 10/11
8. Dashboard serves HTML content (not empty response) on Windows
9. Process termination works gracefully on all platforms (Linux, macOS, Windows)

**Acceptance Test**:
```bash
# On Windows 10/11
spec-kitty dashboard

# Should output:
# Dashboard starting on http://127.0.0.1:9237
# Dashboard ready!

# Access in browser
curl http://127.0.0.1:9237

# Should return HTML content (not empty)
# Content-Length > 0

# Shutdown
spec-kitty dashboard --stop

# Should cleanly terminate process
```

---

## Context & Constraints

**Why This Matters**: Windows users currently experience ERR_EMPTY_RESPONSE when accessing the dashboard. Root cause: POSIX-only signal handling (`signal.SIGKILL`, `signal.SIGTERM`) doesn't work on Windows.

**Problem Details**:
- `signal.SIGKILL` doesn't exist on Windows → AttributeError
- `os.kill(pid, signal.SIGKILL)` crashes on Windows
- Dashboard process may start but signal handling fails
- HTTP server may not fully initialize due to signal errors

**Solution**: Use `psutil` library which abstracts platform differences:
- `psutil.Process(pid).is_running()` works on all platforms
- `psutil.Process(pid).terminate()` = SIGTERM on POSIX, TerminateProcess on Windows
- `psutil.Process(pid).kill()` = SIGKILL on POSIX, force terminate on Windows
- `proc.wait(timeout=N)` prevents hanging on unresponsive processes

**Related Documents**:
- Spec: `kitty-specs/011-constitution-packaging-safety-and-redesign/spec.md` (FR-017 through FR-020, User Story 3, Issue #71)
- Plan: `kitty-specs/011-constitution-packaging-safety-and-redesign/plan.md` (Track 2 UX Improvements)
- Research: `kitty-specs/011-constitution-packaging-safety-and-redesign/research.md` (Research Area 2: psutil Cross-Platform Process Management)
- Data Model: `kitty-specs/011-constitution-packaging-safety-and-redesign/data-model.md` (Entity 4: Process Management)

**Dependencies**: None (can run in parallel with WP01-WP03)

**Platforms to Support**:
- Linux (Ubuntu 20.04+, Debian, Fedora, etc.)
- macOS (10.15+, 11.0+, 12.0+)
- Windows (Windows 10, Windows 11, Windows Server 2019+)

---

## Subtasks & Detailed Guidance

### Subtask T022 – Add psutil>=5.9.0 to pyproject.toml dependencies

**Purpose**: Add psutil library as a project dependency.

**File**: `pyproject.toml`

**Current Dependencies** (around line 8-17):
```toml
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "ruamel.yaml>=0.17.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
]
```

**Add psutil**:
```toml
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
    "ruamel.yaml>=0.17.0",
    "httpx>=0.24.0",
    "pydantic>=2.0.0",
    "psutil>=5.9.0",  # Cross-platform process management
]
```

**Steps**:
1. Read `pyproject.toml`
2. Locate `dependencies` list (around line 8-17)
3. Add `"psutil>=5.9.0",` with inline comment explaining purpose
4. Maintain alphabetical order if dependencies are sorted
5. Verify TOML syntax correct (trailing comma OK)

**Version Selection Rationale**:
- **5.9.0**: Released 2022-01, stable, widely tested
- **Lower bound**: Ensures minimum feature set available
- **No upper bound**: Allow users to get bug fixes and improvements
- **Why not newer**: 5.9.0+ has all features we need, older versions may have Windows bugs

**Verification**:
```bash
# After adding dependency
pip install -e .

# Verify psutil importable
python3 -c "import psutil; print(psutil.__version__)"
# Expected: 5.9.0 or newer

# Verify platform support
python3 << EOF
import psutil
import platform
print(f"Platform: {platform.system()}")
print(f"psutil version: {psutil.__version__}")
print(f"Process class available: {hasattr(psutil, 'Process')}")
EOF
```

**Conflict Check**:
- Note: WP01 also modifies `pyproject.toml` (removes force-includes)
- This subtask adds dependency (different section)
- No conflict: dependency section vs. build section

**Documentation Note**:
```python
# Add to pyproject.toml comment or module docstring
"""
psutil is used for cross-platform process management in the dashboard
lifecycle module. Replaces POSIX-only signal handling (signal.SIGKILL,
signal.SIGTERM) which doesn't work on Windows.
"""
```

---

### Subtask T023 – Replace os.kill(pid, 0) with psutil.Process(pid).is_running()

**Purpose**: Replace POSIX-only process existence check with cross-platform alternative.

**File**: `src/specify_cli/dashboard/lifecycle.py`

**Current Code** (around line 94-102):
```python
def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive.

    Uses signal.SIGZERO to check existence without actually sending a signal.
    """
    try:
        os.kill(pid, 0)  # 0 doesn't kill, just checks if process exists
        return True
    except ProcessLookupError:
        return False
```

**Issue**: `os.kill(pid, 0)` is POSIX-only. Windows doesn't support signal 0.

**New Code**:
```python
def _is_process_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive.

    Uses psutil.Process() which works across all platforms (Linux, macOS, Windows).
    This replaces the POSIX-only os.kill(pid, 0) approach.

    Args:
        pid: Process ID to check

    Returns:
        True if process exists and is running, False otherwise
    """
    try:
        proc = psutil.Process(pid)
        return proc.is_running()
    except psutil.NoSuchProcess:
        # Process doesn't exist
        return False
    except psutil.AccessDenied:
        # Process exists but we don't have permission to access it
        # Consider this as "alive" since process exists
        return True
    except Exception:
        # Unexpected error, assume process dead
        return False
```

**Key Changes**:
1. Import `psutil` instead of using `os.kill`
2. Create `psutil.Process(pid)` object
3. Call `proc.is_running()` for status check
4. Handle `psutil.NoSuchProcess` (equivalent to `ProcessLookupError`)
5. Handle `psutil.AccessDenied` (process exists but no permission)
6. Add generic exception handler for safety

**Exception Handling Details**:

**`psutil.NoSuchProcess`**:
- Raised when process doesn't exist
- Equivalent to POSIX `ProcessLookupError`
- Return `False` (process dead)

**`psutil.AccessDenied`**:
- Raised when process exists but no permission to access
- Common on Windows for system processes
- Return `True` (process exists, even if we can't fully access it)

**Generic `Exception`**:
- Catch-all for unexpected errors
- Prevents function from crashing
- Conservative: assume process dead if unsure

**Platform Differences**:
```python
# POSIX (Linux/macOS):
os.kill(pid, 0)  # Checks if process exists
# Raises ProcessLookupError if not found

# Windows:
os.kill(pid, signal.SIGTERM)  # Only supported signal
# signal.SIGKILL doesn't exist on Windows

# psutil (All platforms):
proc = psutil.Process(pid)
proc.is_running()  # Works identically on Linux, macOS, Windows
```

**Testing**:
```python
# Test 1: Process exists
pid = os.getpid()  # Current process
assert _is_process_alive(pid) == True

# Test 2: Process doesn't exist
assert _is_process_alive(999999) == False

# Test 3: Zombie process (POSIX only)
# Create zombie process, verify is_running() returns False
# (psutil detects zombie state correctly)

# Test 4: System process (Windows)
# Try checking system process PID
# Should return True even with AccessDenied
```

**Performance Note**:
- `psutil.Process(pid)` creation is fast (<0.1ms)
- `is_running()` check is fast (<0.1ms)
- No performance regression vs. `os.kill(pid, 0)`

---

### Subtask T024 – Replace signal.SIGKILL with psutil.Process(pid).kill()

**Purpose**: Replace POSIX-only force kill with cross-platform alternative.

**File**: `src/specify_cli/dashboard/lifecycle.py`

**Locations to Replace** (6 total):
1. Line 188: `os.kill(pid, signal.SIGKILL)` in `_kill_orphaned_processes()`
2. Line 289: `os.kill(pid, signal.SIGKILL)` in `start_dashboard()`
3. Line 354: `os.kill(pid, signal.SIGKILL)` in `start_dashboard()`
4. Line 381: `os.kill(pid, signal.SIGKILL)` in `start_dashboard()`
5. Line 470: `os.kill(pid, signal.SIGKILL)` in `stop_dashboard()`
6. Line 499: `os.kill(pid, signal.SIGKILL)` in `stop_dashboard()`

**Pattern for Each Replacement**:

**Before**:
```python
try:
    os.kill(pid, signal.SIGKILL)
    killed_count += 1
except (ProcessLookupError, PermissionError):
    pass
```

**After**:
```python
try:
    proc = psutil.Process(pid)
    proc.kill()  # Force terminate (SIGKILL on POSIX, force kill on Windows)
    killed_count += 1
except psutil.NoSuchProcess:
    # Process already dead
    pass
except psutil.AccessDenied:
    # Can't kill process (insufficient permissions)
    pass
except Exception as e:
    # Log unexpected errors but don't crash
    import logging
    logging.warning(f"Failed to kill process {pid}: {e}")
```

**Detailed Replacement for Each Location**:

**Location 1: Line 188 (_kill_orphaned_processes)**:
```python
# Context: Killing orphaned dashboard processes
for pid in pids:
    try:
        proc = psutil.Process(pid)
        proc.kill()
        killed_count += 1
    except psutil.NoSuchProcess:
        pass  # Already dead
    except psutil.AccessDenied:
        pass  # Can't kill (permissions)
```

**Location 2: Line 289 (start_dashboard - orphan cleanup)**:
```python
# Context: PID alive but port not responding - kill the orphan
elif existing_pid is not None and existing_port is not None:
    try:
        proc = psutil.Process(existing_pid)
        proc.kill()
        dashboard_file.unlink(missing_ok=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        dashboard_file.unlink(missing_ok=True)
```

**Location 3: Line 354 (start_dashboard - cleanup failed start)**:
```python
# Context: Clean up the failed process we just started
if pid is not None:
    try:
        proc = psutil.Process(pid)
        proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
```

**Location 4: Line 381 (start_dashboard - cleanup after timeout)**:
```python
# Context: Still failed - clean up and raise error
if pid is not None:
    try:
        proc = psutil.Process(pid)
        proc.kill()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
```

**Location 5: Line 470 (stop_dashboard - force kill after SIGTERM)**:
```python
# Context: Still alive after SIGTERM, force kill
if _is_process_alive(pid):
    try:
        proc = psutil.Process(pid)
        proc.kill()
        time.sleep(0.2)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
```

**Location 6: Line 499 (stop_dashboard - timeout, last resort)**:
```python
# Context: Timeout - try killing by PID as last resort
if pid is not None:
    try:
        proc = psutil.Process(pid)
        proc.kill()
        dashboard_file.unlink(missing_ok=True)
        return True, f"Dashboard forced stopped (force kill, PID {pid}) after {timeout}s timeout."
    except Exception:
        pass
```

**Exception Handling Strategy**:
- **NoSuchProcess**: Process already dead (common race condition)
- **AccessDenied**: Insufficient permissions (common on Windows for certain processes)
- **Generic Exception**: Catch-all at cleanup sites (locations 4, 6) to prevent crash

**Verification After Changes**:
```bash
# Grep to verify all signal.SIGKILL removed
grep -n "signal.SIGKILL" src/specify_cli/dashboard/lifecycle.py
# Expected: Empty output (exit code 1)

# Grep to verify psutil.Process().kill() added
grep -n "\.kill()" src/specify_cli/dashboard/lifecycle.py
# Expected: 6 matches (lines updated)
```

**Testing Each Location**:
```python
# Test 1: Normal kill (location 1, 2, 3, 4, 5, 6)
pid = start_test_process()
proc = psutil.Process(pid)
proc.kill()
time.sleep(0.1)
assert not proc.is_running()

# Test 2: Process already dead (NoSuchProcess)
# Should not raise, should be silent
proc = psutil.Process(pid)  # From above, already dead
try:
    proc.kill()
except psutil.NoSuchProcess:
    pass  # Expected

# Test 3: Permission denied (Windows system process)
# Should not crash, should log warning
```

**Platform-Specific Behavior**:
- **Linux/macOS**: `proc.kill()` sends SIGKILL (signal 9)
- **Windows**: `proc.kill()` calls `TerminateProcess()` with exit code 1
- Both are **immediate** and **forceful** (cannot be caught by process)

---

### Subtask T025 – Replace signal.SIGTERM with psutil.Process(pid).terminate()

**Purpose**: Replace POSIX graceful shutdown signal with cross-platform alternative.

**File**: `src/specify_cli/dashboard/lifecycle.py`

**Location**: Line 464 in `stop_dashboard()` function

**Current Code** (lines 461-472):
```python
# If HTTP shutdown failed but we have a PID, try killing the process
if not ok and pid is not None:
    try:
        os.kill(pid, signal.SIGTERM)  # Try graceful termination first
        time.sleep(0.5)

        # Check if process died
        if _is_process_alive(pid):
            # Still alive, force kill
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.2)

        dashboard_file.unlink(missing_ok=True)
```

**New Code**:
```python
# If HTTP shutdown failed but we have a PID, try killing the process
if not ok and pid is not None:
    try:
        proc = psutil.Process(pid)

        # Try graceful termination first (SIGTERM on POSIX, equivalent on Windows)
        proc.terminate()

        # Wait up to 3 seconds for graceful shutdown
        try:
            proc.wait(timeout=3.0)
            # Process exited gracefully
        except psutil.TimeoutExpired:
            # Still alive after timeout, force kill
            proc.kill()
            time.sleep(0.2)

        dashboard_file.unlink(missing_ok=True)
```

**Key Changes**:
1. Create `psutil.Process(pid)` once, reuse for both terminate and kill
2. Use `proc.terminate()` instead of `os.kill(pid, signal.SIGTERM)`
3. Use `proc.wait(timeout=3.0)` instead of `time.sleep(0.5) + is_alive check`
4. Use `proc.kill()` instead of `os.kill(pid, signal.SIGKILL)` (already covered in T024)
5. Proper exception handling for `NoSuchProcess`, `AccessDenied`, `TimeoutExpired`

**Enhanced Version with Full Exception Handling**:
```python
# If HTTP shutdown failed but we have a PID, try killing the process
if not ok and pid is not None:
    try:
        proc = psutil.Process(pid)

        # Try graceful termination first
        proc.terminate()

        # Wait for graceful shutdown
        try:
            proc.wait(timeout=3.0)
            # Process exited gracefully
            ok = True
            message = f"Dashboard stopped via process termination (PID {pid})"
        except psutil.TimeoutExpired:
            # Timeout expired, process still running, force kill
            proc.kill()
            time.sleep(0.2)
            ok = True
            message = f"Dashboard force killed after graceful termination timeout (PID {pid})"

        dashboard_file.unlink(missing_ok=True)

    except psutil.NoSuchProcess:
        # Process already dead (common race condition)
        dashboard_file.unlink(missing_ok=True)
        ok = True
        message = f"Dashboard process already terminated (PID {pid})"

    except psutil.AccessDenied:
        # Can't access process (permissions issue)
        ok = False
        message = f"Cannot terminate dashboard process (PID {pid}): Access denied"

    except Exception as e:
        # Unexpected error
        ok = False
        message = f"Failed to terminate dashboard process (PID {pid}): {e}"
```

**Benefits of proc.wait(timeout=N)**:
1. **Blocks until process exits** or timeout reached
2. **Avoids race conditions** (no sleep + check pattern)
3. **Returns immediately** when process exits (no waiting full timeout)
4. **Cross-platform**: Works identically on Linux, macOS, Windows

**Comparison: Old vs New Approach**:

**Old (POSIX-only)**:
```python
os.kill(pid, signal.SIGTERM)  # Send signal
time.sleep(0.5)                # Wait fixed time
if _is_process_alive(pid):     # Check if still alive
    os.kill(pid, signal.SIGKILL)  # Force kill
```
Problems:
- `signal.SIGTERM` doesn't exist on Windows
- Fixed 0.5s sleep may be too short or too long
- Race condition between check and kill

**New (Cross-platform)**:
```python
proc.terminate()              # Graceful termination
try:
    proc.wait(timeout=3.0)    # Wait up to 3s, return early if exits
except psutil.TimeoutExpired:
    proc.kill()               # Force kill only if timeout
```
Benefits:
- Works on Windows, Linux, macOS
- Dynamic wait (returns early if process exits quickly)
- No race condition (wait() is atomic)
- Longer timeout (3s vs 0.5s) gives process more time to clean up

**Verification**:
```bash
# Grep to verify signal.SIGTERM removed
grep -n "signal.SIGTERM" src/specify_cli/dashboard/lifecycle.py
# Expected: Empty output

# Grep to verify proc.terminate() added
grep -n "\.terminate()" src/specify_cli/dashboard/lifecycle.py
# Expected: 1 match (line ~464)

# Grep to verify proc.wait() added
grep -n "\.wait(timeout=" src/specify_cli/dashboard/lifecycle.py
# Expected: 1 match (same location)
```

**Testing**:
```python
# Test 1: Graceful shutdown
pid = start_dashboard_process()
proc = psutil.Process(pid)
proc.terminate()
try:
    proc.wait(timeout=3.0)
    print("✓ Process exited gracefully")
except psutil.TimeoutExpired:
    print("✗ Process didn't exit gracefully")
    proc.kill()

# Test 2: Timeout scenario (process ignores SIGTERM)
# Start process that catches SIGTERM and doesn't exit
pid = start_stubborn_process()
proc = psutil.Process(pid)
proc.terminate()
try:
    proc.wait(timeout=1.0)
    print("✗ Process shouldn't have exited")
except psutil.TimeoutExpired:
    print("✓ Timeout expired as expected")
    proc.kill()  # Force kill
    proc.wait(timeout=1.0)  # Should exit immediately
    print("✓ Force kill succeeded")
```

**Platform Behavior**:
- **Linux/macOS**: `proc.terminate()` sends SIGTERM (signal 15), catchable by process
- **Windows**: `proc.terminate()` calls `TerminateProcess()` with exit code 0 (immediate)
- **Note**: On Windows, terminate() and kill() are equivalent (both immediate)

---

### Subtask T026 – Add proper exception handling for psutil exceptions

**Purpose**: Ensure all psutil calls have proper exception handling for NoSuchProcess, TimeoutExpired, AccessDenied.

**File**: `src/specify_cli/dashboard/lifecycle.py`

**psutil Exception Types**:
```python
psutil.NoSuchProcess       # Process doesn't exist (like ProcessLookupError)
psutil.TimeoutExpired      # proc.wait(timeout=N) timed out
psutil.AccessDenied        # Insufficient permissions to access process
psutil.ZombieProcess       # Process is zombie (POSIX only)
```

**Common Patterns**:

**Pattern 1: Process existence check (already handled in T023)**:
```python
try:
    proc = psutil.Process(pid)
    return proc.is_running()
except psutil.NoSuchProcess:
    return False
except psutil.AccessDenied:
    return True  # Exists but no permission
```

**Pattern 2: Kill with cleanup**:
```python
try:
    proc = psutil.Process(pid)
    proc.kill()
    # Cleanup code...
except psutil.NoSuchProcess:
    # Already dead, proceed with cleanup
    pass
except psutil.AccessDenied:
    # Can't kill, log warning
    logging.warning(f"Cannot kill process {pid}: Access denied")
```

**Pattern 3: Terminate with timeout**:
```python
try:
    proc = psutil.Process(pid)
    proc.terminate()
    try:
        proc.wait(timeout=3.0)
    except psutil.TimeoutExpired:
        proc.kill()  # Force kill after timeout
except psutil.NoSuchProcess:
    pass  # Already dead
except psutil.AccessDenied:
    pass  # Can't terminate
```

**Audit All psutil Usage**:

**Step 1: Find all psutil.Process() creations**:
```bash
grep -n "psutil.Process(" src/specify_cli/dashboard/lifecycle.py
```

**Step 2: For each usage, verify exception handling**:
- Check if `try/except` block present
- Verify `NoSuchProcess` handled
- Verify `AccessDenied` handled (if killing/terminating)
- Verify `TimeoutExpired` handled (if using wait())

**Step 3: Add missing exception handlers**:

**Example: Line 188 (_kill_orphaned_processes)**:
```python
# Before (from T024)
try:
    proc = psutil.Process(pid)
    proc.kill()
    killed_count += 1
except psutil.NoSuchProcess:
    pass

# After (add AccessDenied)
try:
    proc = psutil.Process(pid)
    proc.kill()
    killed_count += 1
except psutil.NoSuchProcess:
    pass
except psutil.AccessDenied:
    # Can't kill process (system process or different user)
    # Log but don't crash
    pass
```

**Example: Lines 464-472 (stop_dashboard - graceful termination)**:
```python
# After T025, ensure full exception handling
try:
    proc = psutil.Process(pid)
    proc.terminate()

    try:
        proc.wait(timeout=3.0)
        ok = True
    except psutil.TimeoutExpired:
        # Timeout - force kill
        try:
            proc.kill()
            ok = True
        except psutil.NoSuchProcess:
            # Died between wait timeout and kill - that's OK
            ok = True
        except psutil.AccessDenied:
            # Can't force kill
            ok = False

except psutil.NoSuchProcess:
    # Process already dead before we tried to terminate
    ok = True

except psutil.AccessDenied:
    # Can't access process
    ok = False

except Exception as e:
    # Unexpected error
    ok = False
    import logging
    logging.error(f"Unexpected error stopping dashboard: {e}")
```

**Step 4: Add logging for unexpected errors**:
```python
import logging

logger = logging.getLogger(__name__)

# In exception handlers
except Exception as e:
    logger.warning(f"Unexpected error in process management: {e}")
    # Continue with fallback behavior
```

**Verification Checklist**:
- [ ] All `psutil.Process()` calls in try/except
- [ ] All `proc.kill()` calls handle NoSuchProcess and AccessDenied
- [ ] All `proc.terminate()` calls handle NoSuchProcess and AccessDenied
- [ ] All `proc.wait()` calls handle TimeoutExpired
- [ ] All `proc.is_running()` calls handle NoSuchProcess
- [ ] Generic `Exception` handlers present for critical sections
- [ ] Logging added for unexpected errors

**Testing Exception Scenarios**:
```python
# Test NoSuchProcess
try:
    proc = psutil.Process(999999)  # Non-existent PID
    proc.kill()
except psutil.NoSuchProcess:
    print("✓ NoSuchProcess handled")

# Test AccessDenied (platform-specific)
# On Windows, try killing system process
# On Linux, try killing root process as non-root user

# Test TimeoutExpired
proc = psutil.Process(os.getpid())  # Current process
proc.terminate()
try:
    proc.wait(timeout=0.001)  # Very short timeout
except psutil.TimeoutExpired:
    print("✓ TimeoutExpired handled")
```

---

### Subtask T027 – Update imports (remove signal, add psutil)

**Purpose**: Clean up imports after refactoring to psutil.

**File**: `src/specify_cli/dashboard/lifecycle.py`

**Current Imports** (lines 1-15, approximately):
```python
"""Dashboard lifecycle management."""

import json
import os
import signal  # REMOVE - no longer needed
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx
from rich.console import Console

# MISSING: psutil - ADD THIS
```

**New Imports**:
```python
"""Dashboard lifecycle management.

This module handles starting, stopping, and monitoring the dashboard server.
Uses psutil for cross-platform process management (Windows, Linux, macOS).
"""

import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

import httpx
import psutil  # Cross-platform process management
from rich.console import Console

logger = logging.getLogger(__name__)
```

**Changes**:
1. **Remove**: `import signal` (line ~6)
2. **Add**: `import psutil` (add after stdlib imports, before third-party)
3. **Add**: `import logging` (for error logging)
4. **Add**: `logger = logging.getLogger(__name__)` (module-level logger)
5. **Update**: Module docstring to mention psutil and cross-platform support

**Import Organization** (PEP 8):
```python
# 1. Standard library imports
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Optional, Tuple

# 2. Third-party imports
import httpx
import psutil
from rich.console import Console

# 3. Local imports (if any)
# from ..core import something
```

**Verification**:
```bash
# 1. Verify signal import removed
grep -n "^import signal" src/specify_cli/dashboard/lifecycle.py
grep -n "^from signal import" src/specify_cli/dashboard/lifecycle.py
# Expected: Empty output

# 2. Verify psutil import added
grep -n "^import psutil" src/specify_cli/dashboard/lifecycle.py
# Expected: One match (psutil import line)

# 3. Verify no signal usage remains
grep -n "signal\." src/specify_cli/dashboard/lifecycle.py
# Expected: Empty output (all signal.SIGKILL, signal.SIGTERM removed)

# 4. Verify imports can be loaded
python3 -c "from specify_cli.dashboard import lifecycle; print('✓ Imports OK')"
```

**Update Module Docstring**:
```python
"""Dashboard lifecycle management.

This module provides functions to start, stop, and monitor the spec-kitty
dashboard server. The dashboard runs as a background HTTP server and displays
a web-based kanban board for tracking work package progress.

Cross-Platform Support:
    This module uses psutil for process management, ensuring compatibility
    across Linux, macOS, and Windows. The previous implementation used POSIX-only
    signal handling (signal.SIGKILL, signal.SIGTERM) which didn't work on Windows.

Key Functions:
    - start_dashboard(): Start dashboard server in background
    - stop_dashboard(): Stop running dashboard server
    - get_dashboard_status(): Check if dashboard is running
    - _is_process_alive(): Check if process exists (cross-platform)

Dashboard Metadata:
    Dashboard state is tracked in .kittify/.dashboard file containing:
    - pid: Process ID of running dashboard
    - port: HTTP port (default 9237)
    - started_at: Timestamp when dashboard started
    - version: spec-kitty version that started dashboard
"""
```

**Linting Check**:
```bash
# Run ruff or flake8 to verify import ordering
ruff check src/specify_cli/dashboard/lifecycle.py

# Run isort to verify/fix import order
isort --check-only src/specify_cli/dashboard/lifecycle.py

# If issues found, fix with isort
isort src/specify_cli/dashboard/lifecycle.py
```

**Backwards Compatibility Check**:
- This is internal module, not public API
- No external code should import signal from this module
- Change is internal refactoring, transparent to users

**Final Verification**:
```python
# Test that all dashboard functions work with new imports
from specify_cli.dashboard.lifecycle import (
    start_dashboard,
    stop_dashboard,
    get_dashboard_status,
)

# Should not raise ImportError
print("✓ All imports successful")

# Verify psutil available
import psutil
print(f"✓ psutil version: {psutil.__version__}")
```

---

## Test Strategy

**Unit Tests**:
```python
# tests/test_dashboard_lifecycle.py

import psutil
import pytest
from specify_cli.dashboard.lifecycle import (
    _is_process_alive,
    start_dashboard,
    stop_dashboard,
)

def test_is_process_alive_current_process():
    """Test that current process is detected as alive."""
    import os
    pid = os.getpid()
    assert _is_process_alive(pid) == True

def test_is_process_alive_nonexistent():
    """Test that non-existent process is detected as dead."""
    assert _is_process_alive(999999) == False

def test_process_kill_cross_platform():
    """Test that kill() works on current platform."""
    import subprocess
    import time

    # Start sleep process
    proc = subprocess.Popen(["sleep", "10"])
    pid = proc.pid

    # Kill with psutil
    ps_proc = psutil.Process(pid)
    ps_proc.kill()

    # Wait and verify dead
    time.sleep(0.1)
    assert not _is_process_alive(pid)

def test_process_terminate_with_timeout():
    """Test graceful termination with timeout."""
    import subprocess

    # Start sleep process
    proc = subprocess.Popen(["sleep", "10"])
    pid = proc.pid

    # Terminate gracefully
    ps_proc = psutil.Process(pid)
    ps_proc.terminate()

    try:
        ps_proc.wait(timeout=3.0)
        terminated_gracefully = True
    except psutil.TimeoutExpired:
        ps_proc.kill()
        terminated_gracefully = False

    assert terminated_gracefully  # Sleep should exit immediately on SIGTERM
```

**Integration Tests** (defer to WP06):
- Start dashboard on Windows 10/11
- Access dashboard URL, verify HTML response
- Stop dashboard, verify clean shutdown
- Test orphan cleanup (kill process externally, start new dashboard)

**Manual Testing Checklist**:

**On Linux**:
```bash
# Start dashboard
spec-kitty dashboard

# Verify process alive
ps aux | grep dashboard

# Access dashboard
curl http://127.0.0.1:9237 | head -n 20

# Stop dashboard
spec-kitty dashboard --stop

# Verify process dead
ps aux | grep dashboard  # Should be empty
```

**On macOS**:
```bash
# Same as Linux
# Verify no errors related to signal handling
```

**On Windows 10/11**:
```bash
# Start dashboard (PowerShell)
spec-kitty dashboard

# Verify process alive
Get-Process | Where-Object {$_.ProcessName -like "*dashboard*"}

# Access dashboard (PowerShell)
Invoke-WebRequest -Uri http://127.0.0.1:9237

# Stop dashboard
spec-kitty dashboard --stop

# Verify process dead
Get-Process | Where-Object {$_.ProcessName -like "*dashboard*"}  # Should be empty
```

---

## Risks & Mitigations

| Risk | Impact | Mitigation | Covered By |
|------|--------|------------|------------|
| psutil behaves differently on Windows | High | Extensive testing on Windows 10/11 | WP06 integration tests |
| Process termination timing differs | Medium | Use proc.wait() with timeout, not fixed sleep | T025 |
| AccessDenied on system processes | Low | Catch AccessDenied exception, log warning | T026 |
| Breaking existing dashboards | Low | Old dashboards killed by PID, no signal dependency | T024 |
| Import errors if psutil not installed | High | Add psutil to dependencies before refactoring | T022 (do first) |

---

## Definition of Done Checklist

- [ ] All subtasks T022-T027 completed
- [ ] psutil>=5.9.0 added to pyproject.toml
- [ ] All os.kill(pid, 0) replaced with psutil.Process(pid).is_running()
- [ ] All signal.SIGKILL replaced with psutil.Process(pid).kill()
- [ ] All signal.SIGTERM replaced with psutil.Process(pid).terminate()
- [ ] All psutil exceptions properly handled
- [ ] signal import removed, psutil import added
- [ ] No grep matches for "signal.SIG" in lifecycle.py
- [ ] Unit tests pass on Linux/macOS
- [ ] Dashboard starts on Windows (verified in WP06)
- [ ] Dashboard serves HTML on Windows (verified in WP06)
- [ ] Git commit created with clear explanation
- [ ] Code review requested from maintainer

---

## Review Guidance

**Key Acceptance Checkpoints**:
1. **Dependency added**: psutil in pyproject.toml dependencies
2. **Signal usage removed**: No signal.SIGKILL or signal.SIGTERM references
3. **psutil usage added**: All process operations use psutil
4. **Exception handling**: All psutil calls have proper try/except
5. **Imports clean**: signal removed, psutil added, organized per PEP 8

**Red Flags for Reviewer**:
- Any remaining `signal.SIG*` references
- Missing exception handling for psutil calls
- Still using `os.kill()` for kill/terminate operations
- Hardcoded sleep instead of `proc.wait(timeout=N)`

**Testing Checklist for Reviewer**:
```bash
# 1. Verify signal usage gone
grep -rn "signal\.SIG" src/specify_cli/dashboard/

# 2. Verify psutil usage present
grep -rn "psutil\.Process" src/specify_cli/dashboard/

# 3. Run unit tests
pytest tests/test_dashboard_lifecycle.py -v

# 4. Test on current platform
spec-kitty dashboard
curl http://127.0.0.1:9237
spec-kitty dashboard --stop

# 5. Verify no signal import
grep "^import signal" src/specify_cli/dashboard/lifecycle.py
# Expected: Empty
```

**Context for Reviewer**:
- This fixes Windows dashboard ERR_EMPTY_RESPONSE issue (#71)
- psutil provides identical API across Linux/macOS/Windows
- Previous POSIX-only signal handling crashed on Windows
- All process management now cross-platform

---

## Activity Log

- 2026-01-12T11:30:00Z – system – lane=planned – Prompt created via /spec-kitty.tasks

---

### Updating Lane Status

To change this work package's lane, either:

1. **Edit directly**: Change the `lane:` field in frontmatter
2. **Use CLI**: `spec-kitty agent tasks move-task WP04 --to <lane> --note "message"`

The CLI command also updates the activity log automatically.

**Valid lanes**: `planned`, `doing`, `for_review`, `done`
- 2026-01-12T10:48:58Z – agent – lane=doing – Started implementation via workflow command
