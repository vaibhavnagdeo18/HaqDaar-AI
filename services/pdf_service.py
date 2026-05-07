from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import mm
from io import BytesIO
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

def _build_esign_block(styles, transaction_id: str, content: list):
    """Appends a digital signature placeholder block to a ReportLab content list."""
    content.append(Spacer(1, 20))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    content.append(Spacer(1, 8))

    sig_title = ParagraphStyle(
        "SigTitle", parent=styles["Normal"],
        fontSize=10, fontName="Helvetica-Bold", spaceAfter=4
    )
    sig_body = ParagraphStyle(
        "SigBody", parent=styles["Normal"],
        fontSize=8, textColor=colors.grey, leading=12
    )

    content.append(Paragraph("DIGITAL SIGNATURE BLOCK", sig_title))
    content.append(Paragraph(
        "This document is pending Aadhaar eSign authentication. "
        "To complete submission, the claimant must sign this document using their Aadhaar-linked mobile OTP "
        "via the NSDL eSign Gateway.",
        sig_body
    ))
    content.append(Spacer(1, 10))

    sig_table_data = [
        ["Field", "Value"],
        ["eSign Transaction ID", transaction_id],
        ["eSign Gateway", "NSDL eSign Service (mock)"],
        ["Signature Status", "PENDING — Awaiting Aadhaar OTP"],
        ["Timestamp", datetime.now().strftime("%d/%m/%Y %H:%M:%S IST")],
    ]
    sig_table = Table(sig_table_data, colWidths=[140, 300])
    sig_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f0f0f0")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    content.append(sig_table)
    content.append(Spacer(1, 8))
    content.append(Paragraph(
        "Claimant Signature: ________________________________     Date: _______________",
        styles["Normal"]
    ))
    content.append(Paragraph(
        "Witness Signature:  ________________________________     Date: _______________",
        styles["Normal"]
    ))
    content.append(Spacer(1, 4))
    content.append(HRFlowable(width="100%", thickness=1, color=colors.grey))


class PDFService:
    def generate_claim_letter(self, data: dict) -> bytes:
        """
        Generates a formal claim letter PDF for the family.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontSize=16,
            alignment=1, # Center
            spaceAfter=20,
            textColor=colors.black
        )
        
        content = []
        content.append(Paragraph("FORMAL CLAIM APPLICATION", title_style))
        content.append(Spacer(1, 12))
        
        content.append(Paragraph(f"Date: {datetime.now().strftime('%d/%m/%Y')}", styles["Normal"]))
        content.append(Paragraph(f"Reference ID: HQ-{data.get('phone', 'TEST')[-4:]}", styles["Normal"]))
        content.append(Spacer(1, 24))
        
        content.append(Paragraph("<b>Subject: Application for Settlement of Post-Death Entitlements</b>", styles["Normal"]))
        content.append(Spacer(1, 12))
        
        content.append(Paragraph("To the Concerned Authority,", styles["Normal"]))
        content.append(Spacer(1, 12))
        
        body_text = f"""
        This is a formal application regarding the claims and entitlements of the late <b>{data.get('breadwinner_name', 'N/A')}</b>, 
        who passed away on {data.get('date_of_death', 'N/A')}. 
        As the rightful beneficiaries residing in {data.get('state', 'N/A')}, we wish to initiate the processing of all eligible government 
        and employment-based schemes as identified by the Haqdaar AI System.
        """
        content.append(Paragraph(body_text, styles["Normal"]))
        content.append(Spacer(1, 12))
        
        table_data = [
            ["Field", "Details"],
            ["Deceased Name", data.get("breadwinner_name", "N/A")],
            ["Date of Death", data.get("date_of_death", "N/A")],
            ["State of Residence", data.get("state", "N/A")],
            ["Employment Type", data.get("employment_type", "N/A")],
            ["EPF Member", data.get("had_epf", "N/A")],
            ["Est. Entitlement", f"INR {data.get('total_entitlement', 0):,}"]
        ]
        
        t = Table(table_data, colWidths=[150, 250])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        content.append(t)
        content.append(Spacer(1, 24))
        
        content.append(Paragraph("We have attached the audited Death Certificate and other necessary identity documents for your review.", styles["Normal"]))
        content.append(Spacer(1, 12))
        content.append(Paragraph("Please process this claim at the earliest. We look forward to your positive response.", styles["Normal"]))
        content.append(Spacer(1, 48))
        
        content.append(Paragraph("Yours Sincerely,", styles["Normal"]))
        content.append(Paragraph("__________________________", styles["Normal"]))
        content.append(Paragraph(f"(Beneficiary for {data.get('breadwinner_name', 'N/A')})", styles["Normal"]))
        
        content.append(Spacer(1, 100))
        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
        content.append(Paragraph("Generated by Haqdaar AI Agentic System - Helping Indian Families Claim Their Rights", footer_style))

        doc.build(content)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def generate_epf_form_20(self, data: dict, esign_transaction_id: str = None, partner_name: str = None) -> bytes:
        """
        Generates a structured EPF Form 20 with a digital signature block.
        Embeds eSign transaction ID in PDF metadata when provided.
        Renders a white-label partner header when partner_name is supplied.
        """
        transaction_id = esign_transaction_id or f"ESIGN-MOCK-{uuid.uuid4().hex[:12].upper()}"
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50,
            title="EPF Form 20 - Haqdaar",
            author=partner_name or "Haqdaar AI",
            subject=f"eSign Transaction: {transaction_id}",
            keywords=f"EPF,Form20,eSign,{transaction_id}",
        )
        styles = getSampleStyleSheet()

        content = []

        # White-label header for B2B partners
        if partner_name:
            partner_header_style = ParagraphStyle(
                "PartnerHeader", parent=styles["Normal"],
                fontSize=9, textColor=colors.white,
                backColor=colors.HexColor("#1a1a2e"),
                alignment=1, spaceAfter=0,
                leftPadding=8, rightPadding=8, topPadding=6, bottomPadding=6,
            )
            powered_style = ParagraphStyle(
                "PoweredBy", parent=styles["Normal"],
                fontSize=7, textColor=colors.HexColor("#888888"),
                alignment=2, spaceAfter=12,
            )
            content.append(Paragraph(
                f"CLAIMS PROCESSED BY: <b>{partner_name.upper()}</b>",
                partner_header_style,
            ))
            content.append(Paragraph("Powered by Haqdaar AI Agentic Platform", powered_style))

        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=18, alignment=1, spaceAfter=20)
        content.append(Paragraph("EPF FORM 20", title_style))
        content.append(Paragraph("(CLAIM FOR WITHDRAWAL OF PROVIDENT FUND BY NOMINEE/HEIRS)", styles['Normal']))
        content.append(Spacer(1, 20))
        
        # Mapping as requested in Task 1
        form_data = [
            ["FIELD", "INPUT VALUE"],
            ["1. Name of the Deceased Member", data.get("breadwinner_name", "N/A")],
            ["2. Date of Death", data.get("date_of_death", "N/A")],
            ["3. Employment Type", data.get("employment_type", "N/A")],
            ["4. State", data.get("state", "N/A")],
            ["5. Nominee Name", "Claimant"],
            ["6. UAN", "pending verification"],
            ["7. EPFO Office", f"Regional Office for {data.get('state', 'India')}"]
        ]
        
        t = Table(form_data, colWidths=[200, 250])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.darkgreen),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ]))
        content.append(t)
        content.append(Spacer(1, 30))
        
        declaration = f"""
        I, <b>Claimant</b>, hereby declare that the particulars given above are true to the best of my knowledge. 
        I request the EPFO to settle the claims of the deceased member <b>{data.get('breadwinner_name', 'DECEASED')}</b>.
        """
        content.append(Paragraph("<b>DECLARATION:</b>", styles['Normal']))
        content.append(Paragraph(declaration, styles['Normal']))
        content.append(Spacer(1, 50))
        
        _build_esign_block(styles, transaction_id, content)

        doc.build(content)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes, transaction_id

    def generate_affidavit(self, draft_text: str) -> bytes:
        """
        Generates a formal One-and-the-Same Person Affidavit PDF.
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        
        content = []
        content.append(Paragraph("ONE-AND-THE-SAME PERSON AFFIDAVIT", styles["Heading1"]))
        content.append(Spacer(1, 24))
        
        legal_style = ParagraphStyle('Legal', parent=styles['Normal'], leading=16)
        content.append(Paragraph(draft_text.replace('\n', '<br/>'), legal_style))
        
        doc.build(content)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
