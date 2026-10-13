"""
Étape 1 — OCR : rasterisation des PDF et extraction du texte brut avec
PaddleOCR. Fonctions reprises et validées depuis notebooks/01_ocr_extraction.ipynb.

Constantes techniques importantes (voir le notebook 01 pour le détail) :
- enable_mkldnn=False : contourne un bug connu de PaddlePaddle 3.3.0 sur CPU
  (NotImplementedError: ConvertPirAttribute2RuntimeAttribute...).
- Modèles "mobile" (PP-OCRv5) plutôt que le défaut "PP-OCRv6_medium" : bien
  plus rapides sur CPU, seule option viable sans GPU.
"""

import os
import time
from pathlib import Path

import numpy as np
import cv2
import pymupdf as fitz
from paddleocr import PaddleOCR


def creer_moteur_ocr(lang: str = "fr") -> PaddleOCR:
    """Initialise le moteur PaddleOCR avec la configuration validée pour ce projet."""
    return PaddleOCR(
        lang=lang,
        use_textline_orientation=True,
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        enable_mkldnn=False,
        text_detection_model_name="PP-OCRv5_mobile_det",
        text_recognition_model_name="PP-OCRv5_mobile_rec",
        cpu_threads=os.cpu_count(),
    )


def pdf_vers_images(pdf_path, dpi: int = 250) -> list:
    """Rasterise chaque page d'un PDF en image numpy (BGR, pour OpenCV/PaddleOCR)."""
    doc = fitz.open(pdf_path)
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)
    images = []
    for page in doc:
        pix = page.get_pixmap(matrix=mat)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img = cv2.cvtColor(img, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        images.append(img)
    doc.close()
    return images


def _resultat_dict(res):
    """
    Normalise l'accès au résultat PaddleOCR 3.x, qui se comporte comme un
    dict mais expose parfois ses champs sous une clé 'res' selon la version.
    """
    if isinstance(res, dict) and "rec_texts" not in res and "res" in res:
        return res["res"]
    return res


def ocr_page(image: np.ndarray, ocr_engine: PaddleOCR) -> dict:
    """Retourne le texte et les scores de confiance d'une page (API PaddleOCR 3.x)."""
    resultats = ocr_engine.predict(image)
    res = _resultat_dict(resultats[0]) if resultats else {}

    textes = res.get("rec_texts", [])
    scores = res.get("rec_scores", [])
    polys = res.get("rec_polys", res.get("dt_polys", [None] * len(textes)))

    lignes = []
    for texte, score, poly in zip(textes, scores, polys):
        bbox = poly.tolist() if hasattr(poly, "tolist") else poly
        lignes.append({
            "texte": texte,
            "confiance": round(float(score), 4),
            "bbox": bbox,
        })

    confiances = [l["confiance"] for l in lignes]
    return {
        "lignes": lignes,
        "nb_lignes": len(lignes),
        "confiance_moyenne": round(float(np.mean(confiances)), 4) if confiances else 0.0,
        "confiance_min": round(float(np.min(confiances)), 4) if confiances else 0.0,
    }


def ocr_dossier(pdf_path, ocr_engine: PaddleOCR, dpi: int = 250, on_progression=None) -> dict:
    """
    Orchestration complète : PDF -> résultat OCR structuré pour tout le dossier.

    `on_progression`, si fourni, est appelé après chaque page avec
    (page_actuelle, total_pages) — utilisé par l'API pour exposer une
    progression en temps réel sans bloquer sur le résultat final.
    """
    t0 = time.time()
    images = pdf_vers_images(pdf_path, dpi=dpi)
    total_pages = len(images)

    resultat = {"dossier": Path(pdf_path).name, "nb_pages": total_pages, "pages": []}
    for i, img in enumerate(images):
        page = ocr_page(img, ocr_engine)
        page["page"] = i + 1
        resultat["pages"].append(page)
        if on_progression is not None:
            on_progression(i + 1, total_pages)

    resultat["duree_secondes"] = round(time.time() - t0, 2)
    return resultat
