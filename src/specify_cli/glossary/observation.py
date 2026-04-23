"""Inline drift observation surface for glossary semantic-check events.

After a CLI invocation (do / advise / ask), this module reads events written
by the glossary chokepoint (WP5.2) and renders compact inline notices for
high/critical severity drift detected in the current invocation window.

Key invariants:
- collect_notices() NEVER raises — returns [] on any exception.
- render_notices([]) produces zero output.
- No changes are made to ProfileInvocationExecutor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.text import Text

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

    _EVENT_LOG_RELPATH = Path(".kittify") / "events" / "glossary" / "_cli.events.jsonl"
    _TARGET_EVENT_TYPE = "semantic_check_evaluated"

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
            log_path = repo_root / self._EVENT_LOG_RELPATH
            if not log_path.exists():
                return []

            # term_id -> last matching event dict
            seen: dict[str, dict] = {}

            for line in log_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue  # skip malformed lines silently

                if event.get("event_type") != self._TARGET_EVENT_TYPE:
                    continue
                if event.get("severity") not in _HIGH_SEVERITY:
                    continue
                if invocation_id is not None and event.get("invocation_id") != invocation_id:
                    continue

                term_id = event.get("term_id", "")
                seen[term_id] = event

            notices: list[InlineNotice] = []
            for event in seen.values():
                term = event.get("term", "")
                notices.append(
                    InlineNotice(
                        term=term,
                        term_id=event.get("term_id", ""),
                        severity=event.get("severity", ""),
                        conflict_type=event.get("conflict_type", ""),
                        conflicting_senses=list(event.get("conflicting_senses", [])),
                        suggested_action=f"run `spec-kitty glossary resolve {term}`",
                    )
                )
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
