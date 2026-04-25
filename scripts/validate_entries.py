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

    for entry in entries:
        line = entry["line"]

        if entry.get("invalid"):
            errors.append(f"Line {line}: Malformed table row: {entry['raw']}")
            continue

        category = entry["category"]
        name = entry["name"]
        auth = entry["auth"]
        https = entry["https"]
        cors = entry["cors"]

        # Validate Auth field
        if auth not in VALID_AUTH_VALUES:
            errors.append(
                f"Line {line}: Invalid Auth value '{auth}' for '{name}'. "
                f"Must be one of: {sorted(VALID_AUTH_VALUES)}"
            )

        # Validate HTTPS field
        if https not in VALID_HTTPS_VALUES:
            errors.append(
                f"Line {line}: Invalid HTTPS value '{https}' for '{name}'. "
                f"Must be one of: {sorted(VALID_HTTPS_VALUES)}"
            )

        # Validate CORS field
        if cors not in VALID_CORS_VALUES:
            errors.append(
                f"Line {line}: Invalid CORS value '{cors}' for '{name}'. "
                f"Must be one of: {sorted(VALID_CORS_VALUES)}"
            )

        # Track names per category for alphabetical order check
        if category not in categories:
            categories[category] = []
        categories[category].append((name, line))

    # Check alphabetical ordering within each category
    for category, names in categories.items():
        for i in range(1, len(names)):
            prev_name, prev_line = names[i - 1]
            curr_name, curr_line = names[i]
            if curr_name.lower() < prev_name.lower():
                errors.append(
                    f"Line {curr_line}: '{curr_name}' should come before '{prev_name}' "
                    f"in category '{category}' (alphabetical order required)"
                )

    return errors


def main() -> int:
    """Main entry point for the validation script."""
    readme_path = Path(__file__).parent.parent / "README.md"

    if not readme_path.exists():
        print(f"ERROR: README.md not found at {readme_path}", file=sys.stderr)
        return 1

    print(f"Validating entries in {readme_path}...")
    entries = parse_readme(str(readme_path))
    errors = validate_entries(entries)

    valid_count = sum(1 for e in entries if not e.get("invalid"))
    print(f"Found {len(entries)} entries ({valid_count} valid) across the README.")

    if errors:
        print(f"\nFound {len(errors)} error(s):")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("All entries are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
