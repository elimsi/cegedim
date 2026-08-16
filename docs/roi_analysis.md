# Analyse de Retour sur Investissement (ROI)

Ce document présente le *Business Case* formel du projet d'automatisation des bordereaux CETIP. Il confronte les coûts d'opérationnalisation du processus manuel actuel (AS-IS) à la rentabilité du système automatisé n8n + ML (TO-BE).

## 1. Quantification de la Problématique (Processus AS-IS)

Basé sur les données métiers existantes, nous avons établi la modélisation suivante pour un volume représentatif :
- **Temps de traitement manuel** : ~45 min par fichier de bordereau.
- **Fréquence de réception** : ~20 bordereaux par mois (Hypothèse de base).
- **Coût horaire chargé du Gestionnaire** : 80 DH/heure.
- **Taux d'erreur humaine estimé** : ~8% (oublis, mauvais copier-coller).
- **Coût d'une erreur (Retraitement manuel/litiges)** : Temps de correction estimé à ~1h (soit 80 DH) par bordereau erroné.

### Calcul du coût mensuel AS-IS :
- **Coût de traitement nominal** : 20 bordereaux × (45 min / 60) × 80 DH/h = **1 200 DH / mois**.
- **Coût des anomalies/retraitements** : (20 bordereaux × 8%) = 1,6 bordereaux avec erreur. 1,6 × 80 DH = **128 DH / mois**.
- **COÛT TOTAL AS-IS : 1 328 DH / mois.**

---

## 2. Performance de la Solution Proposée (Processus TO-BE)

L'introduction de n8n, du script Python de Machine Learning et du tableau de bord Streamlit transforme radicalement l'équation.

- **Temps de traitement machine** : ~2 minutes par bordereau (Coût humain : 0 DH, traitement asynchrone par le serveur).
- **Temps de révision humaine (Investigateur Fraude)** : Seules les transactions flagguées `ANOMALIE` requièrent une intervention. 
  - Hypothèse : Taux d'alerte ML = 5%. Pour 20 bordereaux (générant par exemple 50 alertes à travers tous les PS) : 50 alertes × 2 min de révision sur le Dashboard = 100 min = 1,66 h.
  - Coût : 1,66h × 80 DH = **133 DH / mois**.
- **Taux d'erreur de formatage/envoi** : 0% (Assuré par la rigueur déterministe de `validators.js`).

### Calcul du coût mensuel TO-BE :
- **Coût de traitement nominal** : **0 DH / mois** (Automatisé).
- **Coût de supervision Fraude** : **133 DH / mois**.
- **Coût des anomalies de saisie** : **0 DH / mois**.
- **COÛT TOTAL TO-BE : 133 DH / mois.**

---

## 3. Tableau Récapitulatif du ROI

| Indicateur | AS-IS (Manuel) | TO-BE (Automatisé) | Gain net |
|------------|----------------|--------------------|----------|
| **Temps d'exécution** | 15 heures / mois | ~0h (traitement) + 1,6h (supervision) | **+13,4 h libérées/mois** |
| **Coût financier (RH)**| 1 328 DH / mois | 133 DH / mois | **~90% de réduction** |
| **Taux d'erreur** | 8 % | 0 % | Fiabilisation totale |
| **Délai de notification**| J+1 à J+3 | Temps réel (quelques minutes) | Expérience Client (PS) optimale |

*(Note : Si le volume d'entrée passe de 20 à 200 bordereaux/mois, le coût manuel explose proportionnellement à 13 280 DH/mois, tandis que l'architecture technique, étant scalable, n'augmentera que légèrement le temps de révision des alertes).*

---

## 4. Gains Non Quantifiables (Valeur Stratégique)

L'impact de ce projet dépasse la simple réduction des coûts horaires :

1. **Auditabilité Réglementaire (PSP Compliance)** : Le processus permet une stricte conformité vis-à-vis des autorités financières. L'ingénierie de la base de données (couche 3) enregistre des logs immuables (`fact_traitements`) pour prouver l'exactitude des opérations, ce qui est impossible avec l'envoi de PDF manuels.
2. **Détection Active de la Fraude** : Le couplage avec l'intelligence artificielle (Isolation Forest) permet d'endiguer la fuite de capitaux vers des prestataires frauduleux (sur-facturation indue), protégeant directement les fonds de roulement de la CETIP.
3. **Observabilité Décisionnelle** : Grâce à l'application `app.py`, la Direction Générale dispose pour la toute première fois d'une visibilité en temps réel sur les flux financiers (*Clean Claim Rate*, volume traité) via la télémétrie.
4. **Agilité Technologique** : Le système repose sur des technologies modernes sans licences restrictives (Open Source : n8n, Python FastAPI, PostgreSQL).

---

## 5. Conclusion & Alignement Stratégique

### Valeur Créée (Économie Annuelle Estimée)

Ce projet, développé dans le cadre d'un stage PFE (investissement en temps humain, coût d'infrastructure quasi-nul grâce à l'Open Source), génère une **valeur opérationnelle immédiate** dès son déploiement :

| Métrique | Calcul | Résultat |
|----------|--------|----------|
| **Coût annuel actuel** (AS-IS) | 1 328 DH/mois × 12 | **15 936 DH/an** |
| **Coût annuel automatisé** (TO-BE) | 133 DH/mois × 12 | **1 596 DH/an** |
| **Économie annuelle nette** | 15 936 − 1 596 | **14 340 DH/an** |
| **Taux de réduction** | 14 340 / 15 936 | **~90%** |

À cela s'ajoute la **valeur défensive** (fraudes détectées et bloquées) qui est difficilement quantifiable mais potentiellement supérieure à l'économie opérationnelle.

### Alignement Stratégique

Cette approche algorithmique s'aligne de manière extrêmement pertinente avec **le partenariat stratégique récent de la CETIP avec Shift Technology**. Alors que Shift Technology couvre l'identification de fraudes macro-complexes (réseaux organisés), le *Fraud Investigator* construit en interne constitue une première barrière de défense, légère et réactive, spécifiquement calibrée pour traiter et fiabiliser la chaîne de facturation automatisée au quotidien.

