"""
Étape 2 — Extraction des champs clés (nom/prénom, CIN, matricules, date de
naissance, numéro de dossier) depuis le texte OCR brut d'une page.

Historique des corrections importantes (voir docs/JOURNAL_V2.md) :
- extraction basée sur la position (bbox), pas seulement le texte, car
  libellé et valeur sont parfois détectés comme deux boîtes séparées ;
- recherche élargie à "en dessous" du libellé et "avant" lui dans l'ordre
  de détection OCR (l'OCR ne suit pas toujours l'ordre de lecture naturel) ;
- liste de mots-parasites et validateur de forme pour éviter qu'un libellé
  voisin sans rapport (ex: "Sexe:", "Cachet") soit pris pour une valeur.
"""

import re

# ---------------------------------------------------------------------------
# Libellés connus par champ (regex tolérantes aux variantes de mise en page
# et aux erreurs OCR fréquentes observées sur les templates CMIM réels)
# ---------------------------------------------------------------------------
LABELS = {
    "numero_dossier": [
        r"\bDOS\d{6,}\b",  # motif de la valeur elle-même (pas le libellé "Référence dossier")
    ],
    "nom_prenom": [
        r"nam?\s+et\s+pr.nom\s*[:\-]?",          # feuille principale (typo "Nam" du template)
        r"nom\s*&\s*pr.nom\s*[:\-]?",             # ordonnance (variante maladie)
        r"^nom\s*[:\-]",                           # ordonnance (variante dentaire)
        r"nom\s+du\s+client\s*[:\-]?",             # facture (variante dentaire)
        r"[fp]acturer\s+[àa]\s*",                  # facture (variante maladie, OCR confond F/P)
        r"nom\s+et\s+pr.nom\s+complets\s*[:\-]?",  # scanner dentaire
    ],
    "cin": [
        r"n[°o]?\s*cin\s*[:\-]?",
    ],
    "matricule_assure": [
        r"matricule\s+assur[ée]\s*[:\-]?",       # = "numéro d'adhérent" du cahier des charges
        r"n[°o]?\s*d.\s*immatriculation",        # libellé réel du template "prise_en_charge"
    ],
    "matricule_beneficiaire": [
        r"matricule\s+b.n.ficiaire\s*[:\-]?",
    ],
    "date_naissance": [
        r"date\s+de\s+naissance\s*[:\-]?",
    ],
}

STRATEGIE_CHAMPS = {
    "numero_dossier": "direct",
    "nom_prenom": "proximite",
    "cin": "proximite",
    "matricule_assure": "proximite",
    "matricule_beneficiaire": "proximite",
    "date_naissance": "proximite",
}


# ---------------------------------------------------------------------------
# Validateurs de forme : une valeur candidate doit ressembler à ce que le
# champ est censé contenir, indépendamment des libellés connus.
# ---------------------------------------------------------------------------
def _ressemble_a_une_date(texte: str) -> bool:
    """
    Une vraie date a 2 séparateurs '/' et reste courte -- filtre les libellés
    voisins (ex: 'Sexe:') sans jamais exiger de vrais chiffres au sens strict :
    une date très bruitée par l'OCR (ex: "26/D9/2OO3") doit rester acceptée,
    seule sa FORME compte ici.
    """
    texte = texte.strip()
    return texte.count("/") >= 2 and len(texte) <= 15


VALIDATEURS_CHAMPS = {
    "date_naissance": _ressemble_a_une_date,
}

# Mots du formulaire qui ne sont jamais une vraie valeur de champ, découverts
# au fil des faux positifs rencontrés (liste pragmatique, à enrichir si
# d'autres cas apparaissent).
MOTS_PARASITES_CONNUS = {"sexe", "cachet", "employeur", "montant", "nombre", "renseignements"}


def _est_mot_parasite(texte: str) -> bool:
    t = texte.strip().lower().rstrip(":")
    return t in MOTS_PARASITES_CONNUS or any(t.startswith(m) for m in MOTS_PARASITES_CONNUS)


def _est_label_connu(texte: str) -> bool:
    """Vrai si ce texte correspond à un des libellés connus (donc ce n'est
    pas une valeur, même s'il se trouve juste à côté d'un autre label)."""
    for patterns in LABELS.values():
        for pattern in patterns:
            if re.search(pattern, texte, flags=re.IGNORECASE):
                return True
    return False


# ---------------------------------------------------------------------------
# Géométrie des bounding boxes
# ---------------------------------------------------------------------------
def _centre_y(bbox) -> float:
    return sum(pt[1] for pt in bbox) / len(bbox)


def _y_top(bbox) -> float:
    return min(pt[1] for pt in bbox)


def _y_bottom(bbox) -> float:
    return max(pt[1] for pt in bbox)


def _x_min(bbox) -> float:
    return min(pt[0] for pt in bbox)


def _x_max(bbox) -> float:
    return max(pt[0] for pt in bbox)


def nettoyer_valeur(texte: str) -> str:
    """Retire la ponctuation de séparation en début de valeur (:, ., _, |, espaces)."""
    return re.sub(r"^[\s:.\-_|]+", "", texte).strip()


# ---------------------------------------------------------------------------
# Recherche de la valeur associée à un libellé
# ---------------------------------------------------------------------------
def trouver_valeur_a_droite(lignes, index_label, tolerance_y=20, max_ecart_x=180,
                             max_ecart_dessous=70, valider=None):
    """
    Cherche la valeur associée à un libellé, dans une fenêtre de quelques
    lignes AVANT et APRÈS lui dans l'ordre de détection OCR (l'OCR ne
    détecte pas toujours dans l'ordre de lecture naturel).

    Deux positions sont acceptées :
    - même ligne visuelle, à droite du libellé (cas le plus courant) ;
    - juste EN DESSOUS du libellé (ex: templates "analyses" où "DATE DE
      NAISSANCE" et sa valeur sont sur deux lignes séparées).
    """
    label = lignes[index_label]
    y_label = _centre_y(label["bbox"])
    y_label_bas = _y_bottom(label["bbox"])
    x_label_debut = _x_min(label["bbox"])
    x_label_fin = _x_max(label["bbox"])

    fenetre = lignes[max(0, index_label - 3): index_label] + lignes[index_label + 1: index_label + 8]

    candidats = []
    for ligne in fenetre:
        if _est_label_connu(ligne["texte"]):
            continue
        if len(ligne["texte"].strip()) > 40:
            continue
        if _est_mot_parasite(ligne["texte"]):
            continue
        if valider and not valider(ligne["texte"]):
            continue

        y_ligne = _centre_y(ligne["bbox"])
        y_ligne_haut = _y_top(ligne["bbox"])
        x_ligne_debut = _x_min(ligne["bbox"])

        meme_ligne = (
            abs(y_ligne - y_label) <= tolerance_y
            and -50 <= (x_ligne_debut - x_label_fin) <= max_ecart_x
        )
        en_dessous = (
            0 <= (y_ligne_haut - y_label_bas) <= max_ecart_dessous
            and abs(x_ligne_debut - x_label_debut) <= 250
        )

        if meme_ligne or en_dessous:
            candidats.append((ligne, meme_ligne))

    if not candidats:
        return None
    # Priorité à "même ligne", sinon la ligne la plus proche verticalement
    candidats.sort(key=lambda c: (not c[1], abs(_centre_y(c[0]["bbox"]) - y_label)))
    return candidats[0][0]


def extraire_par_proximite(lignes, patterns, nom_champ=None):
    """
    Priorité à la valeur déjà collée au libellé -- on ne cherche un voisin
    (à droite ou en dessous) que si rien d'exploitable n'est collé. Un
    validateur optionnel (VALIDATEURS_CHAMPS) vérifie que la valeur trouvée
    a bien la forme attendue pour ce champ.
    """
    LONGUEUR_MIN_VALEUR = 3
    valider = VALIDATEURS_CHAMPS.get(nom_champ)
    for i, ligne in enumerate(lignes):
        for pattern in patterns:
            m = re.search(pattern, ligne["texte"], flags=re.IGNORECASE)
            if not m:
                continue
            reste = nettoyer_valeur(ligne["texte"][m.end():])
            if reste and len(reste) >= LONGUEUR_MIN_VALEUR and (valider is None or valider(reste)):
                return {"valeur": reste, "confiance": ligne["confiance"]}
            voisin = trouver_valeur_a_droite(lignes, i, valider=valider)
            if voisin:
                return {"valeur": voisin["texte"].strip(), "confiance": voisin["confiance"]}
            return {"valeur": None, "confiance": ligne["confiance"]}
    return {"valeur": None, "confiance": None}


def extraire_par_motif_direct(lignes, patterns):
    """
    Champ dont la valeur est reconnaissable par un motif indépendant du
    libellé (ex: DOS\\d+), utile quand libellé et valeur sont trop éloignés
    dans la mise en page (ex: séparés par un code-barres non-OCR).
    """
    for ligne in lignes:
        for pattern in patterns:
            m = re.search(pattern, ligne["texte"], flags=re.IGNORECASE)
            if m:
                return {"valeur": m.group(0), "confiance": ligne["confiance"]}
    return {"valeur": None, "confiance": None}


def extraire_champs_page(page_ocr: dict) -> dict:
    """Point d'entrée principal de l'étape 2 : extrait tous les champs suivis pour une page."""
    lignes = page_ocr["lignes"]
    champs = {}
    for nom_champ, patterns in LABELS.items():
        strategie = STRATEGIE_CHAMPS.get(nom_champ, "proximite")
        if strategie == "direct":
            champs[nom_champ] = extraire_par_motif_direct(lignes, patterns)
        else:
            champs[nom_champ] = extraire_par_proximite(lignes, patterns, nom_champ)
    return champs
