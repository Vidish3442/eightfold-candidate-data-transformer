"""Tests for Milestone 6 — Merge Engine & Provenance.

Covers:
- Scalar field merging (full_name, headline, emails)
- Skill union and fuzzy deduplication
- Experience merging from ATS and resume sources
- ProvenanceTracker registration and serialisation

All tests use lightweight in-memory fixtures; no file I/O is required.
"""

import pytest

from app.merger.merge_engine import MergeEngine
from app.provenance.tracker import ProvenanceTracker
from app.models.ats_candidate import ATSCandidate, ATSExperience, ATSEducation
from app.models.resume_candidate import ResumeCandidate
from app.models.provenance import ProvenanceEntry

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TEST_CONFIG: dict = {
    "source_priority": {
        "full_name": ["ats", "resume"],
        "email": ["ats", "resume"],
        "phone": ["ats", "resume"],
        "skills": {"merge": "union"},
        "education": {"merge": "union"},
        "experience": {"merge": "union"},
    }
}

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_ats(**kwargs) -> ATSCandidate:
    """Return an ATSCandidate with sensible defaults.

    Any field may be overridden via keyword arguments.

    Parameters
    ----------
    **kwargs:
        ATSCandidate field overrides.

    Returns
    -------
    ATSCandidate
        Candidate with ``candidate_id="ATS-001"`` and all other fields
        populated with test defaults unless overridden.
    """
    defaults: dict = {
        "candidate_id": "ATS-001",
        "full_name": "Alice Smith",
        "email": "alice@example.com",
        "phone": "+14155550001",
        "status": "interviewing",
        "headline": "Senior Software Engineer",
        "years_experience": 8.0,
        "location": {"city": "San Francisco", "state": "CA", "country": "US"},
        "links": {"linkedin": "https://linkedin.com/in/alice"},
        "skills": ["Python", "Django", "PostgreSQL"],
        "experience": [],
        "education": [],
    }
    defaults.update(kwargs)
    return ATSCandidate(**defaults)


def _make_resume(**kwargs) -> ResumeCandidate:
    """Return a ResumeCandidate with sensible defaults.

    Any field may be overridden via keyword arguments.

    Parameters
    ----------
    **kwargs:
        ResumeCandidate field overrides.

    Returns
    -------
    ResumeCandidate
        Candidate with pre-populated test defaults unless overridden.
    """
    defaults: dict = {
        "raw_text": "Alice Smith\nSenior Engineer\nalice@example.com",
        "emails": ["alice@example.com"],
        "phones": ["+14155550001"],
        "skills": ["Python", "Docker", "AWS"],
        "experience": [],
        "education": [],
        "certifications": [],
        "links": {"github": "https://github.com/alice"},
        "location": {"city": "San Francisco", "state": "CA", "country": "US"},
        "headline": "Senior Software Engineer",
    }
    defaults.update(kwargs)
    return ResumeCandidate(**defaults)


# ---------------------------------------------------------------------------
# TestMergeEngineScalar
# ---------------------------------------------------------------------------


class TestMergeEngineScalar:
    """Tests for scalar field merging behaviour."""

    def test_ats_wins_for_full_name(self) -> None:
        """ATS full_name should be used when it is non-empty and config priority is [ats, resume]."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats = _make_ats(full_name="Alice Smith")
        resume = _make_resume(headline="Resume Headline Name")

        candidate = engine.merge(ats, resume)

        assert candidate.full_name == "Alice Smith"

    def test_fallback_to_resume_when_ats_missing(self) -> None:
        """Resume headline should be used when ATS full_name is None."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats = _make_ats(full_name=None)
        resume = _make_resume(headline="Resume Only Name")

        candidate = engine.merge(ats, resume)

        assert candidate.full_name == "Resume Only Name"

    def test_ats_email_priority(self) -> None:
        """ATS email should appear in the merged emails list."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats = _make_ats(email="ats@example.com")
        resume = _make_resume(emails=["resume@example.com"])

        candidate = engine.merge(ats, resume)

        assert "ats@example.com" in candidate.emails


# ---------------------------------------------------------------------------
# TestMergeEngineSkills
# ---------------------------------------------------------------------------


class TestMergeEngineSkills:
    """Tests for skill union and fuzzy deduplication."""

    def test_union_of_skills(self) -> None:
        """Skills from both ATS and resume should appear in the merged list."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats = _make_ats(skills=["Python", "Django"])
        resume = _make_resume(skills=["Docker", "AWS"])

        candidate = engine.merge(ats, resume)

        assert "Python" in candidate.skills
        assert "Django" in candidate.skills
        assert "Docker" in candidate.skills
        assert "AWS" in candidate.skills

    def test_dedup_same_canonical_skill(self) -> None:
        """'Python' from ATS and 'Python' from resume should deduplicate to one entry."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats = _make_ats(skills=["Python"])
        resume = _make_resume(skills=["Python"])

        candidate = engine.merge(ats, resume)

        assert candidate.skills.count("Python") == 1

    def test_skills_sorted(self) -> None:
        """Merged skills list should be sorted alphabetically."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats = _make_ats(skills=["Zebra", "Apple"])
        resume = _make_resume(skills=["Mango", "Banana"])

        candidate = engine.merge(ats, resume)

        assert candidate.skills == sorted(candidate.skills)


# ---------------------------------------------------------------------------
# TestMergeEngineExperience
# ---------------------------------------------------------------------------


class TestMergeEngineExperience:
    """Tests for experience list merging."""

    def test_both_sources_merged(self) -> None:
        """Matching ATS and resume experience entries should be merged into one."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats_exp = [
            ATSExperience(
                title="Software Engineer",
                company="Acme Corp",
                start_date="2020-01",
                end_date="2022-06",
                description="Built internal tools.",
            )
        ]
        resume_exp = [
            {
                "title": "Software Engineer",
                "company": "Acme Corp",
                "start_date": "2020-01",
                "end_date": "2022-06",
                "description": "Led backend development and built internal tools.",
                "bullets": ["Reduced latency by 30%"],
            }
        ]

        ats = _make_ats(experience=ats_exp)
        resume = _make_resume(experience=resume_exp)

        candidate = engine.merge(ats, resume)

        # Should have exactly one entry for Acme Corp (matched and merged).
        acme_entries = [e for e in candidate.experience if "Acme" in e.company]
        assert len(acme_entries) == 1

    def test_unmatched_resume_experience_kept(self) -> None:
        """A resume experience entry with no ATS match should appear in the output."""
        tracker = ProvenanceTracker()
        engine = MergeEngine(config=TEST_CONFIG, tracker=tracker)

        ats_exp = [
            ATSExperience(
                title="Backend Engineer",
                company="TechCo",
                start_date="2021-03",
            )
        ]
        resume_exp = [
            {
                "title": "Freelance Developer",
                "company": "Self",
                "start_date": "2019-01",
                "end_date": "2021-02",
                "description": "Independent consulting work.",
                "bullets": [],
            }
        ]

        ats = _make_ats(experience=ats_exp)
        resume = _make_resume(experience=resume_exp)

        candidate = engine.merge(ats, resume)

        titles = [e.title for e in candidate.experience]
        assert "Freelance Developer" in titles
        assert "Backend Engineer" in titles


# ---------------------------------------------------------------------------
# TestProvenanceTracker
# ---------------------------------------------------------------------------


class TestProvenanceTracker:
    """Tests for ProvenanceTracker registry and serialisation."""

    def test_register_and_get_sources(self) -> None:
        """Registering a field/source pair should make it visible via get_sources."""
        tracker = ProvenanceTracker()
        tracker.register("full_name", "ats", 0.95)
        tracker.register("full_name", "resume", 0.85)

        sources = tracker.get_sources("full_name")

        assert "ats" in sources
        assert "resume" in sources

    def test_higher_confidence_wins(self) -> None:
        """When the same field/source is registered twice, the higher confidence is kept."""
        tracker = ProvenanceTracker()
        tracker.register("skills", "ats", 0.90)
        tracker.register("skills", "ats", 0.95)  # higher — should win
        tracker.register("skills", "ats", 0.80)  # lower — should be ignored

        assert tracker.get_confidence("skills", "ats") == pytest.approx(0.95)

    def test_to_provenance_entries(self) -> None:
        """to_provenance_entries should build correct ProvenanceEntry objects."""
        tracker = ProvenanceTracker()
        tracker.register("full_name", "ats", 0.95)
        tracker.register("full_name", "resume", 0.85)
        tracker.register("emails", "ats", 0.95)

        winning_sources = {"full_name": "ats", "emails": "ats"}
        notes = {"full_name": "ats preferred per config"}

        entries = tracker.to_provenance_entries(
            winning_sources=winning_sources,
            notes=notes,
        )

        assert len(entries) == 2

        # Entries are sorted by field name — "emails" comes before "full_name".
        assert entries[0].field == "emails"
        assert entries[1].field == "full_name"

        full_name_entry = entries[1]
        assert isinstance(full_name_entry, ProvenanceEntry)
        assert full_name_entry.winning_source == "ats"
        assert full_name_entry.confidence == pytest.approx(0.95)
        assert full_name_entry.note == "ats preferred per config"
        assert "ats" in full_name_entry.sources
        assert "resume" in full_name_entry.sources

    def test_get_sources_unknown_field(self) -> None:
        """get_sources for an unregistered field should return an empty list."""
        tracker = ProvenanceTracker()
        assert tracker.get_sources("nonexistent_field") == []

    def test_get_confidence_unknown_pair(self) -> None:
        """get_confidence for an unregistered (field, source) pair should return 0.0."""
        tracker = ProvenanceTracker()
        assert tracker.get_confidence("full_name", "resume") == pytest.approx(0.0)

    def test_clear_resets_registry(self) -> None:
        """clear() should remove all registered entries."""
        tracker = ProvenanceTracker()
        tracker.register("full_name", "ats", 0.95)
        tracker.clear()
        assert tracker.get_sources("full_name") == []
