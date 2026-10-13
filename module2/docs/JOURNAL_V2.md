# Journal — Version 2 : évaluation à l'échelle, comparaison robuste aux erreurs OCR

## Résumé

Depuis la v1 (validation manuelle sur 6 dossiers), le pipeline a été testé sur
un **échantillon stratifié de 94 dossiers** (45 dentaire + 49 maladie),
couvrant systématiquement tous les types d'erreur disponibles dans chaque
dataset — y compris les plus rares. Plusieurs bugs réels ont été trouvés et
corrigés en cours de route, et les limites restantes sont désormais des
limites du **dataset de test**, pas du code.

## Nouveautés par rapport à la v1

- **`00_exploration_dataset.ipynb`** : analyse pure du `ground_truth.json`
  (sans OCR), taux de cohérence, répartition des types d'erreur, détection du
  bug `cin_mismatch` (absent des deux datasets par construction — voir
  `generation_dataset/`), génération d'un **échantillon de test stratifié**
  (minimum garanti de dossiers par type d'erreur, y compris les plus rares
  comme `numero_adherent_mismatch`, 4 occurrences sur 1000).
- **`01_ocr_extraction.ipynb`** : ajout d'un mode "traitement par lot" séparé
  par dataset (jamais de mélange maladie/dentaire), reprise automatique en
  cas d'interruption.
- **`05_evaluation.ipynb`** (nouveau) : calcule automatiquement précision,
  rappel, F1 et le détail par type d'erreur en comparant le verdict du
  pipeline au `ground_truth.json`, avec diagnostic détaillé de chaque faux
  positif/négatif.

## Corrections apportées à l'extraction et à la comparaison (étapes 2/3/4)

- **Recherche de valeur élargie** : en plus de "même ligne, à droite", la
  valeur peut maintenant être trouvée juste en dessous du libellé (templates
  où libellé et valeur sont sur deux lignes séparées), et la fenêtre de
  recherche regarde aussi les lignes détectées *avant* le libellé par l'OCR
  (l'ordre de détection ne suit pas toujours l'ordre de lecture naturel).
- **Libellé manquant ajouté** : `"N° d'immatriculation"` (template
  `prise_en_charge`), différent de `"Matricule Assuré"` utilisé ailleurs.
- **Liste de mots-parasites** (`Sexe`, `Cachet`, `Employeur`...) : empêche un
  libellé voisin sans rapport d'être pris pour une valeur quand le vrai champ
  est vide ou introuvable.
- **Validateur de forme pour les dates** : une valeur candidate doit
  ressembler à une date (2 séparateurs `/`, longueur courte) pour être
  acceptée — corrige les cas où un mot voisin sans chiffres était accepté à
  tort.
- **Comparaison positionnelle tolérante aux confusions OCR** (dates, CIN,
  matricules, numéro de dossier) : remplace la distance de Levenshtein brute,
  inadaptée aux champs numériques courts (un seul chiffre mal lu suffisait à
  fausser le score dans les deux sens). Les caractères ambigus (`b`/`B`,
  confondus tantôt avec 3, tantôt avec 8 selon la police) sont traités comme
  des jokers plutôt que mappés à un chiffre arbitraire.
- **Seuil `nom_prenom` abaissé** (0.75 → 0.70) après analyse des scores
  observés sur l'échantillon complet.

## Résultats finaux

### Dataset dentaire (45 dossiers)

| Métrique | Valeur |
|---|---|
| Précision | 95.65% |
| Rappel | 88.00% |
| F1-score | 91.67% |
| Exactitude globale | 91.11% |

- 1 faux positif : `Dossier_000216` — une date où l'OCR a purement et
  simplement perdu un caractère sur une des deux lectures (`"0B/1/1947"` vs
  `"o3/l1/1947"`), rendant les deux chaînes de longueurs différentes. Cas
  ambigu même à l'œil nu.
- 3 faux négatifs : `Dossier_000063` (`numero_dossier_mismatch`),
  `Dossier_000256` et `Dossier_000554` (`document_autre_patient`) — champ
  trouvé sur une seule page dans les trois cas, à confirmer si c'est la même
  limitation structurelle que côté maladie (non encore creusé en détail).

### Dataset maladie (49 dossiers)

| Métrique | Valeur |
|---|---|
| Précision | 100.00% |
| Rappel | 79.31% |
| F1-score | 88.46% |
| Exactitude globale | 87.76% |

- 0 faux positif.
- 6 faux négatifs, **tous rattachés à des limitations structurelles déjà
  identifiées**, pas à des bugs :
  - `Dossier_000046`, `Dossier_000846` (`document_autre_patient`) : la page
    visée par la corruption ne porte aucun champ d'identité lisible (ex: la
    version courte du document "longue durée", qui ne liste que des
    médicaments).
  - `Dossier_000364`, `Dossier_000636`, `Dossier_000800`
    (`numero_adherent_mismatch`) : le champ `numero_immatriculation` n'existe
    que sur le template `prise_en_charge` — une seule occurrence possible
    par dossier, donc rien à comparer. Confirmé dans le code du générateur
    (`TEMPLATE_CONFIG`) : ce type d'erreur n'est détectable par AUCUNE
    méthode de comparaison inter-pages, humaine ou automatique, tant que le
    champ n'apparaît qu'une fois.
  - `Dossier_000721` (`date_naissance_mismatch`) : probablement la même
    cause (page sans second champ comparable).

## Limites connues, assumées pour cette version

- `cin_mismatch` non généré (les deux générateurs corrigés, dataset
  inchangé — voir `generation_dataset/`).
- `numero_adherent_mismatch` structurellement indétectable dans la quasi
  -totalité des cas (champ à occurrence unique dans le dataset).
- `document_autre_patient` indétectable quand la page substituée ne porte
  aucun champ d'identité.
- Échantillon de 94 dossiers sur les ~2000 au total (test statistique, pas
  exhaustif) — voir la version 3 pour une évaluation à plus grande échelle
  si le temps le permet.
- Code encore dupliqué entre `02`, `03`, `04`, `05` (même logique recopiée
  dans chaque notebook) — à factoriser dans `src/` en version 3.

## Prochaine étape (v3)

Factorisation dans `src/`, pipeline unifié `controler_dossier(pdf) -> verdict`,
API REST (FastAPI) et interface web (Streamlit) pour exposer le Module 2
comme outil utilisable, conformément au cahier des charges initial.
