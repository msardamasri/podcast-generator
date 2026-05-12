"""Script generation stage.

Takes the top-ranked articles and produces a structured podcast script
with intro, segments, and outro. Returns a Script object ready for TTS.
"""
from __future__ import annotations

import html
import json
from typing import Literal

from openai import AsyncOpenAI

from ._openai import get_openai_client
from .config import Settings
from .types import Article, Script, ScriptSegment


SCRIPT_MODEL = "gpt-4o-mini"

# Words per minute when read aloud at a natural pace.
# Used to convert "length_min" → approximate word counts per section.
WORDS_PER_MINUTE = 150


# ---------------------------------------------------------------------------
# Style guides per tone
# ---------------------------------------------------------------------------

TONE_GUIDES = {
    "conversational": (
        "Warm, intelligent, like a smart friend explaining the news over coffee. "
        "Contractions, occasional dry humor, casual asides. Never stiff or corporate. "
        "Use 'we', 'you', 'I' freely. First-person host voice."
    ),
    "formal": (
        "Composed, authoritative, NPR-style. Measured pace, full sentences, no slang. "
        "Use 'we' for the show, third person for events. Treat the listener as a professional."
    ),
    "energetic": (
        "Fast-paced, punchy, like a morning radio show. Short sentences. "
        "Strong opinions and reactions. Lots of momentum between stories. "
        "Bring energy without being shouty — think enthusiastic, not manic."
    ),
}


# ---------------------------------------------------------------------------
# JSON schema for structured output
# ---------------------------------------------------------------------------

SCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "intro": {
            "type": "string",
            "description": "Cold-open hook that grabs attention. 2-4 sentences. "
                           "Tease the most interesting story, then give a one-line agenda.",
        },
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Short label for internal use (e.g., 'OpenAI launches GPT-5'). "
                                       "Not spoken in the audio.",
                    },
                    "source_url": {
                        "type": "string",
                        "description": "URL of the source article this segment covers.",
                    },
                    "text": {
                        "type": "string",
                        "description": "What the host actually says. Start with a transition "
                                       "from the previous topic (the model will know what came before). "
                                       "Tell the story with concrete details, then offer one short take. "
                                       "Spoken English: contractions, short sentences, no bullet points.",
                    },
                },
                "required": ["title", "source_url", "text"],
                "additionalProperties": False,
            },
        },
        "outro": {
            "type": "string",
            "description": "Closing remarks. 1-3 sentences. Wrap up the theme of today's stories "
                           "if there is one, sign off naturally. Avoid generic 'thanks for listening'.",
        },
    },
    "required": ["intro", "segments", "outro"],
    "additionalProperties": False,
}


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def _clean_text(text: str) -> str:
    """Decode HTML entities and collapse whitespace.

    RSS feeds frequently leak entities like &#8217; (curly apostrophe).
    These don't render in audio but waste tokens and confuse the model.
    """
    return " ".join(html.unescape(text).split())


def _format_articles_for_prompt(articles: list[Article]) -> str:
    """Render articles as a numbered list for the prompt."""
    lines: list[str] = []
    for i, article in enumerate(articles, 1):
        title = _clean_text(article.title)
        content = _clean_text(article.content or "")[:800]  # cap each article
        lines.append(
            f"[{i}] {title}\n"
            f"Source: {article.outlet} — {article.url}\n"
            f"Content: {content}\n"
        )
    return "\n".join(lines)


def _build_system_prompt(
    length_min: int,
    tone: Literal["conversational", "formal", "energetic"],
    num_segments: int,
) -> str:
    """Construct the system prompt with tone and pacing guidance."""
    tone_guide = TONE_GUIDES[tone]
    total_words = length_min * WORDS_PER_MINUTE
    body_words = int(total_words * 0.9)
    words_per_segment = body_words // max(num_segments, 1)

    return f"""You are the host and writer of a personalized daily news podcast. \
You write the script that you'll read aloud — every word will be spoken by a \
text-to-speech engine, so the script must sound natural when read out loud.

VOICE AND TONE:
{tone_guide}

LENGTH TARGET:
The full episode should be about {length_min} minutes of spoken audio, which is \
roughly {total_words} words. Plan for:
- Intro: ~80-120 words
- Each of the {num_segments} segments: ~{words_per_segment} words
- Outro: ~50-80 words

Vary segment length within that average. The most important story gets more time.

HOW TO OPEN (the intro):
Open with a concrete, surprising fact from one of today's stories. Then preview \
the rest in one short sentence. That's it. No greetings, no "welcome", no \
"imagine a world", no "let's get into it".

Good cold opens (study these):
- "Mira Murati spent the last year very quietly. Now we know what she was building — \
and it's not just another chatbot."
- "Nvidia put forty billion dollars into AI startups this year. Thirty of those \
billion went to one company. That's the story, but it's not the most interesting \
one I've got for you today."

HOW TO CLOSE EACH SEGMENT (the take):
After the facts, give ONE specific opinion or observation. Not a question. \
Not a generalization. A claim a real person would make.

Bad (rhetorical question — AI tell): "Will this rally last, or is it just a bubble?"
Good (specific claim): "I'm skeptical. Robinhood's whole pitch is retail traders \
chasing the next thing, and the next thing always pops first."

Bad (vague gesture): "It's a stark reminder of how AI is reshaping everything."
Good (concrete take): "What's striking is that GM didn't retrain those workers. \
They were cheaper to replace than to teach. That's the real story here."

Bad (clickbait question): "What happens to workers who can't keep up?"
Good (real observation): "The interesting thing isn't the layoffs — it's that \
nobody's pretending these are different jobs anymore. They're the same jobs, \
done by different people."

HOW TO TRANSITION BETWEEN SEGMENTS:
Thread the stories. Find the connective tissue — a shared theme, a contrast, \
a follow-the-money link. Good transitions feel inevitable, like the host \
spotted something the listener missed.

Good: "That AI investment frenzy isn't just hitting startups — it's reshaping \
power markets too."
Good: "Speaking of jobs disappearing into AI..."
Good: "Which makes the next story feel almost predictable."

Bad: "Next up", "Moving on", "In other news", "Let's talk about".

HOW TO CLOSE (the outro):
Reference one specific story from the episode, or note a pattern across them. \
End on a sharp line, not a wave. No "until next time", no "stay tuned", no \
"keep an eye on these trends".

Good: "If you've been wondering what 'AI eating jobs' actually looks like in \
practice, today was the answer."
Good: "Three stories today, three different bets on AI. We'll see which one ages well."

WRITE FOR THE EAR:
- Contractions: "it's", "they're", "we've". Always.
- Short sentences. If a sentence has two commas, split it.
- No bullet points, no lists, no headings, no parentheticals.
- Numbers spoken aloud: write "$30 billion" as "thirty billion dollars" \
when it appears mid-sentence, but TTS can handle "$30B" too — use your judgment.
- No phrases that scream AI: "delve", "navigate the landscape", "in today's \
fast-paced world", "the rise of", "imagine a world", "let's get into it", \
"buckle up", "dive deep", "unpack".

SOURCE ATTRIBUTION:
Mention the outlet naturally at least once per segment. "According to TechCrunch", \
"The Verge is reporting". Helps trust and tells the listener where to read more.

FACTUAL DISCIPLINE:
Only state facts that appear in the source articles. Specific numbers, names, \
and quotes are good — but if the article doesn't have them, don't invent them.

Return a JSON object matching the schema. No markdown in any field.
"""


def _build_user_prompt(articles: list[Article]) -> str:
    return (
        "Here are the articles to cover in today's episode, ranked by relevance "
        "to the listener's interests:\n\n"
        f"{_format_articles_for_prompt(articles)}\n\n"
        "Write the podcast script. Cover the articles in an order that flows well "
        "(this is not necessarily the order given — group related stories together). "
        "Skip an article if it doesn't fit the flow, but cover at least the top 5."
    )


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

async def generate_script(
    articles: list[Article],
    length_min: int = 10,
    tone: Literal["conversational", "formal", "energetic"] = "conversational",
    settings: Settings | None = None,
) -> Script:
    """Generate a structured podcast script from ranked articles.

    The number of articles in the input controls roughly how many segments
    we ask for — but the model can drop or merge stories if pacing requires.
    """
    if not articles:
        raise ValueError("Cannot generate script from empty article list")

    client = get_openai_client(settings)

    system_prompt = _build_system_prompt(
        length_min=length_min,
        tone=tone,
        num_segments=len(articles),
    )
    user_prompt = _build_user_prompt(articles)

    response = await client.chat.completions.create(
        model=SCRIPT_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "podcast_script",
                "strict": True,
                "schema": SCRIPT_SCHEMA,
            },
        },
        temperature=0.7,  # some creativity, but not chaotic
    )

    raw = response.choices[0].message.content
    data = json.loads(raw)

    # Build the Script object. We attribute outlet from the article list
    # (matched by URL) so the model can't hallucinate an outlet name.
    url_to_outlet = {a.url: a.outlet for a in articles}
    segments: list[ScriptSegment] = []
    for i, seg in enumerate(data["segments"]):
        outlet = url_to_outlet.get(seg["source_url"], "Unknown")
        segments.append(
            ScriptSegment(
                idx=i,
                title=seg["title"],
                source_url=seg["source_url"],
                source_outlet=outlet,
                text=seg["text"],
            )
        )

    script = Script(intro=data["intro"], segments=segments, outro=data["outro"])

    total_words = (
        len(script.intro.split())
        + sum(len(s.text.split()) for s in segments)
        + len(script.outro.split())
    )
    print(f"[script] generated {len(segments)} segments, ~{total_words} words "
          f"(~{total_words / WORDS_PER_MINUTE:.1f} min target)")
    return script