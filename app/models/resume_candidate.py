"""Pydantic model for raw resume-extracted data before normalization.

This module defines ``ResumeCandidate``, a permissive schema that holds
everything extracted directly from resume text by the reader and extractor
stages.  No normalization has been applied at this point; values are raw
strings as they appeared in the source document.

The model uses ``extra="ignore"`` so that experimental extractor fields
added during development do not cause validation errors in downstream code
that imports an older version of this schema.
"""

from pydantic import BaseModel, ConfigDict, Field


class ResumeCandidate(BaseModel):
    """Intermediate model carrying raw data extracted from a resume document.

    Produced by the extractor layer (email, phone, skill, education, experience,
    and certification extractors) after ``ResumeReader`` has pulled plain text
    from a ``.txt`` or PDF file and ``ResumeParser`` has split it into labeled
    sections.

    This model is *not* the final output; it feeds into the normalizer and
    merge stages that produce the canonical ``Candidate`` record.

    All fields are optional with sensible defaults so that a partially-parsed
    resume does not raise validation errors.
    """

    model_config = ConfigDict(extra="ignore")

    raw_text: str = Field(
        default="",
        description=(
            "Full raw text extracted from the resume document. "
            "Used as a fallback source for any extractor that needs "
            "the unstructured full text rather than a specific section."
        ),
    )
    emails: list[str] = Field(
        default_factory=list,
        description=(
            "Email addresses found anywhere in the resume. "
            "Raw strings as matched; lowercasing and RFC-5322 validation "
            "are applied later in the normalizer stage."
        ),
    )
    phones: list[str] = Field(
        default_factory=list,
        description=(
            "Phone number strings found in the resume header / contact block. "
            "Raw format; E.164 normalization is applied in ``normalizers/phone.py``."
        ),
    )
    skills: list[str] = Field(
        default_factory=list,
        description=(
            "Skill tokens extracted from the SKILLS section of the resume. "
            "May include abbreviations (e.g. 'py', 'js'); canonical mapping "
            "is applied in ``normalizers/skills.py`` using ``SKILL_ALIASES``."
        ),
    )
    experience: list[dict] = Field(
        default_factory=list,
        description=(
            "List of raw work-experience dicts, each containing keys: "
            "``title``, ``company``, ``start_date``, ``end_date``, "
            "``description``, ``bullets``.  Dates are raw strings; "
            "normalization to YYYY-MM format happens downstream."
        ),
    )
    education: list[dict] = Field(
        default_factory=list,
        description=(
            "List of raw education dicts, each containing keys: "
            "``institution``, ``degree``, ``field_of_study``, "
            "``start_date``, ``end_date``.  Dates are raw strings."
        ),
    )
    certifications: list[str] = Field(
        default_factory=list,
        description=(
            "Certification and licence strings extracted from the "
            "CERTIFICATIONS section.  Raw text; deduplication applied "
            "in the merge stage."
        ),
    )
    links: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of inferred link type to URL found in the resume, "
            "e.g. ``{'linkedin': 'linkedin.com/in/...', 'github': 'github.com/...'}``."
        ),
    )
    location: dict[str, str | None] | None = Field(
        default=None,
        description=(
            "Structured location with keys ``city``, ``state``, ``country`` "
            "parsed from the contact / header block of the resume. "
            "None when no location information could be found."
        ),
    )
    headline: str | None = Field(
        default=None,
        description=(
            "First non-empty, non-contact-info line from the resume header "
            "that appears to be a professional title or summary. "
            "None when not identifiable."
        ),
    )
