"""Unit tests for ResumeParser section splitting.

Tests are self-contained: all input text is constructed from inline strings
derived from the sample resume at ``data/input/resume.txt``.  No file I/O is
performed in any test.

Run with::

    pytest tests/test_resume_parser.py -v
"""

import pytest

from app.parsers.resume_parser import ResumeParser


# ---------------------------------------------------------------------------
# Inline sample resume text (mirrors data/input/resume.txt)
# ---------------------------------------------------------------------------

SAMPLE_RESUME = (
    "Jane Doe\n"
    "San Francisco, CA  |  jane.doe@example.com  |  (415) 555-0192\n"
    "linkedin.com/in/janedoe  |  github.com/janedoe\n"
    "\n"
    "---\n"
    "\n"
    "EXPERIENCE\n"
    "\n"
    "Senior Software Engineer — Acme Corp\n"
    "March 2021 – Present\n"
    "- Led backend development of microservices architecture using py and Django framework.\n"
    "- Reduced API latency by 40% through query optimization and Redis caching.\n"
    "\n"
    "Software Engineer — Beta Solutions\n"
    "June 2018 – February 2021\n"
    "- Designed and maintained RESTful APIs consumed by web and mobile clients.\n"
    "- Managed Postgres databases; wrote complex analytical queries and migrations.\n"
    "\n"
    "---\n"
    "\n"
    "EDUCATION\n"
    "\n"
    "University of California, Berkeley\n"
    "B.S. Computer Science\n"
    "August 2014 – May 2018\n"
    "\n"
    "---\n"
    "\n"
    "SKILLS\n"
    "\n"
    "Languages:    py, js, SQL, Bash\n"
    "Frameworks:   Django, Flask, React\n"
    "Databases:    Postgres, Redis, SQLite\n"
    "DevOps:       Docker, AWS (EC2, S3, ECS), GitHub Actions, Terraform\n"
    "\n"
    "---\n"
    "\n"
    "CERTIFICATIONS\n"
    "\n"
    "AWS Certified Solutions Architect – Associate  (Amazon Web Services, 2022)\n"
    "Certified Kubernetes Application Developer – CKAD  (CNCF, 2023)\n"
)


class TestResumeParseSections:
    """Tests for ``ResumeParser.parse`` section splitting behaviour.

    Each test verifies a single, clearly-named invariant so failures are
    immediately actionable.  All tests operate on a single shared
    ``SAMPLE_RESUME`` inline string that mirrors the content of
    ``data/input/resume.txt``.
    """

    def test_header_section_exists(self) -> None:
        """The parsed result must always contain a 'HEADER' key.

        The ``ResumeParser`` designates any text before the first recognized
        section header as the ``HEADER`` section.  Even when no named headers
        are detected, ``parse`` must return a dict with the ``"HEADER"`` key.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "HEADER" in sections

    def test_experience_section_detected(self) -> None:
        """An 'EXPERIENCE' key must be present when the resume contains that header.

        Validates that the line-by-line header detection recognises the
        ``EXPERIENCE`` keyword and stores subsequent text under that key.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "EXPERIENCE" in sections

    def test_education_section_detected(self) -> None:
        """An 'EDUCATION' key must be present when the resume contains that header.

        Validates that the ``EDUCATION`` keyword is recognized as a section
        boundary and its content is stored correctly.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "EDUCATION" in sections

    def test_skills_section_detected(self) -> None:
        """A 'SKILLS' key must be present when the resume contains that header.

        Validates that the ``SKILLS`` keyword starts a new section and its
        content (skill lines) is captured under the ``"SKILLS"`` key.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "SKILLS" in sections

    def test_certifications_section_detected(self) -> None:
        """A 'CERTIFICATIONS' key must be present when the resume contains that header.

        Validates that ``CERTIFICATIONS`` (and its canonical normalized form)
        is recognized as a section boundary.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "CERTIFICATIONS" in sections

    def test_header_contains_name(self) -> None:
        """The HEADER section text must contain 'Jane Doe'.

        The candidate's name appears before any recognized section header, so
        it should be captured in the ``HEADER`` section value.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "Jane Doe" in sections["HEADER"]

    def test_experience_contains_company(self) -> None:
        """The EXPERIENCE section text must contain 'Acme Corp'.

        Validates that the body text following the EXPERIENCE header (including
        job titles and company names) is captured correctly.
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        assert "Acme Corp" in sections["EXPERIENCE"]

    def test_skills_contains_skill(self) -> None:
        """The SKILLS section text must contain 'Python' or 'py'.

        The sample resume lists 'py' (an abbreviation for Python) in the
        SKILLS section.  The parser should include this raw token in the
        section text without any aliasing (aliasing is done by extractors).
        """
        parser = ResumeParser()
        sections = parser.parse(SAMPLE_RESUME)
        skills_text = sections["SKILLS"].lower()
        assert "python" in skills_text or "py" in skills_text

    def test_empty_text(self) -> None:
        """Parsing an empty string must return exactly {'HEADER': ''}.

        When the input is an empty string, the parser must return a minimal
        dict with the ``HEADER`` key set to an empty string and no other keys.
        """
        parser = ResumeParser()
        result = parser.parse("")
        assert result == {"HEADER": ""}

    def test_whitespace_only(self) -> None:
        """Parsing a whitespace-only string must return exactly {'HEADER': ''}.

        Strings containing only spaces, tabs, or newlines have no meaningful
        content.  The parser must treat them the same as an empty string and
        return ``{"HEADER": ""}``.
        """
        parser = ResumeParser()
        result = parser.parse("   ")
        assert result == {"HEADER": ""}
