# Deployment Control Center

Plateforme pour gérer déploiements microservices sur K8s via GitOps.

## Schéma du Flux de Données (Interactif)


```mermaid
graph TD
    A[Utilisateur: Clique Déployer] -->|API Request| B[Backend: Valide Input]
    B -->|Si STAG/PROD| C[Crée Demande Approbation<br>Notifications Slack/Email]
    C -->|Approbation Validée| D[Orchestration Git: Clone Repo<br>Créer Branche/PR<br>Générer values.yaml + secrets.yaml in 02-nxh-database-config]
    B -->|Si DEV (immédiat)| D
    D -->|Push + Créer PR| E[GitHub: PR en Attente]
    E -->|Polling Backend| F{Statut PR?}
    F -->|En Attente| G[UI: Affiche 'Bloqué par Validation PR'<br>Retry Loop si AWS Down]
    F -->|Mergé| H[Argo CD: Détecte Changement<br>Sync Manifests to EKS]
    H -->|Succès| I[UI: Statut 'Déployé'<br>Historique DB Update]
    G -->|AWS Connexion Retry| D  // Loop si accès AWS down