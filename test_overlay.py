"""
test_overlay.py — coordinate calibration probe for Form5IF.pdf

Run inside the container:
    docker-compose exec app python3 test_overlay.py

This script places a single test value in the "Name of Deceased" field and
saves the result to /app/test_overlay_output.pdf so you can visually verify
alignment before running the full overlay.

Adjust X_NAME / Y_NAME until the text lands cleanly inside the field line.
"""
from reportlab.pdfgen import canvas
from reportlab.lib.colors import blue, red, green
from pypdf import PdfReader, PdfWriter
from io import BytesIO

# ── Tune these until the text sits on the correct field line ─────────────────
X_NAME   = 101   # x coordinate for "Name of Deceased" field
Y_NAME   = 582   # y coordinate (bottom-left origin, points)
FONT     = "Helvetica"
FONTSIZE = 10

# Page dimensions from the PDF (run once to confirm)
PAGE_W = 625
PAGE_H = 864

# ── Test values ───────────────────────────────────────────────────────────────
TEST_DATA = {
    "deceased_name": "RAMESH KUMAR",
    "father_name":   "SURESH KUMAR",
    # Date of death 15/08/2023 split into individual characters
    "dod": ("1", "5", "0", "8", "2", "0", "2", "3"),
    "employer_name": "ACME PRIVATE LIMITED, HYDERABAD",
    "pf_account_no": "HYD/12345/678",
    "claimant_name": "PRIYA KUMAR",
    "relationship":  "WIFE",
}

# Date box x-positions (one entry per digit slot)
# Spans x=213 to x=411; slashes are pre-printed between slots 2-3 and 4-5
DOD_X = [219, 238, 271, 290, 325, 344, 363, 382]
DOD_Y = 523

FATHER_Y       = 552
EMPLOYER_Y     = 468
PF_Y           = 411
CLAIMANT_Y     = 362
RELATIONSHIP_Y = 316


def build_overlay() -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(PAGE_W, PAGE_H))
    c.setFont(FONT, FONTSIZE)
    c.setFillColor(blue)

    # ── Page 1 ─────────────────────────────────────────────────────────────
    # Deceased name
    c.drawString(X_NAME, Y_NAME, TEST_DATA["deceased_name"])

    # Father name
    c.drawString(X_NAME, FATHER_Y, TEST_DATA["father_name"])

    # Date of death - individual characters in boxes
    for i, ch in enumerate(TEST_DATA["dod"]):
        c.drawString(DOD_X[i], DOD_Y, ch)

    # Employer
    c.drawString(X_NAME, EMPLOYER_Y, TEST_DATA["employer_name"])

    # PF account
    c.drawString(X_NAME, PF_Y, TEST_DATA["pf_account_no"])

    # Claimant
    c.drawString(X_NAME, CLAIMANT_Y, TEST_DATA["claimant_name"])

    # Relationship
    c.drawString(X_NAME, RELATIONSHIP_Y, TEST_DATA["relationship"])

    # ── Calibration grid — thin red lines at key y values ──────────────────
    c.setStrokeColor(red)
    c.setLineWidth(0.3)
    for y in [Y_NAME, FATHER_Y, DOD_Y, EMPLOYER_Y, PF_Y, CLAIMANT_Y, RELATIONSHIP_Y]:
        c.line(80, y, 550, y)

    # Green crosshair on the primary probe point
    c.setStrokeColor(green)
    c.setLineWidth(0.5)
    c.line(X_NAME - 5, Y_NAME, X_NAME + 5, Y_NAME)
    c.line(X_NAME, Y_NAME - 5, X_NAME, Y_NAME + 5)

    c.showPage()
    c.save()
    return buf.getvalue()


def merge_with_form(overlay_bytes: bytes, form_path: str, output_path: str):
    reader = PdfReader(form_path)
    overlay_reader = PdfReader(BytesIO(overlay_bytes))

    writer = PdfWriter()
    form_page = reader.pages[0]
    overlay_page = overlay_reader.pages[0]

    form_page.merge_page(overlay_page)
    writer.add_page(form_page)

    # Copy remaining pages as-is
    for i in range(1, len(reader.pages)):
        writer.add_page(reader.pages[i])

    with open(output_path, "wb") as f:
        writer.write(f)

    print(f"Saved: {output_path}")
    print()
    print("Field coordinate probes used:")
    print(f"  deceased_name  → x={X_NAME}, y={Y_NAME}")
    print(f"  father_name    → x={X_NAME}, y={FATHER_Y}")
    print(f"  date_of_death  → y={DOD_Y}, x positions: {DOD_X}")
    print(f"  employer_name  → x={X_NAME}, y={EMPLOYER_Y}")
    print(f"  pf_account_no  → x={X_NAME}, y={PF_Y}")
    print(f"  claimant_name  → x={X_NAME}, y={CLAIMANT_Y}")
    print(f"  relationship   → x={X_NAME}, y={RELATIONSHIP_Y}")


if __name__ == "__main__":
    overlay = build_overlay()
    merge_with_form(overlay, "/app/Form5IF.pdf", "/app/test_overlay_output.pdf")
