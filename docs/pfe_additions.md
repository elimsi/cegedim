# Ajouts PFE : Business Case & BPMN

Ce document contient les éléments de langage et de modélisation à intégrer dans votre rapport de stage PFE et vos slides de soutenance.

---

## 1. Modélisation BPMN (AS-IS vs TO-BE)

Ces étapes sont à dessiner sous forme de logigramme (BPMN 2.0) sur un outil comme **draw.io** ou **Lucidchart**.

### 🔴 Processus AS-IS (L'existant / Le traitement manuel)
1. **Événement déclencheur** : Réception du fichier bordereau (Format texte / ASCII).
2. **Tâche Manuelle** : Ouverture du fichier et lecture visuelle.
3. **Tâche Manuelle** : Vérification champ par champ (Montant, format Date, validité Email).
4. **Passerelle (Décision)** : Y a-t-il une anomalie ?
   - *Oui* : Rejet manuel de la ligne, rédaction d'un email de notification au destinataire.
   - *Non* : Continuer.
5. **Tâche Manuelle** : Groupement des virements par Professionnel de Santé (PS) sur Excel.
6. **Tâche Manuelle** : Création d'un PDF récapitulatif via un outil tiers ou Word.
7. **Tâche Manuelle** : Envoi de l'email avec le PDF en pièce jointe au médecin.
8. **Fin du processus**.

### 🟢 Processus TO-BE (Le système automatisé n8n + ML)
1. **Événement déclencheur** : Dépôt du fichier dans l'interface ou réception automatique.
2. **Script Auto (Parser)** : Parsing et structuration des données en JSON.
3. **Script Auto (Validators)** : Vérification Regex de tous les champs.
4. **Script Auto (ML Scoring)** : Modèle *Isolation Forest* pour scorer la probabilité de fraude sur les montants.
5. **Passerelle Automatique** : Présence de rejets par contagion ou fraude ?
   - *Oui* : Génération du `rejet.csv` et alerte email envoyée automatiquement à l'émetteur.
   - *Non* : Groupement automatique par PS.
6. **Service Auto (Gotenberg)** : Génération dynamique des reçus PDF.
7. **Service Auto (SMTP)** : Envoi asynchrone des emails aux PS avec les PDF.
8. **Base de données (PostgreSQL)** : Journalisation sécurisée des statuts (Audit & Traçabilité).
9. **Fin du processus**.

---

## 2. Analyse ROI (Return on Investment) & Business Case

Voici le texte analytique à inclure dans le chapitre "Bilan du Projet" ou "Analyse de la Valeur" de votre rapport :

### Contexte
La gestion des bordereaux de virements pour les professionnels de santé par la CETIP engendre une charge opérationnelle récurrente, sujette à l'erreur humaine. L'implémentation de la solution automatisée (n8n + Python ML + PostgreSQL) permet de passer d'une gestion curative à une gestion prédictive et standardisée.

### Modélisation du Coût Avant Automatisation (AS-IS)
- **Temps de traitement manuel moyen par fichier** : ~45 minutes (Vérification visuelle, Excel, manipulation PDF, emails).
- **Fréquence estimée** : 20 fichiers traités par mois.
- **Coût horaire chargé du gestionnaire** : ~80 MAD / heure.
- **Taux d'erreur manuel (qualité)** : Estimé à 8% (nécessitant des retraitements coûteux).
- **Coût opérationnel direct** : 20 fichiers × 0,75 heures × 80 MAD = **1 200 MAD / mois** (hors coûts indirects liés aux erreurs de saisie).

### Modélisation du Coût Après Automatisation (TO-BE)
- **Temps de traitement machine par fichier** : ~2 minutes (Processus 100% asynchrone).
- **Supervision humaine requise** : ~5 minutes par fichier (exclusivement pour auditer les cas bloquants / alertes ML).
- **Taux d'erreur de traitement** : ~0% (Grâce au moteur de règles Regex déterministes et au rejet par contagion).
- **Nouveau Coût opérationnel direct** : 20 fichiers × 0,083 heures × 80 MAD = **~133 MAD / mois**.

### Bilan Financier et Valeur Ajoutée (Gains)
1. **Gain Financier Direct** : Économie de **1 067 MAD / mois** (soit environ **12 800 MAD / an** pour ce seul flux).
2. **Gain de Productivité** : **89%** de réduction du temps de traitement (15 heures économisées par mois).
3. **Prévention des Fraudes (ML Layer)** : La détection d'anomalies sur les montants via l'algorithme *Isolation Forest* ajoute un contrôle de conformité critique. Ce gain est difficilement quantifiable financièrement mais est stratégique pour l'agrément PSP (Prestataire de Services de Paiement) de la CETIP.
4. **Pilotage Data-Driven** : La mise en place de la supervision en temps réel (via Streamlit/Power BI) transforme une boîte noire opérationnelle en un processus transparent et auditable.
