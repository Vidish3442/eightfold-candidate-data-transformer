"""Certification and licence extractor for parsed resume sections.

Parses the CERTIFICATIONS (or CERTIFICATIONS AND LICENSES) section of a
resume.  Each non-blank line is treated as one certification string after
stripping leading bullet characters.  Results are deduplicated while
preserving order of first occurrence.
"""

import re


# Matches leading bullet/dash characters at the start of a line
_LEADING_BULLET_RE: re.Pattern[str] = re.compile(r"^\s*[-•*]\s*")


class CertificationExtractor:
    """Extracts certification strings from the CERTIFICATIONS section of a parsed resume.

    Each non-blank, non-separator line in the section is returned as a
    separate certification entry after stripping leading bullet markers.
    Duplicates are removed while preserving order.

    Example usage::

        extractor = CertificationExtractor()
        certs = extractor.extract({
            "CERTIFICATIONS": (
                "AWS Certified Solutions Architect – Associate  (Amazon Web Services, 2022)\\n"
                "Certified Kubernetes Application Developer – CKAD  (CNCF, 2023)"
            )
        })
        # [
        #   "AWS Certified Solutions Architect – Associate  (Amazon Web Services, 2022)",
        #   "Certified Kubernetes Application Developer – CKAD  (CNCF, 2023)"
        # ]
    """

    def extract(self, sections: dict[str, str]) -> list[str]:
        """Parse certification strings from the CERTIFICATIONS section.

        Checks ``sections["CERTIFICATIONS"]`` first, then falls back to
        ``sections["CERTIFICATIONS AND LICENSES"]`` when the former is absent.

        Args:
            sections: Dict mapping normalized section header strings to their
                raw body text, as returned by
                :class:`~app.parsers.resume_parser.ResumeParser`.

        Returns:
            Deduplicated list of certification strings in order of first
            appearance.  Returns ``[]`` when neither section is present or
            both are empty.
        """
        cert_text: str = sections.get("CERTIFICATIONS", "") or sections.get(
            "CERTIFICATIONS AND LICENSES", ""
        )
        if not cert_text.strip():
            return []

        seen: set[str] = set()
        result: list[str] = []

        for line in cert_text.splitlines():
            # Strip leading bullet markers and surrounding whitespace
            cleaned: str = _LEADING_BULLET_RE.sub("", line).strip()

            # Skip empty lines and pure separator lines
            if not cleaned or re.match(r"^[-–—=]+$", cleaned):
                continue

            if cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)

        return result
