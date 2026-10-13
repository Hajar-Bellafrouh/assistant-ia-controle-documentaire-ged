# Journal — Version 3 : factorisation dans `src/` + première API

## 1. Factorisation

Le code des étapes 1 à 4, jusqu'ici dupliqué dans les notebooks `02`, `03`,
`04`, `05`, est maintenant centralisé dans `src/` :

| Fichier | Contenu |
|---|---|
| `src/ocr_utils.py` | OCR (PaddleOCR), rasterisation PDF |
| `src/field_extraction.py` | `LABELS`, extraction de champs par position/motif |
| `src/comparison.py` | Similarité (Levenshtein / positionnelle), `comparer_dossier` |
| `src/detection.py` | Doublons, `generer_verdict_dossier` (point d'entrée du pipeline) |

Chaque notebook importe désormais ces fonctions (`from src.detection import
generer_verdict_dossier`, etc.) au lieu de les recopier.

**Validation** : les deux évaluations (`05_evaluation.ipynb`, dentaire et
maladie) ont été relancées après factorisation et donnent des métriques
**identiques au chiffre près** à celles de la v2 (dentaire : 95.65%
précision / 88% rappel ; maladie : 100% / 79.31%) — confirmation que le
déplacement de code n'a introduit aucune régression.

**Bug corrigé au passage** : `comparer_dossier` avait perdu le remplissage
de `rapport["details"]` dans une version antérieure dupliquée, rendant
muette la cellule de diagnostic des faux négatifs. Restauré dans
`src/comparison.py`.

## 2. Première API REST (`api/main.py`)

Un unique endpoint `POST /controle-dossier` : envoie un PDF, reçoit un
verdict JSON (cohérent/incohérent, anomalies de champs, pages dupliquées).
Le modèle PaddleOCR est chargé une seule fois au démarrage du serveur, pas
à chaque requête. Voir `api/README.md` pour le détail (installation,
lancement, exemple d'appel).

**Ce qui a été vérifié** : la logique interne (appel du pipeline `src/`,
construction de la réponse JSON) a été testée avec des données simulées et
fonctionne correctement.

**Test réel effectué côté utilisateur** : l'API a été lancée (`uvicorn
api.main:app --reload`) et testée via l'interface Swagger (`/docs`) avec
un vrai PDF (`Dossier_000001.pdf`). Réponse HTTP 200, verdict `coherent:
true`, avec le même détail (`numero_dossier`, `nom_prenom`, scores de
similarité) que celui obtenu en passant ce même dossier par les notebooks
`01` + `04` — **confirmation que l'API produit exactement le même
résultat que le pipeline manuel**. L'API est donc validée en conditions
réelles, pas seulement sur des données simulées.

## 3. Limite assumée pour cette version

L'API reste synchrone et lente (1 à 4 minutes par dossier sur CPU) —
adaptée à une vérification ponctuelle, pas à un traitement en masse. Une
version future pourrait passer à un traitement asynchrone (file d'attente)
si un usage à plus grand volume est nécessaire.

## Prochaine étape (v4)

- Interface web consommant cette API (Streamlit, HTML/CSS/JS, ou script
  Python en ligne de commande selon le choix retenu).
- Évaluation à plus grande échelle si le temps le permet.
