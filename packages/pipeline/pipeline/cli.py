"""Command-line entry point for the pipeline.

Usage:
    python -m pipeline --interests "AI,startups,F1" --length 5 --output ./episode.mp3

Constructs a PipelineConfig from CLI args, runs the full pipeline,
and prints the resulting transcript path.
"""
from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from dotenv import load_dotenv

from .config import Interest, PipelineConfig
from .fetch import fetch_articles, enrich_top_articles
from .rank import rank_articles
from .script import generate_script
from .stitch import stitch_audio
from .tts import synthesize_script
from .types import PipelineResult


async def run_pipeline(config: PipelineConfig) -> PipelineResult:
    """Run the full pipeline. Each stage prints its own progress."""
    report = config.progress_callback or (lambda *_: None)

    report("fetching", 0.0)
    articles = await fetch_articles(config.interests, since_hours=config.since_hours)

    report("ranking", 0.2)
    top = await rank_articles(
        articles, config.interests, config.exclusions, top_k=config.max_articles
    )

    report("enriching", 0.35)
    top = await enrich_top_articles(top, top_n=config.max_articles)

    report("scripting", 0.45)
    script = await generate_script(top, length_min=config.length_min, tone=config.tone)

    report("synthesizing", 0.6)
    intro_audio, segment_audios, outro_audio = await synthesize_script(
        script, voice_id=config.voice_id
    )

    report("stitching", 0.9)
    result = stitch_audio(
        intro_audio, segment_audios, outro_audio,
        script=script,
        output_path=config.output_path,
    )

    report("done", 1.0)
    return result


def main() -> None:
    """CLI entry point — defined in pyproject.toml as `pipeline = "pipeline.cli:main"`."""
    load_dotenv()

    parser = argparse.ArgumentParser(description="Generate a personal news podcast.")
    parser.add_argument(
        "--interests",
        type=str,
        required=True,
        help="Comma-separated interests, e.g. 'AI,startups,F1'",
    )
    parser.add_argument(
        "--exclusions",
        type=str,
        default="",
        help="Comma-separated topics to avoid",
    )
    parser.add_argument("--length", type=int, default=5, choices=[5, 10, 20])
    parser.add_argument(
        "--tone",
        type=str,
        default="conversational",
        choices=["conversational", "formal", "energetic"],
    )
    parser.add_argument(
        "--voice-id",
        type=str,
        default="21m00Tcm4TlvDq8ikWAM",  # Rachel
    )
    parser.add_argument("--output", type=str, default="./output.mp3")
    parser.add_argument(
        "--since-hours", type=int, default=24, help="Look-back window for articles"
    )
    parser.add_argument(
        "--max-articles", type=int, default=6, help="Number of articles to cover"
    )

    args = parser.parse_args()

    interests = [
        Interest(label=label.strip(), weight=1.0)
        for label in args.interests.split(",")
        if label.strip()
    ]
    exclusions = [e.strip() for e in args.exclusions.split(",") if e.strip()]

    config = PipelineConfig(
        interests=interests,
        exclusions=exclusions,
        length_min=args.length,
        tone=args.tone,
        voice_id=args.voice_id,
        max_articles=args.max_articles,
        since_hours=args.since_hours,
        output_path=str(Path(args.output).absolute()),
    )

    result = asyncio.run(run_pipeline(config))

    print("\n" + "=" * 60)
    print(f"✓ Podcast ready: {result.audio_path}")
    print(f"  Duration: {result.duration_sec}s ({result.duration_sec / 60:.1f} min)")
    print(f"  Segments: {len(result.segments)}")
    print("=" * 60)


if __name__ == "__main__":
    main()