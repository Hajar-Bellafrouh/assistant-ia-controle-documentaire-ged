# Journal — Version 4 : interface web connectée et progression en temps réel

## 1. Interface web et connexion à l'API

Une interface web (`controle-documentaire/index.html`, `.js`, `.css`) a été
construite pour consommer l'API validée en v3 : dépôt d'un dossier PDF,
suivi de l'analyse, puis affichage du verdict (tampon cohérent/incohérent,
nombre de pages, durée, détail des comparaisons champ par champ).

**Problème rencontré** : le premier test réel a échoué silencieusement
(`Failed to fetch`), l'interface étant servie sur une origine
(`127.0.0.1:5500`) différente de celle de l'API (`127.0.0.1:8001`). L'API
elle-même répondait correctement (confirmé en l'appelant directement) ;
seul l'appel émis par le navigateur était bloqué en l'absence d'un
middleware CORS côté serveur.

**Correction apportée** : ajout de `CORSMiddleware` dans `api/main.py`.
Après relance du serveur, l'interface communique normalement avec l'API,
dépôt et verdict inclus.

**Intégration au site vitrine** : un lien a été ajouté depuis la page
"Solutions" du site `gds-site` vers cette interface, et un lien retour
symétrique côté module 2, permettant de circuler entre les deux sans
passer par une URL tapée à la main.

## 2. Progression par page, sans streaming

Le seul retour disponible pendant l'analyse (1 à 4 minutes sur CPU, cf.
limite notée en v3) était un chronomètre, sans indication de l'avancement
réel. L'appel unique et bloquant `POST /controle-dossier` a été complété
par un mécanisme en trois temps, sans recourir à des WebSockets :

| Endpoint | Rôle |
|---|---|
| `POST /controle-dossier/demarrer` | Reçoit le fichier, lance l'analyse en tâche de fond (`asyncio.to_thread`, l'OCR étant bloquant), retourne un identifiant de tâche |
| `GET /controle-dossier/statut/{job_id}` | Interrogé toutes les secondes par le front, retourne la page en cours et le nombre total de pages |
| `GET /controle-dossier/resultat/{job_id}` | Retourne le verdict complet une fois l'analyse terminée |

Dans `src/ocr_utils.py`, `ocr_dossier` accepte désormais un callback
optionnel `on_progression`, appelé après chaque page traitée — seul
changement dans ce fichier, sans effet sur les appels existants qui ne le
fournissent pas.

**Ce qui a été vérifié** : l'ancien endpoint `POST /controle-dossier` a été
conservé tel quel et continue de fonctionner de façon identique à la v3.
La barre de progression a été testée sur un dossier de plusieurs pages et
avance par palier (page 1/4, 2/4...) en cohérence avec le traitement réel
côté serveur.

## 3. Limite assumée pour cette version

L'état des tâches (`_etat["jobs"]`) est conservé en mémoire côté API : un
redémarrage du serveur (rechargement automatique d'uvicorn compris) efface
les analyses en cours. Sans conséquence pour un usage ponctuel, à revoir
si un usage multi-utilisateurs est envisagé.

Le module a été vérifié que sur des dossiers cohérents et des dossiers incohérents.

## Prochaine étape (v5)

- Validation de l'interface sur un jeu de dossiers incohérents générés
  automatiquement (`generateur_dossiers_dentaires.ipynb` /
  `generateur_dossiers_medicaux.ipynb`, qui produisent une vérité terrain),
  pour confirmer que les anomalies sont bien détectées et affichées de
  bout en bout, pas seulement au niveau du pipeline.
- Traitement par lot (plusieurs dossiers déposés en une fois), envisagé
  seulement si le temps disponible sur le stage le permet.
