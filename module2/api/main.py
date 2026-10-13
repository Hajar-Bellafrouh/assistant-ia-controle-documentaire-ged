"""
API REST du Module 2 — Contrôle documentaire intelligent.

Expose le pipeline complet (OCR -> extraction -> comparaison -> détection)
derrière des endpoints REST : on envoie un ou plusieurs PDF, on reçoit un
verdict de cohérence en JSON.

Lancement (depuis la racine du projet, venv activé) :
    uvicorn api.main:app --reload --port 8001

Documentation interactive une fois lancée : http://127.0.0.1:8001/docs

Point d'attention : le chargement du modèle PaddleOCR se fait une seule
fois au démarrage du serveur (pas à chaque requête), mais l'OCR d'un
dossier reste lent sur CPU (1 à 4 minutes pour un dossier de 4 pages,
voir docs/JOURNAL_V1.md et suivants) -- cette API convient à un usage
ponctuel (un contrôleur qualité qui vérifie un dossier douteux), pas à un
traitement en masse en l'état.

Architecture (v5) : toutes les analyses, qu'elles viennent de l'endpoint
fichier unique ou du traitement par lot, passent par UNE SEULE file
d'attente consommée par UN SEUL worker en tâche de fond. Le moteur
PaddleOCR n'est chargé qu'en une seule instance : deux analyses ne
doivent jamais tourner en parallèle dessus.
"""

import asyncio
import sys
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.detection import generer_verdict_dossier
from src.ocr_utils import creer_moteur_ocr, ocr_dossier

# ---------------------------------------------------------------------------
# État global : moteur OCR (chargé une seule fois), jobs individuels, lots.
# ---------------------------------------------------------------------------
_etat = {"moteur_ocr": None, "jobs": {}, "lots": {}}
_file_dattente: asyncio.Queue = asyncio.Queue()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[API] Chargement du moteur PaddleOCR...")
    _etat["moteur_ocr"] = creer_moteur_ocr()
    print("[API] Moteur OCR prêt.")
    tache_worker = asyncio.create_task(_travailleur_file_dattente())
    yield
    tache_worker.cancel()
    _etat["moteur_ocr"] = None


app = FastAPI(
    title="Module 2 — Contrôle documentaire intelligent",
    description=(
        "Analyse un ou plusieurs dossiers PDF scannés (feuille de soins, "
        "ordonnance, facture...) et signale les incohérences entre leurs "
        "pages : nom, CIN, matricules, date de naissance, numéro de "
        "dossier, pages dupliquées. Complémentaire au contrôle qualité "
        "existant (Kofax Express), pas un remplacement."
    ),
    version="0.4.0",
    lifespan=lifespan,
)

# CORS : l'interface web est servie sur une origine différente de l'API
# (ex. Live Server sur 127.0.0.1:5500, API sur 127.0.0.1:8001). Sans ce
# middleware, le navigateur bloque les appels fetch() avant même qu'ils
# ne partent ("Failed to fetch"), même si l'API répond correctement par
# ailleurs.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # en développement ; à restreindre en production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Worker unique : dépile et traite les analyses une par une, jamais deux en
# même temps (un seul moteur OCR chargé en mémoire).
# ---------------------------------------------------------------------------
async def _travailleur_file_dattente():
    while True:
        job_id, chemin_temp, nom_fichier = await _file_dattente.get()
        await _executer_analyse(job_id, chemin_temp, nom_fichier)
        _file_dattente.task_done()


async def _executer_analyse(job_id: str, chemin_temp: Path, nom_fichier: str):
    job = _etat["jobs"][job_id]
    job["statut"] = "en_cours"
    job["debut"] = time.time()

    def progression(page_actuelle, total_pages):
        job["page_actuelle"] = page_actuelle
        job["total_pages"] = total_pages

    try:
        resultat_ocr = await asyncio.to_thread(
            ocr_dossier, chemin_temp, _etat["moteur_ocr"], 250, progression
        )
        verdict = generer_verdict_dossier(resultat_ocr["pages"])
        job["resultat"] = {
            "fichier": nom_fichier,
            "nb_pages": resultat_ocr["nb_pages"],
            "duree_ocr_secondes": resultat_ocr["duree_secondes"],
            **verdict,
        }
        job["coherent"] = verdict.get("coherent")
        job["statut"] = "termine"
    except Exception as e:
        job["erreur"] = f"Erreur pendant l'analyse : {e}"
        job["statut"] = "erreur"
    finally:
        job["termine"] = True
        chemin_temp.unlink(missing_ok=True)


def _creer_job(fichier_nom: str) -> str:
    job_id = str(uuid.uuid4())
    _etat["jobs"][job_id] = {
        "fichier": fichier_nom,
        "statut": "en_attente",
        "page_actuelle": 0,
        "total_pages": None,
        "termine": False,
        "erreur": None,
        "resultat": None,
        "debut": None,
        "coherent": None,
    }
    return job_id


async def _lire_et_mettre_en_attente(fichier: UploadFile) -> str:
    if not fichier.filename or not fichier.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail=f"{fichier.filename} n'est pas un PDF.")

    contenu = await fichier.read()
    if not contenu:
        raise HTTPException(status_code=400, detail=f"{fichier.filename} est vide.")

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(contenu)
        chemin_temp = Path(tmp.name)

    job_id = _creer_job(fichier.filename)
    await _file_dattente.put((job_id, chemin_temp, fichier.filename))
    return job_id


# ---------------------------------------------------------------------------
# Endpoints généraux
# ---------------------------------------------------------------------------
@app.get("/")
def racine():
    return {
        "message": "API de contrôle documentaire — Module 2.",
        "documentation": "/docs",
        "endpoints": [
            "POST /controle-dossier (historique, synchrone)",
            "POST /controle-dossier/demarrer",
            "GET /controle-dossier/statut/{job_id}",
            "GET /controle-dossier/resultat/{job_id}",
            "POST /controle-dossier/lot/demarrer",
            "GET /controle-dossier/lot/statut/{lot_id}",
        ],
    }


@app.get("/sante")
def verifier_sante():
    """Vérifie que le serveur tourne et que le modèle OCR est bien chargé."""
    return {
        "statut": "ok",
        "modele_ocr_charge": _etat["moteur_ocr"] is not None,
    }


# ---------------------------------------------------------------------------
# Ancien endpoint (v3) : conservé tel quel, synchrone, pour rétrocompatibilité
# avec la documentation Swagger déjà validée en v3.
# ---------------------------------------------------------------------------
@app.post("/controle-dossier")
async def controler_dossier(fichier: UploadFile = File(...)):
    """
    Analyse un dossier PDF et retourne un verdict de cohérence (appel
    synchrone et bloquant — préférer /controle-dossier/demarrer côté
    interface web pour bénéficier de la progression par page).
    """
    if _etat["moteur_ocr"] is None:
        raise HTTPException(status_code=503, detail="Moteur OCR non chargé — réessayer dans quelques instants.")

    if not fichier.filename or not fichier.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés.")

    chemin_temp = None
    try:
        contenu = await fichier.read()
        if not contenu:
            raise HTTPException(status_code=400, detail="Fichier vide.")

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(contenu)
            chemin_temp = Path(tmp.name)

        resultat_ocr = ocr_dossier(chemin_temp, _etat["moteur_ocr"])
        verdict = generer_verdict_dossier(resultat_ocr["pages"])

        return {
            "fichier": fichier.filename,
            "nb_pages": resultat_ocr["nb_pages"],
            "duree_ocr_secondes": resultat_ocr["duree_secondes"],
            **verdict,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur pendant l'analyse : {e}")
    finally:
        if chemin_temp is not None:
            chemin_temp.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Nouveaux endpoints (v4/v5) : analyse asynchrone avec progression, seule ou
# en lot, toutes deux traitées par la même file d'attente séquentielle.
# ---------------------------------------------------------------------------
@app.post("/controle-dossier/demarrer")
async def demarrer_analyse(fichier: UploadFile = File(...)):
    if _etat["moteur_ocr"] is None:
        raise HTTPException(status_code=503, detail="Moteur OCR non chargé — réessayer dans quelques instants.")
    job_id = await _lire_et_mettre_en_attente(fichier)
    return {"job_id": job_id}


@app.post("/controle-dossier/lot/demarrer")
async def demarrer_lot(fichiers: list[UploadFile] = File(...)):
    if _etat["moteur_ocr"] is None:
        raise HTTPException(status_code=503, detail="Moteur OCR non chargé — réessayer dans quelques instants.")
    if not fichiers:
        raise HTTPException(status_code=400, detail="Aucun fichier reçu.")

    job_ids = [await _lire_et_mettre_en_attente(f) for f in fichiers]
    lot_id = str(uuid.uuid4())
    _etat["lots"][lot_id] = job_ids
    return {"lot_id": lot_id, "jobs": job_ids}


@app.get("/controle-dossier/lot/statut/{lot_id}")
def statut_lot(lot_id: str):
    job_ids = _etat["lots"].get(lot_id)
    if job_ids is None:
        raise HTTPException(status_code=404, detail="Lot introuvable.")

    dossiers = []
    for job_id in job_ids:
        job = _etat["jobs"].get(job_id)
        if job is None:
            continue
        temps_ecoule = None
        if job["debut"] is not None:
            temps_ecoule = round(time.time() - job["debut"], 1)
        duree_finale = None
        if job["resultat"] is not None:
            duree_finale = job["resultat"].get("duree_ocr_secondes")
        dossiers.append({
            "job_id": job_id,
            "fichier": job["fichier"],
            "statut": job["statut"],
            "page_actuelle": job["page_actuelle"],
            "total_pages": job["total_pages"],
            "temps_ecoule_secondes": temps_ecoule,
            "duree_finale_secondes": duree_finale,
            "coherent": job["coherent"],
        })
    return {"dossiers": dossiers}


@app.get("/controle-dossier/statut/{job_id}")
def statut_analyse(job_id: str):
    job = _etat["jobs"].get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tâche introuvable.")
    temps_ecoule = None
    if job["debut"] is not None:
        temps_ecoule = round(time.time() - job["debut"], 1)
    return {
        "termine": job["termine"],
        "page_actuelle": job["page_actuelle"],
        "total_pages": job["total_pages"],
        "erreur": job["erreur"],
        "temps_ecoule_secondes": temps_ecoule,
    }


@app.get("/controle-dossier/resultat/{job_id}")
def resultat_analyse(job_id: str):
    job = _etat["jobs"].get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Tâche introuvable.")
    if not job["termine"]:
        raise HTTPException(status_code=409, detail="Analyse encore en cours.")
    if job["erreur"]:
        raise HTTPException(status_code=500, detail=job["erreur"])
    return job["resultat"]
