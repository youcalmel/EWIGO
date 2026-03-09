from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from scraper import VehicleData, extract_vehicle_data


FORM_FIELDS = [
    ("title", "Titre"),
    ("make", "Marque"),
    ("model", "Modèle"),
    ("version", "Version"),
    ("price", "Prix"),
    ("year", "Année"),
    ("mileage", "Kilométrage"),
    ("fuel", "Carburant"),
    ("gearbox", "Boîte"),
    ("power", "Puissance"),
]


def render_page(data: VehicleData, error: str = "") -> str:
    values = data.to_dict()
    rows = "".join(
        f"""
        <div class='field'>
          <label for='{name}'>{label}</label>
          <input id='{name}' type='text' value='{escape(values.get(name, ""))}' />
        </div>
        """
        for name, label in FORM_FIELDS
    )

    image_html = ""
    if values.get("image_url"):
        image_html = (
            "<section class='preview'><h2>Image détectée</h2>"
            f"<img src='{escape(values['image_url'])}' alt='Image véhicule' /></section>"
        )

    error_html = f"<div class='error'>{escape(error)}</div>" if error else ""

    return f"""
<!doctype html>
<html lang='fr'>
  <head>
    <meta charset='UTF-8' />
    <meta name='viewport' content='width=device-width, initial-scale=1.0' />
    <title>Ewigo - Pré-remplissage Lumicadre</title>
    <style>
      body {{ font-family: Arial, sans-serif; margin: 0; padding: 0; background: #f4f7fb; color: #1f2937; }}
      .container {{ max-width: 960px; margin: 2rem auto; background: #fff; border-radius: 12px; box-shadow: 0 10px 25px rgba(0,0,0,.08); padding: 1.5rem; }}
      .url-form {{ display: grid; grid-template-columns: 1fr auto; gap: .75rem; margin-bottom: 1rem; }}
      input, button {{ padding: .8rem; border-radius: 8px; border: 1px solid #c9d2de; }}
      button {{ background: #0f62fe; color: white; border: none; cursor: pointer; }}
      .grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: .75rem; }}
      .field {{ display: flex; flex-direction: column; }}
      label {{ font-weight: 600; margin-bottom: .35rem; }}
      .error {{ background: #fee2e2; color: #991b1b; padding: .75rem; border-radius: 8px; margin-bottom: 1rem; }}
      .preview {{ margin-top: 1rem; text-align: center; }}
      .preview img {{ max-width: 100%; max-height: 280px; border-radius: 10px; border: 1px solid #d1d5db; }}
      @media (max-width: 720px) {{ .url-form, .grid {{ grid-template-columns: 1fr; }} }}
    </style>
  </head>
  <body>
    <main class='container'>
      <h1>Ewigo Saumur – Générateur fiche Lumicadre</h1>
      <p>Collez l'URL de l'annonce pour pré-remplir automatiquement les informations du véhicule.</p>
      {error_html}
      <form class='url-form' method='post' action='/extract'>
        <input type='url' name='url' placeholder='https://...' required value='{escape(values.get("source_url", ""))}' />
        <button type='submit'>Extraire les données</button>
      </form>
      <section class='grid'>{rows}</section>
      {image_html}
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

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/":
            self._send_html("<h1>404</h1>", status=404)
            return
        self._send_html(render_page(VehicleData()))

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
