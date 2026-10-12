"""
Best-effort OCR on a payment screenshot.

Reads whatever text Tesseract can find and tries to spot something that
looks like a paid amount (e.g. "$45.00", "SGD 45", "Amount: 45.00").

This is a heuristic, not a verifier: it does NOT confirm the money actually
moved, who it went to, or that the screenshot wasn't edited. Treat a
detected amount as a helpful hint for the organizer, not proof of payment.
Screenshots with low-contrast text, unusual fonts, or a layout we didn't
anticipate will often come back with needs_review=True — that's expected,
not a bug.
"""
import re
from io import BytesIO

from PIL import Image
import pytesseract

AMOUNT_PATTERNS = [
    r"(?:SGD|S\$|\$)\s?(\d{1,5}(?:\.\d{2})?)",
    r"(?:amount|paid|total)\D{0,5}(\d{1,5}(?:\.\d{2})?)",
]


def extract_text(image_bytes: bytes) -> str:
    img = Image.open(BytesIO(image_bytes))
    return pytesseract.image_to_string(img)


def guess_amount(text: str) -> str | None:
    lowered = text.lower()
    for pattern in AMOUNT_PATTERNS:
        match = re.search(pattern, lowered, flags=re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def analyze_screenshot(image_bytes: bytes):
    """
    Returns (detected_amount: str|None, needs_review: bool).
    needs_review is True whenever we can't confidently confirm an amount,
    so the organizer knows to glance at the screenshot themselves.
    """
    try:
        text = extract_text(image_bytes)
    except Exception:
        return None, True

    amount = guess_amount(text)
    # Very little text recognized at all -> OCR probably struggled, flag it
    needs_review = amount is None or len(text.strip()) < 10
    return amount, needs_review
