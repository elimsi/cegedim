# 🏥 CETIP — Workflow d'Automatisation des Bordereaux de Virements SEPA

> **Solution d'ingénierie no-code / low-code pour le traitement automatisé, le contrôle de conformité métier, la génération documentaire PDF et le pilotage analytique des virements aux professionnels de santé.**

---

## 📌 Présentation & Contexte Métier

Développé pour l'équipe **CETIP** (*Tiers Payant Santé — Cegedim Maroc*), opérateur leader gérant plus de 143 millions de factures de santé par an pour 16 millions de bénéficiaires, ce projet modernise la gestion des flux de virements bancaires adressés aux Professionnels de Santé (PS : médecins généralistes, spécialistes, cliniques, pharmacies).

Le système remplace les traitements manuels ou les scripts rigides par un **workflow orchestré sous n8n**, garantissant un contrôle qualité strict (règle du rejet par contagion), l'envoi personnalisé des bordereaux de règlement au format PDF et une observabilité complète dans un Data Mart PostgreSQL relié à **Power BI**.

---

## 🏗️ Vue d'Ensemble de l'Architecture

Le workflow suit un pipeline transactionnel robuste et modulaire :

```
[Fichier Bordereau ASCII] 
       │
       ▼
[Nœud Parser.js] ──────────► Extraction métadonnées & découpage en JSON structuré
       │
       ▼
[Nœud Validators.js] ──────► Contrôles regex stricts & Rejet par Contagion (N° PS)
       │
       ├───► [Branche Rejets] ──► [Rejet.js] ──► rejet.csv ──► Alerte Email Émetteur
       │
       └───► [Branche Valides] ─► [Grouper.js] ──► Gotenberg (PDF) ──► Email Médecin
                                       │
                                       ▼
                             [Nœud Logger.js] ──► PostgreSQL (dim_ps & fact_traitements) ──► Power BI
```

Pour les spécifications techniques complètes, les diagrammes de flux et les détails nœud par nœud, consultez le document d'architecture :  
👉 **[docs/architecture.md](file:///c:/Users/ismai/OneDrive/Desktop/internships/Stage%20cegedim/cetip-bordereau-workflow/docs/architecture.md)**

---

## ⚙️ Prérequis Système

* **n8n** (v1.0+) : Moteur d'orchestration de workflows.
* **PostgreSQL** (v14+) : Base de données relationnelle pour la persistance et l'audit.
* **Gotenberg** (v7+ via Docker) : Moteur headless Chromium pour la conversion HTML $\to$ PDF A4.
* **Python 3.11+** : Pour la génération déterministe des jeux d'essais.
* **Node.js** (v18+) : Pour l'exécution locale des scripts et tests unitaires.
* **Microsoft Power BI Desktop** : Pour l'exploitation des tableaux de bord décisionnels.

---

## 🚀 Guide d'Installation (Étapes pas à pas)

### 1. Cloner ou ouvrir le projet
Positionnez-vous dans le répertoire racine :
```bash
cd cetip-bordereau-workflow
```

### 2. Démarrer le conteneur Gotenberg (Docker)
Gotenberg fournit l'API de conversion haute fidélité du template HTML vers PDF :
```bash
docker run --rm -p 3000:3000 gotenberg/gotenberg:8
```
*Le service sera accessible sur `http://localhost:3000`.*

### 3. Initialiser la base de données PostgreSQL
Exécutez le script d'initialisation du schéma pour créer les tables `dim_ps` et `fact_traitements` ainsi que les index :
```bash
psql -U postgres -d cegedim_db -f db/schema.sql
```

### 4. Importer le Workflow dans n8n
1. Ouvrez votre instance n8n dans le navigateur (`http://localhost:5678`).
2. Allez dans le menu latéral > **Workflows** > Cliquez sur les **3 points** en haut à droite > **Import from File...**.
3. Sélectionnez le fichier **[n8n/workflow_export.json](file:///c:/Users/ismai/OneDrive/Desktop/internships/Stage%20cegedim/cetip-bordereau-workflow/n8n/workflow_export.json)**.
4. Configurez vos identifiants pour les nœuds **PostgreSQL**, **SMTP Email** et **Gotenberg HTTP**.

---

## 🧪 Exécution des Scénarios de Test

### Étape 1 : Génération des jeux d'essais déterministes
Exécutez le générateur Python pour créer l'ensemble des fichiers de test :
```bash
python scripts/generate_test_data.py
```

### Étape 2 : Exécution de la suite de validation
Validez le comportement du moteur de règles et de contagion sur les 5 scénarios :
```bash
node -e "const fs = require('fs'); const { parseBordereau } = require('./src/parser'); const { validateBatch } = require('./src/validators'); const { groupByPS } = require('./src/grouper'); ['test1_all_valid.txt', 'test2_montant_invalid.txt', 'test3_missing_field.txt', 'test4_email_invalid.txt', 'test5_mixed.txt'].forEach(f => { const p = parseBordereau(fs.readFileSync('data/test_scenarios/' + f, 'utf8')); const v = validateBatch(p.rows); const g = groupByPS(v.rows_valides, p); console.log('==============================\nFichier :', f, '\n- Lignes totales :', p.total_lignes, '\n- Lignes valides :', v.rows_valides.length, '(', v.nb_ps_valides, 'PS)\n- Lignes rejetées :', v.rows_rejetees.length, '(PS rejetés:', v.nb_ps_rejetes, ')\n- Groupes PS prêts pour PDF :', g.length); });"
```

---

## 📊 Résultats Attendus par Scénario

| Scénario de Test | Lignes Totales | Lignes Valides | Lignes Rejetées | PS en Rejet | Comportement Métier Validé |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`test1_all_valid.txt`** | 10 | 10 | 0 | Aucun | **Cas Nominal 100% Conforme :** 4 PS validés (`444444444`, `111111111`, `333333333`, `222222222`), 4 PDFs générés, 0 rejet. |
| **`test2_montant_invalid.txt`** | 10 | 8 | 2 | `222222222` | **Rejet par Contagion :** Une ligne du PS `222222222` a un montant `"INVALID"` $\to$ Les 2 opérations de ce praticien sont rejetées dans `rejet.csv`. |
| **`test3_missing_field.txt`** | 10 | 8 | 2 | `333333333` | **Champ Obligatoire Manquant :** Une ligne du PS `333333333` n'a pas d'adresse `@MAIL` $\to$ Rejet complet du PS `333333333`. |
| **`test4_email_invalid.txt`** | 10 | 6 | 4 | `111111111` | **Syntaxe Email Incorrecte :** L'email `"notanemail"` sur le PS `111111111` entraîne le rejet des 4 virements du PS `111111111`. |
| **`test5_mixed.txt`** | 6 | 4 | 2 | `333333333` | **Scénario Mixte Réduit :** 2 PS conformes (`111111111`, `444444444`) traités avec succès et 1 PS (`333333333`) isolé en anomalie. |

---

## 📈 Connexion de Power BI à PostgreSQL

Pour visualiser les 5 indicateurs clés de performance (KPIs) sous **Power BI Desktop** :

1. **Ouvrir Power BI Desktop** > Cliquez sur **Obtenir les données** (*Get Data*) > Sélectionnez **PostgreSQL**.
2. **Paramètres de connexion :**
   * **Serveur :** `localhost:5432` (ou votre hôte PostgreSQL).
   * **Base de données :** `cegedim_db`.
   * **Mode de connectivité :** **DirectQuery** (pour un suivi en temps réel) ou **Import** (pour une performance optimisée).
3. **Sélection des tables :**
   * Cochez `dim_ps` et `fact_traitements`.
4. **Validation du Modèle Relationnel :**
   * Dans l'onglet **Modèle** de Power BI, vérifiez la relation **1 à plusieurs (1:N)** entre `dim_ps.num_ps` (clé primaire) et `fact_traitements.num_ps` (clé étrangère).
5. **Exploitation des 5 Requêtes d'Analyse :**
   * Vous pouvez directement exécuter les requêtes prêtes à l'emploi contenues dans **[db/queries.sql](file:///c:/Users/ismai/OneDrive/Desktop/internships/Stage%20cegedim/cetip-bordereau-workflow/db/queries.sql)** pour construire les visuels suivants :
     1. Jauge de **Taux de Rejet Global** vs Taux de Conformité.
     2. Graphique à barres du **Top 5 des PS en anomalie**.
     3. Diagramme circulaire de la **Répartition des causes de rejet**.
     4. Matrice financière du **Montant total viré par PS**.
     5. Histogramme temporel du **Volume traité par semaine**.

---

## 📂 Structure du Répertoire

```
cetip-bordereau-workflow/
├── CLAUDE.md                    ← Contexte maître & spécifications pour IA / dev
├── README.md                    ← Guide complet d'installation et de documentation
├── data/
│   ├── sample_bordereau.txt     ← Fichier bordereau source fourni
│   └── test_scenarios/          ← 5 jeux d'essais déterministes
│       ├── test1_all_valid.txt
│       ├── test2_montant_invalid.txt
│       ├── test3_missing_field.txt
│       ├── test4_email_invalid.txt
│       └── test5_mixed.txt
├── src/
│   ├── parser.js                ← Découpage ASCII brut -> JSON structuré
│   ├── validators.js            ← Moteur de validation Regex & Rejet par contagion
│   ├── grouper.js               ← Regroupement par N° PS & sommation monétaire
│   ├── rejet.js                 ← Générateur standardisé du fichier rejet.csv
│   ├── pdf_template.html        ← Modèle HTML5/CSS3 d'impression Gotenberg
│   └── logger.js                ← Générateur de requêtes SQL d'audit PostgreSQL
├── db/
│   ├── schema.sql               ← Définition des tables relationnelles & index
│   └── queries.sql              ← 5 requêtes analytiques pour le reporting Power BI
├── scripts/
│   └── generate_test_data.py    ← Script Python de génération des scénarios d'essais
├── n8n/
│   └── workflow_export.json     ← Export JSON complet du workflow n8n prêt à l'emploi
└── docs/
    ├── architecture.md          ← Spécification technique, nœuds n8n & data flow
    └── user_guide.md            ← Manuel d'exploitation et d'administration
```

---

## 👨‍💻 Auteur & Informations Académiques

* **Auteur :** Ismail EL KHOBZI
* **Établissement :** École Supérieure des Industries du Textile et de l'Habillement (**ESITH**)
* **Filière :** Génie Industriel — Spécialisation *Business & Data Management* (B&DM)
* **Organisme d'Accueil :** Cegedim Maroc (*Division Cegedim Insurance Solutions — Équipe Cetip*)
