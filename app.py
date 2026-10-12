"""
Entry point: runs the Telegram bot and the web dashboard together in one process.
This is what you actually deploy — `python3 app.py`.
"""
import logging
import os
import threading

import db
from bot import build_application
from web import create_app

log = logging.getLogger("bbq-app")


def run_web():
    flask_app = create_app()
    port = int(os.environ.get("PORT", 8080))
    flask_app.run(host="0.0.0.0", port=port)


def main():
    db.init_db()

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    application = build_application()
    log.info("Bot + dashboard starting...")
    application.run_polling()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
