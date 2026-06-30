"""Phone number extractor for parsed resume sections.

Searches the HEADER section of a parsed resume for phone numbers and returns
a deduplicated list of raw phone strings.  Only the HEADER is searched
because phone numbers in body sections (e.g. client contact numbers in a job
description) are almost always false positives.
"""

from app.constants.regex import PHONE_PATTERN


class PhoneExtractor:
    """Extracts phone numbers from the HEADER section of a parsed resume.

    Uses :data:`~app.constants.regex.PHONE_PATTERN` to locate phone strings
    in the contact block.  Raw strings are returned as-is; E.164 normalization
    is applied later in ``normalizers/phone.py``.

    Example usage::

        extractor = PhoneExtractor()
        phones = extractor.extract({"HEADER": "Jane Doe  (415) 555-0192"})
        # ["(415) 555-0192"]
    """

    def extract(self, sections: dict[str, str]) -> list[str]:
        """Find all phone numbers in the HEADER section of *sections*.

        Only ``sections["HEADER"]`` is searched to minimise false positives
        from phone-like digit sequences in experience descriptions.

        Args:
            sections: Dict mapping normalized section header strings to their
                raw body text, as returned by
                :class:`~app.parsers.resume_parser.ResumeParser`.

        Returns:
            Deduplicated list of raw phone strings.  Returns ``[]`` when no
            phone numbers are found or when the HEADER key is absent.
        """
        header_text: str = sections.get("HEADER", "")
        if not header_text:
            return []

        seen: set[str] = set()
        result: list[str] = []

        for match in PHONE_PATTERN.findall(header_text):
            stripped = match.strip()
            if stripped not in seen:
                seen.add(stripped)
                result.append(stripped)

        return result
