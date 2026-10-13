"""
Étape 3 — Chaîne RAG (Retrieval-Augmented Generation) avec mémoire conversationnelle.

Rôle :
- Charger l'index FAISS déjà construit (build_index.py)
- Reformuler la question en une version autonome si un historique existe
  (ex: "Et pour CMIM ?" -> "Comment fonctionne la numérisation pour CMIM ?")
- Récupérer les chunks pertinents pour cette question reformulée (retriever)
- Construire un prompt avec l'historique + ces chunks comme contexte
- Appeler le LLM local (Ollama / Llama 3) pour générer la réponse
- Répondre à partir des connaissances générales du LLM si la question est
  générale/évidente et absente de la documentation (mode hybride)

Peut être lancé directement pour tester en ligne de commande :
    python src/rag_chain.py
"""

from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from build_index import EMBEDDING_MODEL_NAME, INDEX_DIR

# Nom du modèle Ollama à utiliser.
OLLAMA_MODEL = "llama3.2:3b"

# Nombre de chunks récupérés par question. Remonté à 5 (au lieu de 4) : le corpus a
# grandi (ajout de présentations), un k plus large réduit le risque qu'un chunk
# spécifique important soit écarté au profit de contenu générique plus volumineux.
# Nombre de chunks récupérés par question. Remonté à 6 : le corpus contient
# maintenant du contenu redondant (plusieurs diapositives d'intro très similaires
# dans les présentations), qui peut sinon monopoliser plusieurs des places
# disponibles au détriment d'un chunk spécifique moins "démonstratif".
TOP_K = 8

# Nombre maximum de tokens générés par réponse finale.
MAX_OUTPUT_TOKENS = 350

# Nombre de tours (question+réponse) conservés dans l'historique transmis au LLM.
# Volontairement limité : plus d'historique = prompt plus long = réponse plus lente.
MAX_HISTORY_TURNS = 3

PROMPT_TEMPLATE = """Tu es un expert interne de GDS GED Services, spécialisé dans la
    Gestion Électronique des Documents (GED) et dans les procédures internes de
    l'entreprise (ateliers, logiciels Kofax Express et ReadSoft Forms, terminologie
    métier : PEC, RD, etc.).

    Réponds toujours directement, de façon claire, professionnelle et assurée, comme le
    ferait un collègue expérimenté s'adressant à un opérateur.

    INTERDICTIONS STRICTES (aucune exception) :
    - Ne commence JAMAIS ta réponse par une formule d'introduction telle que
    "Voici la réponse", "Voici une réponse concise", "Je suis désolé, mais",
    "Bonne question", ou toute formule similaire. Va directement à l'information,
    dès le premier mot.
    - Ne mentionne JAMAIS, dans aucune partie de ta réponse (y compris quand tu ne sais
    pas), les mots ou expressions : "le contexte", "les extraits", "la documentation
    fournie", "les informations fournies", "d'après les données disponibles", ou toute
    formule qui révèle que tu t'appuies sur des documents transmis. Réponds comme si tu
    connaissais naturellement l'information (ou comme si tu n'avais simplement pas
    cette information en tête, selon le cas).
    - Ne mentionne jamais non plus explicitement "l'historique de la conversation" —
    utilise-le simplement en silence pour comprendre le fil de la discussion.
    - L'historique ci-dessous sert UNIQUEMENT à comprendre à quoi renvoient des mots
    comme "et pour...", "ça", "cela" dans la nouvelle question. Il ne doit JAMAIS
    servir de source d'information pour construire ta réponse : base-toi exclusivement
    sur les "Informations disponibles" ci-dessous pour le contenu factuel. Si le sujet
    de la nouvelle question est différent du sujet précédent (ex: la question
    précédente portait sur un atelier, la nouvelle porte sur un autre atelier), ne
    réutilise SURTOUT PAS les informations de l'échange précédent : réponds
    uniquement à partir des informations disponibles pour CE sujet précis. Attention en
    particulier à ne jamais attribuer une action, une étape ou une opération à un
    atelier différent de celui auquel les informations disponibles l'associent
    réellement — vérifie bien à quel atelier appartient chaque information avant de
    l'utiliser.
    - Réponds UNE SEULE FOIS à LA question posée, puis arrête-toi. N'invente et
    n'écris JAMAIS toi-même une nouvelle question, ni la réponse à une question qui
    n'a pas été posée. Ne poursuis jamais la conversation au-delà de ta réponse.
    - Ne recopie JAMAIS la mise en forme du document source : pas de numéros de
    section à un ou plusieurs niveaux (ex: "2.2", "2.2.1"), pas de titres de chapitre
    ou de titres de partie (ex: "CHAPITRE 2", "Les clients pris en charge"), pas de
    listes à puces recopiées telles quelles si elles ne sont pas nécessaires. Ne
    commence JAMAIS ta réponse par un titre ou une numérotation copiée du document —
    commence toujours directement par une phrase complète qui répond à la question.
    Reformule toujours entièrement l'information avec tes propres mots.

    Procède ainsi pour construire ta réponse :
    0. Si le message de l'opérateur est une simple salutation ("bonjour", "salut"...),
    un remerciement ("merci", "merci à vous"...), une formule de politesse, ou une
    question générale sur ta capacité à aider ("j'ai des questions, peux-tu m'aider
    ?", "es-tu disponible ?"...), réponds directement et chaleureusement, de façon
    courte et naturelle, SANS utiliser les informations disponibles ci-dessous (elles
    ne sont pas pertinentes pour ce type de message, ignore-les complètement dans ce
    cas). Par exemple : à "Bonjour", réponds par une salutation brève et propose ton
    aide sur les procédures GDS GED Services ; à "merci", réponds simplement avec
    plaisir ou équivalent ; à "peux-tu m'aider ?", confirme que oui et précise que tu
    réponds aux questions sur les procédures, ateliers et outils de l'entreprise.
    1. Si l'information demandée est présente ci-dessous, réponds avec, de façon précise
    et fidèle, **en reproduisant exactement les noms propres, sigles, définitions et
    noms de logiciels tels qu'ils apparaissent** — ne les modifie jamais, ne les
    raccourcis pas, et surtout ne combine JAMAIS deux éléments distincts (par exemple
    deux noms de logiciels différents, ou deux définitions différentes d'un même sigle)
    en une seule réponse fusionnée. Si un logiciel est associé à un client précis dans
    les informations disponibles, ne l'associe à aucun autre client. Si plusieurs
    passages des informations disponibles se contredisent ou semblent en désaccord sur
    un même fait, privilégie systématiquement le passage qui associe explicitement et
    sans ambiguïté l'information au client ou au sujet exact de la question — ignore un
    passage qui liste plusieurs éléments ensemble sans préciser clairement lequel
    s'applique à quoi.
    2. Si l'information n'est présente nulle part ci-dessous mais qu'il s'agit d'une
    question générale sur la GED, l'archivage, la numérisation de documents, ou d'une
    notion que tu peux déduire avec certitude à partir de connaissances générales
    fiables, réponds à partir de ces connaissances, avec la même assurance
    professionnelle. Ne fais JAMAIS cela pour un sigle, un nom de client, un nom de
    logiciel ou toute entité propre à GDS GED Services : si tu n'es pas certain à 100%
    de sa définition exacte telle qu'elle apparaît dans les informations disponibles,
    applique plutôt la règle 4.
    3. Avant de répondre, vérifie que les informations disponibles ci-dessous parlent
    bien précisément du sujet exact de la question (ex: si la question porte sur
    "l'atelier archivage", vérifie que les informations parlent bien de cet atelier
    précis, pas d'un autre atelier comme la numérisation ou la préparation, même si
    son nom apparaît quelque part dans le texte). Si aucune information disponible ne
    traite précisément du sujet exact demandé, ne réutilise JAMAIS des informations
    sur un sujet différent ou proche pour improviser une réponse — applique la règle
    ci-dessous à la place.
    4. Si la question porte sur une donnée strictement propre à GDS GED Services (chiffre
    interne, décision, nom, date précise, définition d'un sigle) que tu ne trouves pas
    ci-dessous avec certitude, ou si aucune information disponible ne correspond
    précisément au sujet demandé (voir règle 3), réponds simplement, par exemple sur
    ce modèle : "Cette information n'est pas quelque chose que je peux confirmer
    précisément ; je te recommande de vérifier auprès d'un responsable ou de la
    documentation interne complète." Reste bref, une seule phrase suffit. Il vaut
    mieux dire que tu ne sais pas que d'inventer ou de mélanger deux informations.
    5. Si l'opérateur conteste ou corrige une information que tu as donnée précédemment,
    ne défends JAMAIS ta réponse précédente par une justification inventée. Revérifie
    plutôt strictement les informations disponibles ci-dessous : si elles confirment la
    correction de l'opérateur, donne-lui raison simplement et corrige ta réponse. Si
    elles ne permettent ni de confirmer ni d'infirmer sa remarque avec certitude,
    dis-le honnêtement plutôt que d'inventer une explication qui concilierait les deux
    versions.

    Réponds en français, de façon concise. Structure ta réponse en liste ou en étapes si
    cela facilite la lecture, mais sans jamais commencer par une formule d'introduction.

    Échanges précédents de cette conversation (le cas échéant, à utiliser uniquement pour
    comprendre le fil de la discussion, pas pour y répondre à nouveau) :
    {history}

    Informations disponibles :
    {context}

    Question : {question}

    Réponse :"""

CONDENSE_PROMPT_TEMPLATE = """Voici l'historique d'une conversation entre un opérateur
    et un assistant documentaire, suivi d'une nouvelle question de l'opérateur.

    Ta seule tâche : décider si cette nouvelle question a besoin d'être complétée pour
    être compréhensible seule, hors de son contexte.

    - Si la question contient déjà tous les éléments nécessaires pour être comprise seule
    (un sujet, un client, un nom précis...), même si elle est courte, renvoie-la
    EXACTEMENT telle quelle, mot pour mot, sans rien ajouter ni reformuler.
    - Seulement si la question utilise une référence implicite au message précédent
    (ex: "et pour CMIM ?", "et les autres ?", "et pour ça ?"), complète-la avec le
    minimum de mots nécessaires pour qu'elle soit autonome, en gardant sa formulation
    d'origine autant que possible.

    Ne réponds jamais à la question, ne l'enrichis jamais avec des détails qui n'y sont
    pas explicitement.

    Historique :
    {history}

    Nouvelle question : {question}

Question (reformulée seulement si nécessaire) :"""


def load_vectorstore() -> FAISS:
    if not INDEX_DIR.exists():
        raise FileNotFoundError(
            f"Index introuvable dans {INDEX_DIR}. "
            "Lance d'abord : python src/build_index.py"
        )
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    vectorstore = FAISS.load_local(
        str(INDEX_DIR), embeddings, allow_dangerous_deserialization=True
    )
    return vectorstore


def format_docs(docs) -> str:
    return "\n\n---\n\n".join(doc.page_content for doc in docs)


def format_history(chat_history: list[dict] | None) -> str:
    """Transforme une liste de messages [{"role": "user"/"assistant", "content": ...}]
    en texte lisible, limité aux MAX_HISTORY_TURNS derniers échanges."""
    if not chat_history:
        return "Aucun échange précédent."

    trimmed = chat_history[-(MAX_HISTORY_TURNS * 2):]
    lines = []
    for msg in trimmed:
        role = "Opérateur" if msg.get("role") == "user" else "Assistant"
        lines.append(f"{role} : {msg.get('content', '')}")
    return "\n".join(lines) if lines else "Aucun échange précédent."


class RagAssistant:
    """Encapsule le retriever + la chaîne LLM, avec mémoire conversationnelle et
    accès aux sources utilisées."""

    def __init__(self, top_k: int = TOP_K, model: str = OLLAMA_MODEL):
        self.vectorstore = load_vectorstore()
        # Recherche MMR (Maximal Marginal Relevance) : un pool plus large de
        # candidats (fetch_k) puis sélection pertinente + légèrement diversifiée.
        # lambda_mult proche de 1 = privilégie fortement la pertinence (peu de
        # diversité forcée) ; observé que 0.5 écartait à tort des chunks très
        # pertinents au profit de chunks juste "différents".
        self.retriever = self.vectorstore.as_retriever(
            search_type="mmr",
            search_kwargs={"k": top_k, "fetch_k": max(20, top_k * 5), "lambda_mult": 0.95},
        )

        self.llm = ChatOllama(
            model=model,
            temperature=0.3,
            num_predict=MAX_OUTPUT_TOKENS,
            # Coupe la génération si le modèle tente d'enchaîner sur un nouveau tour
            # de dialogue (question ou réponse inventée) au lieu de s'arrêter après
            # avoir répondu à la question posée.
            stop=["\nOpérateur", "\nOpérateur :", "Opérateur :", "\nQuestion :",
                    "\nQuestion:", "Question :", "\nRéponse :"],
        )
        # LLM séparé pour la reformulation : tâche courte, on limite fortement
        # le nombre de tokens générés pour que cet appel reste rapide.
        self.condense_llm = ChatOllama(model=model, temperature=0.0, num_predict=60)

        self.prompt = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
        self.condense_prompt = ChatPromptTemplate.from_template(CONDENSE_PROMPT_TEMPLATE)
        self.output_parser = StrOutputParser()

    def _standalone_question(self, question: str, history_text: str) -> str:
        """Reformule la question en version autonome si un historique existe."""
        if history_text == "Aucun échange précédent.":
            return question
        prompt_value = self.condense_prompt.invoke(
            {"history": history_text, "question": question}
        )
        raw = self.condense_llm.invoke(prompt_value)
        return self.output_parser.invoke(raw).strip()

    def _retrieve(self, question: str, standalone_question: str):
        """Recherche hybride : interroge FAISS avec la question brute et, si elle
        diffère, avec la question reformulée, puis fusionne sans doublons. Ça évite
        de rater le bon chunk si la reformulation dérive du sujet exact posé."""
        docs_raw = self.retriever.invoke(question)
        if standalone_question.strip() == question.strip():
            return docs_raw

        docs_standalone = self.retriever.invoke(standalone_question)

        combined = []
        seen = set()
        for doc in docs_raw + docs_standalone:
            key = doc.page_content[:120]
            if key not in seen:
                seen.add(key)
                combined.append(doc)
        return combined[:TOP_K]

    def _prepare(self, question: str, chat_history: list[dict] | None):
        """Étapes communes à ask() et ask_stream() : reformulation, recherche,
        construction du prompt final et des sources."""
        history_text = format_history(chat_history)
        standalone_question = self._standalone_question(question, history_text)

        docs = self._retrieve(question, standalone_question)
        sources = [
            {
                "source": doc.metadata.get("source", "inconnu"),
                "extrait": doc.page_content[:200].replace("\n", " ") + "...",
            }
            for doc in docs
        ]

        prompt_value = self.prompt.invoke(
            {
                "context": format_docs(docs),
                "question": question,
                "history": history_text,
            }
        )
        return prompt_value, sources

    def ask(self, question: str, chat_history: list[dict] | None = None) -> dict:
        prompt_value, sources = self._prepare(question, chat_history)
        raw = self.llm.invoke(prompt_value)
        answer = self.output_parser.invoke(raw)
        return {"question": question, "answer": answer, "sources": sources}

    def ask_stream(self, question: str, chat_history: list[dict] | None = None):
        """Génère la réponse token par token (générateur), pour un affichage en
        flux. Renvoie d'abord les sources (dict), puis les morceaux de texte."""
        prompt_value, sources = self._prepare(question, chat_history)
        yield {"type": "sources", "sources": sources}
        for chunk in self.llm.stream(prompt_value):
            yield {"type": "token", "text": chunk.content}


if __name__ == "__main__":
    print("[rag_chain] Chargement de l'assistant RAG (index FAISS + Ollama)...")
    assistant = RagAssistant()
    print("[rag_chain] Prêt. Tape ta question (ou 'quit' pour quitter).\n")

    historique: list[dict] = []
    while True:
        question = input("Question > ").strip()
        if question.lower() in ("quit", "exit", "q"):
            break
        if not question:
            continue

        result = assistant.ask(question, chat_history=historique)
        print(f"\nRéponse : {result['answer']}\n")
        print("Sources utilisées :")
        for src in result["sources"]:
            print(f"  - {src['source']}")
        print()

        historique.append({"role": "user", "content": question})
        historique.append({"role": "assistant", "content": result["answer"]})
