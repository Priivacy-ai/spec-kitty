"""Tests for plan validation module."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from specify_cli.plan_validation import (
    PlanValidationError,
    detect_unfilled_plan,
    validate_plan_filled,
)


def test_detect_unfilled_plan_with_template():
    """Test detection of unfilled plan with template markers."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "plan.md"
        plan_path.write_text(
            """# Implementation Plan: [FEATURE]
**Branch**: `[###-feature-name]` | **Date**: [DATE]

**Language/Version**: [e.g., Python 3.11, Swift 5.9, Rust 1.75 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI, UIKit, LLVM or NEEDS CLARIFICATION]
**Testing**: [e.g., pytest, XCTest, cargo test or NEEDS CLARIFICATION]

## Charter Check
[Gates determined based on charter file]

## Project Structure
# [REMOVE IF UNUSED] Option 1: Single project (DEFAULT)
src/
├── models/
""",
            encoding="utf-8",
        )

        is_unfilled, markers = detect_unfilled_plan(plan_path)
        assert is_unfilled is True
        assert len(markers) >= 5
        assert "[FEATURE]" in markers
        assert "[DATE]" in markers
        assert "or NEEDS CLARIFICATION" in markers


def test_detect_unfilled_plan_with_filled_plan():
    """Test detection passes for a properly filled plan."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "plan.md"
        plan_path.write_text(
            """# Implementation Plan: User Authentication System
**Branch**: `001-user-auth` | **Date**: 2025-11-13

**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, SQLAlchemy, bcrypt
**Testing**: pytest with coverage

## Charter Check
✓ Single responsibility per module
✓ All endpoints have error handling
✓ Passwords never logged

## Project Structure
backend/
├── src/
│   ├── models/
│   │   └── user.py
│   ├── services/
│   │   └── auth.py
│   └── api/
│       └── endpoints.py
""",
            encoding="utf-8",
        )

        is_unfilled, markers = detect_unfilled_plan(plan_path)
        assert is_unfilled is False
        assert len(markers) < 5


def test_detect_unfilled_plan_nonexistent():
    """Test that nonexistent file is not considered unfilled."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "nonexistent.md"
        is_unfilled, markers = detect_unfilled_plan(plan_path)
        assert is_unfilled is False
        assert markers == []


def test_validate_plan_filled_strict_mode():
    """Test strict validation raises error for unfilled plan."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "plan.md"
        plan_path.write_text(
            """# Implementation Plan: [FEATURE]
**Language/Version**: [e.g., Python 3.11 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI or NEEDS CLARIFICATION]
**Testing**: [e.g., pytest or NEEDS CLARIFICATION]
[Gates determined based on charter file]
# [REMOVE IF UNUSED] Option 1: Single project
# [REMOVE IF UNUSED] Option 2: Web application
# [REMOVE IF UNUSED] Option 3: Mobile + API
ACTION REQUIRED: Replace the content
""",
            encoding="utf-8",
        )

        with pytest.raises(PlanValidationError) as exc_info:
            validate_plan_filled(plan_path, feature_slug="001-test-feature", strict=True)

        assert "appears to be unfilled" in str(exc_info.value)
        assert "template markers" in str(exc_info.value)
        assert "001-test-feature" in str(exc_info.value)


def test_validate_plan_filled_lenient_mode(capsys):
    """Test lenient validation warns but doesn't raise for unfilled plan."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "plan.md"
        plan_path.write_text(
            """# Implementation Plan: [FEATURE]
**Language/Version**: [e.g., Python 3.11 or NEEDS CLARIFICATION]
**Primary Dependencies**: [e.g., FastAPI or NEEDS CLARIFICATION]
**Testing**: [e.g., pytest or NEEDS CLARIFICATION]
[Gates determined based on charter file]
# [REMOVE IF UNUSED] Option 1: Single project
# [REMOVE IF UNUSED] Option 2: Web application
# [REMOVE IF UNUSED] Option 3: Mobile + API
ACTION REQUIRED: Replace the content
""",
            encoding="utf-8",
        )

        # Should not raise in lenient mode
        validate_plan_filled(plan_path, strict=False)

        # Should print warning to stderr
        captured = capsys.readouterr()
        assert "Warning:" in captured.err
        assert "appears to be unfilled" in captured.err


def test_validate_plan_filled_passes_for_complete_plan():
    """Test validation passes for a complete plan."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "plan.md"
        plan_path.write_text(
            """# Implementation Plan: Real-time Chat Feature
**Branch**: `002-realtime-chat` | **Date**: 2025-11-13

## Technical Context
**Language/Version**: Python 3.11
**Primary Dependencies**: FastAPI, WebSockets, Redis
**Storage**: PostgreSQL for persistence
**Testing**: pytest, WebSocket test client
**Target Platform**: Linux server (Docker)
**Performance Goals**: Support 10k concurrent connections
**Constraints**: <100ms message latency

## Charter Check
✓ All WebSocket endpoints authenticated
✓ Rate limiting on message send
✓ Message validation and sanitization
✓ Comprehensive error handling

## Project Structure
backend/
├── src/
│   ├── models/
│   │   ├── message.py
│   │   └── room.py
│   ├── services/
│   │   ├── websocket.py
│   │   └── message_queue.py
│   └── api/
│       └── chat_endpoints.py
└── tests/
    ├── unit/
    └── integration/
""",
            encoding="utf-8",
        )

        # Should not raise any errors
        validate_plan_filled(plan_path, feature_slug="002-realtime-chat", strict=True)


def test_validate_plan_with_partial_markers():
    """Test plan with few markers is considered filled."""
    with TemporaryDirectory() as tmpdir:
        plan_path = Path(tmpdir) / "plan.md"
        # Only 2 markers - below threshold
        plan_path.write_text(
            """# Implementation Plan: Dashboard Redesign
**Branch**: `003-dashboard` | **Date**: 2025-11-13

**Language/Version**: TypeScript 5.0
**Primary Dependencies**: React, TailwindCSS
**Testing**: Jest, React Testing Library or NEEDS CLARIFICATION
**Target Platform**: Modern browsers
**Performance Goals**: <2s initial load

## Charter Check
✓ Accessibility WCAG 2.1 AA
✓ Mobile responsive
[Gates determined based on charter file]

## Project Structure
frontend/
├── src/
│   ├── components/
│   │   └── Dashboard.tsx
│   └── styles/
└── tests/
""",
            encoding="utf-8",
        )

        # Should pass - only 2 markers
        is_unfilled, markers = detect_unfilled_plan(plan_path)
        assert is_unfilled is False
        assert len(markers) == 2  # Only 2 markers present
