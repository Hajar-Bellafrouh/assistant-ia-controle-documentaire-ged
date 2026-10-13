/**
 * Contrôle documentaire — Module 2
 *
 * Consomme l'API FastAPI (voir api/main.py). Deux modes :
 * - un seul fichier déposé -> file unique, avec barre de progression par page
 * - plusieurs fichiers déposés -> traitement par lot, avec tableau de suivi
 *
 * INTÉGRATION : change API_BASE_URL pour pointer vers l'adresse réelle du
 * serveur (en local pendant le développement, puis l'adresse de production
 * une fois déployé).
 *
 * NOTE : port 8001, différent du Module 1 (assistant, port 8000) —
 * lancer cette API avec : uvicorn api.main:app --reload --port 8001
 */

const API_BASE_URL = "http://127.0.0.1:8001";

// ---------------------------------------------------------------- Éléments
const elZoneDepot = document.getElementById("cd-zone-depot");
const elDropzone = document.getElementById("cd-dropzone");
const elInputFichier = document.getElementById("cd-input-fichier");
const elFichierChoisi = document.getElementById("cd-fichier-choisi");
const elFichierNom = document.getElementById("cd-fichier-nom");
const elRetirerFichier = document.getElementById("cd-retirer-fichier");
const elBoutonAnalyser = document.getElementById("cd-bouton-analyser");

const elProgression = document.getElementById("cd-progression");
const elFichierEnCours = document.getElementById("cd-fichier-en-cours");
const elChrono = document.getElementById("cd-chrono");
const elBarreRemplissage = document.getElementById("cd-barre-remplissage");
const elProgressionPourcentage = document.getElementById("cd-progression-pourcentage");

const elLot = document.getElementById("cd-lot");
const elLotCorps = document.getElementById("cd-lot-corps");
const elLotNouvelleAnalyse = document.getElementById("cd-lot-nouvelle-analyse");

const elErreur = document.getElementById("cd-erreur");
const elErreurDetail = document.getElementById("cd-erreur-detail");
const elErreurReessayer = document.getElementById("cd-erreur-reessayer");

const elResultat = document.getElementById("cd-resultat");
const elRetourLot = document.getElementById("cd-retour-lot");
const elTampon = document.getElementById("cd-tampon");
const elTamponLabel = document.getElementById("cd-tampon-label");
const elMetaFichier = document.getElementById("cd-meta-fichier");
const elMetaPages = document.getElementById("cd-meta-pages");
const elMetaDuree = document.getElementById("cd-meta-duree");
const elBlocAnomalies = document.getElementById("cd-bloc-anomalies");
const elRegistreCorps = document.getElementById("cd-registre-corps");
const elBlocDoublons = document.getElementById("cd-bloc-doublons");
const elListeDoublons = document.getElementById("cd-liste-doublons");
const elJsonComplet = document.getElementById("cd-json-complet");
const elNouvelleAnalyse = document.getElementById("cd-nouvelle-analyse");

const elStatutPoint = document.getElementById("cd-statut-point");
const elStatutTexte = document.getElementById("cd-statut-texte");

let fichiersSelectionnes = [];
let chronoIntervalle = null;
let intervalePolling = null;
let enContexteLot = false;

// ------------------------------------------------------------- Utilitaires
function formaterDuree(secondes) {
  if (secondes < 60) return `${secondes.toFixed(0)}s`;
  const min = Math.floor(secondes / 60);
  const rest = Math.round(secondes % 60);
  return `${min} min ${rest}s`;
}

function afficherSeulement(...elementsVisibles) {
  const tous = [elZoneDepot, elProgression, elLot, elErreur, elResultat];
  for (const el of tous) {
    el.hidden = !elementsVisibles.includes(el);
  }
}

function echapper(valeur) {
  const div = document.createElement("div");
  div.textContent = valeur == null ? "—" : String(valeur);
  return div.innerHTML;
}

// ---------------------------------------------------------- Vérif service
async function verifierSanteApi() {
  try {
    const reponse = await fetch(`${API_BASE_URL}/sante`);
    const data = await reponse.json();
    if (reponse.ok && data.modele_ocr_charge) {
      elStatutPoint.className = "cd-dot cd-dot--pret";
      elStatutTexte.textContent = "Service prêt";
    } else {
      elStatutPoint.className = "cd-dot";
      elStatutTexte.textContent = "Chargement du modèle…";
      setTimeout(verifierSanteApi, 3000);
    }
  } catch {
    elStatutPoint.className = "cd-dot cd-dot--hors-service";
    elStatutTexte.textContent = "Service indisponible";
  }
}
verifierSanteApi();

// ------------------------------------------------------- Sélection fichier
function selectionnerFichiers(fichiers) {
  const valides = [...fichiers].filter(
    f => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
  );
  if (valides.length === 0) {
    alert("Seuls les fichiers PDF sont acceptés.");
    return;
  }
  fichiersSelectionnes = valides;
  elFichierNom.textContent = valides.length === 1
    ? valides[0].name
    : `${valides.length} dossiers sélectionnés`;
  elFichierChoisi.hidden = false;
  elBoutonAnalyser.disabled = false;
  elBoutonAnalyser.textContent = valides.length === 1
    ? "Analyser le dossier"
    : `Analyser ${valides.length} dossiers`;
}

function reinitialiserSelection() {
  fichiersSelectionnes = [];
  elInputFichier.value = "";
  elFichierChoisi.hidden = true;
  elBoutonAnalyser.disabled = true;
  elBoutonAnalyser.textContent = "Analyser le dossier";
}

elDropzone.addEventListener("click", () => elInputFichier.click());
elDropzone.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") {
    e.preventDefault();
    elInputFichier.click();
  }
});
elInputFichier.addEventListener("change", (e) => selectionnerFichiers(e.target.files));

elDropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  elDropzone.classList.add("cd-dropzone--survol");
});
elDropzone.addEventListener("dragleave", () => {
  elDropzone.classList.remove("cd-dropzone--survol");
});
elDropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  elDropzone.classList.remove("cd-dropzone--survol");
  selectionnerFichiers(e.dataTransfer.files);
});

elRetirerFichier.addEventListener("click", reinitialiserSelection);

// ------------------------------------------------------------------ Envoi
elBoutonAnalyser.addEventListener("click", lancerAnalyse);
elErreurReessayer.addEventListener("click", lancerAnalyse);
elNouvelleAnalyse.addEventListener("click", () => {
  reinitialiserSelection();
  afficherSeulement(elZoneDepot);
});
elLotNouvelleAnalyse.addEventListener("click", () => {
  reinitialiserSelection();
  afficherSeulement(elZoneDepot);
});
elRetourLot.addEventListener("click", () => afficherSeulement(elLot));

async function lancerAnalyse() {
  if (fichiersSelectionnes.length === 0) return;
  if (fichiersSelectionnes.length === 1) {
    await lancerAnalyseUnique(fichiersSelectionnes[0]);
  } else {
    await lancerAnalyseLot(fichiersSelectionnes);
  }
}

// -------------------------------------------------- Analyse fichier unique
async function lancerAnalyseUnique(fichier) {
  enContexteLot = false;
  afficherSeulement(elProgression);
  elFichierEnCours.textContent = fichier.name;
  elBarreRemplissage.style.width = "0%";
  elProgressionPourcentage.textContent = "Page 0 / —";

  const debut = Date.now();
  chronoIntervalle = setInterval(() => {
    elChrono.textContent = formaterDuree((Date.now() - debut) / 1000);
  }, 1000);

  const formData = new FormData();
  formData.append("fichier", fichier);

  try {
    const reponseDemarrage = await fetch(`${API_BASE_URL}/controle-dossier/demarrer`, {
      method: "POST",
      body: formData,
    });
    const data = await reponseDemarrage.json();
    if (!reponseDemarrage.ok) throw new Error(data.detail || "Impossible de démarrer l'analyse.");

    intervalePolling = setInterval(() => suivreProgression(data.job_id), 1000);
  } catch (err) {
    clearInterval(chronoIntervalle);
    elErreurDetail.textContent = err.message || "Erreur réseau — le service est-il bien démarré ?";
    afficherSeulement(elErreur);
  }
}

async function suivreProgression(jobId) {
  try {
    const reponse = await fetch(`${API_BASE_URL}/controle-dossier/statut/${jobId}`);
    const statut = await reponse.json();

    if (statut.total_pages) {
      const pourcentage = Math.round((statut.page_actuelle / statut.total_pages) * 100);
      elBarreRemplissage.style.width = `${pourcentage}%`;
      elProgressionPourcentage.textContent = `Page ${statut.page_actuelle} / ${statut.total_pages}`;
    }

    if (statut.termine) {
      clearInterval(intervalePolling);
      clearInterval(chronoIntervalle);

      if (statut.erreur) {
        elErreurDetail.textContent = statut.erreur;
        afficherSeulement(elErreur);
        return;
      }

      const reponseResultat = await fetch(`${API_BASE_URL}/controle-dossier/resultat/${jobId}`);
      const data = await reponseResultat.json();
      afficherResultat(data);
    }
  } catch (err) {
    clearInterval(intervalePolling);
    clearInterval(chronoIntervalle);
    elErreurDetail.textContent = "Erreur réseau pendant le suivi de l'analyse.";
    afficherSeulement(elErreur);
  }
}

// --------------------------------------------------------- Analyse en lot
const LIBELLES_STATUT = {
  en_attente: "En attente",
  en_cours: "En cours…",
  termine: "Terminé",
  erreur: "Erreur",
};

async function lancerAnalyseLot(fichiers) {
  enContexteLot = true;
  afficherSeulement(elLot);
  elLotCorps.innerHTML = "";
  elLotNouvelleAnalyse.hidden = true;

  const formData = new FormData();
  for (const f of fichiers) formData.append("fichiers", f);

  try {
    const reponse = await fetch(`${API_BASE_URL}/controle-dossier/lot/demarrer`, {
      method: "POST",
      body: formData,
    });
    const data = await reponse.json();
    if (!reponse.ok) throw new Error(data.detail || `Erreur ${reponse.status}`);

    intervalePolling = setInterval(() => suivreLot(data.lot_id), 1500);
  } catch (err) {
    elErreurDetail.textContent = err.message || "Erreur réseau — le service est-il bien démarré ?";
    afficherSeulement(elErreur);
  }
}

async function suivreLot(lotId) {
  try {
    const reponse = await fetch(`${API_BASE_URL}/controle-dossier/lot/statut/${lotId}`);
    const { dossiers } = await reponse.json();

    elLotCorps.innerHTML = "";
    let tousTermines = true;

    for (const d of dossiers) {
      if (d.statut === "en_attente" || d.statut === "en_cours") tousTermines = false;

      const pages = d.total_pages ? `${d.page_actuelle} / ${d.total_pages}` : "—";
      const badge = `<span class="cd-statut-badge cd-statut-badge--${d.statut}">${LIBELLES_STATUT[d.statut] || d.statut}</span>`;
      const action = d.statut === "termine"
        ? `<button type="button" class="cd-lien-voir" data-job="${d.job_id}">Voir</button>`
        : (d.statut === "erreur" ? "—" : "");

      let temps = "—";
      if (d.statut === "termine" && d.duree_finale_secondes != null) {
        temps = formaterDuree(d.duree_finale_secondes);
      } else if (d.statut === "en_cours" && d.temps_ecoule_secondes != null) {
        temps = formaterDuree(d.temps_ecoule_secondes);
      }

      let verdict = "—";
      if (d.statut === "termine" && d.coherent != null) {
        verdict = d.coherent
          ? `<span class="cd-verdict-badge cd-verdict-badge--coherent">COHÉRENT</span>`
          : `<span class="cd-verdict-badge cd-verdict-badge--incoherent">INCOHÉRENT</span>`;
      }

      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${echapper(d.fichier)}</td>
        <td>${badge}</td>
        <td>${verdict}</td>
        <td>${pages}</td>
        <td>${temps}</td>
        <td>${action}</td>
      `;
      elLotCorps.appendChild(tr);
    }

    elLotCorps.querySelectorAll(".cd-lien-voir").forEach(btn => {
      btn.addEventListener("click", async () => {
        const reponse = await fetch(`${API_BASE_URL}/controle-dossier/resultat/${btn.dataset.job}`);
        const data = await reponse.json();
        afficherResultat(data);
      });
    });

    if (tousTermines) {
      clearInterval(intervalePolling);
      elLotNouvelleAnalyse.hidden = false;
    }
  } catch {
    clearInterval(intervalePolling);
    elErreurDetail.textContent = "Erreur réseau pendant le suivi du lot.";
    afficherSeulement(elErreur);
  }
}

// -------------------------------------------------------------- Résultat
function afficherResultat(data) {
  const coherent = data.coherent;

  elRetourLot.hidden = !enContexteLot;

  elTampon.className = coherent ? "cd-tampon" : "cd-tampon cd-tampon--incoherent";
  elTamponLabel.textContent = coherent ? "COHÉRENT" : "INCOHÉRENT";

  elMetaFichier.textContent = data.fichier || "—";
  elMetaFichier.title = data.fichier || "";
  elMetaPages.textContent = data.nb_pages ?? "—";
  elMetaDuree.textContent = data.duree_ocr_secondes != null ? formaterDuree(data.duree_ocr_secondes) : "—";

  const anomalies = data.anomalies_champs || [];
  elBlocAnomalies.hidden = anomalies.length === 0;
  elRegistreCorps.innerHTML = "";
  for (const a of anomalies) {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${echapper(a.champ)}</td>
      <td>${echapper(a.page_reference)}</td>
      <td>${echapper(a.valeur_reference)}</td>
      <td>${echapper(a.page_suspecte)}</td>
      <td>${echapper(a.valeur_suspecte)}</td>
      <td class="cd-score">${a.score_similarite.toFixed(2)}</td>
    `;
    elRegistreCorps.appendChild(tr);
  }

  const doublons = data.pages_dupliquees || [];
  elBlocDoublons.hidden = doublons.length === 0;
  elListeDoublons.innerHTML = "";
  for (const d of doublons) {
    const li = document.createElement("li");
    li.textContent = `Page ${d.page_a} <-> page ${d.page_b} (similarité ${d.similarite_texte.toFixed(2)})`;
    elListeDoublons.appendChild(li);
  }

  elJsonComplet.textContent = JSON.stringify(data.details_champs || {}, null, 2);

  afficherSeulement(elResultat);
}
