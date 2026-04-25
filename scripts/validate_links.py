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
DEFAULT_TIMEOUT = 15  # seconds (increased from 10 - some APIs are slow to respond)
RETRY_COUNT = 3  # increased from 2 to reduce false positives on flaky connections
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

    return False, None, "Fa