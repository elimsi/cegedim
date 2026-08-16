# Architecture Système — CETIP Bordereau Workflow

## 1. Vue Globale de l'Architecture (Les 4 Couches)

```text
[ SOURCE ]                   [ LAYER 1: AUTOMATION ]                     [ DESTINATIONS ]
bordereau.txt  --------->    n8n Workflow Engine      -----------------> PS (Emails + PDF)
(Pipe-delimited)            /                   \                        Émetteurs (Rejets)
                           /                     \
                          /                       \
                         v                         v
               [ LAYER 2: INTELLIGENCE ]    [ LAYER 3: STOCKAGE ]
               FastAPI + scikit-learn        PostgreSQL (Star Schema)
               (IsolationForest / Z-Score)   (fact_traitements, dim_ps...)
                                                   |
                                                   |
                                                   v
                                            [ LAYER 4: VISUALISATION ]
                                            Streamlit (Live Dashboard)
                                            Power BI (Reporting)
```

## 2. Séquence des Nœuds du Workflow n8n

Le flux d'orchestration suit un modèle de "Pipeline de Traitement Déterministe" :

```text
[Watch Folder] 
      ↓
[Read File] 
      ↓
[Code: Parser (src/parser.js)]
      ↓
[Code: Validators (src/validators.js)]
      ↓
[IF: has_rejets?]
   ├── (YES) 
   │    ├── [Code: Rejet Builder (src/rejet_builder.js)]
   │    ├── [Write File: rejet.csv]
   │    └── [Send Email: émetteur (Alerte d'anomalie de format)]
   │
   └── (NO / CONTINUES)
        ├── [Code: Grouper (src/grouper.js)]
        └── [SplitInBatches: one PS at a time] ↻ Boucle sur chaque médecin
                  │
                  ├── [HTTP Request: FastAPI /predict-anomaly] (Scoring ML)
                  ├── [HTTP Request: Gotenberg PDF] (Génération dynamique)
                  ├── [Send Email: PS with PDF attachment]
                  └── [PostgreSQL: INSERT fact_traitements] (Logger la transaction)
        
        ↓ (Sortie de boucle)
[Code: Logger summary] (Rapport global d'exécution)
```

## 3. Modèle de Machine Learning (Détection de Fraude)

Le Layer 2 (FastAPI) expose le point d'accès `/predict-anomaly` appelé par n8n.

### Ingénierie des Caractéristiques (Feature Engineering)
Le modèle est entraîné sur le comportement **spécifique de chaque Professionnel de Santé (PS)** (ou sa spécialité en l'absence de données).
Trois dimensions principales :
- `montant` : Valeur totale de la transaction.
- `nb_actes` : Volume de prestations médicales liées.
- `montant_par_acte` : Variable dérivée (`montant / nb_actes`), un traceur redoutable pour détecter des surfacturations unitaires discrètes.

### Comparaison des Méthodes
| Méthode | Fonctionnement | Cas d'Application Privilégié |
|---------|----------|----------|
| **Z-Score** | Modèle paramétrique mesurant la distance à la moyenne historique. | Ultra-rapide. Identifie immédiatement les anomalies extrêmes "Hard" (`|z| > 3`). Exemple : Erreur de saisie rajoutant un zéro. |
| **Isolation Forest** | Modèle non paramétrique (Arbres d'isolation). Isole les anomalies géométriques. | Détecte les anomalies "douces" et multidimensionnelles sans présumer une distribution normale. Exemple : Un montant normal, mais inhabituel pour un faible nombre d'actes. |

### Flux de Décision
1. **Vérification de l'historique** : Si l'historique est < 10 transactions, renvoie `HISTORIQUE_INSUFFISANT`.
2. **Fast Path (Z-Score)** : Évalue l'écart. Si l'anomalie est évidente et colossale, renvoie immédiatement `ANOMALIE` (gain de puissance de calcul).
3. **Deep Path (Isolation Forest)** : Si le comportement est subtil, le modèle est ajusté dynamiquement (contamination=0.05, n_estimators=100) pour scorer l'enregistrement sur les 3 dimensions de Feature Engineering.

## 4. Modèle de Données (Entity-Relationship Diagram)

La couche de stockage (PostgreSQL) adopte une architecture décisionnelle **Kimball (Star Schema)**.

```text
       +-------------------+
       |    dim_actes      |
       +-------------------+
       | PK code_acte      |
       |    libelle        |
       |    categorie      |
       +---------+---------+
                 |
                 | 1:N
                 v
       +-----------------------------+           +-------------------+
       |     fact_traitements        |           |      dim_ps       |
       +-----------------------------+    N:1    +-------------------+
       | PK id                       |---------->| PK num_ps         |
       | FK date_vir_id              |           |    email          |
       | FK date_soin_id             |           |    intitule       |
       | FK num_ps                   |           |    specialite     |
       | FK code_acte                |           |    region         |
       |    num_virement             |           |    bic            |
       |    montant                  |           |    iban           |
       |    nb_actes                 |           +-------------------+
       |    statut (VALIDE/REJETE)   |
       |    raison_rejet             |
       |    flag_anomalie (ML)       |           +-------------------+
       |    score_anomalie (ML)      |           |    dim_date       |
       |    ecart_vs_historique      |    N:1    +-------------------+
       |    fichier_source           |---------->| PK date_id        |
       +-----------------------------+           |    jour           |
                                                 |    mois           |
       +-----------------------------+           |    trimestre      |
       |  historical_traitements     |           |    annee          |
       +-----------------------------+           |    semaine        |
       | (Données d'entraînement)    |           +-------------------+
       +-----------------------------+
```

## 5. Couche Ingénierie Business & Data Management (B&DM)

L'intérêt majeur du projet réside dans sa traduction de la technique vers la valeur d'entreprise (Business Value).

### Approche Méthodologique BPMN
Pour assurer la conformité d'une infrastructure PSP (Prestataire de Services de Paiement) :
- **AS-IS** : Modélisation des goulots d'étranglement de la vérification manuelle (retards, erreurs de manipulation, risque de non-conformité).
- **TO-BE** : Modélisation du workflow n8n en tant qu'orchestrateur asynchrone central. Le BPMN 2.0 vient cartographier la délégation totale des décisions déterministes à la machine, garantissant l'auditabilité.

### Quantification du Retour sur Investissement (ROI)
Le pont entre le code développé et les KPIs de la Direction :
1. **Productivité** : Remplacement de la charge manuelle (45 min/fichier) par un pipeline asynchrone ultra-rapide (< 2 minutes machine), libérant le temps des gestionnaires CETIP pour de l'analyse décisionnelle à haute valeur ajoutée.
2. **Gestion du Risque (Compliance)** : La tolérance zéro aux erreurs de format imposée par `src/validators.js` (Règle de Contagion) et l'ajout du module prédictif IA (Fraud Investigator) renforcent activement l'agrément financier de la CETIP.
3. **Pilotage des Flux de Trésorerie (Observabilité)** : L'application Streamlit ne se contente pas de montrer des requêtes SQL ; elle rend le *Clean Claim Rate* et les anomalies directement transparentes pour les équipes de supervision, accélérant le temps de traitement des litiges.
