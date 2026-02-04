#!/usr/bin/env python3
"""
Validate and fix UTF-8 encoding in Spec Kitty markdown files.

This utility helps prevent UnicodeDecodeError issues by:
1. Scanning markdown files for encoding problems
2. Detecting likely encoding (UTF-8, Windows-1252, etc.)
3. Converting files to UTF-8 if needed
4. Reporting encoding issues with specific positions

Usage:
    python src/specify_cli/scripts/validate_encoding.py --check kitty-specs/
    python src/specify_cli/scripts/validate_encoding.py --fix kitty-specs/001-feature/
    python src/specify_cli/scripts/validate_encoding.py --scan-all
"""

import argparse
import sys
from pathlib import Path
from typing import List, Tuple, Optional


def check_utf8_encoding(file_path: Path) -> Tuple[bool, Optional[str]]:
    """
    Check if a file is valid UTF-8.

    Returns:
        (is_valid, error_message)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            f.read()
        return (True, None)
    except UnicodeDecodeError as e:
        error_msg = f"Position {e.start}: {e.reason} (byte 0x{e.object[e.start]:02x})"
        return (False, error_msg)
    except Exception as e:
        return (False, str(e))


def detect_encoding(file_path: Path) -> str:
    """
    Try to detect the file's actual encoding.

    Returns encoding name or 'unknown'.
    """
    encodings = ['utf-8', 'windows-1252', 'iso-8859-1', 'utf-16', 'utf-32']

    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                f.read()
            return encoding
        except (UnicodeDecodeError, UnicodeError):
            continue

    return 'unknown'


def convert_to_utf8(file_path: Path, source_encoding: str = 'windows-1252', dry_run: bool = False) -> bool:
    """
    Convert a file from source_encoding to UTF-8.

    Returns True if successful.
    """
    try:
        with open(file_path, 'rb') as f:
            data = f.read()

        # Decode with source encoding
        text = data.decode(source_encoding, errors='replace')

        # Common Windows-1252 → UTF-8 fixes
        text = text.replace('\u0086\u0092', '→')  # Dagger + right-quote = arrow
        text = text.replace('\u0093', '→')  # Sometimes used as arrow
        text = text.replace('\u0094', '"')  # Right double quote
        text = text.replace('\u0091', "'")  # Left single quote
        text = text.replace('\u0092', "'")  # Right single quote

        if dry_run:
            print(f"  [DRY RUN] Would convert {file_path.name}")
            return True

        # Write as UTF-8
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(text)

        return True
    except Exception as e:
        print(f"  ❌ Conversion failed: {e}")
        return False


def scan_directory(directory: Path, fix: bool = False, dry_run: bool = False) -> List[Path]:
    """
    Scan directory for markdown files with encoding issues.

    Returns list of files with problems.
    """
    problem_files = []

    markdown_files = list(directory.rglob('*.md'))

    if not markdown_files:
        print(f"No markdown files found in {directory}")
        return []

    print(f"\nScanning {len(markdown_files)} markdown files in {directory}...\n")

    for md_file in markdown_files:
        is_valid, error = check_utf8_encoding(md_file)

        if is_valid:
            print(f"✅ {md_file.relative_to(directory)}")
        else:
            print(f"❌ {md_file.relative_to(directory)}")
            print(f"   Error: {error}")

            if fix or dry_run:
                detected = detect_encoding(md_file)
                print(f"   Detected encoding: {detected}")

                if detected != 'utf-8' and detected != 'unknown':
                    if convert_to_utf8(md_file, detected, dry_run):
                        if not dry_run:
                            # Verify the fix worked
                            is_valid_now, _ = check_utf8_encoding(md_file)
                            if is_valid_now:
                                print(f"   ✅ Fixed! Converted from {detected} to UTF-8")
                            else:
                                print(f"   ⚠️ Conversion completed but file still has issues")
                                problem_files.append(md_file)
                else:
                    problem_files.append(md_file)
            else:
                problem_files.append(md_file)

            print()

    return problem_files


def main():
    parser = argparse.ArgumentParser(description='Validate UTF-8 encoding in markdown files')
    parser.add_argument('path', nargs='?', default='kitty-specs', help='Path to scan (default: kitty-specs)')
    parser.add_argument('--fix', action='store_true', help='Attempt to fix encoding issues')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be fixed without making changes')
    parser.add_argument('--scan-all', action='store_true', help='Scan entire repository')

    args = parser.parse_args()

    if args.scan_all:
        scan_path = Path.cwd()
    else:
        scan_path = Path(args.path)

    if not scan_path.exists():
        print(f"❌ Error: Path does not exist: {scan_path}")
        sys.exit(1)

    problem_files = scan_directory(scan_path, fix=args.fix, dry_run=args.dry_run)

    print("\n" + "="*60)
    if problem_files:
        print(f"❌ Found {len(problem_files)} file(s) with encoding issues:")
        for f in problem_files:
            print(f"  - {f}")

        if not args.fix and not args.dry_run:
            print("\nRun with --fix to attempt automatic conversion")
            print("Run with --dry-run to preview changes")

        sys.exit(1)
    else:
        print("✅ All markdown files have valid UTF-8 encoding!")
        sys.exit(0)


if __name__ == '__main__':
    main()
