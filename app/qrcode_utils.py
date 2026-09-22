import io

import qrcode


def generate_qr_png(data: str) -> bytes:
    """Erzeugt ein QR-Code-Bild (PNG-Bytes) für den übergebenen Text/Code."""
    img = qrcode.make(data, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
