// ============================================================
// Configuration — adapte l'URL si l'API tourne ailleurs
// ============================================================
const API_BASE = "http://localhost:8000";

// ============================================================
// État de la conversation (équivalent de st.session_state)
// ============================================================
let messages = [];          // [{role, content, sources}]
let memoryEnabled = true;

// ============================================================
// Références DOM
// ============================================================
const chatEl = document.getElementById("chat");
const composerEl = document.getElementById("composer");
const inputEl = document.getElementById("question-input");
const sendBtn = document.getElementById("send-btn");
const memoryToggle = document.getElementById("memory-toggle");
const memoryHint = document.getElementById("memory-hint");
const clearBtn = document.getElementById("clear-btn");
const sidebar = document.getElementById("sidebar");
const sidebarToggle = document.getElementById("sidebar-toggle");

// ============================================================
// Icônes de source selon le type de fichier
// ============================================================
const ICON_FILE_PDF = '<svg class="icon" style="margin-right:5px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>';
const ICON_FILE_MD = '<svg class="icon" style="margin-right:5px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M9 15h6M9 11h6"/></svg>';
const ICON_FILE_PPTX = '<svg class="icon" style="margin-right:5px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="12" rx="1"/><line x1="8" y1="20" x2="16" y2="20"/><line x1="12" y1="16" x2="12" y2="20"/></svg>';
const ICON_FILE_DEFAULT = '<svg class="icon" style="margin-right:5px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>';

function iconeSource(nomFichier) {
  const nom = nomFichier.toLowerCase();
  if (nom.endsWith(".pdf")) return ICON_FILE_PDF;
  if (nom.endsWith(".md")) return ICON_FILE_MD;
  if (nom.endsWith(".pptx")) return ICON_FILE_PPTX;
  return ICON_FILE_DEFAULT;
}

function nomCourt(chemin) {
  return chemin.split("\\").pop().split("/").pop();
}

// ============================================================
// Santé de l'API + stats (sidebar)
// ============================================================
async function rafraichirStatut() {
  const dot = document.getElementById("status-dot");
  const text = document.getElementById("status-text");
  try {
    const res = await fetch(`${API_BASE}/health`, { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    if (data.assistant_charge) {
      dot.className = "dot ok";
      text.textContent = "Opérationnel";
      document.getElementById("model-value").textContent = data.modele || "—";
      document.getElementById("chunks-value").textContent = data.nombre_chunks ?? "—";
    } else {
      dot.className = "dot ko";
      text.textContent = "Chargement…";
    }
  } catch {
    dot.className = "dot ko";
    text.textContent = "Hors ligne";
  }

  try {
    const res = await fetch(`${API_BASE}/feedback/stats`, { signal: AbortSignal.timeout(4000) });
    const data = await res.json();
    document.getElementById("fb-up").textContent = data.up ?? 0;
    document.getElementById("fb-down").textContent = data.down ?? 0;
  } catch {
    /* silencieux : pas bloquant */
  }
}

// ============================================================
// Rendu d'un message dans le fil de discussion
// ============================================================
function creerBulleUser(texte) {
  const msg = document.createElement("div");
  msg.className = "msg user";
  msg.innerHTML = `
    <div class="msg-avatar"><svg class="icon" style="margin:0;width:17px;height:17px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg></div>
    <div class="msg-body"><div class="bubble"></div></div>
  `;
  msg.querySelector(".bubble").textContent = texte;
  chatEl.appendChild(msg);
  chatEl.scrollTop = chatEl.scrollHeight;
  return msg;
}

function creerBulleAssistant() {
  const msg = document.createElement("div");
  msg.className = "msg assistant";
  msg.innerHTML = `
    <div class="msg-avatar"><svg class="icon" style="margin:0;width:17px;height:17px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="10" rx="2"/><circle cx="12" cy="5" r="2"/><path d="M12 7v4"/><line x1="8" y1="16" x2="8" y2="16"/><line x1="16" y1="16" x2="16" y2="16"/></svg></div>
    <div class="msg-body">
      <div class="bubble"><span class="cursor"></span></div>
      <div class="sources-slot"></div>
      <div class="feedback-slot"></div>
    </div>
  `;
  chatEl.appendChild(msg);
  chatEl.scrollTop = chatEl.scrollHeight;
  return msg;
}

function afficherSources(container, sources) {
  if (!sources || sources.length === 0) return;
  const details = document.createElement("details");
  details.className = "sources";
  const summary = document.createElement("summary");
  summary.innerHTML = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>Sources utilisées';
  details.appendChild(summary);
  sources.forEach((src) => {
    const div = document.createElement("div");
    div.className = "source-item";
    div.innerHTML = `
      <span class="src-name">${iconeSource(src.source)} ${nomCourt(src.source)}</span>
      <span class="src-extract">${src.extrait}</span>
    `;
    details.appendChild(div);
  });
  container.appendChild(details);
}

function afficherFeedback(container, question, answer) {
  const row = document.createElement("div");
  row.className = "feedback-row";

  const ICON_THUMB_UP = '<svg class="icon" style="margin:0;width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M7 10v12"/><path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z"/></svg>';
  const ICON_THUMB_DOWN = '<svg class="icon" style="margin:0;width:14px;height:14px" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 14V2"/><path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z"/></svg>';

  const btnUp = document.createElement("button");
  btnUp.className = "fb-btn";
  btnUp.innerHTML = ICON_THUMB_UP;
  btnUp.type = "button";

  const btnDown = document.createElement("button");
  btnDown.className = "fb-btn";
  btnDown.innerHTML = ICON_THUMB_DOWN;
  btnDown.type = "button";

  async function envoyer(valeur) {
    row.innerHTML = `<span class="feedback-thanks">Merci pour votre retour</span>`;
    try {
      await fetch(`${API_BASE}/feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, answer, feedback: valeur }),
      });
      rafraichirStatut();
    } catch {
      /* best-effort */
    }
  }

  btnUp.addEventListener("click", () => envoyer("up"));
  btnDown.addEventListener("click", () => envoyer("down"));

  row.appendChild(btnUp);
  row.appendChild(btnDown);
  container.appendChild(row);
}

// ============================================================
// Envoi d'une question (streaming NDJSON depuis /ask/stream)
// ============================================================
async function envoyerQuestion(question) {
  inputEl.value = "";
  sendBtn.disabled = true;

  creerBulleUser(question);
  messages.push({ role: "user", content: question });

  const historique = memoryEnabled
    ? messages.slice(0, -1).slice(-6).map((m) => ({ role: m.role, content: m.content }))
    : [];

  const msgEl = creerBulleAssistant();
  const bubble = msgEl.querySelector(".bubble");
  const sourcesSlot = msgEl.querySelector(".sources-slot");
  const feedbackSlot = msgEl.querySelector(".feedback-slot");

  let fullAnswer = "";
  let sources = [];

  try {
    const res = await fetch(`${API_BASE}/ask/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question, history: historique }),
    });

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const lignes = buffer.split("\n");
      buffer = lignes.pop(); // dernière ligne potentiellement incomplète

      for (const ligne of lignes) {
        if (!ligne.trim()) continue;
        const event = JSON.parse(ligne);
        if (event.type === "sources") {
          sources = event.sources;
        } else if (event.type === "token") {
          fullAnswer += event.text;
          bubble.innerHTML = "";
          bubble.appendChild(document.createTextNode(fullAnswer));
          const cursor = document.createElement("span");
          cursor.className = "cursor";
          bubble.appendChild(cursor);
          chatEl.scrollTop = chatEl.scrollHeight;
        }
      }
    }
    bubble.textContent = fullAnswer;
  } catch (err) {
    fullAnswer = `Erreur lors de l'appel à l'API : ${err.message}`;
    bubble.textContent = fullAnswer;
  }

  afficherSources(sourcesSlot, sources);
  afficherFeedback(feedbackSlot, question, fullAnswer);

  messages.push({ role: "assistant", content: fullAnswer, sources });
  sendBtn.disabled = false;
  inputEl.focus();
}

// ============================================================
// Événements
// ============================================================
composerEl.addEventListener("submit", (e) => {
  e.preventDefault();
  const question = inputEl.value.trim();
  if (question) envoyerQuestion(question);
});

document.querySelectorAll(".quick-btn").forEach((btn) => {
  btn.addEventListener("click", () => envoyerQuestion(btn.dataset.q));
});

memoryToggle.addEventListener("change", () => {
  memoryEnabled = memoryToggle.checked;
  memoryHint.textContent = memoryEnabled
    ? "Mode conversation naturelle"
    : "Mode questions indépendantes (plus fiable)";
});

clearBtn.addEventListener("click", () => {
  messages = [];
  chatEl.innerHTML = "";
});

sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("open"));

// ============================================================
// Initialisation
// ============================================================
rafraichirStatut();
setInterval(rafraichirStatut, 15000);
