# Journal — Version 5 : traitement par lot et validation sur cas incohérents

## 1. Traitement par lot

L'interface acceptait jusqu'ici un seul dossier à la fois. L'input de
dépôt accepte désormais plusieurs fichiers PDF simultanément, avec deux
comportements distincts côté front selon le nombre de fichiers choisis :
un seul fichier déclenche le mode fichier unique (v4, barre de
progression) ; plusieurs fichiers déclenchent le mode lot.

**Choix d'architecture** : un seul moteur PaddleOCR étant chargé en
mémoire, deux analyses ne doivent jamais tourner en parallèle dessus.
Le fichier unique et le lot passent donc tous les deux par **une seule
file d'attente** (`asyncio.Queue`), consommée par **un seul worker** en
tâche de fond côté API — les dossiers d'un lot sont traités strictement
l'un après l'autre, jamais simultanément.

| Endpoint | Rôle |
|---|---|
| `POST /controle-dossier/lot/demarrer` | Reçoit plusieurs fichiers, crée un job par fichier, retourne un `lot_id` |
| `GET /controle-dossier/lot/statut/{lot_id}` | Retourne, pour chaque dossier du lot : statut, page en cours, temps écoulé, verdict une fois terminé |

### Tableau de suivi

Chaque dossier du lot apparaît comme une ligne dans un tableau, mise à
jour par interrogation toutes les 1,5 secondes (même logique de polling
qu'en v4, sans WebSocket) : nom du fichier, statut (en attente / en
cours / terminé / erreur), pages traitées, temps écoulé — calculé côté
serveur pour éviter tout décalage d'horloge avec le poste client — et
**verdict affiché directement dans le tableau** (cohérent/incohérent),
sans avoir besoin d'ouvrir chaque dossier pour le savoir. Un bouton
"Voir" reste disponible pour consulter le détail complet des anomalies
d'un dossier donné, avec un lien de retour vers le tableau qui n'apparaît
que dans ce contexte (pas lors d'une analyse de fichier unique, où il
n'y a pas de tableau auquel revenir).

## 2. Validation sur dossiers incohérents

**Problème identifié en amont** : les tests réels effectués jusqu'en v4
ne portaient que sur des dossiers cohérents. Rien ne garantissait encore
que le badge "INCOHÉRENT" et le tableau des anomalies s'affichaient
correctement dans cette interface, bien que la détection elle-même ait
été validée séparément au niveau du pipeline `src/` (évaluations
`05_evaluation.ipynb`, v2/v3).

**Test effectué** : un dossier contenant plusieurs types d'erreurs
volontaires a été soumis à l'interface. Le verdict "INCOHÉRENT" et le
détail des anomalies détectées se sont affichés correctement, confirmant
que la chaîne complète — dépôt, file d'attente, OCR, détection, affichage
— fonctionne de bout en bout, pas seulement sur le cas cohérent déjà
testé en v3/v4.

## 3. Limite assumée pour cette version

L'état des jobs et des lots (`_etat["jobs"]`, `_etat["lots"]`) reste en
mémoire côté API, sans persistance sur disque : un redémarrage du
serveur efface l'historique des analyses en cours ou déjà consultées.
Sans conséquence pour un usage de démonstration ou de stage, à revoir
pour un usage en production multi-utilisateurs.

Le suivi de progression reste du polling HTTP classique, pas du
streaming (WebSocket) : suffisant à l'échelle d'un lot de quelques
dossiers, mais générerait un trafic inutile à plus grande échelle.

## Prochaine étape

Ce module est jugé fonctionnellement complet pour le périmètre du stage.
Les pistes suivantes sont identifiées comme améliorations futures plutôt
que traitées dans une version supplémentaire, faute de temps disponible :

- Stockage persistant des jobs (base de données légère type SQLite) au
  lieu d'un état en mémoire.
- Progression en temps réel via WebSocket plutôt que par interrogation
  périodique, si le volume de dossiers traités en parallèle augmente.
- Évaluation à plus grande échelle (plusieurs dizaines de dossiers) si le
  temps le permet.
- Authentification et restriction CORS à une origine précise avant tout
  déploiement au-delà d'un usage local de démonstration.
