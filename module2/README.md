# Module 2 — Contrôle documentaire intelligent

Sous-projet **indépendant** du Module 1 (assistant RAG), dans son **propre
dépôt Git**. Ce module analyse un dossier PDF scanné, extrait les champs
clés de chaque page, compare ces informations entre les pages, et signale
les incohérences (ex : page appartenant par erreur à un autre dossier),
en complément — non en remplacement — du contrôle qualité Kofax Express
déjà en place.

Contexte complet : voir la proposition de sujet de stage GDS GED Services.

## Structure

```
PFA-Module2-ControleDocumentaire/
├── data/
│   ├── Dataset_maladie/       # non versionné (voir .gitignore) — ~1000 dossiers PDF
│   └── Dataset_dentaire/      # non versionné — ~1000 dossiers PDF
├── notebooks/                 # développement progressif, cellules # %%
│   ├── 01_ocr_extraction.py
│   ├── 02_field_extraction.py
│   ├── 03_comparaison_confiance.py
│   └── 04_detection_incoherences.py
├── src/                       # code figé et réutilisable (import futur dans l'API du Module 1)
│   ├── ocr_utils.py
│   ├── field_extraction.py
│   ├── comparison.py
│   └── detection.py
├── outputs/
│   └── ocr_results/           # JSON intermédiaires, non versionnés
├── tests/                     # vérifications objectives par étape
├── requirements.txt
└── .gitignore
```

## Installation (Windows / PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Données

Placer les datasets déjà générés dans :
- `data/Dataset_maladie/` (Dossier_000001.pdf, ..., ground_truth.json)
- `data/Dataset_dentaire/` (même schéma de nommage, contenu différent)

Ces dossiers sont exclus du dépôt Git (`.gitignore`) — seule leur structure
(`.gitkeep`) est versionnée. Ne jamais mélanger les deux datasets dans un
même répertoire (même schéma de nommage interne, données différentes).

## Workflow de développement

1. Développer et valider chaque étape dans `notebooks/`, avec des
   vérifications objectives (pas seulement visuelles) avant de passer à
   la suivante.
2. Une fois une étape stabilisée, figer le code correspondant dans
   `src/` sous forme de fonctions réutilisables.
3. Le module reste générique : pas de logique câblée en dur uniquement
   pour "maladie" — même si la validation initiale se fait sur un seul
   des deux datasets, les fonctions de `src/` doivent fonctionner sur
   les deux (le dataset dentaire n'a par exemple pas de numéro d'adhérent).
4. À terme, `src/` sera importé par l'API FastAPI déjà en place côté
   Module 1, sans dépendre du reste de son code.

## Étapes du pipeline

| Étape | Fichier | Statut |
|---|---|---|
| 1. OCR (PaddleOCR) | `01_ocr_extraction.py` | Implémenté — à valider sur plusieurs dossiers |
| 2. Extraction de champs | `02_field_extraction.py` | Squelette — TODO après inspection des JSON réels |
| 3. Comparaison + score de confiance | `03_comparaison_confiance.py` | Squelette — TODO |
| 4. Détection d'incohérences + évaluation | `04_detection_incoherences.py` | Squelette — TODO |

## Versioning

Ce dossier est un dépôt Git **séparé** de celui du Module 1. Voir la
section "Mise en place Git" ci-dessous pour l'initialisation.
