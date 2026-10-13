# API du Module 2 — Contrôle documentaire intelligent

API REST minimale exposant le pipeline complet (OCR → extraction →
comparaison → détection) : on envoie un PDF, on reçoit un verdict de
cohérence en JSON.

## Installation

Les dépendances de l'API (`fastapi`, `uvicorn`, `python-multipart`) sont
déjà dans `requirements.txt` à la racine du projet :

```powershell
pip install -r requirements.txt
```

## Lancer le serveur

Depuis la racine du projet (pas depuis `api/`), venv activé :

```powershell
uvicorn api.main:app --reload
```

Le chargement du modèle PaddleOCR se fait une seule fois au démarrage
(quelques secondes) — les logs affichent `[API] Moteur OCR prêt.` une fois
que le serveur est prêt à recevoir des requêtes.

## Documentation interactive

Une fois lancé : http://127.0.0.1:8000/docs (interface Swagger générée
automatiquement par FastAPI — permet de tester l'endpoint directement
depuis le navigateur, sans écrire de code).

## Endpoints

| Méthode | Route | Description |
|---|---|---|
| GET | `/` | Message d'accueil |
| GET | `/sante` | Vérifie que le serveur et le modèle OCR sont prêts |
| POST | `/controle-dossier` | Analyse un PDF, retourne le verdict |

## Exemple d'appel

```powershell
curl -X POST "http://127.0.0.1:8000/controle-dossier" -F "fichier=@Dossier_000001.pdf"
```

Réponse attendue (exemple sur un dossier cohérent) :

```json
{
  "fichier": "Dossier_000001.pdf",
  "nb_pages": 4,
  "duree_ocr_secondes": 187.3,
  "coherent": true,
  "anomalies_champs": [],
  "pages_dupliquees": [],
  "details_champs": { "...": "..." }
}
```

## Limite connue

L'OCR sur CPU prend 1 à 4 minutes par dossier (voir `docs/JOURNAL_V1.md`
et `V2.md`) — cette API convient à un usage ponctuel (vérifier un dossier
douteux à la demande), pas à un traitement en masse en l'état. Pour un
usage en production à plus grand volume, il faudrait soit du GPU, soit un
traitement asynchrone en file d'attente plutôt qu'une réponse synchrone.

## Non testé en conditions réelles

Ce code n'a pas pu être exécuté avec un vrai serveur FastAPI dans
l'environnement de développement utilisé pour l'écrire (pas d'accès
réseau pour installer les dépendances). La logique interne (appel au
pipeline `src/`, construction de la réponse JSON) a été testée séparément
et fonctionne correctement — mais le comportement de FastAPI lui-même
(gestion des routes, de l'upload de fichier, des codes d'erreur HTTP)
doit être vérifié à la première exécution réelle. Si une erreur apparaît
au lancement, envoie le message complet pour un diagnostic rapide.
