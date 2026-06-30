"""Pydantic data models for raw and canonical candidate representations.

Public API
----------
ATSCandidate
    Raw candidate record parsed directly from an ATS JSON export.
ATSExperience
    One work-experience entry as it arrives from the ATS.
ATSEducation
    One education record as it arrives from the ATS.
Education
    One educational qualification record (canonical).
Experience
    One work-experience record (canonical).
ProvenanceEntry
    Field-level provenance and confidence metadata.
Candidate
    The full canonical candidate profile produced by the pipeline.
"""

from app.models.ats_candidate import ATSCandidate, ATSEducation, ATSExperience
from app.models.candidate import Candidate
from app.models.education import Education
from app.models.experience import Experience
from app.models.provenance import ProvenanceEntry

__all__ = [
    "ATSCandidate",
    "ATSEducation",
    "ATSExperience",
    "Candidate",
    "Education",
    "Experience",
    "ProvenanceEntry",
]
