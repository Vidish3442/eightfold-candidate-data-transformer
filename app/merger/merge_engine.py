"""Merge engine — resolves conflicts between ATS and resume data, driven by config
source_priority, and records every decision in the ProvenanceTracker.

The ``MergeEngine`` is the core of Milestone 6.  It accepts a matched pair of
``ATSCandidate`` and ``ResumeCandidate`` records and produces a single
``Candidate`` object that carries the best available value for every canonical
field, together with full provenance metadata.

Merge strategy
--------------
- **Scalar fields** (full_name, headline): source-priority list from config;
  first non-empty value wins.
- **List fields** (emails, phones, skills): union with case-insensitive dedup;
  rapidfuzz fuzzy matching used for skills to catch near-duplicates.
- **Structured list fields** (experience, education): fuzzy-matched on
  title+company / institution+degree; the most complete record is kept when
  a pair is matched, otherwise both records are included.
- **Dict fields** (location, links): ATS wins on conflict; resume fills gaps.
"""

import logging
from rapidfuzz import fuzz

from app.models.ats_candidate import ATSCandidate, ATSExperience, ATSEducation
from app.models.resume_candidate import ResumeCandidate
from app.models.candidate import Candidate
from app.models.experience import Experience
from app.models.education import Education
from app.provenance.tracker import ProvenanceTracker
from app.constants.weights import SOURCE_WEIGHTS, NORMALIZATION_FAILURE_PENALTY  # noqa: F401

logger = logging.getLogger(__name__)

# Fuzzy-match thresholds
_SKILL_FUZZY_THRESHOLD: int = 85
_EXPERIENCE_FUZZY_THRESHOLD: int = 80
_EDUCATION_FUZZY_THRESHOLD: int = 80


class MergeEngine:
    """Orchestrates the merge of one ATS record and one resume record into a
    canonical ``Candidate``.

    Every field-level decision is recorded in the supplied ``ProvenanceTracker``
    so that the pipeline can later attach a complete audit trail to the output.
    The tracker is *not* flushed inside this class; the caller owns it.

    Parameters
    ----------
    config:
        Pipeline configuration dict.  The ``source_priority`` sub-dict maps
        field names to either a priority list (e.g. ``["ats", "resume"]``) or
        a merge-strategy dict (e.g. ``{"merge": "union"}``).
    tracker:
        A fresh ``ProvenanceTracker`` instance for the current pipeline run.

    Example::

        tracker = ProvenanceTracker()
        engine = MergeEngine(config=cfg, tracker=tracker)
        candidate = engine.merge(ats_record, resume_record)
    """

    def __init__(self, config: dict, tracker: ProvenanceTracker) -> None:
        """Store the runtime configuration and provenance tracker.

        Parameters
        ----------
        config:
            Full pipeline configuration dict (loaded from ``config.yaml``).
        tracker:
            Provenance tracker that accumulates every merge decision made
            during the lifetime of this engine instance.
        """
        self._config = config
        self._tracker = tracker
        self._source_priority: dict = config.get("source_priority", {})

    @property
    def tracker(self) -> ProvenanceTracker:
        """Return the provenance tracker associated with this engine instance."""
        return self._tracker

    def merge(self, ats: ATSCandidate, resume: ResumeCandidate) -> Candidate:
        """Orchestrate all merge operations and return the canonical ``Candidate``.

        Each field is handled by the appropriate helper method.  Provenance is
        registered inside those helpers; this method registers the two fields
        that are not delegated (``candidate_id``, ``years_experience``, and
        ``certifications``).

        ``overall_confidence`` is left at ``0.0`` and ``provenance`` at ``[]``
        — both are populated later by the confidence engine and pipeline
        orchestrator respectively via ``tracker.to_provenance_entries()``.

        Parameters
        ----------
        ats:
            Parsed ATS candidate record.
        resume:
            Parsed resume candidate record.

        Returns
        -------
        Candidate
            Merged canonical candidate with ``overall_confidence=0.0`` and
            ``provenance=[]`` (to be filled by downstream stages).
        """
        logger.info("MergeEngine: starting merge for candidate '%s'", ats.candidate_id)

        candidate_id: str = ats.candidate_id

        full_name: str = self._merge_scalar(
            "full_name", ats.full_name, resume.headline, default=""
        ) or ""

        emails: list[str] = self._merge_scalar_list(
            "emails",
            [ats.email] if ats.email else [],
            resume.emails,
        )

        phones: list[str] = self._merge_scalar_list(
            "phones",
            [ats.phone] if ats.phone else [],
            resume.phones,
        )

        location: dict = self._merge_location(ats.location, resume.location)

        links: dict = self._merge_dict(
            "links",
            ats.links or {},
            resume.links or {},
        )

        headline: str | None = self._merge_scalar(
            "headline", ats.headline, resume.headline
        )

        years_experience: float | None = ats.years_experience

        skills: list[str] = self._merge_skills(
            ats.skills or [],
            resume.skills,
        )

        experience: list[Experience] = self._merge_experience(
            ats.experience or [],
            resume.experience,
        )

        education: list[Education] = self._merge_education(
            ats.education or [],
            resume.education,
        )

        certifications: list[str] = list(dict.fromkeys(resume.certifications))

        # Register provenance for fields handled directly in this method.
        self._tracker.register("candidate_id", "ats", SOURCE_WEIGHTS["ats"])

        if years_experience is not None:
            self._tracker.register("years_experience", "ats", SOURCE_WEIGHTS["ats"])
        else:
            self._tracker.register("years_experience", "resume", SOURCE_WEIGHTS["resume"])

        if certifications:
            self._tracker.register("certifications", "resume", SOURCE_WEIGHTS["resume"])

        logger.info(
            "MergeEngine: merge complete — %d skills, %d experience entries, "
            "%d education entries, %d certifications",
            len(skills),
            len(experience),
            len(education),
            len(certifications),
        )

        return Candidate(
            candidate_id=candidate_id,
            full_name=full_name,
            emails=emails,
            phones=phones,
            location=location,
            links=links,
            headline=headline,
            years_experience=years_experience,
            skills=skills,
            experience=experience,
            education=education,
            certifications=certifications,
            provenance=[],
            overall_confidence=0.0,
        )

    # ------------------------------------------------------------------
    # Scalar field merge
    # ------------------------------------------------------------------

    def _merge_scalar(
        self,
        field: str,
        ats_val: str | None,
        resume_val: str | None,
        default: str | None = None,
    ) -> str | None:
        """Merge a single-value string field according to the configured source priority.

        The method iterates the configured priority list for *field* and returns
        the first non-None, non-empty string it encounters.  Both sources have
        their provenance registered when they carry a non-empty value.

        Parameters
        ----------
        field:
            Canonical field name used to look up the priority order in config.
        ats_val:
            Value from the ATS source (may be ``None``).
        resume_val:
            Value from the resume source (may be ``None``).
        default:
            Value to return when neither source has a usable value.
            Defaults to ``None``.

        Returns
        -------
        str | None
            The winning value, or *default* when no source has a usable value.
        """
        priority = self._get_priority_sources(field)

        source_values: dict[str, str | None] = {"ats": ats_val, "resume": resume_val}

        # Register provenance for every source that has a non-empty value.
        for source in ("ats", "resume"):
            val = source_values.get(source)
            if val:
                self._tracker.register(field, source, SOURCE_WEIGHTS.get(source, 0.5))

        # Pick the first non-empty value in priority order.
        winning_value: str | None = default
        winning_source: str | None = None

        for source in priority:
            val = source_values.get(source)
            if val:
                winning_value = val
                winning_source = source
                break

        if winning_source:
            logger.debug(
                "MergeEngine._merge_scalar: field='%s' winner='%s' value='%s'",
                field,
                winning_source,
                winning_value,
            )
        else:
            logger.debug(
                "MergeEngine._merge_scalar: field='%s' no value found, using default",
                field,
            )

        return winning_value

    # ------------------------------------------------------------------
    # List field merge
    # ------------------------------------------------------------------

    def _merge_scalar_list(
        self,
        field: str,
        ats_vals: list[str],
        resume_vals: list[str],
    ) -> list[str]:
        """Union two string lists with case-insensitive deduplication.

        The merged list is sorted alphabetically so that the output is
        deterministic regardless of source ordering.

        Parameters
        ----------
        field:
            Canonical field name (used for provenance registration).
        ats_vals:
            Values from the ATS source.
        resume_vals:
            Values from the resume source.

        Returns
        -------
        list[str]
            Sorted, case-insensitively deduplicated union of both input lists.
            The case of the *first* occurrence of each value (in ATS-then-resume
            order) is preserved.
        """
        if ats_vals:
            self._tracker.register(field, "ats", SOURCE_WEIGHTS["ats"])
        if resume_vals:
            self._tracker.register(field, "resume", SOURCE_WEIGHTS["resume"])

        seen_lower: set[str] = set()
        merged: list[str] = []

        for val in list(ats_vals) + list(resume_vals):
            lower = val.lower()
            if lower not in seen_lower:
                seen_lower.add(lower)
                merged.append(val)

        return sorted(merged)

    # ------------------------------------------------------------------
    # Location merge
    # ------------------------------------------------------------------

    def _merge_location(
        self,
        ats_loc: dict | None,
        resume_loc: dict | None,
    ) -> dict:
        """Merge two structured location dicts.

        ATS values take precedence on conflict.  Missing keys in the ATS
        dict are filled from the resume dict.  The returned dict always
        contains the keys ``city``, ``state``, and ``country``; unknown
        values are represented as ``None``.

        Parameters
        ----------
        ats_loc:
            Location dict from the ATS record, or ``None``.
        resume_loc:
            Location dict from the resume record, or ``None``.

        Returns
        -------
        dict
            Merged location with keys ``city``, ``state``, ``country``.
        """
        ats_dict: dict = ats_loc or {}
        resume_dict: dict = resume_loc or {}

        if ats_dict:
            self._tracker.register("location", "ats", SOURCE_WEIGHTS["ats"])
        if resume_dict:
            self._tracker.register("location", "resume", SOURCE_WEIGHTS["resume"])

        merged: dict = {"city": None, "state": None, "country": None}

        for key in ("city", "state", "country"):
            ats_value = ats_dict.get(key)
            resume_value = resume_dict.get(key)
            # ATS wins; fall back to resume when ATS is absent.
            merged[key] = ats_value if ats_value is not None else resume_value

        logger.debug("MergeEngine._merge_location: result=%s", merged)
        return merged

    # ------------------------------------------------------------------
    # Dict field merge
    # ------------------------------------------------------------------

    def _merge_dict(
        self,
        field: str,
        ats_dict: dict,
        resume_dict: dict,
    ) -> dict:
        """Merge two dicts — resume fills in keys absent from ATS; ATS wins on conflict.

        Parameters
        ----------
        field:
            Canonical field name (used for provenance registration).
        ats_dict:
            Dict from the ATS source.
        resume_dict:
            Dict from the resume source.

        Returns
        -------
        dict
            Merged dict containing all keys from both sources, with ATS values
            taking precedence when a key exists in both.
        """
        if ats_dict:
            self._tracker.register(field, "ats", SOURCE_WEIGHTS["ats"])
        if resume_dict:
            self._tracker.register(field, "resume", SOURCE_WEIGHTS["resume"])

        # Start with resume as base, then overwrite/fill with ATS.
        merged: dict = {**resume_dict, **ats_dict}
        return merged

    # ------------------------------------------------------------------
    # Skills merge
    # ------------------------------------------------------------------

    def _merge_skills(
        self,
        ats_skills: list[str],
        resume_skills: list[str],
    ) -> list[str]:
        """Union ATS and resume skill lists with fuzzy deduplication.

        ATS skills are treated as canonical.  Each resume skill is added only
        when no existing skill in the merged list has a ``token_sort_ratio``
        score of ``≥ 85`` against it (case-insensitive comparison).

        Parameters
        ----------
        ats_skills:
            Skill strings from the ATS record.
        resume_skills:
            Skill strings from the resume record.

        Returns
        -------
        list[str]
            Sorted, fuzzy-deduplicated union of both skill lists.
        """
        if ats_skills:
            self._tracker.register("skills", "ats", SOURCE_WEIGHTS["ats"])
        if resume_skills:
            self._tracker.register("skills", "resume", SOURCE_WEIGHTS["resume"])

        merged: list[str] = list(ats_skills)

        for resume_skill in resume_skills:
            resume_lower = resume_skill.lower()
            is_duplicate = any(
                fuzz.token_sort_ratio(resume_lower, existing.lower()) >= _SKILL_FUZZY_THRESHOLD
                for existing in merged
            )
            if not is_duplicate:
                merged.append(resume_skill)

        logger.debug(
            "MergeEngine._merge_skills: %d ATS + %d resume → %d merged",
            len(ats_skills),
            len(resume_skills),
            len(merged),
        )
        return sorted(merged)

    # ------------------------------------------------------------------
    # Experience merge
    # ------------------------------------------------------------------

    def _merge_experience(
        self,
        ats_exp: list[ATSExperience],
        resume_exp: list[dict],
    ) -> list[Experience]:
        """Merge ATS and resume experience entries into a deduplicated list.

        Matching uses fuzzy comparison of title + company
        (``token_sort_ratio ≥ 80``).  When a match is found, the richer entry
        (longer description or more bullets) is kept as the base and the other
        entry's bullets are unioned in.  Unmatched entries from either source
        are included as-is.

        The final list is sorted by ``start_date`` descending (most recent
        first), with ``None`` dates sorted to the end.

        Parameters
        ----------
        ats_exp:
            List of ``ATSExperience`` objects from the ATS record.
        resume_exp:
            List of raw experience dicts from the resume record.

        Returns
        -------
        list[Experience]
            Merged, sorted list of canonical ``Experience`` objects.
        """
        self._tracker.register("experience", "ats", SOURCE_WEIGHTS["ats"])
        if resume_exp:
            self._tracker.register("experience", "resume", SOURCE_WEIGHTS["resume"])

        # Convert ATSExperience objects to plain dicts for uniform handling.
        ats_dicts: list[dict] = [
            {
                "title": e.title or "",
                "company": e.company or "",
                "start_date": e.start_date,
                "end_date": e.end_date,
                "description": e.description,
                "bullets": [],
            }
            for e in ats_exp
        ]

        matched_resume_indices: set[int] = set()
        merged_dicts: list[dict] = []

        for ats_entry in ats_dicts:
            ats_key = f"{ats_entry['title']} {ats_entry['company']}".lower()
            best_match_idx: int | None = None
            best_score: int = 0

            for idx, res_entry in enumerate(resume_exp):
                if idx in matched_resume_indices:
                    continue
                res_key = f"{res_entry.get('title', '')} {res_entry.get('company', '')}".lower()
                score = fuzz.token_sort_ratio(ats_key, res_key)
                if score >= _EXPERIENCE_FUZZY_THRESHOLD and score > best_score:
                    best_score = score
                    best_match_idx = idx

            if best_match_idx is not None:
                matched_resume_indices.add(best_match_idx)
                res_entry = resume_exp[best_match_idx]
                # Keep the entry with the richer description.
                ats_desc = ats_entry.get("description") or ""
                res_desc = res_entry.get("description") or ""
                base = ats_entry if len(ats_desc) >= len(res_desc) else dict(res_entry)

                # Union bullets from both sources.
                all_bullets: list[str] = list(ats_entry.get("bullets") or [])
                for b in res_entry.get("bullets") or []:
                    if b not in all_bullets:
                        all_bullets.append(b)
                base = dict(base)
                base["bullets"] = all_bullets

                logger.debug(
                    "MergeEngine._merge_experience: matched '%s @ %s' (score=%d)",
                    ats_entry["title"],
                    ats_entry["company"],
                    best_score,
                )
                merged_dicts.append(base)
            else:
                merged_dicts.append(ats_entry)

        # Add unmatched resume entries.
        for idx, res_entry in enumerate(resume_exp):
            if idx not in matched_resume_indices:
                merged_dicts.append(dict(res_entry))

        # Sort by start_date descending (None last).
        def _sort_key(entry: dict) -> tuple:
            sd = entry.get("start_date") or ""
            return ("" if sd else "9999", sd) if sd else ("9999", "")

        merged_dicts.sort(key=lambda e: e.get("start_date") or "", reverse=True)

        # Convert to Experience models.
        result: list[Experience] = []
        for d in merged_dicts:
            result.append(
                Experience(
                    title=d.get("title") or "",
                    company=d.get("company") or "",
                    start_date=d.get("start_date"),
                    end_date=d.get("end_date"),
                    description=d.get("description"),
                    bullets=d.get("bullets") or [],
                )
            )

        return result

    # ------------------------------------------------------------------
    # Education merge
    # ------------------------------------------------------------------

    def _merge_education(
        self,
        ats_edu: list[ATSEducation],
        resume_edu: list[dict],
    ) -> list[Education]:
        """Merge ATS and resume education entries into a deduplicated list.

        Matching uses institution name alone as the primary key
        (``token_sort_ratio ≥ 85`` on institution).  This correctly handles
        the common case where the ATS stores a combined degree string
        (e.g. "B.Tech Computer Science and Business Systems") while the resume
        splits it into separate degree + field-of-study lines (e.g.
        "Bachelor of Technology" + "Computer Science and Business Systems").

        When a match is found the most complete record is built by preferring
        non-None values from either source — ATS wins on conflicts.

        Parameters
        ----------
        ats_edu:
            List of ``ATSEducation`` objects from the ATS record.
        resume_edu:
            List of raw education dicts from the resume record.

        Returns
        -------
        list[Education]
            Merged list of canonical ``Education`` objects.
        """
        self._tracker.register("education", "ats", SOURCE_WEIGHTS["ats"])
        if resume_edu:
            self._tracker.register("education", "resume", SOURCE_WEIGHTS["resume"])

        # Convert ATSEducation objects to plain dicts.
        ats_dicts: list[dict] = [
            {
                "institution": e.institution or "",
                "degree": e.degree or "",
                "field_of_study": e.field_of_study,
                "start_date": e.start_date,
                "end_date": e.end_date,
            }
            for e in ats_edu
        ]

        matched_resume_indices: set[int] = set()
        merged_dicts: list[dict] = []

        for ats_entry in ats_dicts:
            ats_inst = ats_entry["institution"].lower()
            best_match_idx: int | None = None
            best_score: int = 0

            for idx, res_entry in enumerate(resume_edu):
                if idx in matched_resume_indices:
                    continue
                res_inst = res_entry.get("institution", "").lower()
                # Match on institution name alone — avoids misses when degree
                # strings differ between sources (e.g. "B.Tech" vs "Bachelor").
                score = fuzz.token_sort_ratio(ats_inst, res_inst)
                if score >= _EDUCATION_FUZZY_THRESHOLD and score > best_score:
                    best_score = score
                    best_match_idx = idx

            if best_match_idx is not None:
                matched_resume_indices.add(best_match_idx)
                res_entry = resume_edu[best_match_idx]

                # ATS degree wins; use resume field_of_study when ATS has none.
                # Prefer the longer / more specific degree string.
                ats_degree = ats_entry["degree"]
                res_degree = res_entry.get("degree") or ""
                res_fos = res_entry.get("field_of_study") or ""

                # If resume has field_of_study and ATS degree already contains
                # it, don't duplicate. Otherwise keep ATS degree as-is.
                merged_degree = ats_degree or res_degree
                merged_fos = (
                    ats_entry.get("field_of_study")
                    or res_fos
                    or None
                )

                best: dict = {
                    "institution": ats_entry["institution"] or res_entry.get("institution") or "",
                    "degree": merged_degree,
                    "field_of_study": merged_fos,
                    "start_date": ats_entry.get("start_date") or res_entry.get("start_date"),
                    "end_date": ats_entry.get("end_date") or res_entry.get("end_date"),
                }
                logger.debug(
                    "MergeEngine._merge_education: matched '%s @ %s' (score=%d)",
                    ats_entry["degree"],
                    ats_entry["institution"],
                    best_score,
                )
                merged_dicts.append(best)
            else:
                merged_dicts.append(ats_entry)

        # Add unmatched resume entries.
        for idx, res_entry in enumerate(resume_edu):
            if idx not in matched_resume_indices:
                merged_dicts.append(dict(res_entry))

        # Convert to Education models.
        result: list[Education] = []
        for d in merged_dicts:
            result.append(
                Education(
                    institution=d.get("institution") or "",
                    degree=d.get("degree") or "",
                    field_of_study=d.get("field_of_study"),
                    start_date=d.get("start_date"),
                    end_date=d.get("end_date"),
                )
            )

        return result

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _get_priority_sources(self, field: str) -> list[str]:
        """Return the source priority list for *field* from the config.

        Handles two config formats:

        - **List format**: ``["ats", "resume"]`` — returned directly.
        - **Dict format**: ``{"merge": "union"}`` — the merge key signals a
          union strategy; ``["ats", "resume"]`` is returned as the default
          priority for scalar fallback purposes.

        When *field* is absent from the ``source_priority`` config, the default
        ``["ats", "resume"]`` order is returned.

        Parameters
        ----------
        field:
            Canonical field name to look up.

        Returns
        -------
        list[str]
            Ordered list of source identifiers, highest priority first.
        """
        priority_entry = self._source_priority.get(field)

        if priority_entry is None:
            return ["ats", "resume"]

        if isinstance(priority_entry, list):
            return priority_entry

        # Dict format — e.g. {"merge": "union"} — treat as union; default order.
        if isinstance(priority_entry, dict):
            return ["ats", "resume"]

        return ["ats", "resume"]
