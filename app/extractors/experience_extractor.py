"""Work-experience record extractor for parsed resume sections.

Parses the EXPERIENCE (or WORK EXPERIENCE) section of a resume into
structured dicts.  Each block is delimited by a blank line.  The first line
of a block is expected to contain "Title — Company" (or "Title at Company")
and the second line a date range.  Bullet points are extracted with
:data:`~app.constants.regex.BULLET_PATTERN`.
"""

import re

from app.constants.regex import BULLET_PATTERN, DATE_RANGE_PATTERN

# Separators used between title and company on the heading line
_TITLE_COMPANY_SEP: re.Pattern[str] = re.compile(
    r"\s+[—–\-]\s+|\s+at\s+", re.IGNORECASE
)


class ExperienceExtractor:
    """Extracts work-experience records from the EXPERIENCE section of a parsed resume.

    Blocks are delimited by one or more blank lines.  For each block:
    - Line 1: "Job Title — Company Name" (or "Title at Company").
    - Line 2 (or nearby): a date range matched by
      :data:`~app.constants.regex.DATE_RANGE_PATTERN`.
    - Remaining lines: bullet points extracted by
      :data:`~app.constants.regex.BULLET_PATTERN`.

    The ``description`` field is set to the bullets joined by a space when
    no prose paragraph is found.

    Example usage::

        extractor = ExperienceExtractor()
        roles = extractor.extract({
            "EXPERIENCE": (
                "Senior Software Engineer — Acme Corp\\n"
                "March 2021 – Present\\n"
                "- Led backend development.\\n"
                "- Reduced latency by 40%."
            )
        })
        # [{"title": "Senior Software Engineer", "company": "Acme Corp",
        #   "start_date": "March 2021", "end_date": "Present",
        #   "description": "Led backend development. Reduced latency by 40%.",
        #   "bullets": ["Led backend development.", "Reduced latency by 40%."]}]
    """

    def extract(self, sections: dict[str, str]) -> list[dict]:
        """Parse experience records from the EXPERIENCE or WORK EXPERIENCE section.

        Checks ``sections["EXPERIENCE"]`` first, then falls back to
        ``sections["WORK EXPERIENCE"]`` when the former is absent.

        Handles two formats:
        - **Compact**: title/company + date on consecutive lines in one block.
        - **Expanded**: title/company, date, and bullets in separate blank-line
          blocks (common in modern resumes).  These are reassembled by scanning
          forward from each heading-detected line.

        Args:
            sections: Dict mapping normalized section header strings to their
                raw body text, as returned by
                :class:`~app.parsers.resume_parser.ResumeParser`.

        Returns:
            List of dicts with keys ``title``, ``company``, ``start_date``,
            ``end_date``, ``description``, and ``bullets``.
            Returns ``[]`` when neither section is present or both are empty.
        """
        exp_text: str = sections.get("EXPERIENCE", "") or sections.get(
            "WORK EXPERIENCE", ""
        )
        if not exp_text.strip():
            return []

        # Collect all non-blank, non-separator lines with their original text
        all_lines: list[str] = [
            ln for ln in exp_text.splitlines()
            if ln.strip() and not re.match(r"^\s*[-–—=]+\s*$", ln)
        ]

        if not all_lines:
            return []

        # Find heading lines (lines that match "Title — Company" pattern or
        # contain a separator between title and company and do NOT start with "-")
        records: list[dict] = []
        i = 0

        while i < len(all_lines):
            line = all_lines[i].strip()

            # Is this line a heading (title — company)?
            heading_parts = _TITLE_COMPANY_SEP.split(line, maxsplit=1)
            is_heading = (
                len(heading_parts) == 2
                and not line.startswith("-")
                and not DATE_RANGE_PATTERN.match(line)
            )

            if is_heading:
                title = heading_parts[0].strip()
                company = heading_parts[1].strip()

                start_date: str | None = None
                end_date: str | None = None
                bullets: list[str] = []

                # Scan forward to collect date + bullets for this entry
                j = i + 1
                while j < len(all_lines):
                    next_line = all_lines[j].strip()

                    # Stop when we hit the next heading
                    next_parts = _TITLE_COMPANY_SEP.split(next_line, maxsplit=1)
                    if (
                        len(next_parts) == 2
                        and not next_line.startswith("-")
                        and not DATE_RANGE_PATTERN.match(next_line)
                    ):
                        break

                    # Date range line
                    date_match = DATE_RANGE_PATTERN.search(next_line)
                    if date_match and start_date is None:
                        start_date = date_match.group(1)
                        end_date = date_match.group(2)
                        j += 1
                        continue

                    # Bullet line
                    bullet_match = BULLET_PATTERN.match(next_line)
                    if bullet_match:
                        bullets.append(bullet_match.group(1).strip())
                        j += 1
                        continue

                    j += 1

                description: str | None = " ".join(bullets) if bullets else None
                records.append({
                    "title": title,
                    "company": company,
                    "start_date": start_date,
                    "end_date": end_date,
                    "description": description,
                    "bullets": bullets,
                })
                i = j  # jump past the consumed lines
            else:
                i += 1

        return records
