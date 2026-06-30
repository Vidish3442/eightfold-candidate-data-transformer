"""Pydantic model for the canonical candidate profile produced by the pipeline."""

from pydantic import BaseModel, ConfigDict, Field

from app.models.education import Education
from app.models.experience import Experience
from app.models.provenance import ProvenanceEntry


class Candidate(BaseModel):
    """The single, unified candidate record emitted by the merge stage.

    All upstream source data (ATS JSON, resume) has been normalised, matched,
    and merged into this model before it is validated, projected through the
    runtime config, and written to ``data/output/canonical_profile.json``.

    Field-level provenance and confidence metadata are carried inline so the
    output file is self-documenting and auditable without any secondary files.
    """

    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(
        description=(
            "Stable unique identifier for the candidate. "
            "Taken from the ATS record when present; otherwise generated."
        )
    )
    full_name: str = Field(
        description="Candidate's full legal name after normalization (title-cased)."
    )
    emails: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated list of email addresses collected across all sources. "
            "Lower-cased and RFC-5322 validated."
        ),
    )
    phones: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated list of phone numbers in E.164 format "
            "(e.g. '+14155552671'), normalised via the ``phonenumbers`` library."
        ),
    )
    location: dict[str, str | None] = Field(
        default_factory=dict,
        description=(
            "Structured location with keys 'city', 'state', and 'country'. "
            "Country is stored as an ISO 3166-1 alpha-2 code where resolvable. "
            "Any key may be None when the source data was incomplete."
        ),
    )
    links: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Map of link type to URL, e.g. "
            "{'linkedin': 'https://linkedin.com/in/...', 'github': 'https://github.com/...'}."
        ),
    )
    headline: str | None = Field(
        default=None,
        description=(
            "Short professional summary or title line extracted from the resume "
            "or ATS profile. None when not available in any source."
        ),
    )
    years_experience: float | None = Field(
        default=None,
        description=(
            "Total years of professional experience computed from the experience "
            "entries' date ranges. None when dates are insufficient to calculate."
        ),
    )
    skills: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated list of canonical skill names after mapping "
            "(e.g. 'py' → 'Python'). Union of all sources."
        ),
    )
    experience: list[Experience] = Field(
        default_factory=list,
        description=(
            "Chronologically ordered work-experience entries, most recent first. "
            "Duplicate roles across sources are merged into the most complete entry."
        ),
    )
    education: list[Education] = Field(
        default_factory=list,
        description=(
            "Education records from all sources, deduplicated by "
            "institution + degree and merged to retain the most complete data."
        ),
    )
    certifications: list[str] = Field(
        default_factory=list,
        description=(
            "Deduplicated list of professional certifications and licences "
            "extracted from resume text and/or the ATS record."
        ),
    )
    provenance: list[ProvenanceEntry] = Field(
        default_factory=list,
        description=(
            "One entry per canonical field describing which source(s) contributed "
            "the value and why the winning source was chosen. "
            "May be omitted from projected output when include_provenance=false."
        ),
    )
    overall_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description=(
            "Weighted average of all field-level confidence scores. "
            "Fields with higher business importance (name, email) carry more weight. "
            "Range [0.0, 1.0]; 0.0 indicates no data could be reliably extracted."
        ),
    )
