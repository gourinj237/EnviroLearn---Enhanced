
"""
gemini_service1.py
-----------------
EnviroLearn AI services.

1. Gemini API: Dynamic video quiz generation.
2. CLIP + PyTorch: Environmental challenge image verification.
"""

import os
# import io  # Used only by disabled CLIP image verification
import json
import logging

from dotenv import load_dotenv
# CLIP/PyTorch imports disabled:
# from PIL import Image
# import torch
# from transformers import CLIPModel, CLIPProcessor

from google import genai

load_dotenv()

logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURATION
# ============================================================

GEMINI_MODEL = "gemini-3.8-flash"
# CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

# Gemini client instance
_gemini_client = None
# CLIP/PyTorch model instances disabled:
# _clip_model = None
# _clip_processor = None
# _clip_device = None


# ============================================================
# GEMINI INITIALIZATION
# ============================================================

def _get_gemini_client():
    global _gemini_client

    if _gemini_client is not None:
        return _gemini_client

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise EnvironmentError(
            "GEMINI_API_KEY is not configured in the .env file."
        )

    _gemini_client = genai.Client(api_key=api_key)

    return _gemini_client


# # ============================================================
# # CLIP INITIALIZATION
# # ============================================================

# def _get_clip_model():
#     global _clip_model, _clip_processor, _clip_device

#     if _clip_model is None:

#         logger.info("Loading pretrained CLIP model...")

#         _clip_device = torch.device(
#             "cuda" if torch.cuda.is_available() else "cpu"
#         )

#         _clip_processor = CLIPProcessor.from_pretrained(
#             CLIP_MODEL_NAME
#         )

#         _clip_model = CLIPModel.from_pretrained(
#             CLIP_MODEL_NAME
#         )

#         _clip_model.to(_clip_device)
#         _clip_model.eval()

#         logger.info(
#             "CLIP model loaded successfully on %s",
#             _clip_device
#         )

#     return _clip_model, _clip_processor, _clip_device


# ============================================================
# VIDEO TOPICS
# ============================================================

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


# # ============================================================
# # ENVIRONMENTAL CHALLENGE DESCRIPTIONS
# # ============================================================

# CHALLENGE_DESCRIPTIONS = {
#     1: "Cleaning a personal study area or desk, making it neat and tidy.",

#     2: "Segregating waste into separate bins for wet waste, dry waste, and e-waste.",

#     3: "Saving energy by switching off lights, fans, or electronics when not in use.",

#     4: "Watering or caring for a plant at home or school.",

#     5: "Participating in a cleanup drive and collecting trash from a public area.",

#     6: "Organizing a school bag neatly with books and stationery.",

#     7: "Saving water by turning off taps, using a bucket instead of a hose, or reusing water.",

#     8: "Using a cloth bag instead of a plastic bag while shopping or carrying items."
# }


# ============================================================
# 1. DYNAMIC VIDEO QUIZ GENERATION USING GEMINI
# ============================================================

def generate_quiz(
    video_id: int,
    previous_questions: list[str] | None = None
) -> list[dict]:

    topic = VIDEO_TOPICS.get(video_id)

    if not topic:
        raise ValueError(f"Unknown video_id: {video_id}")

    avoid_block = ""

    if previous_questions:
        formatted = "\n".join(
            f"- {q}" for q in previous_questions[:15]
        )

        avoid_block = f"""
        Do not repeat or closely paraphrase these previous questions:

        {formatted}
        """

    prompt = f"""
    You are an educational quiz generator for school students
    in Grades 5-8.

    Topic: {topic['name']}

    Topic description:
    {topic['description']}

    Generate exactly FIVE different multiple-choice questions.

    {avoid_block}

    Requirements:

    1. Each question must have exactly four options.
    2. Only one option must be correct.
    3. Questions must test understanding and application.
    4. Use simple language suitable for school students.
    5. Avoid duplicate or very similar questions.
    6. Include a short explanation for each answer.
    7. Ensure all questions are factually correct.

    Return ONLY a valid JSON array.

    Format:

    [
        {{
            "question": "Question text?",
            "options": [
                "Option A",
                "Option B",
                "Option C",
                "Option D"
            ],
            "correct_index": 0,
            "explanation": "Explanation here."
        }}
    ]
    """

    client = _get_gemini_client()

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config={
            "response_mime_type": "application/json"
        }
    )

    raw = response.text

    if not raw:
        raise ValueError("Gemini returned an empty response.")

    raw = raw.strip()

    if raw.startswith("```"):
        raw = raw.split("```")[1]

        if raw.startswith("json"):
            raw = raw[4:]

        raw = raw.strip()

    try:
        questions = json.loads(raw)

    except json.JSONDecodeError as exc:
        logger.error(
            "Invalid Gemini JSON response: %s",
            raw[:500]
        )

        raise ValueError(
            "Gemini returned invalid quiz JSON."
        ) from exc

    if not isinstance(questions, list):
        raise ValueError("Gemini response is not a JSON list.")

    validated = []

    for i, q in enumerate(questions[:5]):

        if not isinstance(q, dict):
            continue

        question = q.get("question")
        options = q.get("options")
        correct = q.get("correct_index")
        explanation = q.get("explanation", "")

        if not isinstance(question, str) or not question.strip():
            continue

        if not isinstance(options, list) or len(options) != 4:
            continue

        if not all(isinstance(o, str) and o.strip() for o in options):
            continue

        if (
            isinstance(correct, bool)
            or not isinstance(correct, int)
            or correct not in range(4)
        ):
            continue

        validated.append({
            "question": question.strip(),
            "options": options,
            "correct_index": correct,
            "explanation": str(explanation)
        })

    if len(validated) < 3:
        raise ValueError(
            f"Only {len(validated)} valid questions generated."
        )

    return validated


# # ============================================================
# # 2. CLIP IMAGE VERIFICATION
# # ============================================================

# def verify_image(image_bytes: bytes, challenge_id: int) -> dict:
#     """
#     Verify whether an uploaded photograph visually matches
#     an environmental challenge using CLIP.

#     Returns:
#         {
#             "status": "relevant" | "not_relevant" |
#                       "uncertain" | "ai_unavailable",
#             "confidence": float,
#             "similarity_score": float,
#             "explanation": str
#         }

#     Note:
#         CLIP similarity is not a calibrated probability
#         and does not prove that an activity was performed.
#     """

#     description = CHALLENGE_DESCRIPTIONS.get(challenge_id)

#     if not description:
#         return {
#             "status": "uncertain",
#             "confidence": 0.0,
#             "similarity_score": 0.0,
#             "explanation": "Unknown challenge ID."
#         }

#     try:

#         # Load model only once
#         model, processor, device = _get_clip_model()

#         # Read uploaded image
#         image = Image.open(
#             io.BytesIO(image_bytes)
#         ).convert("RGB")

#         # Positive and negative text descriptions
#         positive_prompts = [
#             f"A photograph showing {description}",
#             f"A student performing this environmental activity: {description}",
#             f"An image demonstrating {description}"
#         ]

#         negative_prompts = [
#             "A photograph showing an unrelated everyday activity.",
#             "A photograph showing something unrelated to the assigned challenge.",
#             "A photograph of an unrelated object, place, or scene."
#         ]

#         all_prompts = positive_prompts + negative_prompts

#         # Process image and text
#         inputs = processor(
#             text=all_prompts,
#             images=image,
#             return_tensors="pt",
#             padding=True
#         )

#         inputs = {
#             key: value.to(device)
#             for key, value in inputs.items()
#         }

#         # Generate normalized embeddings
#         with torch.inference_mode():

#             image_features = model.get_image_features(
#                 pixel_values=inputs["pixel_values"]
#             )

#             text_features = model.get_text_features(
#                 input_ids=inputs["input_ids"],
#                 attention_mask=inputs.get("attention_mask")
#             )

#             image_features = torch.nn.functional.normalize(
#                 image_features, p=2, dim=-1
#             )

#             text_features = torch.nn.functional.normalize(
#                 text_features, p=2, dim=-1
#             )

#             similarities = (
#                 image_features @ text_features.T
#             )[0]

#         positive_scores = similarities[:len(positive_prompts)]
#         negative_scores = similarities[len(positive_prompts):]

#         positive_score = positive_scores.max().item()
#         negative_score = negative_scores.max().item()

#         margin = positive_score - negative_score

#         # Starter thresholds only.
#         # Calibrate using a representative validation dataset.
#         if positive_score >= 0.25 and margin >= 0.03:

#             status = "relevant"

#             explanation = (
#                 "The uploaded photograph appears visually "
#                 "consistent with the assigned challenge."
#             )

#         elif negative_score > positive_score and margin <= -0.03:

#             status = "not_relevant"

#             explanation = (
#                 "The uploaded photograph does not appear "
#                 "to match the assigned environmental challenge."
#             )

#         else:

#             status = "uncertain"

#             explanation = (
#                 "The image could not be confidently matched. "
#                 "Teacher verification is recommended."
#             )

#         # Legacy confidence field retained for compatibility.
#         # This is a transformed similarity value, not probability.
#         confidence = max(
#             0.0,
#             min(1.0, (positive_score + 1.0) / 2.0)
#         )

#         return {
#             "status": status,
#             "confidence": round(confidence, 4),
#             "similarity_score": round(positive_score, 4),
#             "explanation": explanation
#         }

#     except Exception as exc:

#         logger.exception(
#             "CLIP image verification failed: %s",
#             exc
#         )

#         return {
#             "status": "ai_unavailable",
#             "confidence": 0.0,
#             "similarity_score": 0.0,
#             "explanation": (
#                 "Image verification is temporarily unavailable. "
#                 "Submission should be forwarded for teacher review."
#             )
#         }
