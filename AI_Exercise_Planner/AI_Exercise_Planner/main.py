"""
main.py
-------
Application entry point.

Run modes
---------
  python main.py          → launches the Tkinter desktop GUI (default)
  python main.py --web    → launches the Flask web server (http://localhost:5000)
"""

import logging
import sys
import os


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  –  %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stdout,
    )


def _check_dependencies() -> None:
    """Exit with a helpful message if required packages are missing."""
    missing = []
    try:
        import requests  # noqa: F401
    except ImportError:
        missing.append("requests")
    try:
        import flask  # noqa: F401
    except ImportError:
        missing.append("flask")

    if missing:
        print(
            f"ERROR: Missing packages: {', '.join(missing)}\n"
            "Run:  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)


def _check_credentials() -> None:
    """Warn (but do not exit) when IBM credentials are not configured."""
    # Import config here so .env is already loaded.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    import config  # noqa: E402

    if not config.granite_is_configured():
        print(
            "\n"
            "⚠️  WARNING: IBM Granite AI is NOT configured.\n"
            "   The AI Workout Assistant will not work until you set:\n"
            "\n"
            "     IBM_GRANITE_API_KEY      – your IBM Cloud API key\n"
            "     IBM_WATSONX_PROJECT_ID   – your watsonx.ai project ID\n"
            "\n"
            f"   Edit the file:  {os.path.join(BASE_DIR, '.env')}\n"
            "   Get an API key:  https://cloud.ibm.com/iam/apikeys\n"
            "   Get a project:   https://dataplatform.cloud.ibm.com\n",
            file=sys.stderr,
        )


def run_web() -> None:
    """Start the Flask web application."""
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    from app import app  # noqa: E402

    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    print(f"\n🌐  Flask server starting → http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=debug)


def run_gui() -> None:
    """Start the Tkinter desktop GUI."""
    try:
        import tkinter as _tk  # noqa: F401
    except ImportError:
        print(
            "ERROR: Tkinter is not available.\n"
            "Install a Python build that includes Tkinter, or run:\n"
            "  python main.py --web",
            file=sys.stderr,
        )
        sys.exit(1)

    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    if BASE_DIR not in sys.path:
        sys.path.insert(0, BASE_DIR)

    from gui import App  # noqa: E402

    app = App()
    app.mainloop()


def main() -> None:
    _configure_logging()
    _check_dependencies()
    _check_credentials()

    if "--web" in sys.argv:
        run_web()
    else:
        run_gui()


if __name__ == "__main__":
    main()
