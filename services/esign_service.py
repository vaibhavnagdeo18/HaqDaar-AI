"""
ESign Service — Aadhaar eSign flow (demo-mode implementation).

Production swap-out: replace the sign() method body with a call to the
CDAC / NSDL Aadhaar eSign gateway. The rest of the flow (token generation,
link delivery over WhatsApp, signed-PDF callback) stays identical.
"""
import hashlib
import logging
import uuid
from datetime import datetime
from io import BytesIO

from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.colors import black, HexColor
from pypdf import PdfReader, PdfWriter

logger = logging.getLogger(__name__)


def _generate_token(case_id: str, secret: str) -> str:
    return hashlib.sha256(f"{case_id}:{secret}:{uuid.uuid4().hex}".encode()).hexdigest()[:40]


def _signature_overlay(page_w: float, page_h: float,
                        signer_name: str, transaction_id: str, signed_at: str) -> bytes:
    buf = BytesIO()
    c = rl_canvas.Canvas(buf, pagesize=(page_w, page_h))

    bx, by, bw, bh = page_w - 222, 28, 212, 68
    c.setStrokeColor(HexColor("#1a56db"))
    c.setLineWidth(0.8)
    c.rect(bx, by, bw, bh)

    c.setFont("Helvetica-Bold", 6.5)
    c.setFillColor(HexColor("#1a56db"))
    c.drawString(bx + 5, by + 54, "DIGITALLY SIGNED — Aadhaar eSign")

    c.setFont("Helvetica", 6.5)
    c.setFillColor(black)
    c.drawString(bx + 5, by + 43, f"Name : {signer_name[:32]}")
    c.drawString(bx + 5, by + 32, f"Txn  : {transaction_id}")
    c.drawString(bx + 5, by + 21, f"Date : {signed_at}")
    c.drawString(bx + 5, by + 10, "Verified by Haqdaar AI  |  CDAC eSign")

    c.showPage()
    c.save()
    return buf.getvalue()


class ESignService:

    def create_request(self, case_id: str, secret: str, base_url: str) -> dict:
        """
        Create a signing request. Returns token, transaction_id, and signing_url.
        Store token + transaction_id in onboarding_data before sending link to user.
        """
        token = _generate_token(case_id, secret)
        transaction_id = f"HAQDAAR-{uuid.uuid4().hex[:10].upper()}"
        return {
            "token": token,
            "transaction_id": transaction_id,
            "signing_url": f"{base_url}/esign/{token}",
        }

    def apply_signature(self, pdf_bytes: bytes, signer_name: str, transaction_id: str) -> bytes:
        """
        Apply a visual Aadhaar eSign block to page 1 of the PDF.
        In production: call the CDAC eSign gateway here instead.
        """
        reader = PdfReader(BytesIO(pdf_bytes))
        writer = PdfWriter()

        p0 = reader.pages[0]
        w = float(p0.mediabox.width)
        h = float(p0.mediabox.height)
        signed_at = datetime.now().strftime("%d-%b-%Y %H:%M IST")

        overlay_bytes = _signature_overlay(w, h, signer_name, transaction_id, signed_at)
        overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
        p0.merge_page(overlay_page)
        writer.add_page(p0)

        for page in reader.pages[1:]:
            writer.add_page(page)

        writer.add_metadata({"/Keywords": f"eSigned:{transaction_id}"})

        out = BytesIO()
        writer.write(out)
        logger.info(f"Signature applied — txn {transaction_id}, signer: {signer_name}")
        return out.getvalue()
