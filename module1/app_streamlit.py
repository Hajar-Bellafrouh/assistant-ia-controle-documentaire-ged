"""
Étape 5 — Interface Streamlit (design soigné).

Rôle :
- Interface de chat professionnelle pour les opérateurs GED
- Bannière avec le workflow des ateliers (Réception -> ... -> Archivage)
- Sidebar avec statut de l'assistant, statistiques et questions rapides
- Streaming de la réponse (affichage au fil de l'eau)
- Cartes de sources stylées selon le type de document

Lancement :
    streamlit run app_streamlit.py
"""

import json

import requests
import streamlit as st

API_URL_STREAM = "http://localhost:8000/ask/stream"
API_HEALTH_URL = "http://localhost:8000/health"
API_FEEDBACK_URL = "http://localhost:8000/feedback"
API_FEEDBACK_STATS_URL = "http://localhost:8000/feedback/stats"

st.set_page_config(
    page_title="Assistant Documentaire GED",
    page_icon="🗂️",
    layout="centered",
)

# --------------------------------------------------------------------------
# STYLE — palette bleu marine / doré (registre bancaire / archivage),
# typographie Inter (corps) + Sora (titres)
# --------------------------------------------------------------------------
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600&display=swap');

    :root {
        --navy: #0F2247;
        --navy-light: #1B3A66;
        --gold: #C89B3C;
        --gold-light: #E8C97A;
        --bg-soft: #F6F7FA;
        --text-main: #1F2733;
    }

    html, body, [class*="css"]  { font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Sora', sans-serif !important; }

    /* Fond général */
    .stApp { background-color: var(--bg-soft); }

    /* Bannière d'en-tête */
    .ged-hero {
        background: linear-gradient(135deg, var(--navy) 0%, var(--navy-light) 100%);
        border-radius: 16px;
        padding: 28px 32px 22px 32px;
        margin-bottom: 18px;
        box-shadow: 0 8px 24px rgba(15, 34, 71, 0.18);
    }
    .ged-hero h1 {
        color: white;
        font-size: 1.65rem;
        margin: 0 0 4px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .ged-hero p {
        color: #C9D3E4;
        margin: 0;
        font-size: 0.92rem;
    }

    /* Fil du workflow */
    .ged-workflow {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 18px;
        flex-wrap: wrap;
    }
    .ged-step {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(232, 201, 122, 0.35);
        color: #E8C97A;
        border-radius: 999px;
        padding: 4px 12px;
        font-size: 0.76rem;
        font-weight: 500;
        white-space: nowrap;
    }
    .ged-arrow { color: #5A729E; font-size: 0.8rem; }

    /* Cartes sidebar */
    .ged-card {
        background: white;
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        border: 1px solid #E4E8F0;
    }
    .ged-card-title {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #7A8699;
        font-weight: 600;
        margin-bottom: 6px;
    }
    .ged-status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }
    .ged-status-ok { background-color: #2FA65A; }
    .ged-status-ko { background-color: #D64545; }

    /* Sources */
    .ged-source {
        background: #FBF8F0;
        border-left: 3px solid var(--gold);
        border-radius: 6px;
        padding: 8px 12px;
        margin-bottom: 6px;
        font-size: 0.85rem;
    }
    .ged-source-name {
        font-weight: 600;
        color: var(--navy);
    }

    /* Boutons questions rapides */
    .stButton button {
        border-radius: 8px;
        border: 1px solid #E4E8F0;
        background: white;
        text-align: left;
        font-size: 0.85rem;
        padding: 8px 10px;
    }
    .stButton button:hover {
        border-color: var(--gold);
        color: var(--navy);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# EN-TÊTE
# --------------------------------------------------------------------------
st.markdown(
    """
    <div class="ged-hero">
        <h1>🗂️ Assistant Documentaire GED</h1>
        <p>GDS GED Services · Réponses instantanées sur vos procédures internes</p>
        <div class="ged-workflow">
            <span class="ged-step">📥 Réception</span>
            <span class="ged-arrow">→</span>
            <span class="ged-step">🗃️ Préparation</span>
            <span class="ged-arrow">→</span>
            <span class="ged-step">🖨️ Numérisation</span>
            <span class="ged-arrow">→</span>
            <span class="ged-step">✅ Contrôle qualité</span>
            <span class="ged-arrow">→</span>
            <span class="ged-step">📦 Archivage</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------
# VÉRIFICATION DE L'API + STATS
# --------------------------------------------------------------------------
api_ok = False
health_data = {}
try:
    health_data = requests.get(API_HEALTH_URL, timeout=3).json()
    api_ok = health_data.get("assistant_charge", False)
except requests.exceptions.RequestException:
    api_ok = False

EXEMPLES_QUESTIONS = [
    "🗃️ Comment fonctionne l'atelier Préparation ?",
    "📋 Quelle est la différence entre PEC et RD ?",
    "🖨️ C'est quoi Kofax Express ?",
    "🔎 C'est quoi le module Interpret de ReadSoft ?",
]

# --------------------------------------------------------------------------
# SIDEBAR
# --------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Statut de l'assistant")

    status_class = "ged-status-ok" if api_ok else "ged-status-ko"
    status_text = "Opérationnel" if api_ok else "Hors ligne"
    modele = health_data.get("modele", "—")
    nb_chunks = health_data.get("nombre_chunks", "—")

    feedback_up, feedback_down = "—", "—"
    if api_ok:
        try:
            stats = requests.get(API_FEEDBACK_STATS_URL, timeout=3).json()
            feedback_up = stats.get("up", 0)
            feedback_down = stats.get("down", 0)
        except requests.exceptions.RequestException:
            pass

    st.markdown(
        f"""
        <div class="ged-card">
            <div class="ged-card-title">Connexion</div>
            <span class="ged-status-dot {status_class}"></span>{status_text}
        </div>
        <div class="ged-card">
            <div class="ged-card-title">Modèle IA</div>
            🧠 {modele}
        </div>
        <div class="ged-card">
            <div class="ged-card-title">Base documentaire</div>
            📚 {nb_chunks} extraits indexés
        </div>
        <div class="ged-card">
            <div class="ged-card-title">Retours des opérateurs</div>
            👍 {feedback_up} &nbsp;·&nbsp; 👎 {feedback_down}
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not api_ok:
        st.warning(
            "API non disponible.\n\nLance-la avec :\n"
            "`uvicorn src.api:app --reload --port 8000`"
        )

    st.markdown("### 🧠 Mémoire conversationnelle")
    if "memoire_activee" not in st.session_state:
        st.session_state["memoire_activee"] = True

    st.session_state["memoire_activee"] = st.toggle(
        "Se souvenir des échanges précédents",
        value=st.session_state["memoire_activee"],
        help=(
            "Activée : l'assistant comprend les questions de suivi (\"et pour...\"), "
            "mais peut occasionnellement mélanger deux sujets proches.\n\n"
            "Désactivée : chaque question est traitée indépendamment, réponses plus "
            "fiables, mais il faut reformuler entièrement chaque question."
        ),
    )
    if st.session_state["memoire_activee"]:
        st.caption("✅ Mode conversation naturelle")
    else:
        st.caption("🔒 Mode questions indépendantes (plus fiable)")

    st.markdown("### 💬 Questions rapides")
    for exemple in EXEMPLES_QUESTIONS:
        if st.button(exemple, use_container_width=True, key=f"ex_{exemple}"):
            st.session_state["question_rapide"] = exemple.split(" ", 1)[1]

    st.markdown("---")
    if st.button("🗑️ Effacer la conversation", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --------------------------------------------------------------------------
# ICÔNE DE SOURCE SELON LE TYPE DE FICHIER
# --------------------------------------------------------------------------
def icone_source(nom_fichier: str) -> str:
    nom = nom_fichier.lower()
    if nom.endswith(".pdf"):
        return "📄"
    if nom.endswith(".md"):
        return "📝"
    if nom.endswith(".pptx"):
        return "📊"
    return "📃"


# --------------------------------------------------------------------------
# FEEDBACK (👍 / 👎) SUR CHAQUE RÉPONSE
# --------------------------------------------------------------------------
def envoyer_feedback(question: str, answer: str, valeur: str) -> None:
    """Envoi best-effort : un échec réseau ne doit jamais casser l'UX du chat."""
    try:
        requests.post(
            API_FEEDBACK_URL,
            json={"question": question, "answer": answer, "feedback": valeur},
            timeout=5,
        )
    except requests.exceptions.RequestException:
        pass


def afficher_feedback(idx: int, question: str, answer: str) -> None:
    if "feedback_donne" not in st.session_state:
        st.session_state["feedback_donne"] = {}

    deja_donne = st.session_state["feedback_donne"].get(idx)
    if deja_donne:
        emoji = "👍" if deja_donne == "up" else "👎"
        st.caption(f"Merci pour ton retour {emoji}")
        return

    col_up, col_down, _ = st.columns([1, 1, 10])
    with col_up:
        if st.button("👍", key=f"fb_up_{idx}"):
            envoyer_feedback(question, answer, "up")
            st.session_state["feedback_donne"][idx] = "up"
            st.rerun()
    with col_down:
        if st.button("👎", key=f"fb_down_{idx}"):
            envoyer_feedback(question, answer, "down")
            st.session_state["feedback_donne"][idx] = "down"
            st.rerun()


# --------------------------------------------------------------------------
# HISTORIQUE DE CONVERSATION
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

for idx, message in enumerate(st.session_state.messages):
    avatar = "🧑‍💼" if message["role"] == "user" else "🤖"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        if message.get("sources"):
            with st.expander("📎 Sources utilisées"):
                for src in message["sources"]:
                    icone = icone_source(src["source"])
                    nom_court = src["source"].split("\\")[-1].split("/")[-1]
                    st.markdown(
                        f"""<div class="ged-source">
                        <span class="ged-source-name">{icone} {nom_court}</span><br>
                        <span style="color:#6B7688;">{src['extrait']}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )
        if message["role"] == "assistant" and idx > 0:
            question_associee = st.session_state.messages[idx - 1]["content"]
            afficher_feedback(idx, question_associee, message["content"])

# --------------------------------------------------------------------------
# ZONE DE SAISIE (chat + questions rapides de la sidebar)
# --------------------------------------------------------------------------
question = st.chat_input("💬 Posez votre question sur les procédures internes...")

if "question_rapide" in st.session_state:
    question = st.session_state.pop("question_rapide")

if question:
    # Historique à transmettre = tous les messages précédents (avant la question
    # posée maintenant), limité aux 6 derniers pour garder des requêtes légères.
    # Vide si la mémoire conversationnelle est désactivée dans la sidebar.
    if st.session_state.get("memoire_activee", True):
        historique_a_envoyer = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages[-6:]
        ]
    else:
        historique_a_envoyer = []

    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍💼"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🤖"):
        placeholder = st.empty()
        full_answer = ""
        sources = []

        try:
            with requests.post(
                API_URL_STREAM,
                json={"question": question, "history": historique_a_envoyer},
                timeout=180,
                stream=True,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    event = json.loads(line)
                    if event["type"] == "sources":
                        sources = event["sources"]
                    elif event["type"] == "token":
                        full_answer += event["text"]
                        placeholder.markdown(full_answer + "▌")
                placeholder.markdown(full_answer)
        except requests.exceptions.RequestException as exc:
            full_answer = f"⚠️ Erreur lors de l'appel à l'API : {exc}"
            placeholder.markdown(full_answer)

        if sources:
            with st.expander("📎 Sources utilisées"):
                for src in sources:
                    icone = icone_source(src["source"])
                    nom_court = src["source"].split("\\")[-1].split("/")[-1]
                    st.markdown(
                        f"""<div class="ged-source">
                        <span class="ged-source-name">{icone} {nom_court}</span><br>
                        <span style="color:#6B7688;">{src['extrait']}</span>
                        </div>""",
                        unsafe_allow_html=True,
                    )

        # Index que ce message occupera une fois ajouté à st.session_state.messages
        # juste après (len() actuel = index 0-based qu'aura ce nouvel élément).
        idx_futur = len(st.session_state.messages)
        afficher_feedback(idx_futur, question, full_answer)

    st.session_state.messages.append(
        {"role": "assistant", "content": full_answer, "sources": sources}
    )

st.markdown(
    """<p style="text-align:center; color:#9AA5B5; font-size:0.75rem; margin-top:24px;">
    Propulsé par Llama 3.2 (local) · Module 1 — Assistant Documentaire · GDS GED Services
    </p>""",
    unsafe_allow_html=True,
)
