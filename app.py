from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from scraper import VehicleData, extract_vehicle_data


FORM_FIELDS = [
    ("title", "Titre"),
    ("make", "Marque"),
    ("model", "Modèle"),
    ("version", "Version"),
    ("price", "Prix"),
    ("year", "Année"),
    ("mileage", "Kilométrage"),
    ("fuel", "Énergie"),
    ("gearbox", "Boîte"),
    ("power", "Puissance (CH)"),
]


def render_page(data: VehicleData, error: str = "") -> str:
    values = data.to_dict()
    rows = "".join(
        f"""
        <div class='field'>
          <label for='{name}'>{label}</label>
          <input id='{name}' type='text' value='{escape(str(values.get(name, "")))}' readonly />
        </div>
        """
        for name, label in FORM_FIELDS
    )

    photos = data.image_urls[:5] if data.image_urls else ([data.image_url] if data.image_url else [])
    photos_html = "".join(
        f"<img src='{escape(url)}' alt='Photo {idx + 1}' />" for idx, url in enumerate(photos)
    )

    options = data.options[:8] if data.options else []
    options_html = "".join(f"<li>{escape(opt)}</li>" for opt in options)

    download_button = ""
    if values.get("source_url"):
        download_button = (
            "<a class='download' href='/download-pdf?url="
            f"{escape(str(values['source_url']))}'>📄 Télécharger le Lumicadre A4 (1 clic)</a>"
        )

    error_html = f"<div class='error'>{escape(error)}</div>" if error else ""

    return f"""
<!doctype html>
<html lang='fr'>
  <head>
    <meta charset='UTF-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1.0' />
    <title>Ewigo - Lumicadre automatique</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f4f7fb; color: #1f2937; }}
      .container {{ max-width: 980px; margin: 1.5rem auto; background: #fff; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,.08); padding: 1.2rem; }}
      .steps {{ background: #eef5ff; border: 1px solid #c9ddff; border-radius: 8px; padding: .8rem; margin-bottom: 1rem; }}
      .url-form {{ display: grid; grid-template-columns: 1fr auto; gap: .6rem; margin-bottom: 1rem; }}
      input, button {{ padding: .75rem; border-radius: 8px; border: 1px solid #c9d2de; font-size: 14px; }}
      button {{ background: #0f62fe; color: white; border: none; cursor: pointer; }}
      .download {{ display: inline-block; margin-bottom: 1rem; background: #0a7d35; color: #fff; text-decoration: none; padding: .75rem 1rem; border-radius: 8px; font-weight: 700; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: .7rem; }}
      .field {{ display: flex; flex-direction: column; }}
      label {{ font-weight: 600; margin-bottom: .35rem; }}
      .error {{ background: #fee2e2; color: #991b1b; padding: .75rem; border-radius: 8px; margin-bottom: 1rem; }}
      .photos {{ display: grid; grid-template-columns: repeat(5, 1fr); gap: .5rem; margin-top: 1rem; }}
      .photos img {{ width: 100%; height: 95px; object-fit: cover; border-radius: 8px; border: 1px solid #d1d5db; }}
      .options {{ margin-top: 1rem; }}
      @media (max-width: 800px) {{ .url-form, .grid {{ grid-template-columns: 1fr; }} .photos {{ grid-template-columns: repeat(2,1fr); }} }}
    </style>
  </head>
  <body>
    <main class='container'>
      <h1>Ewigo Saumur – Lumicadre Le Bon Coin (A4)</h1>
      <div class='steps'>
        <strong>Utilisation (débutant) :</strong>
        <ol>
          <li>Collez l'URL de l'annonce Le Bon Coin.</li>
          <li>Cliquez sur <em>Extraire les données</em>.</li>
          <li>Cliquez sur <em>Télécharger le Lumicadre A4</em> (fichier PDF prêt à imprimer).</li>
        </ol>
      </div>
      {error_html}
      <form class='url-form' method='post' action='/extract'>
        <input type='url' name='url' placeholder='https://www.leboncoin.fr/...' required value='{escape(str(values.get("source_url", "")))}' />
        <button type='submit'>Extraire les données</button>
      </form>
      {download_button}
      <section class='grid'>{rows}</section>
      <section class='options'>
        <h2>Options détectées</h2>
        <ul>{options_html or '<li>Aucune option détectée automatiquement.</li>'}</ul>
      </section>
      <section>
        <h2>5 premières photos</h2>
        <div class='photos'>{photos_html}</div>
      </section>
    </main>
  </body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_html(self, html: str, status: int = 200) -> None:
        encoded = html.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_pdf(self, pdf_bytes: bytes, filename: str = "lumicadre_a4.pdf") -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(pdf_bytes)))
        self.end_headers()
        self.wfile.write(pdf_bytes)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html(render_page(VehicleData()))
            return

        if parsed.path == "/download-pdf":
            params = parse_qs(parsed.query)
            url = (params.get("url", [""])[0] or "").strip()
            if not url:
                self._send_html(render_page(VehicleData(), "URL manquante pour générer le PDF."), status=400)
                return

            try:
                data = extract_vehicle_data(url)
                from lumicadre_pdf import build_lumicadre_pdf

                pdf_bytes = build_lumicadre_pdf(data)
                self._send_pdf(pdf_bytes)
            except Exception as exc:  # noqa: BLE001
                self._send_html(
                    render_page(
                        VehicleData(source_url=url),
                        f"Impossible de générer le PDF : {exc}",
                    ),
                    status=500,
                )
            return

        self._send_html("<h1>404</h1>", status=404)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/extract":
            self._send_html("<h1>404</h1>", status=404)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length).decode("utf-8", errors="ignore")
        payload = parse_qs(body)
        url = (payload.get("url", [""])[0] or "").strip()

        if not url:
            self._send_html(render_page(VehicleData(source_url=url), "Veuillez saisir une URL valide."))
            return

        try:
            data = extract_vehicle_data(url)
            self._send_html(render_page(data))
        except Exception as exc:  # noqa: BLE001
            self._send_html(
                render_page(
                    VehicleData(source_url=url),
                    f"Impossible d'extraire les données : {exc}",
                )
            )


def run_server() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 5000), Handler)
    print("Server running on http://localhost:5000")
    server.serve_forever()


if __name__ == "__main__":
    run_server()
