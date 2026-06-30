"""Canonical skill name mapping table.

``SKILL_ALIASES`` maps lowercase abbreviations and alternate spellings to
their canonical form.  The normalizer stage uses this table to convert raw
skill tokens extracted from resumes (e.g. ``"py"``, ``"k8s"``) into the
standardized names stored in the canonical ``Candidate`` model.

Usage example::

    from app.constants.skills import SKILL_ALIASES

    raw = "py"
    canonical = SKILL_ALIASES.get(raw.lower(), raw)  # -> "Python"
"""

# ---------------------------------------------------------------------------
# Alias → Canonical mapping
# Keys must be lowercase; values are the display-ready canonical names.
# ---------------------------------------------------------------------------

SKILL_ALIASES: dict[str, str] = {
    # Python
    "py": "Python",
    "python3": "Python",
    "python 3": "Python",
    # JavaScript / TypeScript
    "js": "JavaScript",
    "javascript": "JavaScript",
    "es6": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    # Databases
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "psql": "PostgreSQL",
    "mongo": "MongoDB",
    "mongodb": "MongoDB",
    # Container orchestration / infrastructure
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "tf": "Terraform",
    "terraform": "Terraform",
    # Cloud platforms
    "aws": "AWS",
    "amazon web services": "AWS",
    "gcp": "GCP",
    "google cloud": "GCP",
    # Machine / Deep learning
    "ml": "Machine Learning",
    "machine learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep learning": "Deep Learning",
    # APIs
    "rest": "REST APIs",
    "rest apis": "REST APIs",
    "restful": "REST APIs",
    # Data / query languages
    "sql": "SQL",
    "nosql": "NoSQL",
    # Frameworks and tools (single canonical form, aliased to self)
    "docker": "Docker",
    "react": "React",
    "django": "Django",
    "flask": "Flask",
    "redis": "Redis",
    "graphql": "GraphQL",
    # Shell / OS
    "bash": "Bash",
    "shell": "Bash",
    "linux": "Linux",
    # Source control / CI
    "git": "Git",
    "github": "Git",
    "ci/cd": "CI/CD",
    # Methodologies
    "agile": "Agile",
    "scrum": "Scrum",
}
