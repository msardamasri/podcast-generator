"""Stitch synthesized audio chunks into a single mp3 file.

Adds:
- Short pauses between segments (natural pacing)
- Slightly longer pauses around intro and outro
- Per-segment start times (for drop-off analytics later)

Returns a PipelineResult with the path, duration, and segment timings.
"""
from __future__ import annotations

import io
from pathlib import Path

from pydub import AudioSegment as PydubSegment

from .types import AudioSegment, PipelineResult, Script, ScriptSegment


# Pause durations in milliseconds.
# These values come from listening — adjust to taste.
PAUSE_AFTER_INTRO_MS = 700      # breath before the first story
PAUSE_BETWEEN_SEGMENTS_MS = 500 # natural beat between stories
PAUSE_BEFORE_OUTRO_MS = 700     # signal the wrap-up


def _bytes_to_audio(data: bytes) -> PydubSegment:
    """Decode mp3 bytes to a pydub AudioSegment for manipulation."""
    return PydubSegment.from_file(io.BytesIO(data), format="mp3")


def stitch_audio(
    intro_audio: bytes,
    segment_audios: list[AudioSegment],
    outro_audio: bytes,
    script: Script,
    output_path: str,
    token_usage: dict[str, int] | None = None,
    cost_cents: int = 0,
) -> PipelineResult:
    """Concatenate all audio into one mp3 with deliberate pauses.

    Also computes per-segment start/end timestamps so the player can
    track which segment is playing for drop-off analytics.
    """
    intro = _bytes_to_audio(intro_audio)
    outro = _bytes_to_audio(outro_audio)

    silence_intro = PydubSegment.silent(duration=PAUSE_AFTER_INTRO_MS)
    silence_between = PydubSegment.silent(duration=PAUSE_BETWEEN_SEGMENTS_MS)
    silence_outro = PydubSegment.silent(duration=PAUSE_BEFORE_OUTRO_MS)

    # Start building the final track
    final = intro + silence_intro
    cursor_ms = len(final)

    # Update each segment with its position in the final audio
    stitched_segments: list[ScriptSegment] = []
    for i, seg in enumerate(segment_audios):
        seg_audio = _bytes_to_audio(seg.audio_bytes)
        seg_duration_ms = len(seg_audio)

        # Record start/end for analytics
        start_sec = cursor_ms / 1000
        end_sec = (cursor_ms + seg_duration_ms) / 1000

        # Update the script segment in place with timing info
        seg.script.start_sec = start_sec
        seg.script.end_sec = end_sec
        seg.duration_sec = seg_duration_ms / 1000
        stitched_segments.append(seg.script)

        final = final + seg_audio
        cursor_ms += seg_duration_ms

        # Pause between segments, but not after the last one (outro pause handles that)
        if i < len(segment_audios) - 1:
            final = final + silence_between
            cursor_ms += PAUSE_BETWEEN_SEGMENTS_MS

    # Outro with leading pause
    final = final + silence_outro + outro

    # Write to disk
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    final.export(
        output_path,
        format="mp3",
        bitrate="128k",
        tags={"title": "Daily Podcast", "artist": "Personal Podcast Generator"},
    )

    duration_sec = len(final) // 1000
    transcript = _build_transcript(script)

    print(f"[stitch] wrote {output_path} — {duration_sec}s, "
          f"{output.stat().st_size / 1024:.1f} KB")

    return PipelineResult(
        audio_path=output_path,
        duration_sec=duration_sec,
        transcript=transcript,
        segments=stitched_segments,
        token_usage=token_usage or {},
        cost_cents=cost_cents,
    )


def _build_transcript(script: Script) -> str:
    """Build a single-string transcript of the full episode."""
    parts: list[str] = [script.intro]
    for seg in script.segments:
        parts.append(f"\n[{seg.source_outlet}] {seg.title}\n{seg.text}")
    parts.append(f"\n{script.outro}")
    return "\n".join(parts)