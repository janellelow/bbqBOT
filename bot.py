"""
BBQ RSVP + payment-screenshot bot.

Flow for guests:
  1. They message the bot (e.g. tap a link you share, or send /start).
  2. Bot asks "Coming to the BBQ?" with Yes/No buttons.
  3. If Yes, bot asks them to send a screenshot of their payment.
  4. Bot runs OCR on the screenshot, stores it, and tells them what it found.

Flow for you (the organizer):
  - /status in the bot chat (or in a group it's in, as an admin) prints a
    live breakdown: paid & coming / came but not paid / RSVP'd no / no
    response yet, plus a "needs review" list for screenshots OCR wasn't
    sure about.
  - /markpaid @handle and /markunpaid @handle let you override OCR by hand
    — this is the safety net, since OCR on real payment screenshots is
    genuinely unreliable (different apps, fonts, cropping, etc).

Setup:
  - Set BOT_TOKEN (from BotFather) and ADMIN_IDS (comma-separated Telegram
    numeric user IDs) as environment variables. See README.md.
"""
import logging
import os
import re
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

import db
from ocr import analyze_screenshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bbq-bot")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_IDS = {int(x) for x in os.environ.get("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
EVENT_NAME = os.environ.get("EVENT_NAME", "the BBQ")
PAYMENT_INSTRUCTIONS = os.environ.get("PAYMENT_INSTRUCTIONS", "").strip()

SCREENSHOT_DIR = Path("screenshots")
SCREENSHOT_DIR.mkdir(exist_ok=True)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def handle_label(user) -> str:
    """Display name used in /status: @handle if they have one, else first name."""
    if user.username:
        return f"@{user.username}"
    return user.full_name or str(user.id)


# ---------- guest-facing flow ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_attendee(user.id, user.username or "", user.full_name or "")

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("✅ I'm coming", callback_data="attend_yes"),
          InlineKeyboardButton("❌ Can't make it", callback_data="attend_no")]]
    )
    await update.message.reply_text(
        f"Hey {user.first_name}! Are you coming to {EVENT_NAME}?",
        reply_markup=keyboard,
    )


async def on_attendance_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    db.upsert_attendee(user.id, user.username or "", user.full_name or "")

    if query.data == "attend_yes":
        db.set_attendance(user.id, True)
        msg = "Awesome, you're on the list! 🎉\n\n"
        if PAYMENT_INSTRUCTIONS:
            msg += PAYMENT_INSTRUCTIONS + "\n\n"
        msg += "Once you've paid, just send a screenshot of the payment here and I'll log it."
        await query.edit_message_text(msg)
    else:
        db.set_attendance(user.id, False)
        await query.edit_message_text("No worries, sorry you can't make it! 👋")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.upsert_attendee(user.id, user.username or "", user.full_name or "")

    attendee = db.get_attendee(user.id)
    if not attendee or attendee["attending"] != 1:
        await update.message.reply_text(
            "Thanks! Just to double check — are you coming to the BBQ? "
            "Send /start if you haven't RSVP'd yet."
        )
        # still log the screenshot below, in case they RSVP after

    photo = update.message.photo[-1]  # highest resolution
    tg_file = await photo.get_file()
    image_bytes = bytes(await tg_file.download_as_bytearray())

    # Save to disk so the web dashboard can display it
    screenshot_path = SCREENSHOT_DIR / f"{user.id}.jpg"
    screenshot_path.write_bytes(image_bytes)

    amount, needs_review = analyze_screenshot(image_bytes)
    db.set_payment(user.id, tg_file.file_id, str(screenshot_path), amount, needs_review, paid=True)

    if amount and not needs_review:
        await update.message.reply_text(
            f"Got it — looks like a payment of {amount} 👍\n"
            f"(Marked as paid. If that's wrong, let the organizer know.)"
        )
    else:
        await update.message.reply_text(
            "Got your screenshot! I couldn't confidently read the amount "
            "automatically, so I've flagged it for the organizer to double-check. "
            "You're marked as paid for now."
        )


# ---------- organizer-facing commands ----------

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            "This command is for the organizer. (Your Telegram ID is "
            f"{user.id} — add it to ADMIN_IDS if that's you.)"
        )
        return

    rows = db.all_attendees()
    paid_coming, unpaid_coming, not_coming, no_response, needs_review = [], [], [], [], []

    for r in rows:
        label = f"@{r['telegram_handle']}" if r["telegram_handle"] else (r["display_name"] or str(r["telegram_id"]))
        if r["attending"] == 1:
            if r["paid"]:
                paid_coming.append(label)
            else:
                unpaid_coming.append(label)
            if r["needs_review"]:
                needs_review.append(f"{label} (OCR read: {r['detected_amount'] or 'nothing'})")
        elif r["attending"] == 0:
            not_coming.append(label)
        else:
            no_response.append(label)

    def section(title, items):
        if not items:
            return f"*{title}* (0): none\n"
        return f"*{title}* ({len(items)}): " + ", ".join(items) + "\n"

    msg = (
        f"📋 *{EVENT_NAME} — status*\n\n"
        + section("✅ Coming & paid", paid_coming)
        + section("🟡 Coming, not paid", unpaid_coming)
        + section("❌ Not coming", not_coming)
        + section("⬜ No response yet", no_response)
    )
    if needs_review:
        msg += "\n⚠️ *Needs manual review:*\n" + "\n".join(needs_review)
        msg += "\n\nUse /markpaid @handle or /markunpaid @handle to override."

    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def _mark(update: Update, context: ContextTypes.DEFAULT_TYPE, paid: bool):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("This command is for the organizer.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /markpaid @handle or name (or /markunpaid ...)")
        return

    target = " ".join(context.args)
    matches = db.find_attendees(target)
    if not matches:
        await update.message.reply_text(
            f"Couldn't find \"{target}\". If they never used the bot, add them with:\n"
            f"/addpaid {target}"
        )
        return
    if len(matches) > 1:
        await update.message.reply_text(
            f"More than one person matches \"{target}\" - please use their @handle instead."
        )
        return

    db.manual_set_paid(matches[0]["telegram_id"], paid)
    await update.message.reply_text(f"Marked {target} as {'paid' if paid else 'not paid'}.")


async def addpaid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Organizer adds someone who paid directly and never used the bot."""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("This command is for the organizer.")
        return
    if not context.args:
        await update.message.reply_text("Usage: /addpaid Name  (e.g. /addpaid Sarah Tan)")
        return

    name = " ".join(context.args)
    if db.find_attendees(name):
        await update.message.reply_text(
            f"\"{name}\" is already in the list. Use /markpaid {name} instead."
        )
        return

    db.add_manual_attendee(name, paid=True)
    await update.message.reply_text(f"Added {name} as coming and paid (entered manually).")


async def markpaid(update, context):
    await _mark(update, context, True)


async def markunpaid(update, context):
    await _mark(update, context, False)


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"Your Telegram numeric ID is: {user.id}")


def build_application():
    if not BOT_TOKEN:
        raise SystemExit("Set the BOT_TOKEN environment variable (get one from @BotFather).")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("markpaid", markpaid))
    application.add_handler(CommandHandler("markunpaid", markunpaid))
    application.add_handler(CommandHandler("addpaid", addpaid))
    application.add_handler(CommandHandler("whoami", whoami))
    application.add_handler(CallbackQueryHandler(on_attendance_button, pattern="^attend_"))
    application.add_handler(MessageHandler(filters.PHOTO, on_photo))
    return application


def main():
    db.init_db()
    application = build_application()
    log.info("Bot starting (admins: %s)...", ADMIN_IDS or "NONE SET")
    application.run_polling()


if __name__ == "__main__":
    main()
