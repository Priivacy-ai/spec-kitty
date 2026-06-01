"""Inline drift observation surface for glossary semantic-check events.

After a CLI invocation (do / advise / ask), this module reads glossary
semantic-check events and renders compact inline notices for high/critical
severity drift detected in the current invocation window.

Key invariants:
- collect_notices() NEVER raises — returns [] on any exception.
- render_notices([]) produces zero output.
- No changes are made to ProfileInvocationExecutor.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.text import Text

from .semantic_events import iter_semantic_conflicts

# ---------------------------------------------------------------------------
# Value object
# ---------------------------------------------------------------------------

_HIGH_SEVERITY = {"high", "critical"}


@dataclass(frozen=True)
class InlineNotice:
    """One drift notice surfaced after a CLI invocation."""

    term: str  # human-readable term surface
    term_id: str  # glossary URN, e.g. "glossary:deployment-target"
    severity: str  # "high" | "critical"
    conflict_type: str  # e.g. "scope_mismatch"
    conflicting_senses: list[str]  # two or more sense texts
    suggested_action: str  # rendered command hint


# ---------------------------------------------------------------------------
# Surface
# ---------------------------------------------------------------------------


class ObservationSurface:
    """Reads glossary drift events and renders inline notices."""

    def collect_notices(
        self,
        repo_root: Path,
        invocation_id: str | None = None,
    ) -> list[InlineNotice]:
        """Read the CLI event log and return high/critical drift notices.

        Returns an empty list on any exception — never raises.

        Args:
            repo_root: Repository root directory.
            invocation_id: If provided, only events with this invocation_id
                are considered (current call window).

        Returns:
            Deduplicated list of InlineNotice objects (last-seen wins per
            term_id), filtered to high/critical severity.
        """
        try:
            # term_id -> last matching event dict
            seen: dict[str, InlineNotice] = {}
            for conflict in iter_semantic_conflicts(repo_root, invocation_id=invocation_id):
                if conflict.severity not in _HIGH_SEVERITY:
                    continue
                if not conflict.term_id:
                    continue
                seen[conflict.term_id] = InlineNotice(
                    term=conflict.term,
                    term_id=conflict.term_id,
                    severity=conflict.severity,
                    conflict_type=conflict.conflict_type,
                    conflicting_senses=conflict.conflicting_senses,
                    suggested_action="run `spec-kitty glossary conflicts --unresolved`",
                )

            notices: list[InlineNotice] = []
            notices.extend(seen.values())
            return notices
        except Exception:  # noqa: BLE001
            return []

    def render_notices(self, notices: list[InlineNotice], console: Console) -> None:
        """Render drift notices to the console. No-op when list is empty.

        A Rich formatting error is silently swallowed — this method never
        raises.

        Args:
            notices: List of InlineNotice objects from collect_notices().
            console: Rich Console to write to.
        """
        if not notices:
            return
        try:
            console.print()  # blank line separator
            for notice in notices:
                line1 = Text()
                line1.append("⚠ Glossary drift ", style="yellow bold")
                line1.append(f"[{notice.severity}]", style="yellow")
                line1.append(f': "{notice.term}" — {notice.conflict_type} detected')
                line2 = Text(f"  Suggest: {notice.suggested_action}", style="dim")
                console.print(line1)
                console.print(line2)
        except Exception:  # noqa: BLE001
            return
