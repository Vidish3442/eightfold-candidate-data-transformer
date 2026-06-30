# Multi-Source Candidate Data Transformer

A production-quality Python pipeline that ingests candidate data from an ATS JSON export and a resume (PDF or plain text), normalizes and merges the two sources, and emits a single canonical candidate profile with field-level provenance and confidence scores.

---

## Features

- Reads **ATS JSON** and **Resume (.txt or .pdf)**
- Normalizes phones → E.164, dates → YYYY-MM, skills → canonical names, location → ISO country codes
- Merges both sources with configurable field-level source priority
- Fuzzy deduplication of skills, experience, and education entries
- Per-field **provenance tracking** (which source contributed each value)
- Per-field and overall **confidence scores**
- Runtime-configurable output via `config.yaml` — no code changes needed
- Outputs `canonical_profile.json` (full) and `transformed_profile.json` (projected/renamed per config)

---

## Project Structure

```
eightfold-candidate-transformer/
├── main.py                      # Entry point
├── cli.py                       # Typer CLI definition
├── config.yaml                  # Runtime configuration
├── requirements.txt
│
├── app/
│   ├── pipeline.py              # Orchestrates all 14 stages
│   ├── models/                  # Pydantic schemas (Candidate, Education, Experience, etc.)
│   ├── readers/                 # ATSReader, ResumeReader
│   ├── parsers/                 # ResumeParser (section splitter)
│   ├── extractors/              # Email, Phone, Skill, Education, Experience, Certification
│   ├── normalizers/             # Phone (E.164), Date (YYYY-MM), Skills, Location
│   ├── matcher/                 # CandidateMatcher (email / phone / fallback)
│   ├── merger/                  # MergeEngine (config-driven conflict resolution)
│   ├── provenance/              # ProvenanceTracker
│   ├── confidence/              # ConfidenceEngine
│   ├── config/                  # ConfigLoader + ConfigValidator
│   ├── projection/              # Projector (field selection, rename, missing policy)
│   ├── validator/               # OutputValidator (Pydantic re-validation)
│   ├── writers/                 # JsonWriter
│   ├── constants/               # SKILL_ALIASES, SOURCE_WEIGHTS, regex patterns
│   └── utils/                   # PipelineLogger, helpers
│
├── data/
│   ├── input/
│   │   ├── ats.json             # ATS candidate export
│   │   └── resume.txt           # Resume (plain text or .pdf)
│   └── output/
│       ├── canonical_profile.json
│       └── transformed_profile.json
│
├── tests/
│   ├── test_phone.py
│   ├── test_date.py
│   ├── test_extractors.py
│   ├── test_matcher.py
│   ├── test_merge.py
│   └── test_resume_parser.py
│
└── docs/
```

---

## Installation

**Requires Python 3.10+** (tested on `stockenv` conda environment with Python 3.10).

### Using conda (recommended)

```bash
conda activate stockenv
pip install -r requirements.txt
```

### Using pip in a virtualenv

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

---

## Usage

### Run the pipeline

```bash
conda run -n stockenv python main.py \
  --ats data/input/ats.json \
  --resume data/input/resume.txt \
  --config config.yaml \
  --output data/output
```

Or if your environment is already active:

```bash
python main.py --ats data/input/ats.json --resume data/input/resume.txt --config config.yaml --output data/output
```

### CLI options

| Flag | Default | Description |
|---|---|---|
| `--ats` | `data/input/ats.json` | Path to ATS JSON input file |
| `--resume` | `data/input/resume.txt` | Path to resume file (`.txt` or `.pdf`) |
| `--config` | `config.yaml` | Path to runtime config file |
| `--output` | `data/output` | Output directory for JSON files |

### Run the tests

```bash
conda run -n stockenv python -m pytest tests/ -v
```

---

## Configuration

All output shaping is controlled by `config.yaml` — no code changes needed.

```yaml
# Which fields to include in transformed_profile.json
fields:
  - full_name
  - email
  - phone
  - skills
  - education
  - experience

# Rename output keys
rename:
  phone: mobile
  full_name: name

# Toggle metadata in output
include_confidence: true
include_provenance: true

# What to do with missing fields: null | omit | "N/A"
missing_policy: null

# Source priority and merge strategies per field
source_priority:
  email:
    - ats
    - resume
  phone:
    - ats
    - resume
  full_name:
    - ats
    - resume
  skills:
    merge: union
  education:
    merge: union
  experience:
    merge: union

# Fuzzy matching threshold for candidate identity matching
matching:
  fuzzy_threshold: 85
```

**To change which source wins for a field**, edit `source_priority` — no code changes needed.  
**To omit null fields**, set `missing_policy: omit`.  
**To hide provenance** from the output, set `include_provenance: false`.

---

## Output

Two files are written to `data/output/`:

### `canonical_profile.json`
The complete merged record with all fields, provenance entries, and confidence scores.

```json
{
  "candidate_id": "ATS-2026-001",
  "full_name": "Vidish Kumar",
  "emails": ["vidishkumar890@gmail.com"],
  "phones": ["+919654403155"],
  "location": { "city": "Greater Noida", "state": "Uttar Pradesh", "country": "IN" },
  "skills": ["Algorithms", "C++", "Deep Learning", "Flask", "Python", ...],
  "experience": [
    {
      "title": "AI/ML Virtual Intern",
      "company": "Infosys",
      "start_date": "2026-01",
      "end_date": "2026-03",
      "bullets": ["Developed an LLM-powered stock screener...", ...]
    }
  ],
  "education": [
    {
      "institution": "Noida Institute of Engineering and Technology",
      "degree": "B.Tech Computer Science and Business Systems",
      "start_date": "2023-08",
      "end_date": "2027-06"
    }
  ],
  "overall_confidence": 0.9639,
  "provenance": [...]
}
```

### `transformed_profile.json`
The projected output shaped by `config.yaml` (selected fields, renames, missing policy applied).

---

## Pipeline Stages

```
ATS JSON ──┐
           ├─► Readers ─► Parser (resume) ─► Extractors ─► Normalizers
Resume     ┘
           └─► Matcher ─► Merge Engine (+Provenance) ─► Confidence Engine
               ─► Canonical Profile ─► Validator ─► Projector ─► Writer ─► Output JSON
```

1. **Config** — load and validate `config.yaml`
2. **Read ATS** — parse JSON into `ATSCandidate`
3. **Read Resume** — extract raw text (PDF via PyMuPDF or `.txt` direct read)
4. **Parse** — split resume text into labeled sections (EXPERIENCE, EDUCATION, SKILLS, etc.)
5. **Extract** — per-field extractors pull emails, phones, skills, education, experience, certifications
6. **Normalize** — phones → E.164, dates → YYYY-MM, skills → canonical names, location → ISO codes
7. **Match** — confirm ATS and resume belong to the same candidate (email → phone → fallback)
8. **Merge** — config-driven conflict resolution; fuzzy dedup for skills/experience/education
9. **Confidence** — per-field scores + weighted `overall_confidence`
10. **Provenance** — build audit trail of which source contributed each field
11. **Validate** — Pydantic schema re-validation before output
12. **Project** — apply `config.yaml` field selection, renames, and missing policy
13. **Write** — emit `canonical_profile.json` and `transformed_profile.json`

---

## Design Decisions

- **ATS > Resume** by default for scalar fields (name, email, phone) — ATS data is structured and verified; resume is self-reported. Override per-field in `config.yaml`.
- **Union + fuzzy dedup** for list fields (skills, experience, education) — rapidfuzz `token_sort_ratio ≥ 85` collapses near-duplicates like "py" and "Python".
- **Education matching by institution name only** — avoids false misses when ATS stores "B.Tech Computer Science" and the resume stores "Bachelor of Technology" as separate fields.
- **Provenance is a side effect of merge** — `ProvenanceTracker` is written to inside each merge helper, keeping conflict-resolution logic separate from audit-trail construction.
- **Confidence is additive** — agreement between sources adds a boost; normalization failure subtracts a penalty; all capped at 0.99.
- **No hardcoded precedence** — every priority rule lives in `config.yaml`.

---

## Tech Stack

Python 3.10 · Pydantic · PyMuPDF · phonenumbers · dateparser · rapidfuzz · pycountry · PyYAML · Typer
