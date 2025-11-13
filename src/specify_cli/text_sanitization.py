"""Text sanitization utilities for preventing encoding errors.

This module provides utilities to normalize Windows-1252 smart quotes and other
problematic characters that can cause UTF-8 encoding errors in markdown files.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

__all__ = [
    "sanitize_markdown_text",
    "sanitize_file",
    "detect_problematic_characters",
    "PROBLEMATIC_CHARS",
]

# Map of Windows-1252 / problematic characters to safe UTF-8 replacements
PROBLEMATIC_CHARS = {
    # Smart quotes (Windows-1252 bytes 0x91-0x94)
    "\u2018": "'",  # LEFT SINGLE QUOTATION MARK → apostrophe
    "\u2019": "'",  # RIGHT SINGLE QUOTATION MARK → apostrophe
    "\u201c": '"',  # LEFT DOUBLE QUOTATION MARK → straight quote
    "\u201d": '"',  # RIGHT DOUBLE QUOTATION MARK → straight quote
    # Em/en dashes
    "\u2013": "--",  # EN DASH → double hyphen
    "\u2014": "---",  # EM DASH → triple hyphen
    # Mathematical operators that may come from cp1252
    "\u00b1": "+/-",  # PLUS-MINUS SIGN → +/-
    "\u00d7": "x",  # MULTIPLICATION SIGN → x
    "\u00f7": "/",  # DIVISION SIGN → /
    # Ellipsis
    "\u2026": "...",  # HORIZONTAL ELLIPSIS → three periods
    # Bullets
    "\u2022": "*",  # BULLET → asterisk
    "\u2023": ">",  # TRIANGULAR BULLET → greater than
    # Degree symbol (often problematic)
    "\u00b0": " degrees",  # DEGREE SIGN → " degrees"
    # Non-breaking space (invisible but causes issues)
    "\u00a0": " ",  # NO-BREAK SPACE → regular space
    # Trademark/copyright symbols
    "\u2122": "(TM)",  # TRADE MARK SIGN
    "\u00a9": "(C)",  # COPYRIGHT SIGN
    "\u00ae": "(R)",  # REGISTERED SIGN
}

# Compile regex for detecting any problematic character
_PROBLEMATIC_PATTERN = re.compile(
    "[" + "".join(re.escape(char) for char in PROBLEMATIC_CHARS.keys()) + "]"
)


def sanitize_markdown_text(text: str, *, preserve_utf8: bool = False) -> str:
    """Sanitize markdown text by replacing problematic characters.

    Args:
        text: The markdown text to sanitize
        preserve_utf8: If True, only replace characters that cause encoding issues.
                      If False (default), replace all problematic characters for
                      maximum compatibility.

    Returns:
        Sanitized text with problematic characters replaced

    Examples:
        >>> sanitize_markdown_text("User's "favorite" feature")
        'User\\'s "favorite" feature'

        >>> sanitize_markdown_text("Price: $100 ± $10")
        'Price: $100 +/- $10'

        >>> sanitize_markdown_text("Temperature: 72° outside")
        'Temperature: 72 degrees outside'
    """
    if not text:
        return text

    # Replace each problematic character with its safe equivalent
    result = text
    for problematic, replacement in PROBLEMATIC_CHARS.items():
        if problematic in result:
            result = result.replace(problematic, replacement)

    return result


def detect_problematic_characters(
    text: str,
) -> list[tuple[int, int, str, str]]:
    """Detect problematic characters in text and return their locations.

    Args:
        text: The text to check

    Returns:
        List of tuples: (line_number, column, character, suggested_replacement)
        Line numbers are 1-indexed, columns are 0-indexed.

    Examples:
        >>> text = "Line 1\\nUser's "test"\\nLine 3"
        >>> issues = detect_problematic_characters(text)
        >>> len(issues)
        3
        >>> issues[0]
        (2, 4, '\u2019', "'")
    """
    issues: list[tuple[int, int, str, str]] = []

    lines = text.splitlines(keepends=True)
    for line_num, line in enumerate(lines, start=1):
        for match in _PROBLEMATIC_PATTERN.finditer(line):
            char = match.group(0)
            replacement = PROBLEMATIC_CHARS.get(char, "?")
            issues.append((line_num, match.start(), char, replacement))

    return issues


def sanitize_file(
    file_path: Path,
    *,
    backup: bool = True,
    dry_run: bool = False,
) -> tuple[bool, Optional[str]]:
    """Sanitize a markdown file in place.

    Args:
        file_path: Path to the markdown file to sanitize
        backup: If True, create a .bak file before modifying
        dry_run: If True, only check and report, don't modify

    Returns:
        Tuple of (was_modified, error_message)
        - was_modified: True if the file had problematic characters
        - error_message: None if successful, error message if failed

    Examples:
        >>> from pathlib import Path
        >>> from tempfile import NamedTemporaryFile
        >>> with NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
        ...     f.write('User's "test"')
        ...     tmp_path = Path(f.name)
        >>> modified, error = sanitize_file(tmp_path, backup=False)
        >>> modified
        True
        >>> tmp_path.read_text()
        'User\\'s "test"'
        >>> tmp_path.unlink()  # cleanup
    """
    if not file_path.exists():
        return False, f"File not found: {file_path}"

    try:
        # Try reading as UTF-8 first
        try:
            original_text = file_path.read_text(encoding="utf-8")
            encoding_issue = False
        except UnicodeDecodeError:
            # Fall back to cp1252 or latin-1
            encoding_issue = True
            original_bytes = file_path.read_bytes()
            for encoding in ("cp1252", "latin-1"):
                try:
                    original_text = original_bytes.decode(encoding)
                    break
                except UnicodeDecodeError:
                    continue
            else:
                # Last resort: replace invalid characters
                original_text = original_bytes.decode("utf-8", errors="replace")

        # Sanitize the text
        sanitized_text = sanitize_markdown_text(original_text)

        # Check if any changes were made
        if sanitized_text == original_text and not encoding_issue:
            return False, None  # No changes needed

        if dry_run:
            return True, None  # Would modify but dry run

        # Create backup if requested
        if backup:
            backup_path = file_path.with_suffix(file_path.suffix + ".bak")
            backup_path.write_bytes(file_path.read_bytes())

        # Write sanitized content
        file_path.write_text(sanitized_text, encoding="utf-8")
        return True, None

    except Exception as exc:
        return False, f"Error sanitizing {file_path}: {exc}"


def sanitize_directory(
    directory: Path,
    *,
    pattern: str = "**/*.md",
    backup: bool = False,
    dry_run: bool = False,
) -> dict[str, tuple[bool, Optional[str]]]:
    """Sanitize all markdown files in a directory.

    Args:
        directory: Directory to scan
        pattern: Glob pattern for files to sanitize (default: **/*.md)
        backup: If True, create .bak files before modifying
        dry_run: If True, only check and report, don't modify

    Returns:
        Dictionary mapping file paths to (was_modified, error_message) tuples
    """
    results: dict[str, tuple[bool, Optional[str]]] = {}

    for file_path in directory.glob(pattern):
        if file_path.is_file():
            result = sanitize_file(file_path, backup=backup, dry_run=dry_run)
            results[str(file_path)] = result

    return results
