"""Skill token extractor for parsed resume sections.

Parses the SKILLS section of a resume and returns individual skill tokens.
Label prefixes such as "Languages:", "Frameworks:", "DevOps:" are stripped
before tokenization.  Bare category header lines (single words like
"Programming", "AI/ML", "Core CS") are also discarded.  Skills are split on
commas, newlines, pipes, and tabs.

Normalization (e.g. ``"py"`` → ``"Python"``) is *not* performed here; that
is handled by ``normalizers/skills.py`` using :data:`~app.constants.skills.SKILL_ALIASES`.
"""

import re

# Matches label prefixes with a colon: "Languages:  ", "Frameworks:  " etc.
_LABEL_PREFIX_RE: re.Pattern[str] = re.compile(r"^[A-Za-z0-9 /&]+:\s*")

# Bare category-header lines: one or two words, possibly with "/" or "&",
# no digits, no special chars — these are section sub-headers, not skills.
# Examples: "Programming", "AI/ML", "Core CS", "Other", "Web", "Data"
_CATEGORY_ONLY_RE: re.Pattern[str] = re.compile(
    r"^[A-Za-z][A-Za-z0-9 /&]*$"
)

# Skill tokens that are actually category labels (common ones to filter)
_CATEGORY_LABELS: frozenset[str] = frozenset({
    "programming", "ai/ml", "data", "web", "core cs", "other",
    "languages", "frameworks", "databases", "devops", "tools",
    "soft skills", "skills", "technical", "technologies",
})


class SkillExtractor:
    """Extracts raw skill tokens from the SKILLS section of a parsed resume.

    Splits skill text on commas, newlines, pipes, and tabs after stripping
    category labels.  Tokens shorter than 2 characters and empty strings are
    discarded.  Order of first occurrence is preserved; duplicates are removed.

    Example usage::

        extractor = SkillExtractor()
        skills = extractor.extract({
            "SKILLS": "Languages:    Python, SQL\\nFrameworks:   Django, Flask"
        })
        # ["Python", "SQL", "Django", "Flask"]
    """

    def extract(self, sections: dict[str, str]) -> list[str]:
        """Parse and return skill tokens from the SKILLS section.

        For each line in the SKILLS section:
        1. Skip separator lines (``---``, ``===``, etc.).
        2. Strip any label prefix with a colon (e.g. ``"Languages:  "``).
        3. Skip bare category-header lines (single/two-word labels with no
           punctuation, e.g. ``"Programming"``, ``"AI/ML"``, ``"Core CS"``).
        4. Split the remainder on ``,``, ``|``, ``\\t``.
        5. Strip whitespace from each token.
        6. Discard tokens that are empty, shorter than 2 characters, or are
           known category labels.
        7. Deduplicate while preserving order of first occurrence.

        Args:
            sections: Dict mapping normalized section header strings to their
                raw body text, as returned by
                :class:`~app.parsers.resume_parser.ResumeParser`.

        Returns:
            Deduplicated list of skill token strings in order of first
            appearance.  Returns ``[]`` when the SKILLS section is absent
            or empty.
        """
        skills_text: str = sections.get("SKILLS", "")
        if not skills_text.strip():
            return []

        seen: set[str] = set()
        result: list[str] = []

        for line in skills_text.splitlines():
            stripped_line = line.strip()

            # Skip separator / ruler lines
            if re.match(r"^[-–—=*#]+$", stripped_line):
                continue

            # Strip label prefix with colon ("Languages:  ", etc.)
            cleaned_line = _LABEL_PREFIX_RE.sub("", stripped_line).strip()

            # Skip bare category-header lines (whole line is just a label)
            if _CATEGORY_ONLY_RE.match(cleaned_line) and cleaned_line.lower() in _CATEGORY_LABELS:
                continue

            # Split on comma, pipe, and tab
            tokens = re.split(r"[,|\t]", cleaned_line)

            for token in tokens:
                token = token.strip()
                if len(token) < 2:
                    continue
                # Skip if this token is itself a category label
                if token.lower() in _CATEGORY_LABELS:
                    continue
                if token not in seen:
                    seen.add(token)
                    result.append(token)

        return result
