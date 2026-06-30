"""Pydantic model for a single education record in the canonical candidate profile."""

from pydantic import BaseModel, ConfigDict, Field


class Education(BaseModel):
    """Represents one completed or ongoing educational qualification.

    Instances are produced by ``education_extractor.py`` from resume text
    and/or the ATS JSON, then merged by the merge engine before being stored
    in ``Candidate.education``.
    """

    model_config = ConfigDict(extra="forbid")

    institution: str = Field(
        description="Name of the school, university, or training provider."
    )
    degree: str = Field(
        description=(
            "Degree or credential awarded, e.g. 'B.Sc. Computer Science' "
            "or 'AWS Certified Developer'."
        )
    )
    field_of_study: str | None = Field(
        default=None,
        description=(
            "Major, concentration, or area of study. "
            "None when not specified in the source data."
        ),
    )
    start_date: str | None = Field(
        default=None,
        description=(
            "Enrolment start date in YYYY-MM format after normalization. "
            "None when the source did not include a start date."
        ),
    )
    end_date: str | None = Field(
        default=None,
        description=(
            "Graduation or completion date in YYYY-MM format. "
            "None when the programme is ongoing or the date is unknown."
        ),
    )
