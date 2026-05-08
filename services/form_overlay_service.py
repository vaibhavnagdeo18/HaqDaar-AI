"""
Form5IF PDF Overlay Service

Loads the official Form5IF.pdf as background, draws user data onto a
transparent ReportLab canvas, and merges the two layers using pypdf.

Coordinate system: origin is bottom-left (PDF standard), points (1/72 inch).
Page size: 625 x 864 pts (confirmed from Form5IF.pdf mediabox).

All coordinates were derived by extracting character positions via pypdf's
visitor API and placing each field ~11 pts below its printed label.
"""
import os
import logging
from io import BytesIO
from typing import Optional

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import black
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

PAGE_W = 625
PAGE_H = 864
FORM_PATH = os.path.join(os.path.dirname(__file__), "..", "Form5IF.pdf")

# ── Coordinate map ────────────────────────────────────────────────────────────
# Tuned from visitor-based extraction. Each entry: (x, y, font_size).
# Date/DOB fields are split into individual digit slots so characters
# land inside the pre-printed boxes on the form.

PAGE1 = {
    # 1(a) Name of the Deceased member  — label at y=593
    "deceased_name":    (101, 582, 10),

    # 1(b) Father's / Husband's name    — label at y=562
    "father_name":      (101, 552, 10),

    # 1(c) Date of Death dd/mm/yyyy boxes — box row at y=524
    #      Slashes at x≈257 and x≈309 are pre-printed on the form.
    "dod_d1":           (219, 523, 10),
    "dod_d2":           (238, 523, 10),
    "dod_m1":           (271, 523, 10),
    "dod_m2":           (290, 523, 10),
    "dod_y1":           (325, 523, 10),
    "dod_y2":           (344, 523, 10),
    "dod_y3":           (363, 523, 10),
    "dod_y4":           (382, 523, 10),

    # 1(d) Factory / Establishment name & address — label at y=497
    "employer_name":    (101, 468, 9),
    "employer_address": (101, 455, 9),

    # 1(e) PF Account fields             — label at y=430, boxes at y=412
    "pf_account_no":    (101, 411, 9),
    "ro_office_code":   (287, 411, 9),
    "estt_code":        (360, 411, 9),
    "ac_no":            (450, 411, 9),

    # 2(a) Claimant name                 — label at y=374
    "claimant_name":    (101, 362, 10),

    # 2(b) Claimant Date of Birth boxes  — label at y=350
    "dob_d1":           (219, 339, 10),
    "dob_d2":           (238, 339, 10),
    "dob_m1":           (271, 339, 10),
    "dob_m2":           (290, 339, 10),
    "dob_y1":           (325, 339, 10),
    "dob_y2":           (344, 339, 10),
    "dob_y3":           (363, 339, 10),
    "dob_y4":           (382, 339, 10),

    # 2(c) Relationship with deceased    — label at y=328
    "relationship":     (101, 316, 10),

    # Claimant address block             — address area y≈225
    "address_line1":    (101, 210, 9),
    "address_line2":    (101, 197, 9),
    "address_pin":      (350, 183, 9),
}

PAGE2 = {
    # Bank / remittance details — right column, label at y≈759
    "bank_account_no":  (362, 758, 9),
    "bank_name":        (368, 727, 9),
    "branch_name":      (310, 708, 9),
    "branch_address":   (280, 675, 9),
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_date(date_str: str) -> tuple[str, str, str, str, str, str, str, str]:
    """
    Accept dates in DD/MM/YYYY or DD-MM-YYYY. Returns 8 single characters.
    Falls back to empty strings on malformed input.
    """
    try:
        clean = date_str.replace("-", "/").strip()
        parts = clean.split("/")
        if len(parts) == 3:
            dd, mm, yyyy = parts[0].zfill(2), parts[1].zfill(2), parts[2].zfill(4)
            return dd[0], dd[1], mm[0], mm[1], yyyy[0], yyyy[1], yyyy[2], yyyy[3]
    except Exception:
        pass
    return ("", "", "", "", "", "", "", "")


def _truncate(text: Optional[str], max_chars: int) -> str:
    if not text:
        return ""
    return str(text)[:max_chars]


import re as _re

def _extract_pin(address: str) -> str:
    """Extract 6-digit PIN from an address string (e.g. 'Hyderabad 500016')."""
    m = _re.search(r'\b(\d{6})\b', address or "")
    return m.group(1) if m else ""


def _split_address(address: str) -> tuple[str, str, str]:
    """
    Split a free-text address into (line1, line2, pin).
    Joins all non-PIN parts into two display lines.
    """
    pin = _extract_pin(address)
    # Remove the PIN from the string, then split on commas
    clean = _re.sub(r'\b\d{6}\b', '', address).strip().strip(',').strip()
    parts = [p.strip() for p in clean.split(',') if p.strip()]
    line1 = parts[0] if parts else ""
    line2 = ", ".join(parts[1:]) if len(parts) > 1 else ""
    return line1, line2, pin


# ── Core overlay logic ────────────────────────────────────────────────────────

def _build_page1_overlay(data: dict) -> bytes:
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setFont("Helvetica", 10)
    c.setFillColor(black)

    def put(field: str, text: str):
        if field not in PAGE1 or not text:
            return
        x, y, size = PAGE1[field]
        c.setFont("Helvetica", size)
        c.drawString(x, y, text)

    # 1(a) Deceased name — upper-case for clarity
    put("deceased_name", _truncate(data.get("breadwinner_name", ""), 45).upper())

    # 1(b) Father/husband name
    put("father_name", _truncate(data.get("father_name", ""), 45).upper())

    # 1(c) Date of death — split into individual box characters
    dod_chars = _parse_date(data.get("date_of_death", ""))
    for i, key in enumerate(["dod_d1","dod_d2","dod_m1","dod_m2","dod_y1","dod_y2","dod_y3","dod_y4"]):
        put(key, dod_chars[i])

    # 1(d) Employer
    employer = data.get("employer_name", "") or data.get("employment_type", "")
    put("employer_name", _truncate(employer, 55).upper())

    # 1(e) PF / UAN account numbers
    pf_raw = data.get("epf_account_number") or data.get("uan_number") or data.get("pf_account_no", "")
    if pf_raw:
        parts = str(pf_raw).split("/")
        put("pf_account_no",  _truncate(parts[0], 18))
        put("ro_office_code", _truncate(parts[1], 8) if len(parts) > 1 else "")
        put("estt_code",      _truncate(parts[2], 10) if len(parts) > 2 else "")
        put("ac_no",          _truncate(parts[3], 10) if len(parts) > 3 else "")

    # 2(a) Claimant name
    put("claimant_name", _truncate(
        data.get("claimant_name") or data.get("nominee_name", ""), 45
    ).upper())

    # 2(b) Claimant date of birth
    dob_chars = _parse_date(data.get("claimant_dob", ""))
    for i, key in enumerate(["dob_d1","dob_d2","dob_m1","dob_m2","dob_y1","dob_y2","dob_y3","dob_y4"]):
        put(key, dob_chars[i])

    # 2(c) Relationship
    put("relationship", _truncate(
        data.get("claimant_relationship") or data.get("relationship", ""), 30
    ).upper())

    # Address — extract PIN from the address string; fall back to pin_code field
    address = data.get("claimant_address", "") or data.get("address", "")
    line1, line2, pin = _split_address(address)
    if not pin:
        pin = _truncate(data.get("pin_code", ""), 8)
    put("address_line1", _truncate(line1, 55).upper())
    put("address_line2", _truncate(line2, 55).upper())
    put("address_pin",   pin)

    c.showPage()
    c.save()
    return buf.getvalue()


def _build_page2_overlay(data: dict) -> bytes:
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setFont("Helvetica", 9)
    c.setFillColor(black)

    def put(field: str, text: str):
        if field not in PAGE2 or not text:
            return
        x, y, size = PAGE2[field]
        c.setFont("Helvetica", size)
        c.drawString(x, y, text)

    bank_acc = data.get("claimant_bank_account") or data.get("bank_account", "")
    ifsc     = data.get("claimant_bank_ifsc") or data.get("bank_ifsc", "")

    put("bank_account_no", _truncate(bank_acc, 25))

    # Derive bank name from IFSC prefix (first 4 chars = bank code)
    bank_name = data.get("bank_name", "")
    if not bank_name and ifsc:
        bank_name = ifsc[:4].upper()
    put("bank_name",    _truncate(bank_name, 30))
    put("branch_name",  _truncate(data.get("bank_branch", ""), 30))
    put("branch_address", _truncate(data.get("bank_address", ""), 50))

    c.showPage()
    c.save()
    return buf.getvalue()


def _merge_overlay(form_page, overlay_bytes: bytes, page_index: int):
    """Merge a single overlay canvas page onto the corresponding form page."""
    overlay_reader = PdfReader(BytesIO(overlay_bytes))
    overlay_page = overlay_reader.pages[0]
    form_page.merge_page(overlay_page)
    return form_page


# ── Public API ────────────────────────────────────────────────────────────────

class FormOverlayService:

    def generate_form5if(self, data: dict, case_id: str) -> bytes:
        """
        Overlay user data onto the official Form5IF.pdf template.
        Returns the filled PDF as bytes.
        """
        form_path = os.path.abspath(FORM_PATH)
        if not os.path.exists(form_path):
            raise FileNotFoundError(f"Form5IF.pdf template not found at {form_path}")

        logger.info(f"Generating filled Form5IF for case {case_id}")

        reader = PdfReader(form_path)
        writer = PdfWriter()

        # Page 1 — claimant and deceased details
        p1_overlay = _build_page1_overlay(data)
        p1 = reader.pages[0]
        p1.merge_page(PdfReader(BytesIO(p1_overlay)).pages[0])
        writer.add_page(p1)

        # Page 2 — bank / remittance details
        p2_overlay = _build_page2_overlay(data)
        p2 = reader.pages[1]
        p2.merge_page(PdfReader(BytesIO(p2_overlay)).pages[0])
        writer.add_page(p2)

        # Pages 3 & 4 — employer certificate + commissioner's office (unchanged)
        for i in range(2, len(reader.pages)):
            writer.add_page(reader.pages[i])

        # Set PDF metadata
        writer.add_metadata({
            "/Title": f"Form5IF - EDLI Claim - {data.get('breadwinner_name', 'Unknown')}",
            "/Author": "Haqdaar AI Agentic Platform",
            "/Subject": f"Case ID: {case_id}",
        })

        out_buf = BytesIO()
        writer.write(out_buf)
        logger.info(f"Form5IF generated successfully for case {case_id}")
        return out_buf.getvalue()

    def save_to_disk(self, pdf_bytes: bytes, case_id: str, storage_path: str = "./documents") -> str:
        """Save filled PDF to storage and return the file path."""
        os.makedirs(storage_path, exist_ok=True)
        filename = f"filled_Form5IF_{case_id}.pdf"
        filepath = os.path.join(storage_path, filename)
        with open(filepath, "wb") as f:
            f.write(pdf_bytes)
        logger.info(f"Saved Form5IF to {filepath}")
        return filepath
