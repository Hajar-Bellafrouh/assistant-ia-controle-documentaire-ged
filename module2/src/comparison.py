"""
Étape 3 — Comparaison inter-pages avec score de confiance tolérant à l'OCR.

Deux stratégies de comparaison, selon la nature du champ :
- `similarite` (Levenshtein) pour les noms, où une vraie variation
  orthographique/OCR est normale et une similarité floue a du sens ;
- `similarite_identifiant` (comparaison positionnelle tolérante aux
  confusions OCR classiques) pour les dates, CIN, matricules et numéros de
  dossier -- des champs qui doivent être identiques ou différents, sans
  entre-deux, où la distance de Levenshtein brute s'est révélée peu fiable
  (un seul chiffre mal lu suffit à fausser le score dans les deux sens).

NOTE DE CORRECTION (voir docs/JOURNAL_V2.md) : dans une version antérieure
dupliquée entre plusieurs notebooks, `comparer_dossier` ne remplissait plus
`rapport["details"]` (seul `rapport["anomalies"]` était mis à jour), ce qui
rendait le diagnostic des faux négatifs muet même quand une comparaison
avait bien eu lieu. Cette version restaure `details` correctement.
"""

from rapidfuzz.distance import Levenshtein

from .field_extraction import LABELS, extraire_champs_page


def similarite(valeur_a: str, valeur_b: str) -> float:
    """Similarité floue générale (Levenshtein) -- adaptée aux noms."""
    if not valeur_a or not valeur_b:
        return 0.0
    a = valeur_a.strip().upper().replace(" ", "")
    b = valeur_b.strip().upper().replace(" ", "")
    distance = Levenshtein.normalized_distance(a, b)
    return round(1 - distance, 4)


# Caractères que l'OCR confond couramment avec un chiffre. Certains sont
# univoques (o/d/p -> 0), d'autres ambigus selon la police (b/B lu tantôt
# comme 6, tantôt comme 8 ou 3 dans nos données réelles) -- traités comme
# des "jokers" plutôt que mappés à un chiffre précis.
CONFUSION_OCR_CHIFFRES = {
    "o": "0", "O": "0", "d": "0", "D": "0", "p": "0", "P": "0", "q": "0", "Q": "0",
    "i": "1", "I": "1", "l": "1", "L": "1", "|": "1",
    "z": "2", "Z": "2",
    "s": "5", "S": "5",
    "g": "9", "G": "9",
}
CARACTERES_AMBIGUS = set("bB")


def normaliser_chiffres_ocr(valeur: str) -> str:
    return "".join(CONFUSION_OCR_CHIFFRES.get(c, c) for c in valeur)


def similarite_identifiant(valeur_a: str, valeur_b: str) -> float:
    """
    Comparaison pour les champs qui doivent être identiques ou différents
    (dates, numéros, matricules). Compare position par position après
    normalisation des confusions OCR connues ; un caractère ambigu (b/B)
    compte comme correspondant à n'importe quoi plutôt que d'imposer un
    mapping arbitraire probablement faux une fois sur deux.
    """
    if not valeur_a or not valeur_b:
        return 0.0
    a = normaliser_chiffres_ocr(valeur_a.strip().upper().replace(" ", ""))
    b = normaliser_chiffres_ocr(valeur_b.strip().upper().replace(" ", ""))

    if len(a) != len(b):
        distance = Levenshtein.normalized_distance(a, b)
        return round(1 - distance, 4)

    correspondances = sum(
        1 for ca, cb in zip(a, b)
        if ca == cb or ca in CARACTERES_AMBIGUS or cb in CARACTERES_AMBIGUS
    )
    return round(correspondances / len(a), 4)


FONCTION_SIMILARITE = {
    "nom_prenom": similarite,
    "cin": similarite_identifiant,
    "matricule_assure": similarite_identifiant,
    "matricule_beneficiaire": similarite_identifiant,
    "date_naissance": similarite_identifiant,
    "numero_dossier": similarite_identifiant,
}

# Seuils recalibrés sur l'échantillon de 94 dossiers (v2) : la comparaison
# positionnelle tolère déjà le bruit OCR connu, donc un seuil plus strict
# qu'à l'origine ne pénalise plus les cas propres.
SEUILS_CHAMPS = {
    "nom_prenom": 0.70,
    "cin": 0.90,
    "matricule_assure": 0.90,
    "matricule_beneficiaire": 0.90,
    "date_naissance": 0.90,
    "numero_dossier": 0.90,
}


def comparer_dossier(pages_ocr: list) -> dict:
    """
    Compare chaque champ entre les pages où il apparaît. Pour chaque champ
    avec 2+ occurrences, la première page où il apparaît sert de référence.

    Retourne un rapport avec :
    - "anomalies" : liste des comparaisons sous le seuil ;
    - "details" : TOUTES les comparaisons faites (y compris cohérentes),
      indispensable pour diagnostiquer un faux négatif (voir le score exact
      calculé même quand il ne déclenche pas d'anomalie) ;
    - "coherent" : verdict global pour ce mécanisme (hors détection de doublons).
    """
    champs_par_page = [{"page": p["page"], "champs": extraire_champs_page(p)} for p in pages_ocr]
    rapport = {"anomalies": [], "details": {}}

    for nom_champ in LABELS.keys():
        occurrences = [
            (p["page"], p["champs"][nom_champ]["valeur"], p["champs"][nom_champ]["confiance"])
            for p in champs_par_page
            if p["champs"][nom_champ]["valeur"]
        ]
        if len(occurrences) < 2:
            continue  # rien à comparer si le champ n'apparaît qu'une fois (ou jamais)

        page_ref, valeur_ref, _ = occurrences[0]
        seuil = SEUILS_CHAMPS.get(nom_champ, 0.80)
        fonction_score = FONCTION_SIMILARITE.get(nom_champ, similarite)

        comparaisons = []
        for page_num, valeur, confiance in occurrences[1:]:
            score = fonction_score(valeur_ref, valeur)
            coherent = score >= seuil
            comparaisons.append({
                "page": page_num, "valeur": valeur, "score_similarite": score, "coherent": coherent,
            })
            if not coherent:
                rapport["anomalies"].append({
                    "champ": nom_champ,
                    "page_reference": page_ref,
                    "valeur_reference": valeur_ref,
                    "page_suspecte": page_num,
                    "valeur_suspecte": valeur,
                    "score_similarite": score,
                })

        rapport["details"][nom_champ] = {
            "page_reference": page_ref,
            "valeur_reference": valeur_ref,
            "comparaisons": comparaisons,
        }

    rapport["coherent"] = len(rapport["anomalies"]) == 0
    return rapport
