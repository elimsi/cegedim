# Modélisation BPMN : Processus TO-BE (Automatisé)

Ce document fournit la description textuelle détaillée pour la création du diagramme BPMN du nouveau processus automatisé (Après implémentation du projet n8n + ML).

## Paramètres du Modèle
- **Code couleur** : 
  - 🟩 Vert = Étape 100% automatisée
  - 🟨 Jaune = Étape humaine d'expertise (Révision d'anomalie)
- **Temps machine estimé** : ~2 minutes par bordereau.

## Swimlanes (Couloirs d'activités)
1. **Émetteur**
2. **Système n8n (Orchestrateur)**
3. **Moteur ML (FastAPI)**
4. **Professionnel de Santé (PS)**
5. **Manager Fraude / Gestionnaire (Tableau de bord)**

## Séquence des Étapes

### Phase d'Acquisition (Automatisée)
1. **Émetteur** : Dépose le fichier `bordereau.txt` dans un dossier sécurisé SFTP (Watch Folder).
2. **Système n8n 🟩** : [Événement de début] Détecte instantanément le nouveau fichier.
3. **Système n8n 🟩** : Parse et extrait les données en format JSON (`src/parser.js`).

### Phase de Validation (Automatisée)
4. **Système n8n 🟩** : Applique les règles métier strictes (`src/validators.js`).
   - *Passerelle (XOR) : Lignes avec erreurs de format ?*
   - *Oui* : Extrait les lignes rejetées, génère un fichier CSV de rejet (`src/rejet_builder.js`), et envoie automatiquement l'email à l'**Émetteur**.
   - *Non / Poursuite* : Les lignes valides passent à l'étape de groupement.

### Phase d'Agrégation et Scoring (Automatisée)
5. **Système n8n 🟩** : Regroupe les transactions par Professionnel de Santé (`src/grouper.js`).
6. **Système n8n 🟩** : [Sous-processus Itératif - Split In Batches] Pour chaque PS :
   - 6a. Envoie les requêtes HTTP au **Moteur ML**.
7. **Moteur ML 🟩** : Calcule le *Z-Score* et exécute *Isolation Forest*. Renvoie le score et le *flag*.

### Phase de Décision et Communication
8. **Système n8n 🟩** : Réception du score.
   - *Passerelle (XOR) : Flag == ANOMALIE ?*
   - *Oui* : 
     - 8a. Insère l'alerte dans la base de données.
     - 8b. **Manager Fraude 🟨** : Consulte l'alerte sur l'application *Streamlit* (Page Fraud Investigator) et statue sur la légitimité du paiement.
   - *Non* : 
     - 8c. Requête HTTP vers *Gotenberg* pour générer le document PDF (Template HTML).
     - 8d. Envoi de l'email au **PS** avec le bordereau PDF en pièce jointe sécurisée.

### Phase d'Historisation (Automatisée)
9. **Système n8n 🟩** : Enregistre toutes les métadonnées (validées et rejetées) en base de données PostgreSQL (`src/logger.js`).
10. **Système n8n 🟩** : [Événement de fin] Clôture du workflow.

---

## Bilan des Améliorations (TO-BE)
- **Coût temporel humain** : Réduit de 45 minutes à 0 minute pour le traitement standard (hors révision de fraude).
- **Taux d'erreur de traitement** : 0% (règles déterministes strictes et inaltérables).
- **Compliance** : Traçabilité totale (100% des logs stockés en base, horodatage systématique).
