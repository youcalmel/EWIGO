#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

PYTHON_BIN=""
if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python n'est pas installé. Installe Python 3 puis relancez ce script."
  exit 1
fi

echo "Installation des dépendances (premier lancement uniquement)..."
"$PYTHON_BIN" -m pip install -r requirements.txt

echo "Démarrage de l'application Ewigo Lumicadre..."
echo "URL: http://localhost:5000"
echo "Arrêt: Ctrl + C"

sleep 1
open "http://localhost:5000" || true
exec "$PYTHON_BIN" app.py
