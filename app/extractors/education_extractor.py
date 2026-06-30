"""Education record extractor for parsed resume sections.

Parses the EDUCATION section of a resume into structured dicts.

Handles two resume formats:
- **Compact**: institution, degree, and dates are on consecutive lines within
  one blank-line-delimited block (original format).
- **Expanded**: each field is on its own blank-line-separated block (common
  in modern resumes), e.g. institution on one block, "Bachelor of Technology"
  on the next, field-of-study on the next, date range on the next.

The extractor first attempts the compact format.  If that yields multiple
records with empty degrees / institutions (sign of the expanded format), it
falls back to reassembling the whole section into a single education record
by scanning all lines together.
"""

import re

from app.constants.regex import DATE_RANGE_PATTERN

# Degree keywords used to identify degree lines
_DEGREE_KEYWORDS_RE: re.Pattern[str] = re.compile(
    r"\b(B\.?[Tt]ech|B\.?E\.?|B\.?S\.?|M\.?S\.?|B\.?A\.?|M\.?A\.?|"
    r"Ph\.?D\.?|Bachelor|Master|Associate|Doctor|M\.?Tech|MBA|BCA|MCA)\b",
    re.IGNORECASE,
)

# Lines that look like CGPA / percentage scores — skip as institution/degree
_SCORE_RE: re.Pattern[str] = re.compile(r"^\d+[\.\d]*\s*[/%]?\s*(CGPA|GPA)?", re.IGNORECASE)
# Lines that are just a year
_YEAR_ONLY_RE: re.Pattern[str] = re.compile(r"^\d{4}$")
# School/board markers
_SCHOOL_BOARD_RE: re.Pattern[str] = re.compile(r"\b(CBSE|ICSE|State Board|ISC)\b", re.IGNORECASE)


class EducationExtractor:
    """Extracts education records from the EDUCATION section of a parsed resume.

    Handles both compact (one block per entry) and expanded (one field per
    block) resume formats.  Produces clean, deduplicated records with
    institution, degree, field_of_study, start_date, and end_date.
    """

    def extract(self, sections: dict[str, str]) -> list[dict]:
        """Parse education records from the EDUCATION section.

        Args:
            sections: Dict mapping normalized section header strings to their
                raw body text, as returned by
                :class:`~app.parsers.resume_parser.ResumeParser`.

        Returns:
            List of dicts with keys ``institution``, ``degree``,
            ``field_of_study``, ``start_date``, and ``end_date``.
            Returns ``[]`` when the section is absent or empty.
        """
        edu_text: str = sections.get("EDUCATION", "")
        if not edu_text.strip():
            return []

        # Collect all meaningful lines in order, ignoring separators/blanks
        all_lines: list[str] = []
        for ln in edu_text.splitlines():
            s = ln.strip()
            if not s or re.match(r"^[-–—=]+$", s):
                continue
            all_lines.append(s)

        if not all_lines:
            return []

        return self._parse_all_lines(all_lines)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _parse_all_lines(self, lines: list[str]) -> list[dict]:
        """Parse the flat list of education lines into structured records.

        Recognises institution names, degree lines, field-of-study lines,
        date ranges, score lines (CGPA/%), year-only lines, and school boards
        (CBSE/ICSE).  Groups them into logical education entries.

        Args:
            lines: Non-blank, non-separator lines from the EDUCATION section.

        Returns:
            List of education record dicts.
        """
        records: list[dict] = []
        current: dict = self._empty_record()

        for line in lines:
            # Date range → start/end date for the current record
            date_match = DATE_RANGE_PATTERN.search(line)
            if date_match:
                if current["start_date"] is None:
                    current["start_date"] = date_match.group(1)
                    current["end_date"] = date_match.group(2)
                continue

            # Year-only line → treat as end date if we have an institution
            if _YEAR_ONLY_RE.match(line):
                if current["institution"] and current["end_date"] is None:
                    current["end_date"] = line
                continue

            # Score line (CGPA, %, percentage) → skip
            if _SCORE_RE.match(line):
                continue

            # Degree keyword line
            if _DEGREE_KEYWORDS_RE.search(line):
                if current["degree"]:
                    # Already have a degree — this signals a new entry
                    if current["institution"]:
                        records.append(current)
                        current = self._empty_record()
                current["degree"] = line
                continue

            # School board line (Class XII, Class X, CBSE) → new entry
            if _SCHOOL_BOARD_RE.search(line) or re.match(r"^Class\s+(?:X{1,3}|IX|VIII|VII)", line, re.IGNORECASE):
                if current["institution"]:
                    records.append(current)
                    current = self._empty_record()
                current["institution"] = line
                # Extract the class level as the degree (e.g. "Class XII", "Class X")
                class_match = re.match(r"^(Class\s+(?:XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I))\b", line, re.IGNORECASE)
                if class_match:
                    current["degree"] = class_match.group(1)
                continue

            # Default: treat as institution name (or field of study if
            # institution and degree already set)
            if not current["institution"]:
                current["institution"] = line
            elif current["degree"] and not current["field_of_study"]:
                # Could be field of study (e.g. "Computer Science and Business Systems")
                current["field_of_study"] = line
            elif not current["degree"]:
                # Second descriptive line before a degree keyword — may be
                # field of study or sub-institution; keep as field_of_study
                current["field_of_study"] = line

        # Flush last record
        if current["institution"]:
            records.append(current)

        # Deduplicate: drop records that have no degree and whose institution
        # duplicates a higher-quality record
        return self._deduplicate(records)

    def _empty_record(self) -> dict:
        """Return a blank education record dict."""
        return {
            "institution": "",
            "degree": "",
            "field_of_study": None,
            "start_date": None,
            "end_date": None,
        }

    def _deduplicate(self, records: list[dict]) -> list[dict]:
        """Remove redundant/empty records, keeping the most complete entry per institution.

        Args:
            records: Raw list of extracted education records (may have duplicates).

        Returns:
            Cleaned, deduplicated list.
        """
        # Keep only records that have at least an institution name
        records = [r for r in records if r["institution"].strip()]

        # Merge records with the same institution: keep the most complete
        merged: dict[str, dict] = {}
        for rec in records:
            key = rec["institution"].strip().lower()
            if key not in merged:
                merged[key] = rec
            else:
                existing = merged[key]
                # Prefer record with more non-empty fields
                existing_score = sum(1 for v in existing.values() if v)
                new_score = sum(1 for v in rec.values() if v)
                if new_score > existing_score:
                    merged[key] = rec

        return list(merged.values())
