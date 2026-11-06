"""
gemini_service.py
─────────────────
Gemini API integration for EnviroLearn.
Provides two functions:
  1. generate_quiz()   – dynamic MCQ generation for video quizzes
  2. verify_image()    – AI image relevance check for challenge submissions
"""

import os
import json
import logging
import google.generativeai as genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

# ── Initialise Gemini ─────────────────────────────────────────────

def _get_model(model_name="gemini-1.5-flash"):
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in environment variables.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


# ── Video topic descriptions (used because MP4s have no transcripts) ─

VIDEO_TOPICS = {
    1: {
        "name": "Pollution",
        "description": (
            "Types of pollution: air, water, land, and noise pollution. "
            "Causes include vehicle emissions, industrial waste, plastic dumping, burning of fossil fuels. "
            "Effects on human health, wildlife, and ecosystems. "
            "Prevention methods: planting trees, recycling, using public transport, reducing plastic use."
        )
    },
    2: {
        "name": "Global Warming",
        "description": (
            "Greenhouse gases (CO2, methane) trap heat in the atmosphere causing global temperature rise. "
            "Human activities: deforestation, burning coal and oil, agriculture. "
            "Effects: melting polar ice caps, rising sea levels, extreme weather events, habitat loss. "
            "Solutions: renewable energy (solar, wind), energy efficiency, reforestation, reducing emissions."
        )
    },
    3: {
        "name": "Biodiversity",
        "description": (
            "Biodiversity is the variety of all living organisms on Earth. "
            "Ecosystems depend on diverse species for balance and function. "
            "Threats: deforestation, habitat destruction, pollution, climate change, invasive species. "
            "Conservation: wildlife sanctuaries, national parks, protecting habitats, sustainable farming."
        )
    },
}

# ── Challenge descriptions for image verification ─────────────────

CHALLENGE_DESCRIPTIONS = {
    1: "Student has cleaned their personal study area or desk, making it neat and tidy.",
    2: "Student is segregating waste into separate bins for wet waste, dry waste, and e-waste.",
    3: "Student is saving energy by switching off lights, fans, or electronics when not in use.",
    4: "Student is watering or caring for a plant at home or school.",
    5: "Student participated in a cleanup drive, collecting trash from a public area.",
    6: "Student has organized their school bag neatly with books and stationery in order.",
    7: "Student is saving water by turning off taps, using a bucket instead of a hose, or reusing water.",
    8: "Student is using a cloth bag instead of a plastic bag while shopping or carrying items.",
}


# ══════════════════════════════════════════════════════════════════
# 1.  DYNAMIC QUIZ GENERATION
# ══════════════════════════════════════════════════════════════════

def generate_quiz(video_id: int, previous_questions: list[str] | None = None) -> list[dict]:
    """
    Generate 5 MCQs for the given video topic using Gemini.

    Parameters
    ----------
    video_id : int
        1 = Pollution, 2 = Global Warming, 3 = Biodiversity
    previous_questions : list[str] | None
        List of question texts from previous attempts to avoid repeating.

    Returns
    -------
    list[dict]  – exactly 5 items, each:
        {
          "question":     str,
          "options":      [str, str, str, str],   # always 4 options
          "correct_index": int,                   # 0-based
          "explanation":  str
        }

    Raises
    ------
    ValueError  – if Gemini returns unparseable / invalid JSON.
    Exception   – propagated from google-generativeai on network / quota errors.
    """

    topic = VIDEO_TOPICS.get(video_id)
    if not topic:
        raise ValueError(f"Unknown video_id: {video_id}")

    avoid_block = ""
    if previous_questions:
        formatted = "\n".join(f"- {q}" for q in previous_questions[:15])
        avoid_block = f"\n\nIMPORTANT: Do NOT repeat any of these previously used questions:\n{formatted}"

    prompt = f"""You are an educational quiz generator for school students (Grade 5–8).

Topic: {topic['name']}
Topic description: {topic['description']}

Generate exactly 5 multiple-choice questions about this topic.{avoid_block}

Requirements:
- Each question must have exactly 4 answer options (A, B, C, D).
- Exactly one option is correct.
- Language must be simple, clear, and appropriate for school children.
- Questions must test understanding, not just recall.
- Include a brief explanation (1-2 sentences) for why the correct answer is right.

Respond with ONLY a valid JSON array. No markdown, no code fences, no extra text.

Format:
[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "Brief explanation of why this is correct."
  }},
  ...
]"""

    model = _get_model()
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if Gemini wraps the JSON anyway
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned non-JSON response: %s", raw[:500])
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc

    if not isinstance(questions, list) or len(questions) == 0:
        raise ValueError("Gemini returned an empty or non-list response.")

    # Validate and sanitise each question
    validated = []
    for i, q in enumerate(questions[:5]):
        if not isinstance(q, dict):
            continue
        opts = q.get("options", [])
        correct = q.get("correct_index", 0)
        if not isinstance(opts, list) or len(opts) != 4:
            continue
        if not isinstance(correct, int) or correct not in range(4):
            continue
        validated.append({
            "question":      str(q.get("question", f"Question {i+1}")),
            "options":       [str(o) for o in opts],
            "correct_index": correct,
            "explanation":   str(q.get("explanation", "")),
        })

    if len(validated) < 3:
        raise ValueError(f"Gemini returned only {len(validated)} valid questions (minimum 3 required).")

    return validated


# ══════════════════════════════════════════════════════════════════
# 2.  IMAGE VERIFICATION
# ══════════════════════════════════════════════════════════════════

def verify_image(image_bytes: bytes, challenge_id: int) -> dict:
    """
    Verify whether an uploaded image matches the environmental challenge.

    Parameters
    ----------
    image_bytes : bytes   – raw image file bytes
    challenge_id : int    – 1-8

    Returns
    -------
    dict:
        {
          "status":      "relevant" | "not_relevant" | "uncertain" | "ai_unavailable",
          "confidence":  float (0.0–1.0),
          "explanation": str
        }
    """
    description = CHALLENGE_DESCRIPTIONS.get(challenge_id, "An environmental activity.")

    try:
        model = _get_model()
        image = Image.open(io.BytesIO(image_bytes))

        prompt = f"""You are an AI verifying student submissions for an environmental education platform.

The student was assigned this challenge:
"{description}"

Examine the uploaded image carefully.

Determine:
1. Does the image clearly show the student completing or attempting the described challenge?
2. Is the image relevant, irrelevant, or uncertain?

Respond with ONLY a valid JSON object. No markdown, no extra text.

Format:
{{
  "status": "relevant" or "not_relevant" or "uncertain",
  "confidence": <float between 0.0 and 1.0>,
  "explanation": "<1-2 sentence explanation of your decision>"
}}

Use:
- "relevant"      if the image clearly matches the challenge
- "not_relevant"  if the image clearly does not match the challenge
- "uncertain"     if you cannot determine from the image alone"""

        response = model.generate_content([prompt, image])
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)

        status = result.get("status", "uncertain")
        if status not in ("relevant", "not_relevant", "uncertain"):
            status = "uncertain"

        confidence = float(result.get("confidence", 0.5))
        confidence = max(0.0, min(1.0, confidence))

        return {
            "status":      status,
            "confidence":  confidence,
            "explanation": str(result.get("explanation", "")),
        }

    except EnvironmentError as exc:
        logger.error("Gemini API key not configured: %s", exc)
        return {"status": "ai_unavailable", "confidence": 0.0, "explanation": "AI verification unavailable (API key missing)."}

    except Exception as exc:
        logger.error("Gemini image verification failed: %s", exc)
        return {"status": "ai_unavailable", "confidence": 0.0, "explanation": "AI verification temporarily unavailable. Submission forwarded to teacher."}
