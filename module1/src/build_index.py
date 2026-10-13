"""
Étape 2 — Construction de l'index vectoriel FAISS.

Rôle :
- Récupérer les chunks générés par ingest.py
- Calculer leurs embeddings avec un modèle Sentence Transformers multilingue
  (important : ta documentation est en français)
- Construire un index FAISS et le sauvegarder sur disque

À relancer à chaque fois que tu ajoutes/modifies des documents dans data/docs/.
"""

from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from ingest import load_and_split

INDEX_DIR = Path(__file__).resolve().parent.parent / "faiss_index"

# Modèle multilingue (français inclus), léger et rapide sur CPU.
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def get_embeddings() -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)


def build_index() -> None:
    print("[build_index] Chargement et découpage des documents...")
    chunks = load_and_split()

    if not chunks:
        print("[build_index] Aucun chunk à indexer. Ajoute des documents dans data/docs/.")
        return

    print(f"[build_index] {len(chunks)} chunks à indexer.")
    print(f"[build_index] Chargement du modèle d'embeddings : {EMBEDDING_MODEL_NAME}")
    embeddings = get_embeddings()

    print("[build_index] Calcul des embeddings et construction de l'index FAISS...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(INDEX_DIR))
    print(f"[build_index] Index sauvegardé dans : {INDEX_DIR}")


if __name__ == "__main__":
    build_index()
