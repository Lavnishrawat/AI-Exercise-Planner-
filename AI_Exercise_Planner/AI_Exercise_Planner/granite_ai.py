"""
granite_ai.py
-------------
IBM Granite / watsonx.ai integration.

This module handles:
  - IAM token acquisition (IBM Cloud API key → Bearer token)
  - Prompt construction for workout-plan generation
  - Sending the request to the watsonx.ai text-generation endpoint
  - Parsing and validating the JSON response from Granite
  - Graceful error handling so the GUI never crashes
  - Demo/fallback mode when credentials are not configured

Configuration is loaded entirely from config.py (which reads environment
variables).  No credentials are hard-coded here.

watsonx.ai REST API reference used:
  POST {endpoint}/ml/v1/text/generation?version=2023-05-29
  Authorization: Bearer <iam_token>
  Body: { "model_id": ..., "input": ..., "parameters": ..., "project_id": ... }

IBM IAM token endpoint:
  POST https://iam.cloud.ibm.com/identity/token
"""

import json
import logging
import time
from typing import Any, Optional

import requests  # type: ignore

import config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_IAM_TOKEN_URL = "https://iam.cloud.ibm.com/identity/token"
_WATSONX_API_VERSION = "2023-05-29"

_AI_DISCLAIMER = (
    "\n\n---\n"
    "⚠️  AI-generated workout suggestions are for general fitness information "
    "only and are NOT a substitute for professional medical advice. "
    "Consult a qualified healthcare professional before starting any new "
    "exercise programme."
)

# Simple in-process IAM token cache { "token": str, "expires_at": float }
_iam_cache: dict[str, Any] = {"token": None, "expires_at": 0.0}


# ---------------------------------------------------------------------------
# IAM token management
# ---------------------------------------------------------------------------

def _get_iam_token() -> str:
    """
    Obtain (or return a cached) IBM Cloud IAM Bearer token.

    Raises RuntimeError if the token cannot be retrieved.
    """
    now = time.time()
    if _iam_cache["token"] and now < _iam_cache["expires_at"] - 60:
        return _iam_cache["token"]

    if not config.IBM_GRANITE_API_KEY:
        raise RuntimeError(
            "IBM_GRANITE_API_KEY is not set.  "
            "Please configure your IBM Cloud API key in the .env file."
        )

    payload = {
        "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
        "apikey": config.IBM_GRANITE_API_KEY,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    try:
        resp = requests.post(
            _IAM_TOKEN_URL,
            data=payload,
            headers=headers,
            timeout=config.GRANITE_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Request to IBM IAM timed out.  "
            "Check your network connection and try again."
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not connect to IBM IAM.  "
            "Check your network connection and try again."
        )
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 400:
            raise RuntimeError(
                "IBM IAM rejected the API key (HTTP 400).  "
                "Verify that IBM_GRANITE_API_KEY is correct."
            )
        if status == 401:
            raise RuntimeError(
                "IBM IAM authentication failed (HTTP 401).  "
                "Verify that IBM_GRANITE_API_KEY is valid."
            )
        raise RuntimeError(f"IBM IAM returned HTTP {status}: {exc}")

    body = resp.json()
    token: str = body.get("access_token", "")
    expires_in: int = int(body.get("expires_in", 3600))

    if not token:
        raise RuntimeError("IBM IAM response did not contain an access_token.")

    _iam_cache["token"] = token
    _iam_cache["expires_at"] = now + expires_in
    logger.debug("IAM token refreshed; expires in %d s", expires_in)
    return token


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

def build_workout_prompt(user_request: dict[str, Any]) -> str:
    """
    Build a structured prompt from the user's workout-request parameters.

    Expected keys in *user_request*
    --------------------------------
    goal          : str  – e.g. "Weight Loss"
    experience    : str  – e.g. "Beginner"
    days_per_week : int  – 1-7
    duration_min  : int  – minutes per session
    equipment     : str  – e.g. "No Equipment"
    extra_notes   : str  – additional free-text instructions (may be empty)
    """
    goal = user_request.get("goal", "General Fitness")
    experience = user_request.get("experience", "Beginner")
    days = user_request.get("days_per_week", 3)
    duration = user_request.get("duration_min", 30)
    equipment = user_request.get("equipment", "No Equipment")
    notes = user_request.get("extra_notes", "").strip()

    notes_line = f"\nAdditional instructions: {notes}" if notes else ""

    prompt = f"""You are an expert personal fitness trainer. Generate a complete, personalised weekly workout plan based on the following information:

Goal: {goal}
Experience level: {experience}
Available workout days per week: {days}
Workout duration per session: {duration} minutes
Available equipment: {equipment}{notes_line}

Return the workout plan as a single valid JSON object with the following structure (no markdown, no extra text outside the JSON):

{{
  "goal": "<goal>",
  "experience": "<experience>",
  "days_per_week": <number>,
  "duration_min": <number>,
  "equipment": "<equipment>",
  "warm_up": {{
    "description": "<warm-up description>",
    "duration_min": <number>
  }},
  "cool_down": {{
    "description": "<cool-down description>",
    "duration_min": <number>
  }},
  "recovery_recommendations": "<recovery advice>",
  "schedule": [
    {{
      "day": "<day name>",
      "focus": "<session focus>",
      "exercises": [
        {{
          "name": "<exercise name>",
          "sets": <number or null>,
          "reps": <number or null>,
          "duration_min": <number or null>,
          "rest_sec": <number>,
          "difficulty": "<Beginner|Intermediate|Advanced>",
          "instructions": "<brief instructions>"
        }}
      ]
    }}
  ]
}}

Important rules:
- Provide exactly {days} workout day(s) in the schedule array.
- Use only the equipment listed.
- Match the difficulty to the experience level.
- Keep each session within {duration} minutes including warm-up and cool-down.
- Return ONLY the JSON object. Do not include any other text.
"""
    return prompt


# ---------------------------------------------------------------------------
# API call
# ---------------------------------------------------------------------------

def _call_watsonx(prompt: str) -> str:
    """
    Send *prompt* to the watsonx.ai text-generation endpoint.

    Returns the raw text generated by the model.
    Raises RuntimeError with a user-friendly message on any failure.
    """
    if not config.IBM_WATSONX_PROJECT_ID:
        raise RuntimeError(
            "IBM_WATSONX_PROJECT_ID is not set.  "
            "Please configure your watsonx.ai project ID in the .env file."
        )

    token = _get_iam_token()

    endpoint = config.IBM_GRANITE_ENDPOINT.rstrip("/")
    url = f"{endpoint}/ml/v1/text/generation?version={_WATSONX_API_VERSION}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = {
        "model_id": config.IBM_GRANITE_MODEL,
        "input": prompt,
        "parameters": {
            "decoding_method": "greedy",
            "max_new_tokens": config.GRANITE_MAX_NEW_TOKENS,
            "temperature": config.GRANITE_TEMPERATURE,
            "repetition_penalty": 1.05,
        },
        "project_id": config.IBM_WATSONX_PROJECT_ID,
    }

    logger.debug("Calling watsonx.ai: model=%s url=%s", config.IBM_GRANITE_MODEL, url)

    try:
        resp = requests.post(
            url,
            json=body,
            headers=headers,
            timeout=config.GRANITE_REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.exceptions.Timeout:
        raise RuntimeError(
            f"Request to watsonx.ai timed out after {config.GRANITE_REQUEST_TIMEOUT}s.  "
            "Check your network connection or increase GRANITE_REQUEST_TIMEOUT."
        )
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Could not connect to watsonx.ai.  "
            "Verify IBM_GRANITE_ENDPOINT and your network connection."
        )
    except requests.exceptions.HTTPError as exc:
        status = exc.response.status_code if exc.response is not None else "?"
        if status == 401:
            raise RuntimeError(
                "watsonx.ai authentication failed (HTTP 401).  "
                "Check your IBM_GRANITE_API_KEY and IBM_WATSONX_PROJECT_ID."
            )
        if status == 404:
            raise RuntimeError(
                f"watsonx.ai endpoint not found (HTTP 404).  "
                f"Check IBM_GRANITE_ENDPOINT and IBM_GRANITE_MODEL.  "
                f"URL tried: {url}"
            )
        if status == 429:
            raise RuntimeError(
                "watsonx.ai rate limit exceeded (HTTP 429).  "
                "Wait a moment and try again."
            )
        # Extract any body message for debugging (never expose API keys).
        try:
            detail = exc.response.json().get("errors", [{}])[0].get("message", "")
        except Exception:
            detail = ""
        raise RuntimeError(
            f"watsonx.ai returned HTTP {status}.  {detail}".strip()
        )

    response_json = resp.json()

    # watsonx.ai wraps the generated text inside results[0].generated_text
    try:
        generated_text: str = response_json["results"][0]["generated_text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError(
            "Unexpected response structure from watsonx.ai.  "
            f"Raw response: {json.dumps(response_json)[:500]}"
        )

    return generated_text.strip()


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def _extract_json(raw: str) -> Optional[dict[str, Any]]:
    """
    Attempt to extract a JSON object from *raw*.

    Granite sometimes wraps the JSON in markdown code fences or adds a
    sentence before/after.  This function tries several strategies.
    Returns a dict on success, None on failure.
    """
    # Strategy 1: parse directly.
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    # Strategy 2: strip markdown code fences (```json ... ``` or ``` ... ```).
    stripped = raw
    for fence in ("```json", "```"):
        if fence in stripped:
            parts = stripped.split(fence)
            # Take the content between the first pair of fences.
            if len(parts) >= 3:
                stripped = parts[1].strip()
                break
            elif len(parts) == 2:
                stripped = parts[1].strip()
                break

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass

    # Strategy 3: find the outermost { … } substring.
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end > start:
        candidate = raw[start: end + 1]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class GraniteResponse:
    """
    Container for a Granite API call result.

    Attributes
    ----------
    success      : bool
    plan         : dict | None   – parsed workout plan (if success)
    raw_text     : str           – the raw text returned by the model
    error_message: str           – user-friendly error description (if not success)
    """

    def __init__(
        self,
        success: bool,
        plan: Optional[dict[str, Any]],
        raw_text: str,
        error_message: str = "",
    ) -> None:
        self.success = success
        self.plan = plan
        self.raw_text = raw_text
        self.error_message = error_message


# ---------------------------------------------------------------------------
# Demo / fallback plan builder
# ---------------------------------------------------------------------------

_DEMO_EXERCISES: dict[str, list[dict[str, Any]]] = {
    "Weight Loss": [
        {"name": "Jumping Jacks",        "sets": None, "reps": None, "duration_min": 3,  "rest_sec": 30,  "difficulty": "Beginner",     "instructions": "Perform continuously at a moderate pace, keeping arms and legs wide."},
        {"name": "Bodyweight Squats",     "sets": 3,    "reps": 15,   "duration_min": None,"rest_sec": 45, "difficulty": "Beginner",     "instructions": "Stand feet shoulder-width apart, lower until thighs are parallel to floor."},
        {"name": "Mountain Climbers",     "sets": 3,    "reps": 20,   "duration_min": None,"rest_sec": 30, "difficulty": "Intermediate", "instructions": "Start in push-up position and alternate driving knees to chest rapidly."},
        {"name": "Burpees",               "sets": 3,    "reps": 10,   "duration_min": None,"rest_sec": 60, "difficulty": "Intermediate", "instructions": "Drop to squat, kick feet back, do a push-up, return and jump."},
        {"name": "High Knees",            "sets": None, "reps": None, "duration_min": 2,  "rest_sec": 30,  "difficulty": "Beginner",     "instructions": "Run in place, driving knees to hip height as fast as you can."},
        {"name": "Plank",                 "sets": 3,    "reps": None, "duration_min": 1,  "rest_sec": 30,  "difficulty": "Beginner",     "instructions": "Hold a straight body position on forearms and toes. Brace your core."},
    ],
    "Muscle Gain": [
        {"name": "Push-Ups",              "sets": 4,    "reps": 12,   "duration_min": None,"rest_sec": 60, "difficulty": "Beginner",     "instructions": "Lower chest to floor with elbows at 45 degrees, then press back up."},
        {"name": "Dumbbell Rows",         "sets": 4,    "reps": 10,   "duration_min": None,"rest_sec": 60, "difficulty": "Intermediate", "instructions": "Brace on a bench, pull dumbbell to hip, squeeze shoulder blade at top."},
        {"name": "Dumbbell Shoulder Press","sets": 3,   "reps": 12,   "duration_min": None,"rest_sec": 60, "difficulty": "Intermediate", "instructions": "Press dumbbells overhead from shoulder height, fully extend arms."},
        {"name": "Dumbbell Lunges",       "sets": 3,    "reps": 12,   "duration_min": None,"rest_sec": 60, "difficulty": "Intermediate", "instructions": "Step forward, lower back knee toward floor, then return to standing."},
        {"name": "Tricep Dips",           "sets": 3,    "reps": 12,   "duration_min": None,"rest_sec": 45, "difficulty": "Beginner",     "instructions": "Using a chair or bench, lower body by bending elbows then press back up."},
    ],
    "Strength": [
        {"name": "Barbell Squat",         "sets": 5,    "reps": 5,    "duration_min": None,"rest_sec": 120,"difficulty": "Advanced",     "instructions": "Bar on upper traps, squat below parallel, drive through heels to stand."},
        {"name": "Deadlift",              "sets": 5,    "reps": 5,    "duration_min": None,"rest_sec": 120,"difficulty": "Advanced",     "instructions": "Hinge at hips, grip bar just outside legs, keep back flat and drive hips forward."},
        {"name": "Bench Press",           "sets": 5,    "reps": 5,    "duration_min": None,"rest_sec": 120,"difficulty": "Intermediate", "instructions": "Lower bar to chest with 75-degree elbow angle, press back up powerfully."},
        {"name": "Overhead Press",        "sets": 4,    "reps": 6,    "duration_min": None,"rest_sec": 90, "difficulty": "Intermediate", "instructions": "Press bar from collar-bone height to overhead, squeezing glutes throughout."},
        {"name": "Pull-Ups",              "sets": 4,    "reps": 6,    "duration_min": None,"rest_sec": 90, "difficulty": "Advanced",     "instructions": "Dead hang, then pull chin above bar leading with elbows. Lower slowly."},
    ],
    "General Fitness": [
        {"name": "Bodyweight Squats",     "sets": 3,    "reps": 15,   "duration_min": None,"rest_sec": 45, "difficulty": "Beginner",     "instructions": "Feet shoulder-width apart, chest up, sit back and down until thighs are parallel."},
        {"name": "Push-Ups",              "sets": 3,    "reps": 10,   "duration_min": None,"rest_sec": 45, "difficulty": "Beginner",     "instructions": "Hands shoulder-width apart, lower chest to floor, press back up."},
        {"name": "Plank",                 "sets": 3,    "reps": None, "duration_min": 1,  "rest_sec": 30,  "difficulty": "Beginner",     "instructions": "Hold a straight body position on forearms and toes. Brace your core."},
        {"name": "Reverse Lunges",        "sets": 3,    "reps": 12,   "duration_min": None,"rest_sec": 45, "difficulty": "Beginner",     "instructions": "Step backward and lower your back knee toward the floor, then return."},
        {"name": "Glute Bridges",         "sets": 3,    "reps": 15,   "duration_min": None,"rest_sec": 30, "difficulty": "Beginner",     "instructions": "Lie on back, feet flat, drive hips up squeezing glutes at top."},
        {"name": "Superman Hold",         "sets": 3,    "reps": 12,   "duration_min": None,"rest_sec": 30, "difficulty": "Beginner",     "instructions": "Lie face down, lift arms and legs simultaneously, hold 2 seconds."},
    ],
    "Flexibility": [
        {"name": "Standing Quad Stretch", "sets": 2,    "reps": None, "duration_min": 1,  "rest_sec": 15,  "difficulty": "Beginner",     "instructions": "Stand on one leg, pull the other heel to glute. Hold 30 seconds each side."},
        {"name": "Seated Hamstring Stretch","sets": 2,  "reps": None, "duration_min": 1,  "rest_sec": 15,  "difficulty": "Beginner",     "instructions": "Sit with legs extended, reach toward toes, hold 30–45 seconds."},
        {"name": "Cat-Cow Stretch",       "sets": 2,    "reps": 10,   "duration_min": None,"rest_sec": 15, "difficulty": "Beginner",     "instructions": "On hands and knees, alternate arching and rounding the spine slowly."},
        {"name": "Hip Flexor Lunge Stretch","sets": 2,  "reps": None, "duration_min": 1,  "rest_sec": 15,  "difficulty": "Beginner",     "instructions": "Step one foot forward into a lunge, lower back knee, lean forward slightly."},
        {"name": "Child's Pose",          "sets": 2,    "reps": None, "duration_min": 1,  "rest_sec": 15,  "difficulty": "Beginner",     "instructions": "Kneel and stretch arms forward on the floor, hold and breathe deeply."},
        {"name": "Doorway Chest Stretch", "sets": 2,    "reps": None, "duration_min": 1,  "rest_sec": 15,  "difficulty": "Beginner",     "instructions": "Place forearms on a doorframe, lean forward gently until you feel a stretch."},
    ],
}

_DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

_FOCUS_MAP: dict[str, list[str]] = {
    "Weight Loss":    ["Full Body HIIT", "Cardio Burn", "Circuit Training", "Active Recovery", "Lower Body Blast", "Upper Body Cardio", "Total Body"],
    "Muscle Gain":    ["Push Day", "Pull Day", "Legs & Core", "Upper Body", "Lower Body", "Full Body Hypertrophy", "Arms & Shoulders"],
    "Strength":       ["Lower Body Strength", "Upper Body Strength", "Full Body Strength", "Posterior Chain", "Push Strength", "Pull Strength", "Accessory Work"],
    "General Fitness":["Full Body", "Cardio & Core", "Strength & Mobility", "Lower Body", "Upper Body", "Active Recovery", "Conditioning"],
    "Flexibility":    ["Full Body Stretch", "Lower Body Flexibility", "Upper Body Flexibility", "Hip & Spine Mobility", "Morning Flow", "Cool-Down Stretch", "Yoga Flow"],
}

_WARM_UP_MAP: dict[str, dict[str, Any]] = {
    "Weight Loss":    {"description": "5 minutes of light jogging in place, arm circles, and dynamic leg swings to elevate heart rate and loosen joints", "duration_min": 5},
    "Muscle Gain":    {"description": "5 minutes of light cardio followed by dynamic stretches — shoulder rolls, hip circles, and bodyweight squats", "duration_min": 5},
    "Strength":       {"description": "10 minutes of progressive warm-up sets at 50% then 70% of working weight, plus joint mobility drills", "duration_min": 10},
    "General Fitness":{"description": "5 minutes of brisk walking or light jogging, plus dynamic stretches targeting major muscle groups", "duration_min": 5},
    "Flexibility":    {"description": "5 minutes of gentle walking or marching in place, followed by slow full-body circles to warm tissues", "duration_min": 5},
}

_COOL_DOWN_MAP: dict[str, dict[str, Any]] = {
    "Weight Loss":    {"description": "5 minutes of slow walking followed by static stretches for quads, hamstrings, calves, and hip flexors", "duration_min": 5},
    "Muscle Gain":    {"description": "5–10 minutes of static stretching targeting every trained muscle group, holding each stretch 30–45 seconds", "duration_min": 7},
    "Strength":       {"description": "10 minutes of thorough static and PNF stretching for all major muscles; include foam rolling if available", "duration_min": 10},
    "General Fitness":{"description": "5 minutes of slow walking, followed by static stretches for the whole body focusing on tight areas", "duration_min": 5},
    "Flexibility":    {"description": "5 minutes of deep breathing in restorative poses such as child's pose, supine twist, and legs-up-the-wall", "duration_min": 5},
}

_RECOVERY_MAP: dict[str, str] = {
    "Weight Loss":    "Stay hydrated (2–3 L water/day). Aim for 7–8 hours of sleep. On rest days, take a 20–30 minute light walk to maintain fat-burning metabolism without overtraining.",
    "Muscle Gain":    "Consume 1.6–2.2 g protein per kg bodyweight daily. Prioritise 8 hours of sleep for muscle protein synthesis. Allow 48 hours between sessions targeting the same muscle group.",
    "Strength":       "Eat a calorie-sufficient diet rich in protein and complex carbohydrates. Sleep 8–9 hours. Use deload weeks every 4–6 weeks to prevent CNS fatigue. Ice sore joints as needed.",
    "General Fitness":"Balance workout days with full rest or active recovery days. Walk, swim, or cycle lightly on off-days. Maintain consistent sleep patterns to support energy levels.",
    "Flexibility":    "Stretch daily, even on rest days. Stay well-hydrated to maintain tissue elasticity. Avoid stretching cold muscles — always warm up first. Consider yoga or foam rolling on recovery days.",
}


def _build_demo_plan(user_request: dict[str, Any]) -> dict[str, Any]:
    """
    Build a realistic workout plan locally without calling the IBM API.
    Used when credentials are not configured or the API is unavailable.
    """
    import math

    goal         = user_request.get("goal", "General Fitness")
    experience   = user_request.get("experience", "Beginner")
    days         = int(user_request.get("days_per_week", 3))
    duration     = int(user_request.get("duration_min", 30))
    equipment    = user_request.get("equipment", "No Equipment")

    exercise_pool = list(_DEMO_EXERCISES.get(goal, _DEMO_EXERCISES["General Fitness"]))
    focus_pool    = list(_FOCUS_MAP.get(goal, _FOCUS_MAP["General Fitness"]))

    # Filter by difficulty so we match experience level
    diff_order = {"Beginner": 0, "Intermediate": 1, "Advanced": 2}
    max_diff   = diff_order.get(experience, 1)

    def _fits(ex: dict[str, Any]) -> bool:
        return diff_order.get(ex.get("difficulty", "Beginner"), 0) <= max_diff

    filtered = [e for e in exercise_pool if _fits(e)] or exercise_pool

    # How many exercises fit in the session duration (rough estimate: 5–7 min/exercise)
    exercises_per_day = max(2, min(len(filtered), math.floor((duration - 10) / 6)))

    schedule = []
    for i in range(days):
        day_name  = _DAY_NAMES[i % len(_DAY_NAMES)]
        focus     = focus_pool[i % len(focus_pool)]
        # Rotate through the pool so each day has a different subset
        start     = (i * exercises_per_day) % len(filtered)
        day_exs   = []
        for j in range(exercises_per_day):
            ex = dict(filtered[(start + j) % len(filtered)])
            ex["difficulty"] = experience
            day_exs.append(ex)
        schedule.append({"day": day_name, "focus": focus, "exercises": day_exs})

    plan = {
        "goal":                   goal,
        "experience":             experience,
        "days_per_week":          days,
        "duration_min":           duration,
        "equipment":              equipment,
        "warm_up":                _WARM_UP_MAP.get(goal, _WARM_UP_MAP["General Fitness"]),
        "cool_down":              _COOL_DOWN_MAP.get(goal, _COOL_DOWN_MAP["General Fitness"]),
        "recovery_recommendations": _RECOVERY_MAP.get(goal, _RECOVERY_MAP["General Fitness"]),
        "schedule":               schedule,
        "_disclaimer":            "AI-generated workout suggestions are for general fitness information only and are NOT a substitute for professional medical advice.",
        "_demo_mode":             True,
    }
    return plan


def generate_workout_plan(user_request: dict[str, Any]) -> GraniteResponse:
    """
    High-level entry point called by the GUI.

    1. Checks that Granite is configured; falls back to demo mode if not.
    2. Builds the prompt.
    3. Sends it to watsonx.ai.
    4. Parses the JSON response.
    5. Returns a GraniteResponse (never raises).

    When IBM credentials are not set the function returns a fully-formed
    demo plan generated locally so the UI always works.
    """
    # --- Demo / fallback mode -----------------------------------------------
    _placeholder_values = {"your_ibm_cloud_api_key_here", "", None}
    _placeholder_proj   = {"your_watsonx_project_id_here", "", None}

    credentials_missing = (
        config.IBM_GRANITE_API_KEY   in _placeholder_values or
        config.IBM_WATSONX_PROJECT_ID in _placeholder_proj
    )

    if credentials_missing or getattr(config, "DEMO_MODE", False):
        logger.info("IBM credentials not configured — returning demo workout plan.")
        plan = _build_demo_plan(user_request)
        return GraniteResponse(
            success=True,
            plan=plan,
            raw_text="[Demo mode — IBM Granite API credentials not configured]",
        )

    # --- Build prompt --------------------------------------------------------
    try:
        prompt = build_workout_prompt(user_request)
    except Exception as exc:
        logger.exception("Prompt construction error.")
        return GraniteResponse(
            success=False,
            plan=None,
            raw_text="",
            error_message=f"Failed to build the AI prompt: {exc}",
        )

    # --- Call API ------------------------------------------------------------
    try:
        raw_text = _call_watsonx(prompt)
    except RuntimeError as exc:
        logger.warning("watsonx.ai call failed (%s); falling back to demo plan.", exc)
        plan = _build_demo_plan(user_request)
        plan["_api_error"] = str(exc)
        return GraniteResponse(
            success=True,
            plan=plan,
            raw_text=f"[Demo fallback — API error: {exc}]",
        )
    except Exception as exc:
        logger.exception("Unexpected error calling watsonx.ai — falling back to demo plan.")
        plan = _build_demo_plan(user_request)
        plan["_api_error"] = f"{type(exc).__name__}: {exc}"
        return GraniteResponse(
            success=True,
            plan=plan,
            raw_text=f"[Demo fallback — unexpected error: {type(exc).__name__}: {exc}]",
        )

    if not raw_text:
        logger.warning("Granite returned empty response — falling back to demo plan.")
        plan = _build_demo_plan(user_request)
        return GraniteResponse(
            success=True,
            plan=plan,
            raw_text="[Demo fallback — Granite returned empty response]",
        )

    # --- Parse response ------------------------------------------------------
    plan = _extract_json(raw_text)

    if plan is None:
        logger.warning("Could not parse Granite response as JSON — falling back to demo plan.")
        demo_plan = _build_demo_plan(user_request)
        demo_plan["_parse_error"] = "Could not parse Granite JSON response"
        return GraniteResponse(
            success=True,
            plan=demo_plan,
            raw_text=raw_text,
        )

    # --- Attach disclaimer ---------------------------------------------------
    plan["_disclaimer"] = (
        "AI-generated workout suggestions are for general fitness information "
        "only and are NOT a substitute for professional medical advice."
    )

    logger.info("Granite workout plan generated successfully.")
    return GraniteResponse(success=True, plan=plan, raw_text=raw_text)
