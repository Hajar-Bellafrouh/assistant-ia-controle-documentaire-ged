"""
Étape 4 — Détection d'incohérences et verdict final.

Combine deux mécanismes complémentaires :
1. Comparaison de champs (comparison.comparer_dossier) : détecte
   nom/CIN/date/numéro incompatibles entre les pages.
2. Détection de doublons (ce module) : compare le TEXTE BRUT complet de
   chaque paire de pages -- indispensable car deux pages dupliquées ont,
   par définition, des champs identiques et sont donc invisibles au
   mécanisme de comparaison de champs seul.
"""

import difflib

from .comparison import comparer_dossier


def texte_complet_page(page_ocr: dict) -> str:
    """Concatène toutes les lignes OCR d'une page en une seule chaîne normalisée."""
    lignes = [l["texte"].strip().upper() for l in page_ocr["lignes"] if l["texte"].strip()]
    return " ".join(lignes)


def detecter_doublons(pages_ocr: list, seuil_similarite_texte: float = 0.85) -> list:
    """
    Compare chaque paire de pages du dossier par similarité de texte brut.
    Retourne la liste des paires dont le texte se ressemble au point d'être
    probablement la même page scannée deux fois.
    """
    textes = {p["page"]: texte_complet_page(p) for p in pages_ocr}
    doublons = []

    numeros_pages = list(textes.keys())
    for i in range(len(numeros_pages)):
        for j in range(i + 1, len(numeros_pages)):
            page_a, page_b = numeros_pages[i], numeros_pages[j]
            texte_a, texte_b = textes[page_a], textes[page_b]
            if not texte_a or not texte_b:
                continue
            ratio = difflib.SequenceMatcher(None, texte_a, texte_b).ratio()
            if ratio >= seuil_similarite_texte:
                doublons.append({"page_a": page_a, "page_b": page_b, "similarite_texte": round(ratio, 4)})

    return doublons


def generer_verdict_dossier(pages_ocr: list) -> dict:
    """
    Point d'entrée principal du pipeline de contrôle documentaire : combine
    comparaison de champs et détection de doublons en un verdict unique.

    C'est la fonction que l'API/interface web (v3) appellera avec le
    résultat de l'étape 1 (OCR) pour obtenir directement un verdict.
    """
    rapport_champs = comparer_dossier(pages_ocr)
    doublons = detecter_doublons(pages_ocr)

    return {
        "coherent": rapport_champs["coherent"] and len(doublons) == 0,
        "anomalies_champs": rapport_champs["anomalies"],
        "pages_dupliquees": doublons,
        "details_champs": rapport_champs["details"],
    }
