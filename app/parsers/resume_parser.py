"""Resume text section splitter.

Takes raw resume text (as produced by :class:`~app.readers.resume_reader.ResumeReader`)
and splits it into named sections keyed by a normalized header label.

Section detection is line-by-line: any line whose stripped, upper-cased
content matches one of the known section header names is treated as the
start of a new section.  Text before the first recognized header is stored
under the special key ``"HEADER"`` and typically contains the candidate's
name and contact information.

The returned dict is consumed by the extractor layer (email, phone, skill,
education, experience, certification extractors) which each operate on the
section text most relevant to them.
"""

import re
from typing import ClassVar


# Regex that matches lines beginning with a known section header keyword,
# optionally followed by punctuation (colon, dash) and trailing whitespace.
_HEADER_RE: re.Pattern[str] = re.compile(
    r"^(EXPERIENCE|WORK EXPERIENCE|EMPLOYMENT|EDUCATION|SKILLS|"
    r"CERTIFICATIONS.*|SUMMARY|OBJECTIVE|PROJECTS|ACHIEVEMENTS|AWARDS|"
    r"PUBLICATIONS|VOLUNTEER|LANGUAGES|INTERESTS|HOBBIES)"
    r"[:\-\s]*$",
    re.IGNORECASE,
)


class ResumeParser:
    """Splits raw resume text into a dict of labeled sections.

    Each key in the returned dict is a normalized section header (uppercase,
    no trailing punctuation) and each value is the raw text that appeared
    between that header and the next detected header.

    The special key ``"HEADER"`` always exists and holds any text that
    appeared before the first recognized section header (typically the
    candidate's name, email, phone, and profile links).

    Example usage::

        parser = ResumeParser()
        sections = parser.parse(raw_text)
        print(sections.keys())
        # dict_keys(['HEADER', 'EXPERIENCE', 'EDUCATION', 'SKILLS', 'CERTIFICATIONS'])
    """

    # Ordered list of known section header names used for matching.
    KNOWN_HEADERS: ClassVar[list[str]] = [
        "EXPERIENCE",
        "WORK EXPERIENCE",
        "EMPLOYMENT",
        "EDUCATION",
        "SKILLS",
        "CERTIFICATIONS AND LICENSES",
        "CERTIFICATIONS",
        "SUMMARY",
        "OBJECTIVE",
        "PROJECTS",
        "ACHIEVEMENTS",
        "AWARDS",
        "PUBLICATIONS",
        "VOLUNTEER",
        "LANGUAGES",
        "INTERESTS",
        "HOBBIES",
    ]

    def parse(self, text: str) -> dict[str, str]:
        """Split *text* into labeled resume sections.

        Lines are scanned sequentially.  A line is recognized as a section
        header when its stripped, upper-cased content matches
        :data:`_HEADER_RE` (i.e. it starts with one of the known header
        keywords, optionally trailed by punctuation).

        Args:
            text: Full raw text of a resume document as returned by
                :class:`~app.readers.resume_reader.ResumeReader`.

        Returns:
            A dict mapping normalized section header strings to the raw body
            text of that section.  The key ``"HEADER"`` always exists and
            holds pre-section contact/name information.  If *text* is empty
            the dict ``{"HEADER": ""}`` is returned.

        Example::

            >>> parser = ResumeParser()
            >>> sections = parser.parse("Jane Doe\\njane@example.com\\n\\nEXPERIENCE\\nEngineer at Acme")
            >>> list(sections.keys())
            ['HEADER', 'EXPERIENCE']
        """
        if not text or not text.strip():
            return {"HEADER": ""}

        sections: dict[str, str] = {}
        current_key: str = "HEADER"
        current_lines: list[str] = []

        for line in text.splitlines():
            stripped: str = line.strip()
            normalized: str = stripped.upper().rstrip(":- ")

            if _HEADER_RE.match(stripped):
                # Save accumulated text under the current key
                sections[current_key] = "\n".join(current_lines).strip()
                # Determine the canonical key: prefer the longest matching
                # known header (so "WORK EXPERIENCE" beats "EXPERIENCE")
                current_key = self._normalize_header(normalized)
                current_lines = []
            else:
                current_lines.append(line)

        # Flush the final section
        sections[current_key] = "\n".join(current_lines).strip()

        return sections

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalize_header(self, raw_upper: str) -> str:
        """Return the canonical section key for *raw_upper*.

        Tries to match *raw_upper* against known header names (longest match
        first to prefer "CERTIFICATIONS AND LICENSES" over "CERTIFICATIONS").
        Falls back to *raw_upper* itself when no known header matches.

        Args:
            raw_upper: Uppercase, stripped header string from the source text.

        Returns:
            Canonical uppercase header key (e.g. ``"CERTIFICATIONS"``).
        """
        # Sort by descending length so longer (more specific) headers win
        for known in sorted(self.KNOWN_HEADERS, key=len, reverse=True):
            if raw_upper.startswith(known):
                return known
        return raw_upper
