"""CLI entry point — Typer-based command-line interface for the Candidate Data Transformer."""

import typer
from pathlib import Path
from app.pipeline import Pipeline

app = typer.Typer(help="Multi-Source Candidate Data Transformer")


@app.command()
def run(
    ats: Path = typer.Option(
        Path("data/input/ats.json"),
        "--ats",
        help="Path to ATS JSON input file.",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    resume: Path = typer.Option(
        Path("data/input/resume.txt"),
        "--resume",
        help="Path to resume file (PDF or .txt).",
    ),
    config: Path = typer.Option(
        Path("config.yaml"),
        "--config",
        help="Path to config.yaml.",
    ),
    output: Path = typer.Option(
        Path("data/output"),
        "--output",
        help="Output directory for generated JSON files.",
    ),
) -> None:
    """Run the full candidate data transformation pipeline.

    Reads ATS JSON and resume file, normalises/merges/deduplicates fields,
    and writes canonical_profile.json and transformed_profile.json to the
    output directory.
    """
    pipeline = Pipeline(
        ats_path=ats,
        resume_path=resume,
        config_path=config,
        output_dir=output,
    )
    results = pipeline.run()
    typer.echo(f"Pipeline complete. overall_confidence={results['canonical'].get('overall_confidence', 'n/a'):.4f}")
