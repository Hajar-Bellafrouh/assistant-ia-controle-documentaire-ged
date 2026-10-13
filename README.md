# GDS GED Services -- Assistant Documentaire & Contrôle Documentaire

Système intelligent en deux modules développé dans le cadre d'un stage de fin d'année :
- **Module 1** : Assistant documentaire basé sur une architecture RAG (Retrieval-Augmented Generation), exécuté 100% en local.
- **Module 2** : Module de contrôle documentaire, détectant automatiquement les incohérences entre les pages d'un dossier scanné via OCR.

> ⚠️ **[À adapter]** Ce README suppose une organisation du projet en deux dossiers `module1/` et `module2/`, chacun avec son propre point d'entrée. Ajustez les chemins ci-dessous à l'arborescence réelle du projet avant de le pousser sur GitHub.

---

## Sommaire

- [Prérequis](#prérequis)
- [Installation](#installation)
- [Module 1 -- Assistant documentaire](#module-1----assistant-documentaire)
- [Module 2 -- Contrôle documentaire](#module-2----contrôle-documentaire)
- [Structure du projet](#structure-du-projet)
- [Problèmes fréquents](#problèmes-fréquents)

---

## Prérequis

Avant de commencer, installez sur votre machine :

| Outil | Version recommandée | Lien |
|---|---|---|
| Python | 3.10 ou supérieur | https://www.python.org/downloads/ |
| Ollama | Dernière version | https://ollama.com/download |
| Git | Dernière version | https://git-scm.com/downloads |

Vérifiez les installations :

```bash
python --version
git --version
ollama --version
```

---

## Installation

### 1. Cloner le dépôt

```bash
git clone <URL_DU_DEPOT>
cd <NOM_DU_DEPOT>
```

### 2. Créer un environnement virtuel Python

```bash
python -m venv venv

# Activer l'environnement :
# Sous Windows :
venv\Scripts\activate
# Sous macOS / Linux :
source venv/bin/activate
```

### 3. Installer les dépendances

> ⚠️ **[À adapter]** Si vous avez un seul `requirements.txt` à la racine :
```bash
pip install -r requirements.txt
```
> Si chaque module a son propre fichier de dépendances :
```bash
pip install -r module1/requirements.txt
pip install -r module2/requirements.txt
```

### 4. Télécharger le modèle de langage (Llama 3.2 via Ollama)

Cette étape nécessite une connexion internet la première fois seulement (le modèle est ensuite mis en cache localement) :

```bash
ollama pull llama3.2
```

Vérifiez que le modèle est bien disponible :

```bash
ollama list
```

### 5. Premier lancement de PaddleOCR (téléchargement des modèles)

Les modèles OCR de PaddleOCR se téléchargent automatiquement au premier lancement du Module 2 (connexion internet nécessaire une seule fois). Aucune action manuelle n'est requise, mais prévoyez quelques minutes la première fois.

---

## Module 1 -- Assistant documentaire

### Lancer l'API (backend)

> ⚠️ **[À adapter]** selon le nom réel du fichier principal FastAPI :

```bash
cd module1
uvicorn main:app --reload --port 8000
```

### Lancer l'interface

**Option A -- Interface Streamlit :**
```bash
streamlit run app_streamlit.py
```

**Option B -- Interface web autonome (HTML/CSS/JS) :**
Ouvrez le fichier `index.html` du site vitrine dans un navigateur, ou servez-le via un petit serveur local :
```bash
python -m http.server 5500
```
puis rendez-vous sur `http://localhost:5500`.

### Vérifier que tout fonctionne

Posez une question de test dans l'interface. Si le système répond « je ne trouve pas cette information dans la documentation », c'est normal si la base documentaire n'a pas encore été indexée -- voir l'étape suivante.

### (Ré)indexer la base documentaire

> ⚠️ **[À adapter]** selon le nom réel du script d'indexation :

```bash
python indexer.py --source ./documents
```

Cette étape reconstruit la base vectorielle FAISS à partir des documents placés dans le dossier source. À relancer chaque fois que la documentation interne est mise à jour.

---

## Module 2 -- Contrôle documentaire

### Lancer l'API

> ⚠️ **[À adapter]** :

```bash
cd module2
uvicorn main:app --reload --port 8001
```

### Lancer l'interface web

Ouvrez `index.html` dans un navigateur, ou servez-le comme indiqué pour le Module 1.

### Utilisation

- **Dossier unique** : importez un seul fichier PDF, le système restitue un verdict détaillé page par page.
- **Lot de dossiers** : importez plusieurs fichiers PDF, ils sont traités séquentiellement via la file d'attente interne.

---

## Structure du projet

```
.
├── module1/
│   ├── main.py                # API FastAPI [à adapter]
│   ├── app_streamlit.py       # Interface Streamlit [à adapter]
│   ├── indexer.py             # Script d'indexation [à adapter]
│   ├── faiss_index/           # Index vectoriel généré (non versionné)
│   ├── feedback.db            # Base SQLite du retour utilisateur (non versionnée)
│   ├── notebooks/              # Notebooks de validation
│   ├── .env                   # Configuration locale (non versionnée)
│   ├── requirements.txt
│   └── .gitignore
├── module2/
│   ├── main.py                # API FastAPI [à adapter]
│   ├── ocr_pipeline.py        # Pipeline OCR + comparaison [à adapter]
│   ├── data/
│   │   ├── Dataset_maladie/   # Jeu de test (non versionné, structure conservée via .gitkeep)
│   │   └── Dataset_dentaire/  # Jeu de test (non versionné, structure conservée via .gitkeep)
│   ├── outputs/
│   │   ├── ocr_results/       # Résultats OCR générés (non versionnés)
│   │   └── field_results/     # Résultats de comparaison de champs (non versionnés)
│   ├── requirements.txt
│   └── .gitignore
├── .gitignore                  # Règles communes à la racine
└── README.md
```

> ⚠️ **[À adapter]** Les noms de fichiers `main.py`, `app_streamlit.py`, `indexer.py` et `ocr_pipeline.py` sont des exemples -- remplacez-les par les noms réels de vos fichiers.

### Données de test

Les dossiers `module2/data/Dataset_maladie/` et `module2/data/Dataset_dentaire/` sont vides dans le dépôt Git (seule leur structure est conservée via des fichiers `.gitkeep`). Votre encadrant devra récupérer les jeux de test séparément (clé USB, partage interne) si il souhaite relancer l'évaluation du Module 2 -- ces données ne sont pas transmises via GitHub.

---

## Problèmes fréquents

| Problème | Cause probable | Solution |
|---|---|---|
| `ollama: command not found` | Ollama non installé ou pas dans le PATH | Réinstallez Ollama et redémarrez le terminal |
| Le modèle met du temps à répondre la première fois | Chargement initial du modèle en mémoire | Normal, les réponses suivantes seront plus rapides |
| Erreur de connexion à `localhost:8000` | L'API n'est pas lancée ou tourne sur un autre port | Vérifiez que `uvicorn` tourne bien et que le port correspond à celui utilisé côté interface |
| PaddleOCR échoue au premier lancement | Pas de connexion internet pour télécharger les modèles | Connectez-vous à internet une première fois, les modèles seront ensuite mis en cache |
| Erreur CORS dans la console du navigateur | L'interface et l'API tournent sur des ports différents | Vérifiez que le middleware CORS est bien activé côté API |

---

## Notes de confidentialité

Ce dépôt ne contient **aucune donnée réelle de dossier client**. Les jeux de test (`module2/data/`), les résultats générés (`module2/outputs/`), la base de feedback (`module1/feedback.db`) et les fichiers de configuration (`.env`) sont exclus via les `.gitignore` de chaque module. Seule la structure des dossiers est conservée (fichiers `.gitkeep`) afin que le code s'exécute sans erreur de chemin manquant -- les données elles-mêmes doivent être transmises séparément, en dehors de GitHub.

## 👥 Auteurs

- Hajar Bellafrouh 
- IID2
