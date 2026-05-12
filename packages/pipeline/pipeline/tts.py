"""Text-to-speech stage.

Renders each script segment (plus intro/outro) into audio bytes via ElevenLabs.
Segments are processed concurrently with a cap to respect API limits.
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from elevenlabs.client import AsyncElevenLabs
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .config import Settings
from .types import AudioSegment, Script, ScriptSegment


# eleven_multilingual_v2: best quality, slower. Use for production.
# eleven_turbo_v2_5: 2-3x faster, slight quality dip. Use for dev iteration.
TTS_MODEL = "eleven_multilingual_v2"

# Output format: 44.1kHz mono mp3 at 128kbps.
# Plenty of fidelity for spoken word; smaller files than 192kbps.
OUTPUT_FORMAT = "mp3_44100_128"

# Voice settings — tuned for news narration.
# stability=0.5: varied delivery without going off the rails
# similarity_boost=0.75: stays close to the chosen voice's character
# style=0.0: no exaggeration (would sound theatrical for news)
# use_speaker_boost=True: slight enhancement, free quality bump
VOICE_SETTINGS = {
    "stability": 0.5,
    "similarity_boost": 0.75,
    "style": 0.0,
    "use_speaker_boost": True,
}

# Max concurrent ElevenLabs requests.
# Free tier: 2 concurrent. Starter: 3. Creator: 5.
# Keep at 2 to be safe across plans.
TTS_CONCURRENCY = 2


def _get_client(settings: Settings | None = None) -> AsyncElevenLabs:
    settings = settings or Settings()
    return AsyncElevenLabs(api_key=settings.elevenlabs_api_key)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _synthesize_one(
    client: AsyncElevenLabs,
    text: str,
    voice_id: str,
) -> bytes:
    """Render a single chunk of text to mp3 bytes."""
    audio_stream = client.text_to_speech.convert(
        voice_id=voice_id,
        text=text,
        model_id=TTS_MODEL,
        output_format=OUTPUT_FORMAT,
        voice_settings=VOICE_SETTINGS,
    )

    # The SDK returns an async iterator of bytes chunks; concat them.
    chunks: list[bytes] = []
    async for chunk in audio_stream:
        if chunk:
            chunks.append(chunk)
    return b"".join(chunks)


async def synthesize_script(
    script: Script,
    voice_id: str,
    settings: Settings | None = None,
) -> tuple[bytes, list[AudioSegment], bytes]:
    """Synthesize intro, all segments, and outro concurrently.

    Returns (intro_audio, segment_audios, outro_audio) so the stitcher
    can insert pauses between sections later.
    """
    client = _get_client(settings)
    semaphore = asyncio.Semaphore(TTS_CONCURRENCY)

    async def bounded_synth(text: str) -> bytes:
        async with semaphore:
            return await _synthesize_one(client, text, voice_id)

    # Build the task list: intro, each segment, outro
    intro_task = bounded_synth(script.intro)
    segment_tasks = [bounded_synth(seg.text) for seg in script.segments]
    outro_task = bounded_synth(script.outro)

    print(f"[tts] synthesizing intro + {len(script.segments)} segments + outro "
          f"(concurrency={TTS_CONCURRENCY})...")

    intro_audio, *segment_audios, outro_audio = await asyncio.gather(
        intro_task, *segment_tasks, outro_task
    )

    # Wrap segment audio with their script metadata
    audio_segments: list[AudioSegment] = []
    for seg, audio in zip(script.segments, segment_audios):
        audio_segments.append(
            AudioSegment(
                script=seg,
                audio_bytes=audio,
                duration_sec=0.0,  # filled in by stitch.py
            )
        )

    total_bytes = len(intro_audio) + sum(len(a.audio_bytes) for a in audio_segments) + len(outro_audio)
    print(f"[tts] {total_bytes / 1024:.1f} KB of audio generated")

    return intro_audio, audio_segments, outro_audio