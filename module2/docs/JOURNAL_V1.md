# Journal — Version 1 : pipeline validé sur cas unitaires

Date : voir l'historique Git pour la date exacte du commit associé à ce tag.

## Résumé

Les 4 étapes du pipeline de contrôle documentaire (OCR → extraction de
champs → comparaison inter-pages → détection + verdict) sont écrites et
validées **individuellement, sur 6 dossiers choisis à la main** — un par
type d'incohérence disponible dans le dataset dentaire, plus un dossier
cohérent du dataset maladie.

## Ce qui fonctionne

| Étape | Notebook | Rôle |
|---|---|---|
| 1 | `01_ocr_extraction.ipynb` | OCR (PaddleOCR, modèles mobile CPU) sur un dossier PDF, sauvegarde JSON par dossier |
| 2 | `02_field_extraction.ipynb` | Extraction de nom/prénom, CIN, matricules, date de naissance, n° dossier — par position (bbox) et par motif direct |
| 3 | `03_comparaison_confiance.ipynb` | Comparaison inter-pages avec score de similarité tolérant à l'OCR (Levenshtein, sans espaces) |
| 4 | `04_detection_incoherences.ipynb` | Combine la comparaison de champs + une détection de doublons (similarité de texte brut par paire de pages) en un verdict final |

## Résultats sur les 6 dossiers de test

| Dossier | Dataset | Erreur attendue (ground truth) | Verdict obtenu |
|---|---|---|---|
| Dossier_000001 | maladie | cohérent | ✅ `Cohérent : True` |
| Dossier_000005 | dentaire | nom/prénom incompatible | ✅ anomalie `nom_prenom`, score 0.24 |
| Dossier_000022 | dentaire | document d'un autre patient | ✅ anomalie `nom_prenom`, score 0.18 |
| Dossier_000032 | dentaire | date de naissance incompatible | ✅ anomalie `date_naissance`, score 0.40 |
| Dossier_000034 | dentaire | numéro de dossier incompatible | ✅ anomalie `numero_dossier`, score 0.67 |
| Dossier_000009 | dentaire | document dupliqué | ✅ pages 4↔5, similarité texte 1.00 |

**6/6 verdicts corrects**, sur les deux datasets (généricité confirmée
entre maladie et dentaire), sans fausse alerte sur les champs réellement
cohérents des dossiers incohérents.

## Choix techniques validés en cours de route

- **OCR** : PaddleOCR 3.x, modèles `PP-OCRv5_mobile_det` / `PP-OCRv5_mobile_rec`
  (les modèles par défaut, plus lourds, étaient trop lents sur CPU),
  `enable_mkldnn=False` (contourne un bug connu de PaddlePaddle 3.3.0 sur
  CPU), rasterisation via PyMuPDF à 250 DPI.
- **Extraction de champs** : deux stratégies selon le champ — "direct"
  (motif autonome, ex. `DOS\d+`) quand libellé et valeur sont trop
  éloignés dans la mise en page (code-barres entre les deux), et
  "proximité" (position bbox) pour les champs où libellé et valeur sont
  sur la même ligne visuelle mais parfois détectés comme deux boîtes de
  texte séparées par l'OCR.
- **Comparaison** : distance de Levenshtein normalisée, espaces retirés
  avant comparaison (l'OCR colle parfois deux mots), seuils différents
  par champ (0.75 pour les noms, 0.85-0.90 pour les identifiants stricts).
- **Doublons** : similarité de texte brut complet par paire de pages
  (`difflib.SequenceMatcher`), nécessaire car deux pages dupliquées ont
  des champs identiques et sont donc invisibles à la comparaison de
  champs seule.

## Limites connues, à traiter dans les versions suivantes

- **`cin_mismatch` absent du dataset dentaire** : sur ~1000 dossiers et
  ~209 incohérents, ce type d'erreur n'apparaît jamais dans le
  `ground_truth.json` fourni — probablement un bug du générateur de
  dataset, à vérifier avant de considérer ce type d'erreur comme couvert.
- **Seuil `nom_prenom` (0.75) proche de la marge** : sur `Dossier_000005`,
  deux comparaisons cohérentes obtiennent un score de 0.76, à peine
  au-dessus du seuil — à surveiller sur un échantillon plus large.
- **Validation sur 6 dossiers choisis à la main, pas représentatifs** :
  aucune mesure de précision/rappel à l'échelle du dataset pour l'instant.
  C'est l'objet de la version suivante (lots de 20-50 dossiers par
  dataset, dans `outputs/ocr_results/<dataset>/`, jamais mélangés).
- **Code dupliqué entre les 4 notebooks** (chaque notebook redéfinit les
  fonctions des précédents pour rester autonome pendant la mise au
  point) — à factoriser dans `src/` une fois le taux de détection validé
  à plus grande échelle.
- **`document_duplique` détecté par seuil fixe (0.85)**, non encore
  testé pour les faux positifs (deux pages différentes mais qui se
  ressembleraient beaucoup par coïncidence).
