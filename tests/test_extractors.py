"""Unit tests for all field extractor classes.

Tests are self-contained: all section dicts are constructed from inline
strings derived from the sample resume at ``data/input/resume.txt``.  No
file I/O is performed in any test.

Run with::

    pytest tests/test_extractors.py -v
"""

import pytest

from app.extractors.certification_extractor import CertificationExtractor
from app.extractors.education_extractor import EducationExtractor
from app.extractors.email_extractor import EmailExtractor
from app.extractors.experience_extractor import ExperienceExtractor
from app.extractors.phone_extractor import PhoneExtractor
from app.extractors.skill_extractor import SkillExtractor

# ---------------------------------------------------------------------------
# Shared sample sections (derived from resume.txt)
# ---------------------------------------------------------------------------

SAMPLE_HEADER = (
    "Jane Doe\n"
    "San Francisco, CA  |  jane.doe@example.com  |  (415) 555-0192\n"
    "linkedin.com/in/janedoe  |  github.com/janedoe"
)

SAMPLE_EXPERIENCE = (
    "Senior Software Engineer — Acme Corp\n"
    "March 2021 – Present\n"
    "- Led backend development of microservices architecture using Python and Django.\n"
    "- Reduced API latency by 40% through query optimization and Redis caching.\n"
    "\n"
    "Software Engineer — Beta Solutions\n"
    "June 2018 – February 2021\n"
    "- Designed and maintained RESTful APIs consumed by web and mobile clients.\n"
    "- Managed Postgres databases; wrote complex analytical queries and migrations."
)

SAMPLE_EDUCATION = (
    "University of California, Berkeley\n"
    "B.S. Computer Science\n"
    "August 2014 – May 2018\n"
    "Relevant coursework: Data Structures, Operating Systems, Distributed Systems"
)

SAMPLE_SKILLS = (
    "Languages:    Python, JavaScript, SQL, Bash\n"
    "Frameworks:   Django, Flask, React\n"
    "Databases:    PostgreSQL, Redis, SQLite\n"
    "DevOps:       Docker, AWS (EC2, S3, ECS), GitHub Actions, Terraform\n"
    "Other:        REST APIs, GraphQL, Agile/Scrum, System Design"
)

SAMPLE_CERTIFICATIONS = (
    "AWS Certified Solutions Architect – Associate  (Amazon Web Services, 2022)\n"
    "Certified Kubernetes Application Developer – CKAD  (CNCF, 2023)"
)


# ---------------------------------------------------------------------------
# TestEmailExtractor
# ---------------------------------------------------------------------------


class TestEmailExtractor:
    """Tests for :class:`~app.extractors.email_extractor.EmailExtractor`."""

    def test_extracts_email_from_header(self) -> None:
        """An email present in the HEADER section is returned in the list."""
        extractor = EmailExtractor()
        sections = {"HEADER": SAMPLE_HEADER}
        result = extractor.extract(sections)

        assert "jane.doe@example.com" in result

    def test_email_is_lowercased(self) -> None:
        """Emails are lowercased regardless of source capitalisation."""
        extractor = EmailExtractor()
        sections = {"HEADER": "Contact: Jane.DOE@Example.COM"}
        result = extractor.extract(sections)

        assert result == ["jane.doe@example.com"]

    def test_no_emails_returns_empty_list(self) -> None:
        """When no email is present, an empty list is returned."""
        extractor = EmailExtractor()
        sections = {"HEADER": "Jane Doe, San Francisco, CA"}
        result = extractor.extract(sections)

        assert result == []

    def test_deduplicates_emails(self) -> None:
        """The same email address appearing twice is returned only once."""
        extractor = EmailExtractor()
        sections = {
            "HEADER": "jane.doe@example.com",
            "SKILLS": "contact: jane.doe@example.com",
        }
        result = extractor.extract(sections)

        assert result.count("jane.doe@example.com") == 1

    def test_empty_sections_returns_empty_list(self) -> None:
        """An empty sections dict returns an empty list without error."""
        extractor = EmailExtractor()
        result = extractor.extract({})

        assert result == []


# ---------------------------------------------------------------------------
# TestPhoneExtractor
# ---------------------------------------------------------------------------


class TestPhoneExtractor:
    """Tests for :class:`~app.extractors.phone_extractor.PhoneExtractor`."""

    def test_extracts_phone_from_header(self) -> None:
        """A phone number present in the HEADER section is returned."""
        extractor = PhoneExtractor()
        sections = {"HEADER": SAMPLE_HEADER}
        result = extractor.extract(sections)

        assert len(result) >= 1
        assert any("415" in p for p in result)

    def test_no_phones_returns_empty_list(self) -> None:
        """When no phone is present, an empty list is returned."""
        extractor = PhoneExtractor()
        sections = {"HEADER": "Jane Doe  jane.doe@example.com"}
        result = extractor.extract(sections)

        assert result == []

    def test_missing_header_returns_empty_list(self) -> None:
        """When the HEADER key is absent, an empty list is returned."""
        extractor = PhoneExtractor()
        sections = {"SKILLS": "Python, SQL"}
        result = extractor.extract(sections)

        assert result == []

    def test_deduplicates_phones(self) -> None:
        """The same phone number appearing twice is returned only once."""
        extractor = PhoneExtractor()
        sections = {"HEADER": "(415) 555-0192  |  (415) 555-0192"}
        result = extractor.extract(sections)

        # There should be at most one distinct match for the duplicate number
        assert len(result) == len(set(result))


# ---------------------------------------------------------------------------
# TestSkillExtractor
# ---------------------------------------------------------------------------


class TestSkillExtractor:
    """Tests for :class:`~app.extractors.skill_extractor.SkillExtractor`."""

    def test_extracts_skills_from_section(self) -> None:
        """Common skills from the SKILLS section are returned."""
        extractor = SkillExtractor()
        sections = {"SKILLS": SAMPLE_SKILLS}
        result = extractor.extract(sections)

        assert "Python" in result
        assert "Django" in result
        assert "SQL" in result

    def test_strips_label_prefixes(self) -> None:
        """Category labels like 'Languages:' are stripped from skill tokens."""
        extractor = SkillExtractor()
        sections = {"SKILLS": "Languages:    Python, SQL"}
        result = extractor.extract(sections)

        assert "Languages" not in result
        assert "Python" in result
        assert "SQL" in result

    def test_empty_section_returns_empty_list(self) -> None:
        """An absent or empty SKILLS section returns an empty list."""
        extractor = SkillExtractor()
        assert extractor.extract({}) == []
        assert extractor.extract({"SKILLS": ""}) == []

    def test_deduplicates_skills(self) -> None:
        """Duplicate skill tokens are returned only once."""
        extractor = SkillExtractor()
        sections = {"SKILLS": "Python, Python, SQL"}
        result = extractor.extract(sections)

        assert result.count("Python") == 1


# ---------------------------------------------------------------------------
# TestEducationExtractor
# ---------------------------------------------------------------------------


class TestEducationExtractor:
    """Tests for :class:`~app.extractors.education_extractor.EducationExtractor`."""

    def test_extracts_institution(self) -> None:
        """The institution name is extracted as the first non-blank line."""
        extractor = EducationExtractor()
        sections = {"EDUCATION": SAMPLE_EDUCATION}
        result = extractor.extract(sections)

        assert len(result) >= 1
        assert result[0]["institution"] == "University of California, Berkeley"

    def test_extracts_degree(self) -> None:
        """The degree string is extracted correctly."""
        extractor = EducationExtractor()
        sections = {"EDUCATION": SAMPLE_EDUCATION}
        result = extractor.extract(sections)

        assert result[0]["degree"] == "B.S. Computer Science"

    def test_extracts_dates(self) -> None:
        """Start and end dates are extracted from the education block."""
        extractor = EducationExtractor()
        sections = {"EDUCATION": SAMPLE_EDUCATION}
        result = extractor.extract(sections)

        assert result[0]["start_date"] == "August 2014"
        assert result[0]["end_date"] == "May 2018"

    def test_empty_section_returns_empty_list(self) -> None:
        """An absent or empty EDUCATION section returns an empty list."""
        extractor = EducationExtractor()
        assert extractor.extract({}) == []
        assert extractor.extract({"EDUCATION": ""}) == []

    def test_field_of_study_is_none(self) -> None:
        """field_of_study is None at extraction stage (set by normalizer later)."""
        extractor = EducationExtractor()
        sections = {"EDUCATION": SAMPLE_EDUCATION}
        result = extractor.extract(sections)

        assert result[0]["field_of_study"] is None


# ---------------------------------------------------------------------------
# TestExperienceExtractor
# ---------------------------------------------------------------------------


class TestExperienceExtractor:
    """Tests for :class:`~app.extractors.experience_extractor.ExperienceExtractor`."""

    def test_extracts_title_and_company(self) -> None:
        """Job title and company are split correctly from the heading line."""
        extractor = ExperienceExtractor()
        sections = {"EXPERIENCE": SAMPLE_EXPERIENCE}
        result = extractor.extract(sections)

        titles = [r["title"] for r in result]
        companies = [r["company"] for r in result]

        assert "Senior Software Engineer" in titles
        assert "Acme Corp" in companies

    def test_extracts_multiple_roles(self) -> None:
        """Multiple experience blocks are all extracted."""
        extractor = ExperienceExtractor()
        sections = {"EXPERIENCE": SAMPLE_EXPERIENCE}
        result = extractor.extract(sections)

        assert len(result) >= 2

    def test_extracts_dates(self) -> None:
        """Start and end dates are extracted from experience blocks."""
        extractor = ExperienceExtractor()
        sections = {"EXPERIENCE": SAMPLE_EXPERIENCE}
        result = extractor.extract(sections)

        dates = [(r["start_date"], r["end_date"]) for r in result]
        assert ("March 2021", "Present") in dates

    def test_extracts_bullets(self) -> None:
        """Bullet points are extracted into the bullets list."""
        extractor = ExperienceExtractor()
        sections = {"EXPERIENCE": SAMPLE_EXPERIENCE}
        result = extractor.extract(sections)

        # At least one role should have bullets
        all_bullets = [b for r in result for b in r["bullets"]]
        assert len(all_bullets) > 0

    def test_empty_section_returns_empty_list(self) -> None:
        """An absent or empty EXPERIENCE section returns an empty list."""
        extractor = ExperienceExtractor()
        assert extractor.extract({}) == []
        assert extractor.extract({"EXPERIENCE": ""}) == []

    def test_falls_back_to_work_experience_key(self) -> None:
        """The extractor falls back to 'WORK EXPERIENCE' when 'EXPERIENCE' is absent."""
        extractor = ExperienceExtractor()
        sections = {
            "WORK EXPERIENCE": (
                "Engineer — Example Co\n"
                "January 2020 – December 2022\n"
                "- Built things."
            )
        }
        result = extractor.extract(sections)

        assert len(result) == 1
        assert result[0]["title"] == "Engineer"
        assert result[0]["company"] == "Example Co"


# ---------------------------------------------------------------------------
# TestCertificationExtractor
# ---------------------------------------------------------------------------


class TestCertificationExtractor:
    """Tests for :class:`~app.extractors.certification_extractor.CertificationExtractor`."""

    def test_extracts_certifications(self) -> None:
        """Certification strings are extracted as individual list entries."""
        extractor = CertificationExtractor()
        sections = {"CERTIFICATIONS": SAMPLE_CERTIFICATIONS}
        result = extractor.extract(sections)

        assert len(result) == 2
        assert any("AWS" in c for c in result)
        assert any("CKAD" in c for c in result)

    def test_strips_leading_bullets(self) -> None:
        """Leading bullet characters are stripped from each certification line."""
        extractor = CertificationExtractor()
        sections = {"CERTIFICATIONS": "- AWS Certified Developer\n• Google Cloud Professional"}
        result = extractor.extract(sections)

        assert "AWS Certified Developer" in result
        assert "Google Cloud Professional" in result

    def test_deduplicates_certifications(self) -> None:
        """Duplicate certification strings are returned only once."""
        extractor = CertificationExtractor()
        sections = {
            "CERTIFICATIONS": (
                "AWS Certified Solutions Architect\n"
                "AWS Certified Solutions Architect"
            )
        }
        result = extractor.extract(sections)

        assert result.count("AWS Certified Solutions Architect") == 1

    def test_empty_section_returns_empty_list(self) -> None:
        """An absent or empty CERTIFICATIONS section returns an empty list."""
        extractor = CertificationExtractor()
        assert extractor.extract({}) == []
        assert extractor.extract({"CERTIFICATIONS": ""}) == []

    def test_falls_back_to_certifications_and_licenses_key(self) -> None:
        """Falls back to 'CERTIFICATIONS AND LICENSES' key when primary key is absent."""
        extractor = CertificationExtractor()
        sections = {"CERTIFICATIONS AND LICENSES": "PMP Certified"}
        result = extractor.extract(sections)

        assert "PMP Certified" in result
