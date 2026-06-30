"""Raw ATS candidate model — mirrors the shape of ``data/input/ats.json``.

This module defines the Pydantic models that represent what comes directly out
of an Applicant Tracking System export, *before* any normalization takes place.
The models are deliberately permissive (``extra="ignore"``) because real ATS
integrations routinely include undocumented vendor-specific fields that we do
not need and should not error on.

All fields except ``candidate_id`` are optional (``None`` default) because any
individual field may be absent in a real-world ATS export — the pipeline must
tolerate missing data gracefully and apply ``missing_policy`` as configured.
"""

from pydantic import BaseModel, ConfigDict, Field


class ATSExperience(BaseModel):
    """One work-experience entry as it arrives from the ATS.

    Dates and descriptions are kept as raw strings here; normalization to
    ``YYYY-MM`` dates and canonical ``Experience`` objects happens downstream
    in the extractor/normalizer stages.
    """

    model_config = ConfigDict(extra="ignore")

    title: str | None = Field(
        default=None,
        description="Job title or role name as supplied by the ATS, e.g. 'Senior Software Engineer'.",
    )
    company: str | None = Field(
        default=None,
        description="Name of the employer or client organisation as supplied by the ATS.",
    )
    start_date: str | None = Field(
        default=None,
        description=(
            "Role start date as a raw string from the ATS (e.g. '2021-03', 'March 2021'). "
            "Not yet normalized to YYYY-MM at this stage."
        ),
    )
    end_date: str | None = Field(
        default=None,
        description=(
            "Role end date as a raw string from the ATS. "
            "None when this is the candidate's current position or the field was omitted."
        ),
    )
    description: str | None = Field(
        default=None,
        description=(
            "Free-form prose summary of responsibilities and achievements as stored in the ATS. "
            "None when the ATS did not include a description for this role."
        ),
    )


class ATSEducation(BaseModel):
    """One education record as it arrives from the ATS.

    Fields are kept as raw strings; normalization and deduplication happen
    downstream in the extractor/normalizer stages before merging into the
    canonical ``Education`` model.
    """

    model_config = ConfigDict(extra="ignore")

    institution: str | None = Field(
        default=None,
        description="Name of the school, university, or training provider as supplied by the ATS.",
    )
    degree: str | None = Field(
        default=None,
        description=(
            "Degree or credential as supplied by the ATS, "
            "e.g. 'B.S. Computer Science' or 'AWS Certified Developer'."
        ),
    )
    field_of_study: str | None = Field(
        default=None,
        description=(
            "Major, concentration, or area of study. "
            "None when not specified in the ATS record."
        ),
    )
    start_date: str | None = Field(
        default=None,
        description=(
            "Enrolment start date as a raw string from the ATS. "
            "Not yet normalized to YYYY-MM at this stage."
        ),
    )
    end_date: str | None = Field(
        default=None,
        description=(
            "Graduation or completion date as a raw string from the ATS. "
            "None when the programme is ongoing or the date was omitted."
        ),
    )


class ATSCandidate(BaseModel):
    """Raw candidate record parsed directly from an ATS JSON export.

    This model mirrors the shape of ``data/input/ats.json`` and is produced by
    ``ats_reader.py``.  It intentionally stays close to the source format so
    that source-specific quirks are isolated here rather than leaking into the
    canonical ``Candidate`` schema.

    ``extra="ignore"`` ensures the model tolerates the undocumented vendor
    fields that many ATS platforms append without warning.  All fields except
    ``candidate_id`` are optional because any of them may be absent in a
    real-world export; the pipeline will fall back to resume data or apply the
    configured ``missing_policy`` for each absent field.
    """

    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(
        description=(
            "Stable unique identifier assigned by the ATS (e.g. 'ATS-001'). "
            "Required — used as the primary key when matching the ATS record "
            "to the resume and when constructing the canonical candidate_id."
        )
    )
    full_name: str | None = Field(
        default=None,
        description="Candidate's full name as stored in the ATS. Not yet normalized to title case.",
    )
    email: str | None = Field(
        default=None,
        description=(
            "Single email address as stored in the ATS. "
            "Not yet lower-cased or RFC-5322 validated at this stage."
        ),
    )
    phone: str | None = Field(
        default=None,
        description=(
            "Raw phone string as stored in the ATS (e.g. '+1-415-555-0192'). "
            "May not yet be in E.164 format; normalization happens in ``normalizers/phone.py``."
        ),
    )
    status: str | None = Field(
        default=None,
        description=(
            "Candidate pipeline status as recorded in the ATS "
            "(e.g. 'interviewing', 'applied', 'offer'). "
            "Informational only — not mapped into the canonical schema."
        ),
    )
    headline: str | None = Field(
        default=None,
        description=(
            "Short professional summary or title line from the ATS profile, "
            "e.g. 'Senior Software Engineer'. None when absent."
        ),
    )
    years_experience: float | None = Field(
        default=None,
        description=(
            "Years of professional experience as declared in or computed by the ATS. "
            "None when the ATS did not supply this value."
        ),
    )
    location: dict[str, str | None] | None = Field(
        default=None,
        description=(
            "Structured location dict with keys such as 'city', 'state', and 'country' "
            "as returned by the ATS.  Values are raw strings, not yet normalized to "
            "ISO codes.  None when the ATS omitted location entirely."
        ),
    )
    links: dict[str, str] | None = Field(
        default=None,
        description=(
            "Map of link type to URL as stored in the ATS "
            "(e.g. {'linkedin': 'https://...', 'github': 'https://...'}). "
            "None when the ATS included no profile links."
        ),
    )
    skills: list[str] | None = Field(
        default=None,
        description=(
            "List of skill strings as stored in the ATS. "
            "May include abbreviations or non-canonical names; "
            "normalization and deduplication happen in ``normalizers/skills.py``. "
            "None when the ATS omitted the skills section."
        ),
    )
    experience: list[ATSExperience] | None = Field(
        default=None,
        description=(
            "Ordered list of work-experience entries from the ATS, "
            "each modelled as ``ATSExperience``. "
            "None when the ATS omitted the experience section."
        ),
    )
    education: list[ATSEducation] | None = Field(
        default=None,
        description=(
            "List of education records from the ATS, "
            "each modelled as ``ATSEducation``. "
            "None when the ATS omitted the education section."
        ),
    )
