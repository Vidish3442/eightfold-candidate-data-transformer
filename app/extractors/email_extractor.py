"""Email address extractor for parsed resume sections.

Searches every section of the parsed resume for email addresses and returns
a deduplicated, lowercased list.  The HEADER section (where contact info
typically lives) is always checked; all other sections are checked as a
fallback to catch emails embedded in body text.
"""

from app.constants.regex import EMAIL_PATTERN


class EmailExtractor:
    """Extracts email addresses from parsed resume section dicts.

    Uses :data:`~app.constants.regex.EMAIL_PATTERN` to find all email
    addresses across the full set of sections.  Results are lowercased and
    deduplicated while preserving the order of first occurrence.

    Example usage::

        extractor = EmailExtractor()
        emails = extractor.extract({"HEADER": "Jane Doe  jane.doe@example.com"})
        # ["jane.doe@example.com"]
    """

    def extract(self, sections: dict[str, str]) -> list[str]:
        """Find all email addresses in *sections*.

        The HEADER section is searched first; all other sections follow.
        Results are deduplicated and lowercased.

        Args:
            sections: Dict mapping normalized section header strings to their
                raw body text, as returned by
                :class:`~app.parsers.resume_parser.ResumeParser`.

        Returns:
            Deduplicated list of lowercased email strings found anywhere in
            the sections.  Returns ``[]`` when no emails are found.
        """
        seen: set[str] = set()
        result: list[str] = []

        # Build a scan order: HEADER first, then every other section
        ordered_texts: list[str] = []
        header_text = sections.get("HEADER", "")
        if header_text:
            ordered_texts.append(header_text)

        for key, text in sections.items():
            if key != "HEADER" and text:
                ordered_texts.append(text)

        for text in ordered_texts:
            for match in EMAIL_PATTERN.findall(text):
                lower = match.lower()
                if lower not in seen:
                    seen.add(lower)
                    result.append(lower)

        return result
