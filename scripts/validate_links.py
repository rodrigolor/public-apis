#!/usr/bin/env python3
"""Script to validate links in the README.md file.

This script checks all URLs in the README.md to ensure they are
accessible and return valid HTTP responses.
"""

import re
import sys
import time
import argparse
from typing import Optional

import requests
from requests.exceptions import ConnectionError, Timeout, TooManyRedirects


README_PATH = "README.md"
URL_PATTERN = re.compile(r'https?://[^\s\)\]\>"]+', re.IGNORECASE)
DEFAULT_TIMEOUT = 10  # seconds
RETRY_COUNT = 2
RETRY_DELAY = 2  # seconds

# HTTP status codes considered valid
VALID_STATUS_CODES = {200, 201, 204, 301, 302, 403, 405, 429}


def extract_urls(filepath: str) -> list[str]:
    """Extract all URLs from the given file.

    Args:
        filepath: Path to the file to extract URLs from.

    Returns:
        A list of unique URLs found in the file.
    """
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    urls = URL_PATTERN.findall(content)
    # Remove trailing punctuation that may have been captured
    cleaned = [url.rstrip(".,;:'") for url in urls]
    return list(dict.fromkeys(cleaned))  # deduplicate while preserving order


def check_url(url: str, timeout: int = DEFAULT_TIMEOUT) -> tuple[bool, Optional[int], str]:
    """Check if a URL is accessible.

    Args:
        url: The URL to check.
        timeout: Request timeout in seconds.

    Returns:
        A tuple of (is_valid, status_code, message).
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; public-apis-validator/1.0; "
            "+https://github.com/public-apis/public-apis)"
        )
    }

    for attempt in range(RETRY_COUNT + 1):
        try:
            response = requests.head(
                url, headers=headers, timeout=timeout, allow_redirects=True
            )
            if response.status_code in VALID_STATUS_CODES:
                return True, response.status_code, "OK"
            # Some servers don't support HEAD, try GET
            if response.status_code in {400, 404, 405}:
                response = requests.get(
                    url, headers=headers, timeout=timeout, allow_redirects=True
                )
                if response.status_code in VALID_STATUS_CODES:
                    return True, response.status_code, "OK"
            return False, response.status_code, f"HTTP {response.status_code}"

        except Timeout:
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
                continue
            return False, None, "Timeout"
        except ConnectionError as e:
            if attempt < RETRY_COUNT:
                time.sleep(RETRY_DELAY)
                continue
            return False, None, f"Connection error: {e}"
        except TooManyRedirects:
            return False, None, "Too many redirects"
        except Exception as e:  # pylint: disable=broad-except
            return False, None, f"Unexpected error: {e}"

    return False, None, "Failed after retries"


def main() -> int:
    """Main entry point for the link validator.

    Returns:
        Exit code: 0 for success, 1 if any links are broken.
    """
    parser = argparse.ArgumentParser(description="Validate links in README.md")
    parser.add_argument(
        "--file", default=README_PATH, help="Path to the markdown file to validate"
    )
    parser.add_argument(
        "--timeout", type=int, default=DEFAULT_TIMEOUT, help="Request timeout in seconds"
    )
    args = parser.parse_args()

    print(f"Extracting URLs from {args.file}...")
    urls = extract_urls(args.file)
    print(f"Found {len(urls)} unique URLs to check.\n")

    broken = []
    for i, url in enumerate(urls, start=1):
        is_valid, status_code, message = check_url(url, timeout=args.timeout)
        status_label = f"[{status_code}]" if status_code else "[---]"
        symbol = "✓" if is_valid else "✗"
        print(f"  {symbol} ({i}/{len(urls)}) {status_label} {url} — {message}")
        if not is_valid:
            broken.append((url, message))

    print(f"\n{'='*60}")
    if broken:
        print(f"FAILED: {len(broken)} broken link(s) found:")
        for url, reason in broken:
            print(f"  - {url} ({reason})")
        return 1

    print(f"SUCCESS: All {len(urls)} links are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
