"""Pydantic model for a single work-experience record in the canonical candidate profile."""

from pydantic import BaseModel, ConfigDict, Field


class Experience(BaseModel):
    """Represents one position held by the candidate.

    Instances are produced by ``experience_extractor.py`` from resume text
    and/or the ATS JSON, then merged by the merge engine (duplicate roles from
    different sources are reconciled into the most-complete entry) before being
    stored in ``Candidate.experience``.
    """

    model_config = ConfigDict(extra="forbid")

    title: str = Field(
        description="Job title or role name, e.g. 'Senior Software Engineer'."
    )
    company: str = Field(
        description="Name of the employer or client organisation."
    )
    start_date: str | None = Field(
        default=None,
        description=(
            "Role start date in YYYY-MM format after normalization. "
            "None when the source did not include a start date."
        ),
    )
    end_date: str | None = Field(
        default=None,
        description=(
            "Role end date in YYYY-MM format. "
            "None when this is the candidate's current position."
        ),
    )
    description: str | None = Field(
        default=None,
        description=(
            "Free-form prose summary of responsibilities and achievements. "
            "None when only bullet points were extracted."
        ),
    )
    bullets: list[str] = Field(
        default_factory=list,
        description=(
            "Individual achievement or responsibility bullet points. "
            "When the same role appears in multiple sources their bullet lists "
            "are merged and deduplicated by the merge engine."
        ),
    )
