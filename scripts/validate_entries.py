#!/usr/bin/env python3
"""Validate API entries in the README.md file.

This script checks that all entries in the README follow the required format:
- Correct table structure
- Required fields (API, Description, Auth, HTTPS, CORS, Link)
- Valid values for Auth, HTTPS, and CORS fields
- Alphabetical ordering within categories
"""

import re
import sys
from pathlib import Path

# Valid values for specific columns
# Note: "No" means no auth required (not invalid), empty string also means no auth
VALID_AUTH_VALUES = {"", "apiKey", "OAuth", "X-Mashape-Key", "User-Agent", "No"}
VALID_HTTPS_VALUES = {"Yes", "No"}
VALID_CORS_VALUES = {"Yes", "No", "Unknown"}

# Table header pattern
TABLE_HEADER_PATTERN = re.compile(
    r"^\|\s*API\s*\|\s*Description\s*\|\s*Auth\s*\|\s*HTTPS\s*\|\s*CORS\s*\|"
)

# Table row pattern: | Name | Description | Auth | HTTPS | CORS | Link |
TABLE_ROW_PATTERN = re.compile(
    r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(`[^`]*`|)\s*\|\s*(Yes|No)\s*\|\s*(Yes|No|Unknown)\s*\|\s*\[.*?\]\(.*?\)\s*\|"
)

# Category header pattern
CATEGORY_PATTERN = re.compile(r"^#{2,3}\s+(.+)")


def parse_readme(filepath: str) -> list[dict]:
    """Parse the README.md and extract all API entries with their categories."""
    entries = []
    current_category = None
    in_table = False

    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line_num, line in enumerate(lines, start=1):
        line = line.rstrip()

        # Detect category headers
        category_match = CATEGORY_PATTERN.match(line)
        if category_match:
            current_category = category_match.group(1).strip()
            in_table = False
            continue

        # Detect table header
        if TABLE_HEADER_PATTERN.match(line):
            in_table = True
            continue

        # Skip separator row
        if in_table and re.match(r"^\|[-| :]+\|$", line):
            continue

        # Parse table rows
        if in_table and line.startswith("|"):
            row_match = TABLE_ROW_PATTERN.match(line)
            if row_match:
                entries.append({
                    "line": line_num,
                    "category": current_category,
                    "name": row_match.group(1).strip(),
                    "description": row_match.group(2).strip(),
                    "auth": row_match.group(3).strip().strip("`"),
                    "https": row_match.group(4).strip(),
                    "cors": row_match.group(5).strip(),
                    "raw": line,
                })
            elif line.strip() != "|":
                entries.append({
                    "line": line_num,
                    "category": current_category,
                    "invalid": True,
                    "raw": line,
                })
        elif not line.startswith("|"):
            in_table = False

    return entries


def validate_entries(entries: list[dict]) -> list[str]:
    """Validate all parsed entries and return a list of error messages."""
    errors = []
    categories: dict[str, list[str]] = {}

    # Check for invalid (malformed) rows first
    for entry in entries:
        if entry.get("invalid"):
            errors.append(f"Line {entry['line']}: Malformed table row in category '{entry['category']}': {entry['raw']}")
            continue

        # Validate auth value
        if entry.get("auth") not in VALID_AUTH_VALUES:
            errors.append(
                f"Line {entry['line']}: Invalid Auth value '{entry['auth']}' "
                f"(must be one of: {', '.join(repr(v) for v in sorted(VALID_AUTH_VALUES))})"
            )

        # Validate HTTPS value
        if entry.get("https") not in VALID_HTTPS_VALUES:
            errors.append(
                f"Line {entry['line']}: Invalid HTTPS value '{entry['https']}' "
                f"(must be one of: {', '.join(sorted(VALID_HTTPS_VALUES))})"
            )

        # Validate CORS value
        if entry.get("cors") not in VALID_CORS_VALUES:
            errors.append(
                f"Line {entry['line']}: Invalid CORS value '{entry['cors']}' "
                f"(must be one of: {', '.join(sorted(VALID_CORS_VALUES))})"
            )

        # Collect names per category for alphabetical order check
        cat = entry.get("category", "Unknown")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((entry["line"], entry["name"]))

    # Check alphabetical ordering within each category
    for cat, name_list in categories.items():
        names = [n for _, n in name_list]
        sorted_names = sorted(names, key=lambda s: s.lower())
        for i, (line_no, name) in enumerate(name_list):
            if name != sorted_names[i]:
                errors.append(
                    f"Line {line_no}: '{name}' is out of alphabetical order in category '{cat}' "
                    f"(expected '{sorted_names[i]}' at this position)"
                )
                # Only report the first ordering issue per category to avoid noise
                break

    return errors


def main() -> int:
    """Main entry point."""
    readme_path = Path("README.md")
    if not readme_path.exists():
        print("Error: README.md not found in current directory.", file=sys.stderr)
        return 1

    entries = parse_readme(str(readme_path))
    errors = validate_entries(entries)

    if errors:
        print(f"Found {len(errors)} validation error(s):\n")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"All {len(entries)} entries are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
