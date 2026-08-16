# Projet : Automatisation et Détection de Fraude pour les Bordereaux de Virement (CETIP)

## 1. Contexte
Ce projet s'inscrit dans le cadre d'un stage de fin d'études (PFE) réalisé au sein de la **CETIP** (groupe Cegedim), acteur majeur du tiers-payant. La CETIP gère quotidiennement d'importants volumes de facturation et de remboursements pour le compte des professionnels de santé (PS).
Une des tâches clés de ce processus est le traitement des **bordereaux de virement**, qui actent les paiements émis vers les professionnels de santé suite à leurs actes médicaux.

## 2. La Problématique (Processus AS-IS)
Actuellement, le traitement de ces bordereaux souffre de plusieurs points de douleur majeurs :
* **Traitement Manuel et Chronophage** : Le processus nécessite une intervention humaine importante pour lire les fichiers, valider les données, identifier les erreurs de format (rejets), et générer des documents de retour. (Estimation : ~45 min par bordereau).
* **Risque d'Erreur Humaine** : La validation manuelle des lignes (montants, actes, IBAN) est sujette à des erreurs, nécessitant souvent des retraitements coûteux.
* **Absence de Détection de Fraude Proactive** : Face à des volumes importants, il est impossible pour un humain de détecter des anomalies subtiles (ex: un professionnel de santé qui facture soudainement des montants inhabituellement élevés par rapport à son historique). La fuite de capitaux vers des facturations abusives ou frauduleuses est un risque financier direct.
* **Manque de Visibilité (Observabilité)** : Il n'y a pas de tableau de bord en temps réel permettant à la direction de suivre les flux financiers, le taux de rejet (*Clean Claim Rate*), ou les alertes en cours.

## 3. La Solution Proposée (Processus TO-BE)
La solution développée est un **Pipeline de bout-en-bout (Workflow) automatisé et intelligent**, intégrant une brique d'Intelligence Artificielle pour la détection des anomalies. 

Le nouveau système permet de :
1. **Ingérer et Valider automatiquement** les fichiers texte des bordereaux entrants.
2. **Filtrer les Rejets** (erreurs de format, données manquantes) et générer automatiquement un rapport CSV pour l'émetteur.
3. **Détecter la Fraude par IA** : Chaque ligne valide passe par un modèle de Machine Learning (Isolation Forest) qui compare le comportement de facturation actuel du PS par rapport à son historique afin de lever des alertes sur les transactions suspectes.
4. **Générer des PDF Professionnels** : Pour chaque PS validé, un reçu PDF structuré est généré automatiquement puis envoyé par email.
5. **Monitorer en Temps Réel** : Une application web permet aux analystes d'inspecter les alertes de fraude, de valider les faux positifs, et de visualiser les KPI financiers.

## 4. Architecture Technologique
La solution repose sur une stack moderne, 100% Open Source et micro-services (orchestrée via Docker) :
* **n8n (Orchestration)** : Le moteur de workflow qui pilote l'ensemble du processus (lecture de fichier, exécution de scripts JS pour le parsing/grouping, appels API, envois d'emails).
* **Python / FastAPI & Scikit-Learn (Moteur ML)** : Un micro-service dédié exposant l'algorithme d'Isolation Forest pour scorer chaque transaction de manière isolée.
* **PostgreSQL (Data Warehouse)** : Base de données modélisée en étoile (Kimball Star Schema) pour stocker les faits financiers (`fact_traitements`) et les dimensions (`dim_ps`, `dim_actes`, `dim_date`).
* **Streamlit (Fraud Investigator Dashboard)** : Interface utilisateur interactive offrant une vue temps réel et un outil d'investigation des transactions suspectes.
* **Gotenberg** : API pour la conversion de templates HTML dynamiques en PDF de qualité professionnelle.

## 5. Valeur Créée & Alignement Stratégique
* **Réduction drastique des coûts opérationnels** : Le temps de traitement passe d'environ 45 minutes (manuel) à ~2 minutes (automatisé), représentant une réduction des coûts de gestion d'environ 90%.
* **Valeur défensive** : Le modèle IA agit comme un filet de sécurité proactif, bloquant ou signalant les sur-facturations avant validation définitive.
* **Alignement Stratégique** : Cette barrière de défense de premier niveau, légère et réactive, complémente parfaitement les outils de détection de fraude complexes à large échelle (comme Shift Technology), en sécurisant spécifiquement la chaîne de facturation automatisée au quotidien.
