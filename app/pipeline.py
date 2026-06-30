"""Pipeline orchestrator — runs all stages in order: read → parse → extract → normalize → match → merge (+provenance) → confidence → validate → project → write.

This module is the top-level coordinator for the Eightfold Candidate Data
Transformer.  It wires every sub-system together in the correct order,
shuttles data between stages, and ensures that provenance, confidence, and
output writing all happen after the merge is complete.

Typical usage::

    pipeline = Pipeline(
        ats_path=Path("data/input/ats.json"),
        resume_path=Path("data/input/resume.txt"),
        config_path=Path("config.yaml"),
        output_dir=Path("data/output"),
    )
    results = pipeline.run()
"""

import logging
from pathlib import Path

from app.readers.ats_reader import ATSReader
from app.readers.resume_reader import ResumeReader
from app.parsers.resume_parser import ResumeParser
from app.extractors.email_extractor import EmailExtractor
from app.extractors.phone_extractor import PhoneExtractor
from app.extractors.skill_extractor import SkillExtractor
from app.extractors.education_extractor import EducationExtractor
from app.extractors.experience_extractor import ExperienceExtractor
from app.extractors.certification_extractor import CertificationExtractor
from app.normalizers.phone import PhoneNormalizer
from app.normalizers.date import DateNormalizer
from app.normalizers.skills import SkillNormalizer
from app.normalizers.location import LocationNormalizer
from app.matcher.candidate_matcher import CandidateMatcher
from app.merger.merge_engine import MergeEngine
from app.provenance.tracker import ProvenanceTracker
from app.confidence.confidence_engine import ConfidenceEngine
from app.validator.validator import OutputValidator
from app.projection.projector import Projector
from app.writers.json_writer import JsonWriter
from app.config.loader import ConfigLoader
from app.config.validator import ConfigValidator
from app.models.resume_candidate import ResumeCandidate
from app.utils.logger import PipelineLogger

class Pipeline:
    """Full candidate data transformation pipeline.

    Orchestrates all stages in a fixed sequence:

    1. Load and validate configuration.
    2. Read the ATS JSON record.
    3. Read the resume file (PDF or plain text).
    4. Parse the resume into named sections.
    5. Extract emails, phones, skills, education, experience, and certifications.
    6. Normalize phones, dates, skills, and location.
    7. Build a ``ResumeCandidate`` from the normalized data.
    8. Match the ATS and resume candidates.
    9. Merge into a canonical ``Candidate``.
    10. Compute field-level and overall confidence scores.
    11. Build provenance entries and attach them to the candidate.
    12. Validate the candidate against the Pydantic schema.
    13. Project the candidate through the runtime config.
    14. Write canonical and transformed JSON output files.

    Parameters
    ----------
    ats_path:
        Path to the ATS JSON input file.
    resume_path:
        Path to the resume file (PDF or ``.txt``).
    config_path:
        Path to the ``config.yaml`` pipeline configuration file.
    output_dir:
        Directory where ``canonical_profile.json`` and
        ``transformed_profile.json`` will be written.
    """

    def __init__(
        self,
        ats_path: Path,
        resume_path: Path,
        config_path: Path,
        output_dir: Path,
    ) -> None:
        """Store the four paths needed to run the pipeline.

        Parameters
        ----------
        ats_path:
            Path to the ATS JSON input file.
        resume_path:
            Path to the resume file.
        config_path:
            Path to the YAML configuration file.
        output_dir:
            Output directory for the two generated JSON files.
        """
        self._ats_path = ats_path
        self._resume_path = resume_path
        self._config_path = config_path
        self._output_dir = output_dir
        self._logger = PipelineLogger("pipeline")

    def run(self) -> dict:
        """Execute all pipeline stages in order and return the output dicts.

        Runs the complete transformation: reading inputs, extracting and
        normalizing fields, merging sources, computing confidence, validating
        the result, projecting through config, and writing JSON output files.

        Returns
        -------
        dict
            A dict with two keys:

            - ``"canonical"``: the full ``Candidate.model_dump(mode="json")``
              dict including all fields, provenance, and confidence.
            - ``"transformed"``: the projected output dict shaped by the
              runtime config (field selection, renames, missing policy).

        Example::

            pipeline = Pipeline(ats_path, resume_path, config_path, output_dir)
            results = pipeline.run()
            print(results["canonical"]["overall_confidence"])
        """
        # ------------------------------------------------------------------
        # Stage 1: Load config
        # ------------------------------------------------------------------
        self._logger.info("Config", "Loading configuration...")
        loader = ConfigLoader()
        config = loader.load(self._config_path)
        validator = ConfigValidator()
        ok, errors = validator.validate(config)
        if not ok:
            self._logger.warning("Config", f"Config validation errors: {errors}")
        self._logger.success("Config", "Configuration loaded")

        # ------------------------------------------------------------------
        # Stage 2: Read ATS
        # ------------------------------------------------------------------
        self._logger.info("Reading ATS...", "")
        ats_reader = ATSReader()
        ats = ats_reader.read(self._ats_path)
        self._logger.success("Reading ATS", "ATS loaded")

        # ------------------------------------------------------------------
        # Stage 3: Read resume
        # ------------------------------------------------------------------
        self._logger.info("Reading Resume...", "")
        resume_reader = ResumeReader()
        raw_text = resume_reader.read(self._resume_path)
        self._logger.success("Reading Resume", "Resume parsed")

        # ------------------------------------------------------------------
        # Stage 4: Parse resume sections
        # ------------------------------------------------------------------
        parser = ResumeParser()
        sections = parser.parse(raw_text)

        # ------------------------------------------------------------------
        # Stage 5: Extract fields from resume
        # ------------------------------------------------------------------
        self._logger.info("Extracting fields...", "")
        emails = EmailExtractor().extract(sections)
        phones = PhoneExtractor().extract(sections)
        raw_skills = SkillExtractor().extract(sections)
        raw_education = EducationExtractor().extract(sections)
        raw_experience = ExperienceExtractor().extract(sections)
        certifications = CertificationExtractor().extract(sections)
        self._logger.success("Extracting fields", "Done")

        # ------------------------------------------------------------------
        # Stage 6: Normalize
        # ------------------------------------------------------------------
        self._logger.info("Normalizing...", "")
        normalization_failures: set[str] = set()

        phone_norm = PhoneNormalizer()
        norm_phones_results = phone_norm.normalize_list(phones)
        if any(not ok for _, ok in norm_phones_results):
            normalization_failures.add("phones")

        # Also normalize the ATS phone so it deduplicates correctly with
        # the resume phone when both are passed to the merge engine.
        if ats.phone:
            ats_phone_norm, ats_phone_ok = phone_norm.normalize(ats.phone)
            if ats_phone_ok:
                ats = ats.model_copy(update={"phone": ats_phone_norm})

        date_norm = DateNormalizer()
        skill_norm = SkillNormalizer()
        loc_norm = LocationNormalizer()

        # Normalize skills
        norm_skills = skill_norm.normalize_list(raw_skills)

        # Normalize education dates
        norm_education = []
        for edu in raw_education:
            start, _, start_ok = date_norm.normalize_date_range(edu.get("start_date"), None)
            end, _, end_ok = date_norm.normalize_date_range(edu.get("end_date"), None)
            if not start_ok and edu.get("start_date"):
                normalization_failures.add("education")
            norm_education.append({**edu, "start_date": start, "end_date": end})

        # Normalize experience dates
        norm_experience = []
        for exp in raw_experience:
            start, end, ok = date_norm.normalize_date_range(exp.get("start_date"), exp.get("end_date"))
            if not ok and (exp.get("start_date") or exp.get("end_date")):
                normalization_failures.add("experience")
            norm_experience.append({**exp, "start_date": start, "end_date": end})

        # Parse location from header
        header_text = sections.get("HEADER", "")
        resume_location = loc_norm.normalize(header_text.split("\n")[1] if "\n" in header_text else "")

        self._logger.success("Normalizing", "Done")

        # ------------------------------------------------------------------
        # Stage 7: Build ResumeCandidate
        # ------------------------------------------------------------------
        resume = ResumeCandidate(
            raw_text=raw_text,
            emails=emails,
            phones=[p for p, _ in norm_phones_results],
            skills=norm_skills,
            experience=norm_experience,
            education=norm_education,
            certifications=certifications,
            links={},
            location=resume_location if any(v for v in resume_location.values()) else None,
        )

        # ------------------------------------------------------------------
        # Stage 8: Candidate matching
        # ------------------------------------------------------------------
        self._logger.info("Matching...", "")
        fuzzy_threshold = config.get("matching", {}).get("fuzzy_threshold", 85)
        matcher = CandidateMatcher(fuzzy_threshold=fuzzy_threshold)
        matched = matcher.match(ats, resume)
        self._logger.success("Matching", f"{'1 candidate matched' if matched else 'No match — using ATS only'}")

        # ------------------------------------------------------------------
        # Stage 9: Merge
        # ------------------------------------------------------------------
        self._logger.info("Merging...", "")
        tracker = ProvenanceTracker()
        merge_engine = MergeEngine(config=config, tracker=tracker)
        candidate = merge_engine.merge(ats, resume)
        self._logger.success("Merging", "Finished")

        # ------------------------------------------------------------------
        # Stage 10: Confidence
        # ------------------------------------------------------------------
        self._logger.info("Confidence...", "")
        confidence_engine = ConfidenceEngine(tracker)
        field_confidences, overall = confidence_engine.compute_all(normalization_failures)
        candidate = candidate.model_copy(update={"overall_confidence": overall})
        self._logger.success("Confidence", f"{overall:.4f}")

        # ------------------------------------------------------------------
        # Stage 11: Build provenance list
        # ------------------------------------------------------------------
        winning_sources = {
            "full_name": "ats" if ats.full_name else "resume",
            "emails": "ats" if ats.email else "resume",
            "phones": "ats" if ats.phone else "resume",
            "skills": "ats",
            "experience": "ats",
            "education": "ats",
            "location": "ats",
            "links": "ats",
            "headline": "ats" if ats.headline else "resume",
            "years_experience": "ats",
            "certifications": "resume",
            "candidate_id": "ats",
        }
        notes = {k: f"{v} preferred per config" for k, v in winning_sources.items()}
        provenance_entries = tracker.to_provenance_entries(winning_sources=winning_sources, notes=notes)
        candidate = candidate.model_copy(update={"provenance": provenance_entries})

        # ------------------------------------------------------------------
        # Stage 12: Validate
        # ------------------------------------------------------------------
        self._logger.info("Validation...", "")
        output_validator = OutputValidator()
        valid, val_errors = output_validator.validate(candidate)
        if not valid:
            self._logger.warning("Validation", f"Errors: {val_errors}")
        else:
            self._logger.success("Validation", "Passed")

        # ------------------------------------------------------------------
        # Stage 13: Project
        # ------------------------------------------------------------------
        projector = Projector(config)
        transformed = projector.project(candidate)

        # ------------------------------------------------------------------
        # Stage 14: Write outputs
        # ------------------------------------------------------------------
        self._logger.info("Writing Output...", "")
        writer = JsonWriter()
        canonical_path = self._output_dir / "canonical_profile.json"
        transformed_path = self._output_dir / "transformed_profile.json"

        canonical_dict = candidate.model_dump(mode="json")
        writer.write(canonical_dict, canonical_path)
        writer.write(transformed, transformed_path)

        self._logger.success("Writing Output", f"canonical → {canonical_path}")
        self._logger.success("Writing Output", f"transformed → {transformed_path}")

        return {"canonical": canonical_dict, "transformed": transformed}
