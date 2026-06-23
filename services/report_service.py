"""
report_service.py

Generates a single-page Employee Summary Report as a PDF, using a fixed
canvas layout (absolute x/y coordinates) rather than flowing text. This
guarantees every report produced has IDENTICAL structure, regardless of
content length — names get truncated/wrapped within their box, not the
other way around.

If you need to change the template, edit the coordinates/styles below.
Every report generated will reflect the new layout uniformly.
"""

import json
from datetime import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

PAGE_W, PAGE_H = letter  # 612 x 792 pt

# ---- Design tokens (fixed — do not vary per report) ----
INK = HexColor("#1A1D29")
ACCENT = HexColor("#4F6F52")
MUTED = HexColor("#8B8578")
BORDER = HexColor("#E8E6E0")
PAGE_BG = HexColor("#FFFFFF")

MARGIN_X = 56
FONT_TITLE = "Helvetica-Bold"
FONT_LABEL = "Helvetica-Bold"
FONT_BODY = "Helvetica"
FONT_MONO = "Courier"


def _truncate(text: str, font: str, size: float, max_width: float) -> str:
    """Truncate text with an ellipsis so it never overflows its box."""
    text = "" if text is None else str(text)
    if stringWidth(text, font, size) <= max_width:
        return text
    while text and stringWidth(text + "…", font, size) > max_width:
        text = text[:-1]
    return text + "…" if text else ""


def _field_row(c, x, y, label, value, label_width=120, value_max_width=300):
    """One label/value row in the fixed grid. Always same font/size/position logic."""
    c.setFont(FONT_LABEL, 9)
    c.setFillColor(MUTED)
    c.drawString(x, y, label.upper())

    c.setFont(FONT_BODY, 11)
    c.setFillColor(INK)
    safe_value = _truncate(value if value not in (None, "") else "—", FONT_BODY, 11, value_max_width)
    c.drawString(x + label_width, y, safe_value)


def generate_employee_summary(employee: dict, leave_info: dict | None = None) -> Path:
    """
    Build a fixed one-page PDF summary for a single employee.

    Expected `employee` keys (missing keys render as "—", never break layout):
        id, name, department, role/title, email, phone, start_date, status

    Expected `leave_info` keys (optional):
        leave_balance, leave_taken, leave_type

    Returns the Path to the generated PDF.
    """
    emp_id = employee.get("id", "unknown")
    filename = f"employee_summary_{emp_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    out_path = REPORTS_DIR / filename

    c = canvas.Canvas(str(out_path), pagesize=letter)

    # ---- Background ----
    c.setFillColor(PAGE_BG)
    c.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)

    # ---- Header band ----
    header_h = 96
    c.setFillColor(INK)
    c.rect(0, PAGE_H - header_h, PAGE_W, header_h, fill=1, stroke=0)

    c.setFillColor(HexColor("#FFFFFF"))
    c.setFont(FONT_TITLE, 20)
    c.drawString(MARGIN_X, PAGE_H - 46, "Employee Summary")

    c.setFont(FONT_BODY, 10)
    c.setFillColor(HexColor("#C9CCD6"))
    c.drawString(MARGIN_X, PAGE_H - 64, "Personnel Desk · Generated report")

    # Accent rule under header
    c.setFillColor(ACCENT)
    c.rect(0, PAGE_H - header_h - 3, PAGE_W, 3, fill=1, stroke=0)

    # Generated timestamp, top-right
    c.setFont(FONT_MONO, 8)
    c.setFillColor(HexColor("#C9CCD6"))
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 28, f"GENERATED {ts}")

    # ---- Identity block ----
    y = PAGE_H - header_h - 50
    c.setFont(FONT_TITLE, 18)
    c.setFillColor(INK)
    c.drawString(MARGIN_X, y, employee.get("name", "—"))

    c.setFont(FONT_MONO, 10)
    c.setFillColor(ACCENT)
    c.drawRightString(PAGE_W - MARGIN_X, y, f"ID #{emp_id}")

    y -= 18
    c.setFont(FONT_BODY, 12)
    c.setFillColor(MUTED)
    c.drawString(MARGIN_X, y, employee.get("department") or "—")

    # Divider
    y -= 18
    c.setStrokeColor(BORDER)
    c.setLineWidth(1)
    c.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)

    # ---- Section: Leave ----
    y -= 34
    c.setFont(FONT_LABEL, 10)
    c.setFillColor(ACCENT)
    c.drawString(MARGIN_X, y, "LEAVE")

    leave_info = leave_info or {}
    y -= 22
    _field_row(c, MARGIN_X, y, "Balance (days)", leave_info.get("leave_balance"))

    # ---- Footer (fixed, always same position from bottom) ----
    footer_y = 50
    c.setStrokeColor(BORDER)
    c.line(MARGIN_X, footer_y + 14, PAGE_W - MARGIN_X, footer_y + 14)
    c.setFont(FONT_BODY, 8)
    c.setFillColor(MUTED)
    c.drawString(MARGIN_X, footer_y, "This report is system-generated and reflects records at time of generation.")
    c.drawRightString(PAGE_W - MARGIN_X, footer_y, "Page 1 of 1")

    c.showPage()
    c.save()

    return out_path