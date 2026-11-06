"""
gemini_service.py
─────────────────
EnviroLearn AI services using Google Gemini API only.
No torch, no CLIP, no transformers needed.

1. generate_quiz()  – Dynamic MCQ generation via Gemini text
2. verify_image()   – Challenge photo verification via Gemini Vision
"""

import os
import io
import json
import logging

from dotenv import load_dotenv
from PIL import Image
import google.generativeai as genai

load_dotenv()

logger = logging.getLogger(__name__)

# ── Gemini model (flash = free tier, fast) ────────────────────────
GEMINI_MODEL = "gemini-1.5-flash"

# ── Lazy client ───────────────────────────────────────────────────
_model = None

def _get_model():
    global _model
    if _model is not None:
        return _model
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY is not set in environment variables.")
    genai.configure(api_key=api_key)
    _model = genai.GenerativeModel(GEMINI_MODEL)
    return _model


# ══════════════════════════════════════════════════════════════════
# VIDEO TOPIC DESCRIPTIONS
# ══════════════════════════════════════════════════════════════════

VIDEO_TOPICS = {
    1: {
        "name": "Pollution",
        "description": (
            "Types of pollution: air, water, land, and noise pollution. "
            "Causes include vehicle emissions, industrial waste, plastic "
            "dumping, burning of fossil fuels. Effects on human health, "
            "wildlife, and ecosystems. Prevention methods: planting trees, "
            "recycling, using public transport, reducing plastic use."
        )
    },
    2: {
        "name": "Global Warming",
        "description": (
            "Greenhouse gases such as CO2 and methane trap heat in the "
            "atmosphere, causing global temperature rise. Human activities "
            "include deforestation, burning coal and oil, and agriculture. "
            "Effects include melting polar ice caps, rising sea levels, "
            "extreme weather events, and habitat loss. Solutions include "
            "renewable energy, reforestation, and reducing emissions."
        )
    },
    3: {
        "name": "Biodiversity",
        "description": (
            "Biodiversity is the variety of all living organisms on Earth. "
            "Ecosystems depend on diverse species for balance and function. "
            "Threats include deforestation, habitat destruction, pollution, "
            "climate change, and invasive species. Conservation includes "
            "wildlife sanctuaries, national parks, habitat protection, "
            "and sustainable farming."
        )
    }
}


# ══════════════════════════════════════════════════════════════════
# CHALLENGE DESCRIPTIONS (for image verification)
# ══════════════════════════════════════════════════════════════════

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
# 1. DYNAMIC QUIZ GENERATION
# ══════════════════════════════════════════════════════════════════

def generate_quiz(video_id: int, previous_questions: list | None = None) -> list:
    """
    Generate 5 MCQs for the given video topic using Gemini.

    Parameters
    ----------
    video_id : int          1=Pollution, 2=GlobalWarming, 3=Biodiversity
    previous_questions :    list of past question strings to avoid repeating

    Returns
    -------
    list of dicts: [{question, options:[4], correct_index, explanation}]
    """

    topic = VIDEO_TOPICS.get(video_id)
    if not topic:
        raise ValueError(f"Unknown video_id: {video_id}")

    avoid_block = ""
    if previous_questions:
        formatted = "\n".join(f"- {q}" for q in previous_questions[:15])
        avoid_block = f"\n\nDo NOT repeat or paraphrase these previously used questions:\n{formatted}"

    prompt = f"""You are an educational quiz generator for school students (Grade 5-8).

Topic: {topic['name']}
Description: {topic['description']}

Generate exactly 5 multiple-choice questions about this topic.{avoid_block}

Requirements:
- Each question must have exactly 4 options (A, B, C, D)
- Exactly 1 correct answer per question
- Simple language suitable for school students
- Include a 1-2 sentence explanation for the correct answer
- All facts must be accurate

Respond with ONLY a valid JSON array. No markdown, no code fences, no extra text.

[
  {{
    "question": "Question text here?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "Explanation of why this answer is correct."
  }}
]"""

    model = _get_model()
    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        questions = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Gemini returned non-JSON: %s", raw[:300])
        raise ValueError(f"Gemini returned invalid JSON: {exc}") from exc

    if not isinstance(questions, list):
        raise ValueError("Gemini response is not a JSON list.")

    validated = []
    for q in questions[:5]:
        if not isinstance(q, dict):
            continue
        opts    = q.get("options", [])
        correct = q.get("correct_index", 0)
        if not isinstance(opts, list) or len(opts) != 4:
            continue
        if not isinstance(correct, int) or correct not in range(4):
            continue
        validated.append({
            "question":      str(q.get("question", "")),
            "options":       [str(o) for o in opts],
            "correct_index": correct,
            "explanation":   str(q.get("explanation", "")),
        })

    if len(validated) < 3:
        raise ValueError(f"Only {len(validated)} valid questions generated (need at least 3).")

    return validated


# ══════════════════════════════════════════════════════════════════
# 2. IMAGE VERIFICATION VIA GEMINI VISION
# ══════════════════════════════════════════════════════════════════

def verify_image(image_bytes: bytes, challenge_id: int) -> dict:
    """
    Verify whether an uploaded photo matches the environmental challenge
    using Gemini Vision multimodal API.

    Returns
    -------
    dict:
        status      : "relevant" | "not_relevant" | "uncertain" | "ai_unavailable"
        confidence  : float 0.0–1.0
        explanation : str
    """

    description = CHALLENGE_DESCRIPTIONS.get(challenge_id, "An environmental activity.")

    try:
        model  = _get_model()
        image  = Image.open(io.BytesIO(image_bytes))

        prompt = f"""You are verifying a student's environmental challenge photo submission.

The student was assigned this challenge:
"{description}"

Look at the uploaded image carefully and determine:
- Does it clearly show the student completing or attempting the described challenge?

Respond with ONLY a valid JSON object. No extra text, no markdown.

{{
  "status": "relevant" or "not_relevant" or "uncertain",
  "confidence": <float between 0.0 and 1.0>,
  "explanation": "<1-2 sentence explanation>"
}}

Use:
  "relevant"     – image clearly matches the challenge
  "not_relevant" – image clearly does not match
  "uncertain"    – cannot determine from image alone"""

        response = model.generate_content([prompt, image])
        raw = response.text.strip()

        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result     = json.loads(raw)
        status     = result.get("status", "uncertain")
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
        logger.error("Gemini API key missing: %s", exc)
        return {"status": "ai_unavailable", "confidence": 0.0,
                "explanation": "AI verification unavailable — API key not set."}

    except Exception as exc:
        logger.error("Gemini image verification failed: %s", exc)
        return {"status": "ai_unavailable", "confidence": 0.0,
                "explanation": "AI verification temporarily unavailable. Forwarded to teacher for manual review."}
