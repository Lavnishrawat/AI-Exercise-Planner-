# AI Exercise Planner – Web Application

A modern, responsive web application for managing workouts, creating weekly exercise plans, tracking progress, and generating AI-powered workout plans using **IBM Granite via watsonx.ai**.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Technologies](#technologies)
4. [Project Structure](#project-structure)
5. [IBM Granite AI Integration](#ibm-granite-ai-integration)
6. [Setting Up IBM Granite Credentials](#setting-up-ibm-granite-credentials)
7. [Installation](#installation)
8. [Running Locally](#running-locally)
9. [How the AI Assistant Works](#how-the-ai-assistant-works)
10. [Data Storage](#data-storage)
11. [API Endpoints](#api-endpoints)
12. [Deployment](#deployment)
13. [Troubleshooting](#troubleshooting)
14. [Future Improvements](#future-improvements)

---

## Overview

AI Exercise Planner is a full-stack web application built with **Python Flask** on the backend and plain **HTML/CSS/JavaScript** on the frontend. It stores all data locally in a `data.json` file — no external database required. The AI Workout Assistant connects directly to IBM Granite through the watsonx.ai REST API.

---

## Features

| Feature | Description |
|---|---|
| **Exercise Library** | Add, edit, delete, search, and view exercises with full details |
| **Weekly Planner** | Assign exercises to any day Mon–Sun, mark them complete, manage schedules |
| **Progress Tracker** | Overall and per-day stats with visual progress bars |
| **Quick Workout** | Randomly generate a 3–5 exercise session from your library |
| **AI Workout Assistant** | Sends your preferences to IBM Granite and renders a full personalised plan |
| **Dashboard** | At-a-glance overview of stats, progress, and quick actions |
| **Settings** | IBM Granite status, data management |
| **Responsive** | Works on desktop and mobile browsers |
| **Deployment-ready** | Uses `PORT` env var; compatible with Render, Railway, Heroku, etc. |

---

## Technologies

| Layer | Technology |
|---|---|
| Backend | Python 3.9+, Flask 3 |
| AI | IBM Granite via watsonx.ai REST API |
| Frontend | HTML5, CSS3 (custom properties), Vanilla JavaScript (ES2020) |
| Data | JSON file (`data.json`) |
| Auth | IBM Cloud IAM Bearer tokens (auto-refreshed) |
| Deployment | Gunicorn + PORT env var |

---

## Project Structure

```
AI_Exercise_Planner/
│
├── app.py              ← Flask application, all routes and API endpoints
├── config.py           ← Configuration, reads all env vars
├── storage.py          ← JSON load/save with atomic writes
├── exercise.py         ← Exercise CRUD and validation logic
├── planner.py          ← Weekly plan entry logic
├── progress.py         ← Progress calculation helpers
├── granite_ai.py       ← IBM Granite / watsonx.ai integration
│
├── templates/
│   ├── base.html       ← Shared layout: sidebar, topbar, footer, modals
│   ├── dashboard.html
│   ├── exercises.html
│   ├── planner.html
│   ├── ai_assistant.html
│   ├── quick_workout.html
│   ├── progress.html
│   ├── settings.html
│   └── 404.html
│
├── static/
│   ├── css/style.css   ← All styles (custom properties, responsive)
│   └── js/
│       ├── app.js          ← Shared: sidebar, modals, toast, API helper
│       ├── exercises.js
│       ├── planner.js
│       ├── ai_assistant.js
│       ├── quick_workout.js
│       └── progress.js
│
├── data.json           ← Local data store (auto-created)
├── requirements.txt
├── .env.example        ← Credential template
└── README.md
```

---

## IBM Granite AI Integration

The AI Workout Assistant page sends a structured prompt to the **IBM Granite** model hosted on **watsonx.ai**.

**Flow:**
1. User fills in preferences (goal, experience, days, duration, equipment).
2. Browser posts to `/api/ai/generate`.
3. Flask calls `granite_ai.generate_workout_plan()`.
4. The module exchanges your API key for an IBM Cloud IAM Bearer token.
5. The Bearer token is used to POST to `{IBM_GRANITE_ENDPOINT}/ml/v1/text/generation`.
6. The JSON response is parsed and returned to the browser.
7. The browser renders the plan — schedule, exercises, warm-up, cool-down, recovery.

**IBM credentials are NEVER sent to the browser.** All API calls happen server-side in Flask.

---

## Setting Up IBM Granite Credentials

### Step 1 – Create an IBM Cloud account

Visit [https://cloud.ibm.com](https://cloud.ibm.com) and sign up for a free account.

### Step 2 – Create an IBM Cloud API Key

1. Go to **Manage → Access (IAM) → API keys**.
2. Click **Create an IBM Cloud API key**.
3. Copy the key immediately — it is shown only once.

### Step 3 – Create a watsonx.ai project

1. Go to [https://dataplatform.cloud.ibm.com](https://dataplatform.cloud.ibm.com).
2. Create a new project (or use an existing one).
3. Open the project → **Manage → General**.
4. Copy the **Project ID** (a UUID).

### Step 4 – Create your `.env` file

```bash
cp .env.example .env
```

Edit `.env`:

```env
IBM_GRANITE_API_KEY=your_ibm_cloud_api_key_here
IBM_WATSONX_PROJECT_ID=your_watsonx_project_id_here

# Optional – defaults shown:
IBM_GRANITE_ENDPOINT=https://us-south.ml.cloud.ibm.com
IBM_GRANITE_MODEL=ibm/granite-3-8b-instruct
GRANITE_MAX_NEW_TOKENS=1200
GRANITE_TEMPERATURE=0.7
GRANITE_REQUEST_TIMEOUT=60
```

> ⚠️ **Never commit `.env` to version control.**

### Step 5 – Verify

Start the app and open **Settings** in the browser. You will see whether each credential is detected.

---

## Installation

### Prerequisites

- Python 3.9 or newer ([python.org](https://www.python.org/downloads/))
- pip

### Install dependencies

```bash
cd AI_Exercise_Planner
pip install -r requirements.txt
```

This installs: **Flask**, **requests**, **python-dotenv**, **gunicorn**.

---

## Running Locally

```bash
cd AI_Exercise_Planner
python app.py
```

Then open your browser at:

```
http://localhost:5000
```

### Development mode (auto-reload on file changes)

```bash
FLASK_DEBUG=true python app.py
```

### With Gunicorn (production-style, local test)

```bash
gunicorn app:app --bind 0.0.0.0:5000
```

---

## How the AI Assistant Works

1. Open **AI Assistant** in the sidebar.
2. Fill in:
   - **Fitness Goal** – Weight Loss / Muscle Gain / Strength / General Fitness / Flexibility
   - **Experience Level** – Beginner / Intermediate / Advanced
   - **Days per Week** – 1–7
   - **Session Duration** – 15–120 min
   - **Equipment** – No Equipment / Dumbbells / Resistance Bands / Full Gym / Other
   - **Additional instructions** – optional free text
3. Click **Generate AI Workout Plan**.
4. The server sends a structured prompt to IBM Granite (via watsonx.ai).
5. The plan is parsed from JSON and displayed: schedule, exercises, sets/reps, warm-up, cool-down, recovery.
6. Use **Save Plan** to store it in `data.json`.
7. Use **Add to Weekly Planner** to automatically populate your weekly schedule.

**If Granite is not configured**, a clear warning banner is shown and the Generate button is disabled. All other pages work normally.

> ⚠️ AI-generated workout suggestions are for general fitness information only and are NOT a substitute for professional medical advice.

---

## Data Storage

All data lives in `data.json` in the project folder.

**Structure:**
```json
{
  "exercises": [ { "id": "...", "name": "...", ... } ],
  "weekly_plan": {
    "Monday": [ { "entry_id": "...", "exercise_name": "...", "completed": false, ... } ],
    ...
  },
  "ai_plans": [ { "saved_at": "...", "plan": { ... } } ],
  "settings": { "theme": "light" }
}
```

- Created automatically on first run with 10 sample exercises.
- Written atomically (`.tmp` → rename) to prevent corruption.
- Missing / empty / corrupted files fall back to defaults without crashing.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard |
| `GET` | `/exercises` | Exercise Library page |
| `GET` | `/planner` | Weekly Planner page |
| `GET` | `/ai-assistant` | AI Assistant page |
| `GET` | `/quick-workout` | Quick Workout page |
| `GET` | `/progress` | Progress page |
| `GET` | `/settings` | Settings page |
| `GET` | `/api/exercises` | List exercises (supports `?q=`, `?category=`, `?difficulty=`) |
| `POST` | `/api/exercises` | Add exercise |
| `GET` | `/api/exercises/:id` | Get single exercise |
| `PUT` | `/api/exercises/:id` | Update exercise |
| `DELETE` | `/api/exercises/:id` | Delete exercise |
| `GET` | `/api/planner` | Get full weekly plan |
| `GET` | `/api/planner/:day` | Get entries for one day |
| `POST` | `/api/planner/:day` | Add entry to a day |
| `DELETE` | `/api/planner/:day/:entry_id` | Remove entry |
| `POST` | `/api/planner/:day/:entry_id/toggle` | Toggle completed |
| `POST` | `/api/planner/reset` | Reset all completions |
| `GET` | `/api/progress` | Get progress stats |
| `GET` | `/api/quick-workout` | Generate random workout |
| `POST` | `/api/ai/generate` | Generate AI workout plan |
| `POST` | `/api/ai/save-plan` | Save AI plan to data.json |
| `POST` | `/api/ai/add-to-planner` | Add AI plan to weekly planner |
| `POST` | `/api/settings/clear-data` | Delete all data |

---

## Deployment

The app reads the `PORT` environment variable, making it compatible with most hosting platforms.

### Render / Railway / Fly.io

1. Push the `AI_Exercise_Planner` folder to a Git repository.
2. Set environment variables on your hosting platform:
   - `IBM_GRANITE_API_KEY`
   - `IBM_WATSONX_PROJECT_ID`
   - `IBM_GRANITE_ENDPOINT`
   - `IBM_GRANITE_MODEL`
   - `FLASK_SECRET_KEY` (any random string)
3. Set the start command to:
   ```
   gunicorn app:app
   ```

### Heroku

```
web: gunicorn app:app
```

> **Note on data persistence:** `data.json` is written to the local filesystem. On ephemeral platforms (Heroku, Render free tier), data will reset on each deploy. For persistent storage, consider switching `storage.py` to use a database or a persistent volume.

---

## Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: flask` | Run `pip install -r requirements.txt` |
| IBM Granite shows "not configured" | Add `IBM_GRANITE_API_KEY` and `IBM_WATSONX_PROJECT_ID` to `.env` and restart |
| HTTP 401 from watsonx.ai | Your API key is invalid or expired — generate a new one in IBM Cloud IAM |
| HTTP 404 from watsonx.ai | Check `IBM_GRANITE_ENDPOINT` and `IBM_GRANITE_MODEL` |
| AI plan parse error | Granite occasionally returns non-JSON; the raw text is shown — click Generate again |
| `data.json` corrupted | Delete the file and restart — it will be recreated with sample data |
| App doesn't start on port X | Set `PORT=X` in your environment before running |
| Page looks unstyled | Ensure the browser can reach `https://fonts.googleapis.com` (optional; falls back to system fonts) |

---

## Future Improvements

- **User accounts** – multi-user support with sessions.
- **Database backend** – replace `data.json` with SQLite or PostgreSQL for persistence on cloud platforms.
- **Exercise timer** – built-in countdown for sets and rest periods.
- **Charts** – workout frequency and completion trend charts (Chart.js).
- **Export** – download the weekly plan or AI plan as PDF.
- **Dark mode** – CSS variable-based theme switching.
- **Offline support** – Progressive Web App with service worker caching.
- **Granite conversation** – multi-turn AI chat with follow-up questions.

---

*AI Exercise Planner — Python 3 · Flask · IBM Granite · watsonx.ai*
