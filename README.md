# Ewigo Lumicadre Helper (Le Bon Coin)

Outil simple pour **débutant** : collez une URL Le Bon Coin, récupérez automatiquement les infos, puis téléchargez un **PDF A4 prêt à imprimer** (Lumicadre).

## Ce que le logiciel extrait

- Prix
- 5 premières photos
- Année
- Kilométrage
- Énergie
- Boîte de vitesse
- Puissance (CH)
- Quelques options trouvées dans la description

## Démarrage sur Mac (très simple)

1. Téléchargez le dossier du projet.
2. Double-cliquez sur `start_mac.command`.
3. Une fenêtre Terminal s'ouvre et lance automatiquement le site sur `http://localhost:5000`.
4. Collez l'URL Le Bon Coin, puis cliquez sur **Télécharger le Lumicadre A4 (1 clic)**.

> Si macOS bloque au 1er lancement : clic droit sur `start_mac.command` → **Ouvrir**.

## Démarrage manuel (si besoin)

```bash
python3 -m pip install -r requirements.txt
python3 app.py
```

Puis ouvrir `http://localhost:5000`.

## Fichiers

- `app.py` : interface web + bouton de téléchargement PDF en 1 clic.
- `scraper.py` : extraction des données depuis les annonces (priorité Le Bon Coin).
- `lumicadre_pdf.py` : génération du fichier PDF A4 prêt à imprimer.
- `start_mac.command` : lanceur Mac en double-clic.
