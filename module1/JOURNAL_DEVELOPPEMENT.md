# Journal de développement — Module 1 : Assistant documentaire intelligent (RAG)

> Document de suivi technique du développement du Module 1 du projet de stage.
> Destiné à servir de base pour la rédaction du **chapitre 4 (Réalisation)** du rapport de PFA.

---

## 1. Objectif du Module 1

Développer un assistant conversationnel permettant aux opérateurs GED de poser des
questions en langage naturel sur les procédures internes (ateliers, logiciels Kofax
Express / ReadSoft Forms, terminologie métier) et d'obtenir une réponse générée
automatiquement à partir de la documentation interne, plutôt que de devoir chercher
manuellement dans des documents dispersés.

Ce module repose sur une architecture **RAG (Retrieval-Augmented Generation)** :
plutôt que de laisser un LLM répondre à partir de ses seules connaissances générales
(avec un risque d'hallucination), le système récupère d'abord les passages pertinents
de la documentation interne, puis demande au LLM de générer sa réponse **uniquement**
à partir de ces passages.

---

## 2. Architecture technique retenue

```
Documents de référence (.md, .pdf)
        │
        ▼
┌─────────────────┐
│  1. Ingestion    │   Chargement des documents + découpage en chunks
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  2. Embeddings   │   Transformation de chaque chunk en vecteur numérique
│     + FAISS      │   Indexation dans une base vectorielle (recherche par similarité)
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  3. Chaîne RAG   │   Retriever (top-k chunks) → Prompt → LLM (Ollama / Llama 3)
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  4. API REST     │   FastAPI, endpoint POST /ask
└─────────────────┘
        │
        ▼
┌─────────────────┐
│  5. Interface    │   Streamlit (chat + affichage des sources)
└─────────────────┘
```

### Stack technique utilisée

| Catégorie | Technologie | Rôle |
|---|---|---|
| Langage | Python 3.14 | Langage principal |
| Chargement de documents | LangChain (`document_loaders`) | Lecture des `.txt`, `.md`, `.pdf` |
| Découpage (chunking) | `langchain-text-splitters` (`RecursiveCharacterTextSplitter`) | Découpage des documents en morceaux de taille contrôlée |
| Embeddings | Sentence Transformers, modèle `paraphrase-multilingual-MiniLM-L12-v2` | Transformation du texte en vecteurs numériques (384 dimensions), modèle **multilingue** car documentation en français |
| Base vectorielle | FAISS (Facebook AI Similarity Search) | Indexation et recherche par similarité des chunks |
| LLM | Ollama + Llama 3.2 (3B) en local | Génération de la réponse en langage naturel |
| Orchestration | LangChain (LCEL — LangChain Expression Language) | Assemblage retriever → prompt → LLM |
| API | FastAPI + Uvicorn | Exposition de l'assistant via une API REST (`/ask`, `/health`) |
| Interface | Streamlit | Interface de chat pour les opérateurs |
| Environnement | venv Python dédié + Jupyter Lab | Isolation des dépendances, développement itératif par notebooks |

---

## 3. Démarche de développement

Le développement a été mené de façon **itérative et progressive**, notebook par
notebook, chaque étape étant validée avant de passer à la suivante — approche
adaptée à un travail en solo sur une durée courte (1,5 à 2 mois).

### 3.1 Mise en place de l'environnement

- Création d'un environnement virtuel Python dédié (`venv-ged-rag`), isolé du reste
  du système, contenant l'ensemble des dépendances du projet.
- Enregistrement d'un kernel Jupyter dédié (`Python (RAG GED)`) pour travailler en
  notebooks.
- Installation d'Ollama (application locale) permettant de faire tourner un LLM
  **en local**, sans dépendre d'une API cloud payante — argument important pour un
  déploiement futur chez GDS GED Services (maîtrise des coûts, confidentialité des
  données traitées, pas de dépendance à un service externe).

### 3.2 Étape 1 — Ingestion des documents (notebook `01_ingestion.ipynb`)

- Chargement des documents (`.md`, `.pdf`) présents dans `data/docs/`.
- Découpage en chunks de **800 caractères** avec un chevauchement de **150
  caractères**, en respectant en priorité les titres et paragraphes du document
  (séparateurs hiérarchiques : titres Markdown, sauts de paragraphe, phrases).
- **Test réalisé** : combinaison d'un document de démonstration et d'un vrai
  document interne (note de synthèse sur l'entreprise et le processus documentaire,
  22 pages) → **63 chunks générés**, longueur moyenne de 635 caractères.
- Validation : aucun chunk ne dépasse la taille cible, découpage cohérent avec la
  structure du document source.

### 3.3 Étape 2 — Embeddings et indexation FAISS (notebook `02_embeddings_index.ipynb`)

- Calcul des embeddings de chaque chunk avec le modèle multilingue.
- Construction d'un index FAISS permettant la recherche par similarité.
- **Test réalisé** : recherche de similarité "à nu" (sans LLM) sur deux questions
  types :
  - *"Comment fonctionne l'atelier Préparation ?"*
  - *"Quelle est la différence entre PEC et RD ?"*
- Validation : dans les deux cas, les chunks les plus proches (score de distance le
  plus bas) contenaient effectivement l'information recherchée, confirmant la
  pertinence du découpage et du modèle d'embeddings choisi.

### 3.4 Étape 3 — Chaîne RAG complète (notebook `03_rag_chain.ipynb`)

- Construction du prompt de génération, avec des consignes explicites :
  - répondre **uniquement** à partir du contexte fourni ;
  - indiquer clairement l'absence d'information plutôt que d'inventer une réponse
    (limitation des hallucinations) ;
  - répondre en français, de façon claire et professionnelle.
- Assemblage de la chaîne complète via LangChain (LCEL) : retriever → mise en forme
  du contexte → prompt → LLM (Ollama, Llama 3.2 3B) → parseur de sortie.
- **Test réalisé** : 3 questions, dont une question **volontairement hors sujet**
  ("Quel est le salaire moyen des opérateurs GED ?").
- Résultat : les réponses aux deux premières questions étaient cohérentes et bien
  reformulées (pas une simple copie du texte source) ; la troisième question a bien
  été traitée par un refus explicite ("je ne trouve pas cette information dans la
  documentation disponible"), validant le comportement anti-hallucination du
  système.

### 3.5 Étape 4 — API REST (`src/api.py`)

- Exposition de l'assistant via une API FastAPI, avec deux endpoints :
  - `GET /health` : vérification que l'assistant est bien chargé.
  - `POST /ask` : reçoit une question, renvoie la réponse générée ainsi que les
    sources documentaires utilisées (nom du fichier + extrait).
- L'assistant (modèle d'embeddings + index FAISS + LLM) est chargé **une seule
  fois** au démarrage du serveur, afin d'éviter un rechargement coûteux à chaque
  requête.
- Documentation interactive générée automatiquement par FastAPI (Swagger UI).

### 3.6 Étape 5 — Interface utilisateur (`app_streamlit.py`)

- Interface de chat simple, développée avec Streamlit.
- Interrogation de l'API REST développée à l'étape précédente.
- Affichage de la réponse générée ainsi que des sources documentaires utilisées
  (extrait + nom du document), pour la traçabilité et la crédibilité des réponses
  auprès des opérateurs.

### 3.7 Test de bout en bout

- Enchaînement complet validé : question posée dans l'interface Streamlit → appel
  à l'API → recherche des chunks pertinents (FAISS) → génération de la réponse
  (Llama 3.2) → affichage de la réponse et des sources dans l'interface.
- Le système répond correctement aux questions couvertes par la documentation
  fournie, et indique honnêtement son incapacité à répondre en dehors de ce
  périmètre.

---

## 4. Difficultés rencontrées et solutions apportées

Cette section peut alimenter une partie "difficultés rencontrées" du chapitre 4,
souvent valorisée dans un rapport de PFA.

| Difficulté rencontrée | Cause | Solution apportée |
|---|---|---|
| Blocage de l'exécution de scripts sous PowerShell (`chmod` inexistant, script `.ps1` non signé) | Différences d'environnement entre Linux/macOS et Windows | Création d'un script d'installation dédié à Windows (`setup_env.ps1`), utilisation de `Set-ExecutionPolicy` / `-ExecutionPolicy Bypass` |
| Échec d'installation de certaines dépendances (versions figées indisponibles pour la version de Python installée) | Contraintes de version trop strictes dans `requirements.txt` | Passage à des contraintes de version plus souples (`>=` au lieu de `==X.Y.*`) |
| Erreur d'import (`RecursiveCharacterTextSplitter` introuvable) | Changement de version majeure de LangChain (1.x) pendant le développement, réorganisation des modules internes | Mise à jour des imports vers les nouveaux emplacements (`langchain_text_splitters`, `langchain_core.documents`) |
| `ModuleNotFoundError` au lancement de l'API (`rag_chain` introuvable) | Le dossier `src/` n'était pas automatiquement ajouté au chemin de recherche Python lors du lancement via `uvicorn src.api:app` | Ajout explicite du dossier `src/` à `sys.path` en tête du fichier `api.py` |
| Erreur affichée à l'arrêt de Streamlit (`Ctrl+C`) | Incompatibilité mineure connue entre la dernière version de Streamlit et Uvicorn, au niveau de la procédure d'arrêt uniquement | Non bloquant : l'application fonctionne normalement, seule la fermeture propre est affectée |

---

## 5. Résultats obtenus à ce stade

- Pipeline RAG fonctionnel de bout en bout, testé avec de la documentation réelle
  (note de synthèse de 22 pages sur l'entreprise et ses processus documentaires).
- Comportement anti-hallucination validé (le système reconnaît explicitement les
  limites de ses connaissances).
- Architecture modulaire (ingestion / indexation / génération / API / interface)
  facilitant la maintenance et les évolutions futures.
- Développement local, sans dépendance à une API LLM payante (Ollama), pertinent
  pour un contexte d'entreprise soucieuse de la confidentialité des données
  traitées (secteur bancaire/assurance).

## 6. Limites actuelles et pistes d'amélioration

- Corpus documentaire encore restreint (documentation de test + un document
  interne) — à enrichir avec davantage de procédures et de documentation
  logicielle (Kofax Express, ReadSoft Forms).
- Absence de mémoire conversationnelle (chaque question est traitée indépendamment
  des précédentes).
- Temps de génération perfectible (piste : réduction du nombre de chunks récupérés,
  limitation de la longueur de génération, affichage en flux/streaming des
  réponses).
- Pas encore d'évaluation quantitative systématique de la qualité des réponses
  (piste : constitution d'un petit jeu de questions/réponses de référence pour
  mesurer objectivement les améliorations futures).

## 7. Prochaines étapes

1. Enrichissement du corpus documentaire (procédures internes, documentation
   Kofax/ReadSoft, glossaire des sigles métier, FAQ des questions fréquentes des
   nouveaux employés).
2. Ajustements de performance (taille des chunks, nombre de chunks récupérés,
   paramètres de génération).
3. Développement du **Module 2** : contrôle documentaire automatique (OCR via
   PaddleOCR, extraction des champs clés, détection d'incohérences entre pages
   d'un même dossier via un score de confiance).
4. Intégration des deux modules dans une interface web unique.
5. Rédaction du chapitre 4 du rapport de stage à partir des éléments consignés
   dans ce document.

---

# Version 2 — Amélioration du ton, de la vitesse et de l'interface

## 8. Contexte de la version 2

Après la validation complète du pipeline RAG (version 1), trois axes d'amélioration
ont été identifiés à l'usage : le ton des réponses restait trop "visiblement
robotique" (mentions explicites du mécanisme RAG), la vitesse perçue pouvait être
meilleure, et l'interface, bien que fonctionnelle, restait très basique visuellement.

## 9. Amélioration du prompt — ton professionnel et mode hybride

Le prompt de génération a été entièrement retravaillé pour obtenir un comportement
plus proche d'un collègue expert répondant naturellement, plutôt que d'un système
révélant son fonctionnement interne.

**Problèmes constatés lors des premiers tests** :
- Le modèle commençait systématiquement ses réponses par des formules
  d'introduction ("Voici la réponse :", "Je suis désolé, mais...").
- Sur une question sans réponse dans la documentation, le modèle révélait
  explicitement le mécanisme RAG ("je n'ai pas trouvé cette information dans les
  extraits fournis"), ce qui n'était pas souhaitable pour un usage professionnel.

**Solution apportée** : le prompt interdit désormais explicitement :
- toute formule d'introduction avant la réponse ;
- toute mention des mots "contexte", "extraits", "documentation fournie", y
  compris dans le cas où l'information n'est pas disponible.

Un **mode hybride en trois niveaux** a également été introduit :
1. Réponse basée sur la documentation interne si l'information y figure.
2. Réponse basée sur les connaissances générales du LLM si la question est
   générale (notions de GED, archivage, numérisation) et absente des documents.
3. Réponse honnête et brève, sans révéler le mécanisme, si la question porte sur
   une donnée strictement interne introuvable (ex. données chiffrées internes).

Ce comportement a été validé sur 4 questions tests couvrant chacun des trois cas,
avec des résultats jugés satisfaisants après un cycle d'ajustement du prompt.

**Compromis assumé** : le mode hybride réintroduit un risque limité
d'approximation sur les questions générales (le modèle peut légèrement extrapoler
ses connaissances générales), en échange d'une meilleure couverture des questions
qui ont une réponse évidente mais absente du corpus documentaire actuel.

## 10. Optimisation de la vitesse de réponse

- Réduction du nombre de chunks récupérés par question (`TOP_K` : 4 → 3),
  diminuant la quantité de texte transmise au LLM à chaque requête.
- Limitation de la longueur maximale générée (`num_predict = 350` tokens), évitant
  les réponses inutilement longues.
- Ajout du **streaming** : la réponse s'affiche désormais mot par mot au fur et à
  mesure de sa génération (nouvel endpoint `/ask/stream`, format NDJSON), plutôt
  que d'attendre le texte complet avant affichage. Le temps de génération total
  n'est pas réduit, mais la latence perçue par l'utilisateur est nettement
  améliorée.

## 11. Refonte de l'interface utilisateur

L'interface Streamlit a été redessinée pour un rendu plus professionnel :

- **Identité visuelle** : palette bleu marine / doré (registre bancaire et
  archivage, cohérent avec l'écosystème du Groupe BANK OF AFRICA), typographies
  Sora (titres) et Inter (texte courant).
- **Bannière d'en-tête** avec un fil visuel représentant le workflow réel des
  ateliers (Réception → Préparation → Numérisation → Contrôle qualité →
  Archivage), ancrant l'outil dans le processus métier observé au chapitre 2.
- **Barre latérale** affichant : le statut de connexion à l'API, le modèle LLM
  utilisé, le nombre d'extraits actuellement indexés, une liste de questions
  rapides pré-remplies, et un bouton de réinitialisation de la conversation.
- **Avatars distincts** pour l'opérateur et l'assistant, et **cartes de sources**
  mises en forme avec une icône selon le type de document (PDF / Markdown).
- Extension de l'endpoint `/health` de l'API pour exposer ces informations
  (modèle utilisé, nombre d'extraits indexés).

## 12. Bilan de la version 2

- Ton des réponses jugé professionnel et naturel, sans exposition du mécanisme
  RAG sous-jacent.
- Couverture élargie aux questions générales sur la GED, en plus des questions
  strictement documentaires.
- Latence perçue réduite grâce au streaming.
- Interface nettement plus soignée, cohérente avec l'identité de l'entreprise.

## 13. Pistes identifiées pour la suite (version 3 et au-delà)

Par ordre de priorité recommandé :
1. **Mémoire conversationnelle** (historique multi-tours) — actuellement chaque
   question est traitée indépendamment des précédentes.
2. **Journalisation des échanges** (logs / SQLite) — traçabilité des questions
   posées, temps de réponse, utile pour un suivi d'usage réel et pour des
   statistiques dans le rapport.
3. **Jeu de questions/réponses de référence** et **mécanisme de retour
   utilisateur (👍/👎)** — pour évaluer objectivement la qualité des réponses au
   fil des évolutions, plutôt que de façon uniquement qualitative.
4. Améliorations d'ingénierie : configuration externalisée (`.env`), tests
   automatisés, gestion d'erreurs renforcée, conteneurisation (Docker) en vue
   d'une intégration future chez GDS GED Services.
5. Démarrage du **Module 2** (contrôle documentaire par OCR), qui reste à
   entreprendre en parallèle ou à la suite de ces améliorations.

---

# Version 3 — Mémoire conversationnelle, enrichissement du corpus et fiabilisation

## 14. Contexte de la version 3

L'objectif principal de cette version était d'ajouter une **mémoire
conversationnelle** à l'assistant : permettre à un opérateur d'enchaîner des
questions de suivi ("Et pour CMIM ?", "Et pour les autres clients ?") sans devoir
reformuler entièrement chaque question. Cette évolution s'est révélée nettement
plus délicate que prévu, car elle a fait apparaître plusieurs classes de problèmes
nouveaux, non présents en mode question-par-question isolée. Le travail correctif
qui en a découlé constitue une part importante et instructive de cette version.

## 15. Implémentation de la mémoire conversationnelle

**Principe retenu** (technique standard en RAG conversationnel) :
1. **Reformulation (condensation)** : avant la recherche documentaire, un appel
   LLM léger transforme une question de suivi ("Et pour CMIM ?") en question
   autonome ("Quel logiciel est utilisé pour CMIM ?"), à partir de l'historique
   récent. Cette question reformulée sert uniquement à la recherche vectorielle.
2. **Génération** : le LLM répond à la question **originale** (non reformulée),
   avec l'historique récent et les extraits documentaires comme contexte, sans
   jamais révéler explicitement qu'il s'appuie sur un "historique de conversation".
3. **Recherche hybride** : la recherche est effectuée à la fois avec la question
   brute et la question reformulée, puis les résultats sont fusionnés — ceci afin
   d'éviter qu'une reformulation imparfaite ne fasse manquer le bon extrait.

L'historique est transmis de bout en bout : Streamlit conserve les échanges dans
`st.session_state`, les envoie à l'API (`POST /ask` et `/ask/stream`, champ
`history`), qui les transmet à `RagAssistant.ask()` / `ask_stream()`.

## 16. Problèmes rencontrés — diagnostic progressif

Trois classes de problèmes distinctes ont été identifiées au fil des tests, par
observation directe des réponses (et non uniquement par des métriques globales) :

| # | Problème observé | Exemple concret |
|---|---|---|
| A | Le modèle inventait de fausses questions/réponses supplémentaires après avoir répondu, poursuivant seul le dialogue | Répond "Kofax Express." puis enchaîne de lui-même sur une question jamais posée |
| B | Recopie de la mise en forme du document source (numéros de section, titres de chapitre) au lieu de reformuler | "2.2.1 CMIM Les opérations de traitement documentaire..." recopié tel quel |
| C | L'historique "contaminait" la réponse : le sujet de l'échange précédent réapparaissait à tort dans une réponse sur un sujet différent | Répondre avec des détails de l'atelier Préparation à une question sur l'atelier Numérisation ou Archivage |

À cela s'est ajouté un problème distinct, découvert plus tard :

| # | Problème observé | Cause identifiée |
|---|---|---|
| D | Deux logiciels différents (Kofax Express, ReadSoft Forms) mélangés dans une même réponse, y compris avec une définition de sigle inventée | Le tableau comparatif du document source (section 2.7.1), une fois son texte extrait du PDF, perd sa mise en page en colonnes : les deux noms de logiciels se retrouvent côte à côte sur une même ligne de texte brut, sans séparation visuelle — le modèle les lit alors comme une liste unique |
| E | Le modèle ne remettait pas en question une réponse précédente contestée par l'opérateur, et justifiait sa première réponse par une explication inventée | Absence de consigne explicite sur la gestion des corrections utilisateur |

## 17. Corrections appliquées (par ordre chronologique)

1. **Séquences d'arrêt** (`stop`) sur le LLM (Ollama) pour empêcher la génération
   de continuer au-delà de la réponse à la question posée → corrige le problème A.
2. **Nettoyage du texte extrait des PDF** à l'ingestion (suppression des en-têtes
   de chapitre répétés sur chaque page) → réduit le problème B.
3. **Renforcement itératif du prompt système**, en plusieurs passes, avec des
   consignes de plus en plus précises et négatives (ce qu'il ne faut **jamais**
   faire), notamment :
   - interdiction de recopier la mise en forme du document (numéros de section à
     un ou plusieurs niveaux, titres de chapitre) ;
   - interdiction de réutiliser des informations d'un sujet différent de celui de
     la question posée, même si ce sujet a été discuté juste avant ;
   - consigne explicite de vérifier que les informations disponibles concernent
     bien le sujet exact de la question avant de répondre, plutôt que d'improviser
     avec un sujet proche ;
   - consigne explicite de ne jamais combiner deux éléments d'information distincts
     (ex: deux logiciels) en une seule réponse fusionnée ;
   - consigne explicite sur la gestion des corrections de l'opérateur : revérifier
     les informations disponibles plutôt que de défendre une réponse précédente par
     une justification inventée → corrige le problème E.
4. **Passage à une recherche MMR** (Maximal Marginal Relevance) avec un pool de
   candidats élargi, pour éviter qu'un contenu volumineux mais générique (ex: une
   présentation PowerPoint aux formulations proches sur de nombreux sujets) ne
   prenne la place d'un extrait plus spécifique mais moins "démonstratif" en
   similarité brute. Le paramètre de diversité (`lambda_mult`) a dû être ajusté
   expérimentalement : une diversité trop marquée (0.5) écartait à tort des
   extraits très pertinents ; une diversité minimale (0.95, quasi pure pertinence)
   s'est révélée nettement plus fiable.
5. **Augmentation progressive de `TOP_K`** (nombre de chunks récupérés), de 3 à 5,
   au fur et à mesure de l'enrichissement du corpus.
6. **Ajout d'un document de clarification** (`clarification_logiciels_par_client.md`)
   résumant sans ambiguïté, en prose, quel logiciel est utilisé pour quel client —
   afin de compenser la perte d'information structurelle du tableau PDF (problème D).
   Cette pratique (note de clarification en complément d'une source dont le format
   d'origine est mal exploité par l'extraction automatique) est une réponse
   pragmatique et courante aux limites de l'extraction de tableaux PDF en RAG.
7. **Outil de diagnostic direct de l'index** (voir section 18) pour distinguer,
   face à une réponse incorrecte, un problème d'indexation, de classement
   (retrieval) ou de génération — plutôt que de procéder par ajustements successifs
   non vérifiés.

## 18. Méthode de diagnostic direct de l'index

Un notebook dédié (`06_diagnostic_index.ipynb`) permet de vérifier, indépendamment
du LLM :
1. si un mot-clé donné (ex: "Kofax") existe littéralement dans un chunk indexé ;
2. à quel rang ce chunk ressort pour une question donnée, par recherche de
   similarité brute.

Cette méthode a permis d'identifier avec certitude la cause du problème D (tableau
PDF mal linéarisé) plutôt que de continuer à ajuster le prompt à l'aveugle.

## 19. Enrichissement du corpus documentaire

- Ajout du support des présentations **PowerPoint (.pptx)** dans le pipeline
  d'ingestion (une diapositive = un document, texte des zones de texte et des
  tableaux extrait via `python-pptx`).
- Ajout de plusieurs présentations réelles fournies par l'encadrant de stage
  (présentation générale de GDS, présentation sur l'optimisation des processus
  documentaires médicaux pour la CMIM).
- Suppression du document de démonstration initial (`exemple_atelier_preparation.md`),
  qui avait servi à valider le pipeline avant l'arrivée des vrais documents, et qui
  contenait une définition de "RD" non vérifiée (à ne pas réutiliser).
- Constat méthodologique : l'ajout de nouveaux documents modifie l'équilibre de la
  recherche vectorielle et peut faire régresser la précision sur des questions qui
  fonctionnaient auparavant — nécessitant un réajustement des paramètres de
  recherche (`TOP_K`, méthode MMR) en conséquence.

## 20. Comparaison de modèles (`llama3.2:3b` vs `llama3`)

Un notebook dédié (`04_comparaison_modeles.ipynb`) a permis de comparer
objectivement les deux modèles Ollama disponibles, sur un jeu de 5 questions
identiques :

| Critère | `llama3.2:3b` | `llama3` (8B) |
|---|---|---|
| Temps de réponse moyen | 34,1 s | 92,2 s (2,7× plus lent) |
| Qualité sur questions isolées | Bonne | Bonne, très similaire |
| Fiabilité en contexte conversationnel | Un défaut observé (redondance) | Un défaut observé (erreur d'attribution factuelle) |

**Décision retenue : conserver `llama3.2:3b`.** Le modèle plus gros n'a pas
démontré d'avantage de fiabilité suffisant pour justifier un temps de réponse
2,7 fois supérieur — il a même produit une erreur factuelle (attribution d'une
étape à un atelier incorrect) que le petit modèle n'a pas commise sur le même test.
Ce résultat, contre-intuitif au premier abord, illustre qu'un modèle plus grand
n'est pas automatiquement plus fiable dans un pipeline RAG : la qualité de la
recherche et du prompt a montré plus d'impact que la taille du modèle sur ce cas
d'usage.

## 21. Fonctionnalité complémentaire : interrupteur de mémoire conversationnelle

Malgré les corrections successives, certains cas résiduels de confusion entre
sujets proches subsistent occasionnellement en mode mémoire activée (limite
reconnue, voir section 22). Plutôt que de poursuivre indéfiniment l'ajustement du
prompt avec des gains marginaux décroissants, un **interrupteur dans l'interface**
a été ajouté, permettant à l'opérateur de choisir :
- **Mémoire activée** : conversation naturelle avec questions de suivi, au prix
  d'un risque résiduel de confusion entre sujets proches ;
- **Mémoire désactivée** : chaque question traitée indépendamment, comportement le
  plus fiable observé sur l'ensemble des tests.

Ce choix reflète une décision d'ingénierie assumée : donner le contrôle à
l'utilisateur plutôt que de masquer un compromis non résolu à 100 %.

## 22. Bilan et limites connues de la version 3

**Fonctionnalités validées** :
- Mémoire conversationnelle avec reformulation de question et recherche hybride.
- Correction fiable des cas testés impliquant CMIM, RMA et l'atelier archivage.
- Ton professionnel sans exposition du mécanisme RAG, y compris lors d'une
  correction de l'opérateur.
- Support de trois formats de documents (`.pdf`, `.md`, `.pptx`).
- Streaming des réponses, interface enrichie (statut, statistiques, questions
  rapides, interrupteur mémoire).

**Limites connues, assumées et documentées** :
- Confusion occasionnelle entre deux sujets proches en mode mémoire activée,
  notamment lorsque le corpus ne contient pas d'extrait traitant précisément et
  explicitement du sujet demandé.
- Tendance ponctuelle à enrichir une énumération peu détaillée du document source
  (ex: types de dossiers PEC/RD, mentionnés sans être définis dans la
  documentation) avec des précisions non vérifiées.
- Ces limites sont cohérentes avec l'usage d'un modèle de langage compact (3
  milliards de paramètres) exécuté localement, choix assumé pour des raisons de
  vitesse et de confidentialité (voir section 20).

## 23. Prochaines étapes

1. Enrichissement continu du corpus (glossaire des sigles métier, FAQ des
   questions fréquentes, documentation Kofax Express / ReadSoft Forms).
2. Journalisation des échanges et mécanisme de retour utilisateur (👍/👎) pour un
   suivi objectif de la qualité dans le temps.
3. Améliorations d'ingénierie (configuration externalisée, tests automatisés,
   conteneurisation).
4. Démarrage du **Module 2** (contrôle documentaire par OCR).
---

# Version 4 — Enrichissement du corpus, feedback utilisateur et flexibilité conversationnelle

## 24. Enrichissement du corpus documentaire

De nouveaux documents ont été ajoutés à `data/docs/` : organigramme de l'entreprise,
ordre de classement des pièces par type de dossier (remboursement, PEC PA, PEC PH),
et documentation technique des logiciels (guide d'installation Kofax Express, manuel
ReadSoft FORMS 5.3 en anglais).

## 25. Leçon méthodologique : format des documents sources

L'ajout de ces nouveaux documents a révélé un principe important pour la qualité du
RAG : **les tableaux et les listes à puces fortement imbriquées se prêtent mal à
l'extraction et à la recherche vectorielle**.

- Un organigramme rédigé en liste à puces indentée (relations parent/enfant
  implicites dans l'indentation) a d'abord donné des réponses incomplètes ou
  hallucinées : l'indentation ne porte quasiment aucune information sémantique pour
  un modèle d'embeddings.
- Un tableau de classement de pièces (3 colonnes, dont une répétée 17 fois) risquait
  d'être coupé au milieu par le découpage en chunks, séparant un numéro d'ordre de
  la pièce qu'il concernait.

**Solution appliquée** : reformulation systématique de ce type de contenu en
**prose explicite** (phrases complètes déclarant chaque relation ou chaque rang) ou
en **listes numérotées simples** plutôt qu'en tableaux à colonnes redondantes. Cette
reformulation a immédiatement corrigé les réponses correspondantes, validées sur des
questions ciblées ("Qui est le PDG ?", "Quels sont les responsables sous le Sénior
Manager ?", "Quel est l'ordre de classement pour un dossier de remboursement ?").

## 26. Ajustements progressifs des paramètres de recherche

Au fur et à mesure de l'enrichissement du corpus, plusieurs paramètres ont dû être
réajustés pour compenser la dilution de la pertinence liée à un corpus plus
volumineux et plus hétérogène (PDF, Markdown, PowerPoint) :

- `CHUNK_SIZE` : 800 → 1000 caractères, pour que les documents de référence courts
  (organigramme, listes) restent en un seul chunk plutôt que d'être coupés.
- `TOP_K` (nombre de chunks récupérés) : augmenté progressivement de 4 à 8, à mesure
  que le corpus grandissait et que du contenu générique (diapositives de
  présentation d'entreprise, répétées sous plusieurs formulations proches)
  monopolisait les premières places au détriment de chunks plus spécifiques.
- Recherche MMR (`lambda_mult`) : ajustée de 0.5 à 0.95, pour privilégier fortement
  la pertinence plutôt que la diversité artificielle, qui écartait à tort des
  chunks très pertinents au profit de chunks simplement "différents".

**Constat méthodologique** : pour des questions très larges ("je veux l'ensemble de
mon organigramme"), un système RAG reste structurellement limité — il optimise la
récupération pour une question donnée, pas la couverture exhaustive d'un document.
Des questions progressives et ciblées donnent de bien meilleurs résultats qu'une
question unique trop large. Ce comportement a été documenté comme limite connue
plutôt que sur-corrigé indéfiniment par des réglages.

## 27. Découverte d'une ambiguïté multilingue

L'ajout du manuel ReadSoft FORMS (en anglais) a révélé un nouveau type de confusion :
le mot anglais "preparation" (utilisé dans ce manuel pour désigner la préparation
d'un formulaire logiciel avant mise en production) est sémantiquement très proche du
mot français "préparation" (désignant l'atelier physique de préparation des
dossiers) pour un modèle d'embeddings multilingue. Une question vague ("quel est
l'ordre dans la préparation ?") pouvait ainsi mélanger des passages des deux sources
sans rapport. Une question plus précise résout le problème sans modification de code
— documenté comme limite connue liée à la coexistence de sources françaises et
anglaises dans un même corpus.

## 28. Système de feedback utilisateur (👍 / 👎)

Un mécanisme de retour a été ajouté pour permettre une évaluation continue et
objective de la qualité perçue des réponses :
- Base SQLite locale (`feedback.db`, `src/database.py`) enregistrant chaque retour
  (question, réponse, valeur, horodatage).
- Endpoints API `POST /feedback` et `GET /feedback/stats`.
- Boutons 👍/👎 sous chaque réponse dans l'interface Streamlit, avec compteur affiché
  dans la barre latérale.

Ce mécanisme permet, à terme, d'identifier objectivement les questions à améliorer
en priorité plutôt que de se fier uniquement à des tests manuels ponctuels.

## 29. Flexibilité conversationnelle (messages non documentaires)

Le prompt a été complété pour gérer nativement les échanges de politesse
(salutations, remerciements) et les questions générales sur la capacité de
l'assistant à aider, qui ne doivent pas déclencher de recherche documentaire ni de
réponse artificielle du type "information non disponible". L'assistant répond
désormais naturellement à "Bonjour", "Merci", ou "Peux-tu m'aider ?", sans afficher
de sources non pertinentes.

## 30. Bilan de la version 4

- Corpus enrichi et diversifié (organigramme, procédures de classement, manuels
  techniques bilingues).
- Robustesse du retrieval améliorée par l'ajustement progressif et documenté des
  paramètres (taille de chunk, nombre de résultats, méthode de recherche).
- Mécanisme d'évaluation continue en place (feedback).
- Interface plus naturelle sur les échanges non documentaires.
- Limites connues et assumées : couverture partielle sur les questions trop larges,
  sensibilité aux formulations vagues en corpus multilingue.

## 31. Prochaines étapes

1. Poursuivre l'enrichissement ciblé du corpus si de nouveaux documents deviennent
   disponibles, en appliquant systématiquement le principe de la section 25 (prose
   plutôt que tableaux/listes imbriquées).
2. Exploiter les données de `feedback.db` pour prioriser les améliorations futures.
3. Démarrer le **Module 2** (contrôle documentaire par OCR).

---

# Version 5 — Interface web en JavaScript

## 32. Contexte et motivation

Si l'interface Streamlit avait été suffisante pour valider le fonctionnement du
Module 1, elle présentait un plafond en matière de personnalisation visuelle :
Streamlit reste un framework pensé pour des applications de données, pas pour la
conception d'une interface sur-mesure. Une interface web autonome, en HTML/CSS/JS,
a donc été développée pour offrir un contrôle total sur le rendu, tout en
réutilisant l'API FastAPI existante sans aucune modification de sa logique
métier.

Ce choix valide a posteriori une décision d'architecture prise dès le départ :
la séparation stricte entre le backend (API FastAPI, indépendante de toute
interface) et le frontend (initialement Streamlit) a permis d'ajouter une
seconde interface entièrement différente sans toucher au code de l'assistant
RAG lui-même — seul un nouveau client HTTP a été écrit. 

## 33. Architecture technique de la nouvelle interface

- **Aucune dépendance, aucun outil de build** : HTML, CSS et JavaScript "vanilla",
  servie localement via un simple serveur HTTP (`python -m http.server`).
- Communication directe avec l'API existante :
  - `GET /health` et `GET /feedback/stats` pour l'état du système et les
    statistiques, affichés dans la barre latérale.
  - `POST /ask/stream` pour les questions, avec lecture du flux de réponse
    (NDJSON) via l'API `ReadableStream` du navigateur — équivalent JavaScript du
    streaming déjà implémenté côté Streamlit.
  - `POST /feedback` pour les retours 👍/👎.
- **CORS** : l'API FastAPI a dû être configurée pour accepter les requêtes
  provenant d'une origine différente (`CORSMiddleware`), puisque cette interface
  tourne sur un port distinct de l'API — point technique absent jusque-là car
  Streamlit interrogeait l'API côté serveur (Python), sans restriction de
  navigateur.
- L'historique de conversation, l'interrupteur de mémoire conversationnelle, les
  questions rapides et l'affichage des sources ont été réimplémentés à
  l'identique de la version Streamlit, garantissant que les deux interfaces
  offrent exactement les mêmes fonctionnalités.

## 34. Choix de conception visuelle

Une identité visuelle spécifique a été construite autour du métier réel de
l'entreprise plutôt qu'un habillage générique :

- **Palette** : bleu marine (`#0F2247`) et or (`#C89B3C`), registre bancaire et
  archivistique cohérent avec l'appartenance de GDS GED Services au groupe BANK
  OF AFRICA ; complétée d'un accent cyan (`#5FE1D6`) évoquant la lumière d'un
  scanner, utilisé avec parcimonie (curseur de streaming, éléments actifs).
- **Typographies** : Space Grotesk (titres), Inter (texte courant), JetBrains
  Mono (identifiants, sources documentaires) — cohérent avec l'univers de la
  traçabilité documentaire (codes-barres, numéros de dossier).
- **Signature visuelle** : le bandeau représentant le workflow physique
  (Réception → Préparation → Numérisation → Contrôle → Archivage) a été prolongé
  d'une sixième étape, "Assistant IA", matérialisant que l'assistant s'intègre
  au pipeline de traitement documentaire plutôt que d'être un outil externe.
- **Animations thématiques** : un faisceau lumineux balaie l'en-tête en continu
  (référence directe au scanner de documents, cœur du métier de l'entreprise),
  une texture inspirée d'un code-barres orne le bandeau, et chaque nouvelle
  réponse apparaît avec un effet de balayage ("scan-reveal") plutôt qu'un simple
  fondu. Toutes les animations respectent la préférence système de réduction des
  animations (`prefers-reduced-motion`) pour l'accessibilité.

## 35. Bilan de la version 5

- Deux interfaces fonctionnelles et interchangeables (Streamlit et JavaScript),
  s'appuyant sur la même API sans duplication de logique métier.
- Démonstration concrète de l'intérêt d'une architecture backend/frontend
  découplée, réutilisable pour d'éventuelles interfaces futures (mobile,
  intranet, etc.).
- Identité visuelle propre à l'entreprise, construite à partir d'éléments
  authentiques du métier (workflow réel, thématique du scanner) plutôt que d'un
  habillage générique d'assistant IA.

## 36. Prochaines étapes

1. Poursuivre, si besoin, l'enrichissement du corpus documentaire du Module 1.
2. Démarrer le développement du **Module 2** (contrôle documentaire par OCR),
   traité désormais comme un sous-projet distinct.
3. Envisager, en fin de projet, l'intégration des deux modules dans une
   interface unique.

---

# Version 6 — Site vitrine de l'entreprise et interconnexion des deux applications

## 37. Contexte de la version 6

Jusqu'à la version 5, le Module 1 n'existait que comme une application isolée,
accessible directement par son URL locale, sans point d'entrée présentant
l'entreprise ni contextualisant l'outil au sein de son activité réelle. Cette
version introduit un **site vitrine** (`gds-site/`) présentant GDS GED Services
et son processus métier, servant de porte d'entrée vers l'assistant, ainsi que
les ajustements nécessaires à l'assistant lui-même pour s'intégrer proprement
à cet ensemble à deux applications.

L'objectif n'était plus seulement de faire fonctionner l'assistant, mais de le
présenter dans un contexte crédible pour une soutenance ou une démonstration :
un visiteur arrive sur un site d'entreprise, comprend l'activité de GDS GED
Services et son processus documentaire, puis accède à l'assistant depuis ce
site plutôt que de recevoir directement un lien technique isolé.

## 38. Développement du site vitrine (`gds-site/`)

Le site a été construit comme une application statique indépendante (HTML /
CSS / JS, sans framework ni dépendance de build), structurée en cinq pages :

| Page | Contenu |
|---|---|
| `index.html` | Accueil : positionnement de l'entreprise, mission, aperçu du processus, mise en avant de l'assistant |
| `services.html` | Solutions et domaines d'activité |
| `processus.html` | Détail du workflow documentaire (réception → archivage) |
| `a-propos.html` | Positionnement dans le groupe (BANK OF AFRICA → DocuPrint → GDS GED Services), fiche d'identité |
| `contact.html` | Formulaire de contact |

**Sources du contenu** : les informations affichées (positionnement dans le
groupe, mission, secteurs desservis, étapes du processus documentaire) sont
issues de documents internes de présentation de l'entreprise et du processus
métier (note de synthèse et proposition de sujet de stage), et non de données
inventées. Un point de méthode a été appliqué : les noms des partenaires cités
nommément dans les documents sources ne sont **pas** repris sur le site public,
conformément à la mention explicite de confidentialité figurant dans le
document de référence — seuls les secteurs d'activité (banques, assurances,
organismes de protection sociale) et les types de processus sont mentionnés,
sans jamais nommer un partenaire précis.

**Démarche de conception** : plusieurs directions visuelles ont été explorées
successivement (registre éditorial/papier, palette multicolore, thème sombre
minimal) avant de converger vers une identité alignée sur celle de l'assistant
lui-même (voir section 40), plutôt que l'inverse — décision motivée par la
cohérence de marque entre les deux applications.

## 39. Interconnexion des deux applications

Le site et l'assistant restent deux applications **techniquement séparées**
(deux dossiers, deux serveurs distincts), reliées uniquement par des liens
configurables, à l'image de la séparation backend/frontend déjà retenue en
version 5 :

- **Site → Assistant** : chaque bouton "Assistant IA" du site pointe vers une
  variable unique, `ASSISTANT_URL`, définie dans `gds-site/app.js`. Modifier
  cette seule variable met à jour tous les points d'entrée du site vers
  l'assistant, sans toucher au HTML de chaque page.
- **Assistant → Site** : un bouton de retour (icône flèche, sans texte) a été
  ajouté dans l'interface de l'assistant, positionné à cheval sur le bord de
  la barre latérale, pointant vers `index.html` du site.

**Fonctionnement en développement local** : les deux applications sont servies
par deux processus distincts sur deux ports différents — l'API RAG via
`uvicorn src.api:app --reload --port 8000` (backend), et le frontend de
l'assistant via un serveur HTTP statique dédié (`python -m http.server 5500`),
le site vitrine pouvant être servi de la même façon sur un port distinct. Ce
point a nécessité une clarification explicite : l'URL de l'API (port 8000)
n'est pas la même que l'URL de l'interface de l'assistant (port du serveur
statique) — seule la seconde doit être renseignée dans `ASSISTANT_URL`.

**Limite assumée à ce stade** : cette interconnexion fonctionne en local
(sur la machine de développement, tant que les serveurs concernés tournent)
mais n'est pas encore déployée publiquement. Le passage à un hébergement
public nécessiterait de séparer à nouveau le statique (site + frontend de
l'assistant, déployables sur Netlify ou GitHub Pages) du backend Python
(API RAG, nécessitant un hébergeur exécutant du Python — Render, Railway ou
Hugging Face Spaces), puis de mettre à jour les URL de configuration en
conséquence.

## 40. Alignement de l'identité visuelle entre le site et l'assistant

Une décision explicite a été prise de faire **converger le site vitrine vers
l'identité déjà établie de l'assistant** (palette bleu marine / or, typographies
Space Grotesk / Inter / JetBrains Mono — voir section 34), plutôt que
d'harmoniser l'assistant sur un style propre au site. Justification : l'assistant
constitue le livrable technique central du Module 1, déjà validé et démontré ;
il est plus cohérent que la vitrine de présentation reprenne cette identité que
l'inverse, pour donner l'impression d'un produit unique cohérent plutôt que de
deux outils juxtaposés.

Concrètement, le site reprend :
- la même palette (bleu marine `#0F2247` / or `#C89B3C`) ;
- les mêmes typographies ;
- un aperçu de l'interface de l'assistant (mini fenêtre avec logo, statut "En
  ligne", question/réponse d'exemple) intégré directement dans la page
  d'accueil du site, pour donner un avant-goût fidèle du produit avant même de
  cliquer sur le bouton "Assistant IA".

## 41. Bilan de la version 6

- Site vitrine fonctionnel à cinq pages, présentant l'entreprise et son
  processus documentaire à partir de sources internes réelles, dans le respect
  de la confidentialité des partenariats.
- Les deux applications (site et assistant) sont reliées dans les deux sens par
  des liens configurables, sans dépendance de code entre elles.
- Identité visuelle unifiée entre le site et l'assistant, donnant une
  impression de produit cohérent plutôt que de deux outils distincts.
- Fonctionnement de bout en bout validé en environnement de développement
  local ; déploiement public identifié comme prochaine étape distincte.

## 42. Prochaines étapes

1. Déployer les deux applications publiquement (statique sur Netlify/GitHub
   Pages, API sur un hébergeur Python) et mettre à jour les URL de
   configuration en conséquence.
2. Démarrer le développement du **Module 2** (contrôle documentaire par OCR).
3. Envisager, en fin de projet, l'intégration des deux modules dans une
   interface unique, accessible depuis le même site vitrine.