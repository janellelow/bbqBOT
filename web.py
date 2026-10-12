"""
Simple password-protected web dashboard showing the live RSVP/payment table.
Reads from the same SQLite file the bot writes to.
"""
import os
from datetime import datetime
from functools import wraps
from zoneinfo import ZoneInfo

from flask import Flask, Response, redirect, request, send_file, session, url_for

import db

DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "")
EVENT_NAME = os.environ.get("EVENT_NAME", "the BBQ")
# Times are stored in UTC; this is just how they're displayed on the dashboard.
LOCAL_TZ = ZoneInfo(os.environ.get("TIMEZONE", "Asia/Singapore"))


def format_local(iso_utc: str) -> str:
    """Convert a stored UTC ISO timestamp to a readable local time string."""
    dt = datetime.fromisoformat(iso_utc).astimezone(LOCAL_TZ)
    return dt.strftime("%d %b, %I:%M %p")


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("FLASK_SECRET", "change-me-please")

    def login_required(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if DASHBOARD_PASSWORD and not session.get("ok"):
                return redirect(url_for("login"))
            return view(*args, **kwargs)
        return wrapped

    @app.route("/login", methods=["GET", "POST"])
    def login():
        error = None
        if request.method == "POST":
            if request.form.get("password") == DASHBOARD_PASSWORD:
                session["ok"] = True
                return redirect(url_for("dashboard"))
            error = "Wrong password."
        return f"""
        <html><body style="font-family: sans-serif; max-width: 320px; margin: 80px auto;">
          <h3>{EVENT_NAME} — dashboard login</h3>
          <form method="post">
            <input type="password" name="password" placeholder="Password" autofocus
                   style="padding:8px; width:100%; box-sizing:border-box;">
            <button style="margin-top:10px; padding:8px 16px;">Enter</button>
          </form>
          {f'<p style="color:red">{error}</p>' if error else ''}
        </body></html>
        """

    @app.route("/")
    @login_required
    def dashboard():
        rows = db.all_attendees()

        def label(r):
            return f"@{r['telegram_handle']}" if r["telegram_handle"] else (r["display_name"] or str(r["telegram_id"]))

        def attend_text(r):
            return {1: "✅ Coming", 0: "❌ Not coming", None: "⬜ No response"}[r["attending"]]

        def paid_cell(r):
            if not r["paid"]:
                return "—"
            badge = "⚠️ review" if r["needs_review"] else "✅ paid"
            amount = f" ({r['detected_amount']})" if r["detected_amount"] else ""
            # cache-bust with the row's updated_at so a NEW screenshot always
            # shows, instead of the browser reusing a stale cached image
            img_url = f'/screenshot/{r["telegram_id"]}?v={r["updated_at"]}'
            thumb = f'<br><a href="{img_url}" target="_blank">' \
                    f'<img src="{img_url}" style="height:60px;border-radius:4px;margin-top:4px;"></a>' \
                    if r["screenshot_path"] else ""
            return f"{badge}{amount}{thumb}"

        paid_count = sum(1 for r in rows if r["paid"])
        coming_count = sum(1 for r in rows if r["attending"] == 1)

        rows_html = "\n".join(
            f"""<tr>
                  <td>{label(r)}</td>
                  <td>{attend_text(r)}</td>
                  <td>{paid_cell(r)}</td>
                  <td style="font-size:12px;color:#888">{format_local(r['updated_at'])}</td>
                </tr>"""
            for r in rows
        )

        return f"""
        <html>
        <head>
          <title>{EVENT_NAME} — dashboard</title>
          <meta http-equiv="refresh" content="15">
          <meta name="viewport" content="width=device-width, initial-scale=1">
          <style>
            body {{ font-family: -apple-system, sans-serif; max-width: 720px; margin: 24px auto; padding: 0 12px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
            th, td {{ text-align: left; padding: 8px; border-bottom: 1px solid #eee; vertical-align: top; }}
            th {{ color: #666; font-size: 13px; text-transform: uppercase; }}
            .stat {{ display: inline-block; margin-right: 24px; font-size: 14px; color: #444; }}
            .stat b {{ font-size: 20px; display:block; }}
          </style>
        </head>
        <body>
          <h2>{EVENT_NAME}</h2>
          <div class="stat"><b>{coming_count}</b>coming</div>
          <div class="stat"><b>{paid_count}</b>paid</div>
          <div class="stat"><b>{len(rows)}</b>total responded</div>
          <table>
            <tr><th>Guest</th><th>Attendance</th><th>Payment</th><th>Last update</th></tr>
            {rows_html if rows else '<tr><td colspan="4">No RSVPs yet.</td></tr>'}
          </table>
          <p style="color:#999;font-size:12px;margin-top:24px;">Auto-refreshes every 15s.</p>
        </body>
        </html>
        """

    @app.route("/screenshot/<int:telegram_id>")
    @login_required
    def screenshot(telegram_id):
        attendee = db.get_attendee(telegram_id)
        if not attendee or not attendee["screenshot_path"]:
            return Response(status=404)
        resp = send_file(attendee["screenshot_path"], conditional=False)
        resp.headers["Cache-Control"] = "no-store, must-revalidate"
        return resp

    return app


if __name__ == "__main__":
    db.init_db()
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), debug=True)
