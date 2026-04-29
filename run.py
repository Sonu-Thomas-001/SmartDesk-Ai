import logging

from app.main import app

if __name__ == "__main__":
    # Suppress Werkzeug request logs
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    app.run(host="0.0.0.0", port=8000, debug=True)
