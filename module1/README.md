# Assistant documentaire intelligent — GDS GED Services (Module 1)

Assistant RAG (Retrieval-Augmented Generation) permettant aux opérateurs GED de poser
des questions en langage naturel sur les procédures internes (Kofax Express, ReadSoft
Forms, ateliers Préparation / Numérisation / Contrôle qualité, etc.) et d'obtenir une
réponse générée à partir de la documentation interne.

## 1. Architecture du projet

```
rag-assistant-ged/
├── data/
│   └── docs/                 <- Dépose ici tes documents (.txt, .md, .pdf)
├── faiss_index/               <- Index vectoriel généré automatiquement (ne pas éditer)
├── src/
│   ├── ingest.py              <- Étape 1 : chargement + découpage des documents
│   ├── build_index.py         <- Étape 2 : embeddings + construction de l'index FAISS
│   ├── rag_chain.py           <- Étape 3 : chaîne RAG (retriever + LLM Ollama/Llama 3)
│   └── api.py                 <- Étape 4 : API FastAPI (/ask)
├── app_streamlit.py            <- Étape 5 : interface Streamlit (interroge l'API)
├── requirements.txt
└── README.md
```

Ce découpage correspond exactement à ton pipeline RAG classique :
`chunking → embeddings → indexation FAISS → recherche sémantique → génération LLM`.

## 2. Installation de l'environnement dédié (venv + Jupyter)

### Sous Windows (PowerShell)

Un script automatise toute la création de l'environnement virtuel, l'installation
des dépendances et l'enregistrement du kernel Jupyter :

```powershell
cd rag-assistant-ged
.\setup_env.ps1
```

Si PowerShell refuse d'exécuter le script (erreur liée à la politique d'exécution),
lance une seule fois cette commande, puis réessaie :
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Pour réactiver l'environnement plus tard (nouveau terminal) :
```powershell
.\venv-ged-rag\Scripts\Activate.ps1
```

### Sous macOS / Linux (bash)

```bash
cd rag-assistant-ged
chmod +x setup_env.sh
./setup_env.sh
```

Pour réactiver l'environnement plus tard :
```bash
source venv-ged-rag/bin/activate
```

### Dans les deux cas

Cela crée un dossier `venv-ged-rag/` (environnement isolé, propre à ce projet) et
enregistre un kernel Jupyter nommé **"Python (RAG GED)"**.

Pour lancer Jupyter Lab et travailler avec les notebooks :
```bash
jupyter lab
```
Puis, dans chaque notebook, sélectionne bien le kernel **"Python (RAG GED)"**
(menu Kernel → Change Kernel).

### 2.1 Installation manuelle (alternative)

**Windows (PowerShell) :**
```powershell
cd rag-assistant-ged
python -m venv venv-ged-rag
.\venv-ged-rag\Scripts\Activate.ps1
pip install -r requirements.txt
python -m ipykernel install --user --name=rag-ged --display-name "Python (RAG GED)"
```

**macOS / Linux :**
```bash
cd rag-assistant-ged
python3 -m venv venv-ged-rag
source venv-ged-rag/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name=rag-ged --display-name "Python (RAG GED)"
```

### 2.2 Ollama + Llama 3 (LLM local, gratuit, tourne sur ton PC)

1. Télécharge et installe Ollama : https://ollama.com/download
2. Récupère le modèle Llama 3 :
   ```bash
   ollama pull llama3
   ```
3. Vérifie qu'Ollama tourne (il se lance normalement automatiquement) :
   ```bash
   ollama list
   ```

Si ton PC de stage est peu puissant (pas de GPU), utilise plutôt `llama3.2:3b` ou
`llama3.2:1b` (beaucoup plus légers, moins précis mais suffisants pour une démo/PFA) :
```bash
ollama pull llama3.2:3b
```
Et remplace `"llama3"` par `"llama3.2:3b"` dans `src/rag_chain.py`.

## 2.2 Organisation des notebooks

Le dossier `notebooks/` contient un notebook par étape du pipeline RAG, pour explorer
et valider chaque résultat intermédiaire avant de figer le code dans `src/` :

```
notebooks/
├── 01_ingestion.ipynb          <- Étape 1 : chargement + chunking
├── 02_embeddings_index.ipynb   <- Étape 2 : embeddings + index FAISS (à venir)
├── 03_rag_chain.ipynb          <- Étape 3 : retriever + LLM (à venir)
```

Chaque notebook importe directement les fonctions de `src/` (`ingest.py`,
`build_index.py`, `rag_chain.py`) : le code "officiel" reste dans `src/`, les
notebooks servent à l'expérimentation et à la vérification visuelle.

## 3. Ajouter des documents de test

Un premier document d'exemple est déjà fourni dans `data/docs/` (basé sur ton propre
rapport d'observation) pour que tu puisses tester le pipeline immédiatement, avant de
brancher tes vraies procédures.

Tu peux ajouter :
- des `.txt` ou `.md` (le plus simple à commencer)
- des `.pdf` (documentation publique Kofax Express / ReadSoft Forms, procédures internes
  non confidentielles)

## 4. Construire l'index (à refaire à chaque ajout/modif de documents)

```bash
python src/build_index.py
```

Tu dois voir un message confirmant le nombre de chunks indexés et la sauvegarde dans
`faiss_index/`.

## 5. Tester la chaîne RAG en ligne de commande (sans API, pour debug rapide)

```bash
python src/rag_chain.py
```

Ça lance une petite boucle question/réponse dans le terminal.

## 6. Lancer l'API FastAPI

```bash
uvicorn src.api:app --reload --port 8000
```

Documentation interactive automatique : http://localhost:8000/docs

## 7. Lancer l'interface Streamlit

Dans un **autre terminal** (l'API doit tourner en parallèle) :

```bash
streamlit run app_streamlit.py
```

## 8. Prochaines étapes suggérées

1. Tester avec le document d'exemple → vérifier que les réponses sont cohérentes.
2. Ajouter progressivement tes vrais documents (rapport d'observation, doc Kofax/ReadSoft).
3. Améliorer le prompt (`src/rag_chain.py`) selon les erreurs observées.
4. Ajouter l'affichage des sources dans Streamlit (déjà prévu dans le code).
5. Une fois Module 1 stable → attaquer Module 2 (OCR + PaddleOCR + score de confiance).
