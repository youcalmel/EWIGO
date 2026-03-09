# Ewigo Lumicadre Helper

Application web légère pour pré-remplir une fiche vitrine (lumicadre) à partir de l'URL d'une annonce véhicule.

## Fonctionnalités

- Saisie d'une URL d'annonce.
- Récupération automatique des informations détectables sur la page :
  - titre,
  - marque/modèle,
  - prix,
  - kilométrage,
  - année,
  - carburant,
  - boîte,
  - puissance,
  - image principale.
- Formulaire modifiable avant validation/impression.

> ⚠️ Le scraping dépend de la structure du site ciblé. Sur certains sites, certains champs peuvent rester vides.

## Lancer le projet

```bash
python app.py
```

Puis ouvrir `http://localhost:5000`.

## Architecture

- `app.py` : serveur HTTP et interface web.
- `scraper.py` : logique d'extraction des données à partir d'une page HTML.
- `requirements.txt` : note de dépendances (MVP sans packages externes).
