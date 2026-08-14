"""
config.py
---------
Handles all application configuration and environment variable loading.
Reads IBM Granite credentials from environment variables or a .env file.
Never hard-codes credentials.
"""

import os

# ---------------------------------------------------------------------------
# Try to load a .env file if python-dotenv is installed.
# If it is not installed the application still works; variables must then
# be exported in the shell before running the application.
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(_env_path):
        load_dotenv(_env_path)
    else:
        load_dotenv()  # searches CWD / parent directories
except ImportError:
    pass  # python-dotenv is optional


# ---------------------------------------------------------------------------
# IBM Granite / watsonx.ai configuration
# ---------------------------------------------------------------------------

# Your IBM Cloud API key.
IBM_GRANITE_API_KEY: str = os.environ.get("IBM_GRANITE_API_KEY", "")

# The watsonx.ai inference endpoint, e.g.:
#   https://us-south.ml.cloud.ibm.com
IBM_GRANITE_ENDPOINT: str = os.environ.get(
    "IBM_GRANITE_ENDPOINT",
    "https://us-south.ml.cloud.ibm.com",
)

# The Granite model ID to use, e.g.:
#   ibm/granite-13b-instruct-v2
#   ibm/granite-3-8b-instruct
IBM_GRANITE_MODEL: str = os.environ.get(
    "IBM_GRANITE_MODEL",
    "ibm/granite-3-8b-instruct",
)

# Your watsonx.ai project ID (required by the watsonx.ai inference API).
IBM_WATSONX_PROJECT_ID: str = os.environ.get("IBM_WATSONX_PROJECT_ID", "")

# ---------------------------------------------------------------------------
# Request tuning defaults
# ---------------------------------------------------------------------------

# Maximum tokens the model is allowed to generate in a single response.
GRANITE_MAX_NEW_TOKENS: int = int(os.environ.get("GRANITE_MAX_NEW_TOKENS", "1200"))

# Sampling temperature (0.0 = deterministic, 1.0 = creative).
GRANITE_TEMPERATURE: float = float(os.environ.get("GRANITE_TEMPERATURE", "0.7"))

# HTTP request timeout in seconds.
GRANITE_REQUEST_TIMEOUT: int = int(os.environ.get("GRANITE_REQUEST_TIMEOUT", "60"))

# ---------------------------------------------------------------------------
# Application-level constants
# ---------------------------------------------------------------------------

APP_TITLE: str = "AI Exercise Planner"
APP_VERSION: str = "1.0.0"

# Path to the JSON data file (relative to this file's directory).
DATA_FILE: str = os.path.join(os.path.dirname(__file__), "data.json")

# Days of the week used throughout the planner.
DAYS_OF_WEEK: list[str] = [
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
]

# Exercise categories.
EXERCISE_CATEGORIES: list[str] = [
    "Cardio", "Strength", "Core", "Flexibility", "Full Body", "Other",
]

# Difficulty levels.
DIFFICULTY_LEVELS: list[str] = ["Beginner", "Intermediate", "Advanced"]

# Equipment options.
EQUIPMENT_OPTIONS: list[str] = [
    "No Equipment", "Dumbbells", "Resistance Bands", "Full Gym", "Other",
]

# Fitness goals.
FITNESS_GOALS: list[str] = [
    "Weight Loss", "Muscle Gain", "Strength", "General Fitness", "Flexibility",
]

# Experience levels.
EXPERIENCE_LEVELS: list[str] = ["Beginner", "Intermediate", "Advanced"]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def granite_is_configured() -> bool:
    """Return True when the minimum Granite credentials are present."""
    return bool(IBM_GRANITE_API_KEY and IBM_WATSONX_PROJECT_ID)
