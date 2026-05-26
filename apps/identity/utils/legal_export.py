import io
from reportlab.pdfgen import canvas
def generate_pdf_certificate(record):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer)
    c.drawString(100, 800, "LEGAL CONSENT CERTIFICATE")
    c.drawString(100, 780, f"User: {record.user.email}")
    c.drawString(100, 760, f"Terms: {record.terms_version}")
    c.drawString(100, 740, f"Date: {record.accepted_at}")
    c.drawString(100, 700, f"Cert Hash: {record.crypto_signature or ''}")
    c.showPage(); c.save(); buffer.seek(0)
    return buffer
