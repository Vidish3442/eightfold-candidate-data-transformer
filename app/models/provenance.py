"""Pydantic model for provenance metadata attached to each field in the canonical profile."""

from pydantic import BaseModel, ConfigDict, Field


class ProvenanceEntry(BaseModel):
    """Records which source(s) contributed a canonical field and how confident we are.

    One ``ProvenanceEntry`` is created per canonical field by the provenance
    tracker (``provenance/tracker.py``) during the merge stage.  The full list
    is stored in ``Candidate.provenance`` so downstream consumers can audit
    every merge decision without re-running the pipeline.
    """

    model_config = ConfigDict(extra="forbid")

    field: str = Field(
        description=(
            "Canonical field name this entry describes, "
            "e.g. 'full_name', 'emails', 'skills'."
        )
    )
    sources: list[str] = Field(
        description=(
            "All source identifiers that provided a value for this field, "
            "e.g. ['ats', 'resume'].  Order is not significant."
        )
    )
    winning_source: str = Field(
        description=(
            "The source whose value was kept in the canonical profile. "
            "For list fields this is the primary contributor after union/dedup."
        )
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Field-level confidence score in the range [0.0, 1.0]. "
            "Derived from the winning source's base reliability weight, "
            "adjusted for normalization success and cross-source agreement."
        ),
    )
    note: str | None = Field(
        default=None,
        description=(
            "Optional human-readable explanation of the merge decision, "
            "e.g. 'ats preferred per config' or 'resume only — field absent in ats'."
        ),
    )
