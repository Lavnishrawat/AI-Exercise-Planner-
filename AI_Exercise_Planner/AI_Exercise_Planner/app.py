"""
app.py
------
Flask web application for the AI Exercise Planner.
All routes return JSON for API endpoints or render Jinja2 templates for pages.
IBM Granite credentials are read from environment variables only — never
exposed to the browser.
"""

import datetime
import logging
import os
import random
import sys

from flask import Flask, jsonify, render_template, request

# ---------------------------------------------------------------------------
# Path setup – allow imports of the shared modules (config, storage, etc.)
# that live in the same directory.
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import config
import exercise as ex_module
import granite_ai
import planner as plan_module
import progress as prog_module
import storage

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "templates"),
        static_folder=os.path.join(BASE_DIR, "static"),
    )
    app.secret_key = os.environ.get("FLASK_SECRET_KEY", os.urandom(24))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s – %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )

    storage.ensure_data_file()

    # -----------------------------------------------------------------------
    # Helper: load / save data
    # -----------------------------------------------------------------------
    def _load():
        return storage.load_data()

    def _save(data):
        return storage.save_data(data)

    # -----------------------------------------------------------------------
    # Page routes
    # -----------------------------------------------------------------------

    @app.route("/")
    def dashboard():
        data = _load()
        total_ex = len(ex_module.get_all_exercises(data))
        p = prog_module.calculate_overall_progress(data)
        breakdown = prog_module.calculate_weekly_breakdown(data)
        return render_template(
            "dashboard.html",
            total_exercises=total_ex,
            progress=p,
            breakdown=breakdown,
            granite_configured=config.granite_is_configured(),
            app_title=config.APP_TITLE,
        )

    @app.route("/exercises")
    def exercises():
        return render_template(
            "exercises.html",
            categories=config.EXERCISE_CATEGORIES,
            difficulties=config.DIFFICULTY_LEVELS,
            equipment_options=config.EQUIPMENT_OPTIONS,
            app_title=config.APP_TITLE,
        )

    @app.route("/planner")
    def planner():
        return render_template(
            "planner.html",
            days=config.DAYS_OF_WEEK,
            app_title=config.APP_TITLE,
        )

    @app.route("/ai-assistant")
    def ai_assistant():
        return render_template(
            "ai_assistant.html",
            goals=config.FITNESS_GOALS,
            experience_levels=config.EXPERIENCE_LEVELS,
            equipment_options=config.EQUIPMENT_OPTIONS,
            granite_configured=config.granite_is_configured(),
            app_title=config.APP_TITLE,
        )

    @app.route("/quick-workout")
    def quick_workout():
        return render_template(
            "quick_workout.html",
            app_title=config.APP_TITLE,
        )

    @app.route("/progress")
    def progress():
        return render_template(
            "progress.html",
            days=config.DAYS_OF_WEEK,
            app_title=config.APP_TITLE,
        )

    @app.route("/settings")
    def settings():
        return render_template(
            "settings.html",
            granite_configured=config.granite_is_configured(),
            granite_endpoint=config.IBM_GRANITE_ENDPOINT,
            granite_model=config.IBM_GRANITE_MODEL,
            max_tokens=config.GRANITE_MAX_NEW_TOKENS,
            api_key_set=bool(config.IBM_GRANITE_API_KEY),
            project_id_set=bool(config.IBM_WATSONX_PROJECT_ID),
            data_file=config.DATA_FILE,
            app_version=config.APP_VERSION,
            app_title=config.APP_TITLE,
        )

    # -----------------------------------------------------------------------
    # Exercise API
    # -----------------------------------------------------------------------

    @app.route("/api/exercises", methods=["GET"])
    def api_get_exercises():
        data = _load()
        query = request.args.get("q", "").strip()
        category = request.args.get("category", "").strip()
        difficulty = request.args.get("difficulty", "").strip()
        results = ex_module.search_exercises(
            data, query=query, category=category, difficulty=difficulty
        )
        return jsonify({"exercises": results})

    @app.route("/api/exercises", methods=["POST"])
    def api_add_exercise():
        body = request.get_json(force=True, silent=True) or {}
        ok, err = ex_module.validate_exercise(body)
        if not ok:
            return jsonify({"error": err}), 400
        try:
            new_ex = ex_module.make_exercise(
                name=body["name"],
                category=body.get("category", "Other"),
                sets=int(body.get("sets", 0)),
                reps=int(body.get("reps", 0)),
                duration=int(body.get("duration", 0)),
                difficulty=body.get("difficulty", "Beginner"),
                equipment=body.get("equipment", "No Equipment"),
                notes=body.get("notes", ""),
            )
        except (ValueError, TypeError) as exc:
            return jsonify({"error": f"Invalid numeric field: {exc}"}), 400
        data = _load()
        ex_module.add_exercise(data, new_ex)
        _save(data)
        return jsonify({"exercise": new_ex}), 201

    @app.route("/api/exercises/<exercise_id>", methods=["GET"])
    def api_get_exercise(exercise_id):
        data = _load()
        ex = ex_module.get_exercise_by_id(data, exercise_id)
        if not ex:
            return jsonify({"error": "Exercise not found"}), 404
        return jsonify({"exercise": ex})

    @app.route("/api/exercises/<exercise_id>", methods=["PUT"])
    def api_update_exercise(exercise_id):
        body = request.get_json(force=True, silent=True) or {}
        ok, err = ex_module.validate_exercise(body)
        if not ok:
            return jsonify({"error": err}), 400
        try:
            updated = {
                "name": body["name"],
                "category": body.get("category", "Other"),
                "sets": int(body.get("sets", 0)),
                "reps": int(body.get("reps", 0)),
                "duration": int(body.get("duration", 0)),
                "difficulty": body.get("difficulty", "Beginner"),
                "equipment": body.get("equipment", "No Equipment"),
                "notes": body.get("notes", ""),
            }
        except (ValueError, TypeError) as exc:
            return jsonify({"error": f"Invalid numeric field: {exc}"}), 400
        data = _load()
        if not ex_module.update_exercise(data, exercise_id, updated):
            return jsonify({"error": "Exercise not found"}), 404
        _save(data)
        return jsonify({"exercise": ex_module.get_exercise_by_id(data, exercise_id)})

    @app.route("/api/exercises/<exercise_id>", methods=["DELETE"])
    def api_delete_exercise(exercise_id):
        data = _load()
        if not ex_module.delete_exercise(data, exercise_id):
            return jsonify({"error": "Exercise not found"}), 404
        _save(data)
        return jsonify({"success": True})

    # -----------------------------------------------------------------------
    # Planner API
    # -----------------------------------------------------------------------

    @app.route("/api/planner", methods=["GET"])
    def api_get_planner():
        data = _load()
        result = {}
        for day in config.DAYS_OF_WEEK:
            result[day] = plan_module.get_day_entries(data, day)
        return jsonify({"weekly_plan": result})

    @app.route("/api/planner/<day>", methods=["GET"])
    def api_get_day(day):
        if day not in config.DAYS_OF_WEEK:
            return jsonify({"error": "Invalid day"}), 400
        data = _load()
        return jsonify({"day": day, "entries": plan_module.get_day_entries(data, day)})

    @app.route("/api/planner/<day>", methods=["POST"])
    def api_add_to_day(day):
        if day not in config.DAYS_OF_WEEK:
            return jsonify({"error": "Invalid day"}), 400
        body = request.get_json(force=True, silent=True) or {}
        exercise_id = body.get("exercise_id", "").strip()
        exercise_name = body.get("exercise_name", "").strip()
        if not exercise_name:
            return jsonify({"error": "exercise_name is required"}), 400
        try:
            sets = int(body.get("sets", 0))
            reps = int(body.get("reps", 0))
            duration = int(body.get("duration", 0))
        except (ValueError, TypeError):
            return jsonify({"error": "sets, reps, duration must be integers"}), 400
        notes = body.get("notes", "")
        entry = plan_module.make_plan_entry(
            exercise_id=exercise_id,
            exercise_name=exercise_name,
            sets=sets, reps=reps, duration=duration, notes=notes,
        )
        data = _load()
        plan_module.add_entry_to_day(data, day, entry)
        _save(data)
        return jsonify({"entry": entry}), 201

    @app.route("/api/planner/<day>/<entry_id>", methods=["DELETE"])
    def api_remove_entry(day, entry_id):
        if day not in config.DAYS_OF_WEEK:
            return jsonify({"error": "Invalid day"}), 400
        data = _load()
        if not plan_module.remove_entry_from_day(data, day, entry_id):
            return jsonify({"error": "Entry not found"}), 404
        _save(data)
        return jsonify({"success": True})

    @app.route("/api/planner/<day>/<entry_id>/toggle", methods=["POST"])
    def api_toggle_entry(day, entry_id):
        if day not in config.DAYS_OF_WEEK:
            return jsonify({"error": "Invalid day"}), 400
        data = _load()
        new_state = plan_module.toggle_entry_completed(data, day, entry_id)
        if new_state is None:
            return jsonify({"error": "Entry not found"}), 404
        _save(data)
        return jsonify({"completed": new_state})

    @app.route("/api/planner/reset", methods=["POST"])
    def api_reset_completions():
        data = _load()
        plan_module.reset_all_completions(data)
        _save(data)
        return jsonify({"success": True})

    # -----------------------------------------------------------------------
    # Progress API
    # -----------------------------------------------------------------------

    @app.route("/api/progress", methods=["GET"])
    def api_get_progress():
        data = _load()
        overall = prog_module.calculate_overall_progress(data)
        breakdown = prog_module.calculate_weekly_breakdown(data)
        return jsonify({"overall": overall, "breakdown": breakdown})

    # -----------------------------------------------------------------------
    # Quick Workout API
    # -----------------------------------------------------------------------

    @app.route("/api/quick-workout", methods=["GET"])
    def api_quick_workout():
        data = _load()
        all_ex = ex_module.get_all_exercises(data)
        if len(all_ex) < 3:
            return jsonify({
                "error": f"Not enough exercises (need at least 3, have {len(all_ex)}). "
                         "Add more exercises to the library first.",
                "count": len(all_ex),
            }), 400
        count = random.randint(3, min(5, len(all_ex)))
        selected = random.sample(all_ex, count)
        return jsonify({"exercises": selected, "count": count})

    # -----------------------------------------------------------------------
    # AI Assistant API
    # -----------------------------------------------------------------------

    @app.route("/api/ai/generate", methods=["POST"])
    def api_ai_generate():
        body = request.get_json(force=True, silent=True) or {}

        # --- Validate ---
        goal = body.get("goal", "").strip()
        experience = body.get("experience", "").strip()
        equipment = body.get("equipment", "").strip()
        extra_notes = body.get("extra_notes", "").strip()

        try:
            days = int(body.get("days_per_week", 0))
            if not 1 <= days <= 7:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "days_per_week must be between 1 and 7"}), 400

        try:
            duration = int(body.get("duration_min", 0))
            if not 15 <= duration <= 120:
                raise ValueError
        except (ValueError, TypeError):
            return jsonify({"error": "duration_min must be between 15 and 120"}), 400

        if goal not in config.FITNESS_GOALS:
            return jsonify({"error": "Invalid fitness goal"}), 400
        if experience not in config.EXPERIENCE_LEVELS:
            return jsonify({"error": "Invalid experience level"}), 400
        if equipment not in config.EQUIPMENT_OPTIONS:
            return jsonify({"error": "Invalid equipment option"}), 400

        user_request = {
            "goal": goal,
            "experience": experience,
            "days_per_week": days,
            "duration_min": duration,
            "equipment": equipment,
            "extra_notes": extra_notes,
        }

        result = granite_ai.generate_workout_plan(user_request)

        if result.success:
            return jsonify({
                "success": True,
                "plan": result.plan,
                "raw_text": result.raw_text,
            })
        else:
            return jsonify({
                "success": False,
                "error": result.error_message,
                "raw_text": result.raw_text,
            }), 422

    @app.route("/api/ai/save-plan", methods=["POST"])
    def api_ai_save_plan():
        body = request.get_json(force=True, silent=True) or {}
        plan = body.get("plan")
        raw = body.get("raw_text", "")
        if not plan or not isinstance(plan, dict):
            return jsonify({"error": "plan is required"}), 400
        data = _load()
        plans = data.setdefault("ai_plans", [])
        entry = {
            "saved_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "plan": plan,
            "raw": raw,
        }
        plans.append(entry)
        _save(data)
        return jsonify({"success": True, "total_saved": len(plans)}), 201

    @app.route("/api/ai/add-to-planner", methods=["POST"])
    def api_ai_add_to_planner():
        body = request.get_json(force=True, silent=True) or {}
        plan = body.get("plan")
        if not plan or not isinstance(plan, dict):
            return jsonify({"error": "plan is required"}), 400

        schedule = plan.get("schedule", [])
        if not schedule:
            return jsonify({"error": "Plan has no schedule"}), 400

        data = _load()
        added = 0
        for i, day_block in enumerate(schedule):
            raw_day = day_block.get("day", "")
            matched_day = None
            for d in config.DAYS_OF_WEEK:
                if d.lower() in raw_day.lower():
                    matched_day = d
                    break
            if not matched_day:
                if i < len(config.DAYS_OF_WEEK):
                    matched_day = config.DAYS_OF_WEEK[i]
                else:
                    continue

            for ex_item in day_block.get("exercises", []):
                name = ex_item.get("name", "AI Exercise")
                try:
                    sets_val = int(ex_item.get("sets") or 0)
                    reps_val = int(ex_item.get("reps") or 0)
                    dur_val  = int(ex_item.get("duration_min") or 0)
                except (TypeError, ValueError):
                    sets_val = reps_val = dur_val = 0
                entry = plan_module.make_plan_entry(
                    exercise_id="ai_generated",
                    exercise_name=name,
                    sets=sets_val, reps=reps_val, duration=dur_val,
                    notes=ex_item.get("instructions", ""),
                )
                plan_module.add_entry_to_day(data, matched_day, entry)
                added += 1

        _save(data)
        return jsonify({"success": True, "added": added})

    @app.route("/api/settings/clear-data", methods=["POST"])
    def api_clear_data():
        import storage as _s
        fresh = _s._deep_merge(_s._DEFAULT_DATA, {})
        _save(fresh)
        return jsonify({"success": True})

    # -----------------------------------------------------------------------
    # Error handlers
    # -----------------------------------------------------------------------

    @app.errorhandler(404)
    def not_found(e):
        return render_template("404.html", app_title=config.APP_TITLE), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
