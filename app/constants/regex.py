"""Shared compiled regular-expression patterns used across extractor modules.

All patterns are compiled once at module import time and re-used throughout
the pipeline to avoid redundant compilation overhead.

Usage example::

    from app.constants.regex import EMAIL_PATTERN

    emails = EMAIL_PATTERN.findall(text)
"""

import re

# ---------------------------------------------------------------------------
# Contact information patterns
# ---------------------------------------------------------------------------

EMAIL_PATTERN: re.Pattern[str] = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)
"""Matches a standard email address (local-part @ domain)."""

PHONE_PATTERN: re.Pattern[str] = re.compile(
    r"[\+\(]?[0-9][0-9\s\-\.\(\)]{7,}[0-9]"
)
"""Matches phone numbers in a variety of formats, e.g. '(415) 555-0192' or '+1-800-123-4567'."""

URL_PATTERN: re.Pattern[str] = re.compile(
    r"https?://[^\s]+|(?:linkedin|github)\.com/[^\s|]+"
)
"""Matches HTTP/HTTPS URLs and bare linkedin.com / github.com profile paths."""

# ---------------------------------------------------------------------------
# Date and timeline patterns
# ---------------------------------------------------------------------------

DATE_RANGE_PATTERN: re.Pattern[str] = re.compile(
    r"([A-Za-z]+\s+\d{4}|\d{4}-\d{2}|\d{4})"
    r"\s*[–\-—to]+"
    r"\s*([A-Za-z]+\s+\d{4}|\d{4}-\d{2}|\d{4}|[Pp]resent|[Cc]urrent|[Nn]ow)",
    re.IGNORECASE,
)
"""Matches date ranges such as 'March 2021 – Present' or '2018-06 — 2021-02'."""

# ---------------------------------------------------------------------------
# Resume formatting patterns
# ---------------------------------------------------------------------------

BULLET_PATTERN: re.Pattern[str] = re.compile(
    r"^\s*[-•*]\s+(.+)",
    re.MULTILINE,
)
"""Matches bullet-point lines starting with '-', '•', or '*'."""
