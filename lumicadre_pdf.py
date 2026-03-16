from io import BytesIO
from urllib.request import Request, urlopen

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from scraper import VehicleData


def _download_image(image_url: str, timeout: int = 12) -> bytes | None:
    if not image_url:
        return None
    try:
        req = Request(image_url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as response:  # noqa: S310
            return response.read()
    except Exception:  # noqa: BLE001
        return None


def _draw_image_fit(c: canvas.Canvas, image_bytes: bytes, x: float, y: float, width: float, height: float) -> None:
    reader = ImageReader(BytesIO(image_bytes))
    img_w, img_h = reader.getSize()
    ratio = min(width / img_w, height / img_h)
    draw_w = img_w * ratio
    draw_h = img_h * ratio
    draw_x = x + (width - draw_w) / 2
    draw_y = y + (height - draw_h) / 2
    c.drawImage(reader, draw_x, draw_y, width=draw_w, height=draw_h, preserveAspectRatio=True, mask="auto")


def build_lumicadre_pdf(data: VehicleData) -> bytes:
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    page_w, page_h = A4

    margin = 24
    top = page_h - margin

    c.setTitle("Lumicadre A4")

    c.setFillColor(colors.HexColor("#0f62fe"))
    c.rect(margin, top - 55, page_w - 2 * margin, 40, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(margin + 12, top - 40, "EWIGO SAUMUR - FICHE VÉHICULE (A4)")

    c.setFillColor(colors.black)
    title = data.title or f"{data.make} {data.model}".strip() or "Véhicule"
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, top - 84, title[:70])

    c.setFont("Helvetica-Bold", 24)
    c.setFillColor(colors.HexColor("#b00020"))
    c.drawRightString(page_w - margin, top - 84, data.price or "Prix à compléter")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    specs = [
        ("Année", data.year),
        ("Kilométrage", data.mileage),
        ("Énergie", data.fuel),
        ("Boîte", data.gearbox),
        ("Puissance", data.power),
    ]

    spec_y = top - 118
    c.roundRect(margin, spec_y - 70, page_w - 2 * margin, 72, 8, stroke=1, fill=0)
    col_width = (page_w - 2 * margin) / 5
    for idx, (label, value) in enumerate(specs):
        x = margin + idx * col_width + 8
        c.setFont("Helvetica-Bold", 10)
        c.drawString(x, spec_y - 18, label)
        c.setFont("Helvetica", 10)
        c.drawString(x, spec_y - 36, (value or "-")[:18])

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, spec_y - 96, "Options (extraites de l'annonce)")
    c.setFont("Helvetica", 10)

    options = data.options[:8] if data.options else ["Aucune option détectée automatiquement"]
    opt_y = spec_y - 114
    for option in options:
        c.drawString(margin + 8, opt_y, f"• {option[:85]}")
        opt_y -= 14

    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, 300, "Photos (5 premières)")

    photos = data.image_urls[:5]
    if not photos and data.image_url:
        photos = [data.image_url]

    box_w = (page_w - (2 * margin) - 16) / 3
    box_h = 110
    start_y = 170

    for i in range(5):
        row = i // 3
        col = i % 3
        x = margin + col * (box_w + 8)
        y = start_y - row * (box_h + 10)

        c.setStrokeColor(colors.HexColor("#9ca3af"))
        c.rect(x, y, box_w, box_h, stroke=1, fill=0)

        if i < len(photos):
            image_bytes = _download_image(photos[i])
            if image_bytes:
                try:
                    _draw_image_fit(c, image_bytes, x + 2, y + 2, box_w - 4, box_h - 4)
                except Exception:  # noqa: BLE001
                    c.setFont("Helvetica", 9)
                    c.drawString(x + 6, y + box_h / 2, "Image non lisible")
            else:
                c.setFont("Helvetica", 9)
                c.drawString(x + 6, y + box_h / 2, "Téléchargement image impossible")
        else:
            c.setFont("Helvetica", 9)
            c.drawString(x + 6, y + box_h / 2, "Photo non disponible")

    c.setFont("Helvetica", 8)
    c.setFillColor(colors.HexColor("#6b7280"))
    c.drawString(margin, 24, f"Source: {data.source_url[:110]}")

    c.showPage()
    c.save()
    return buffer.getvalue()
