# 📖 Guide Utilisateur — Traitement Automatisé des Bordereaux CETIP

Ce guide simple vous explique pas à pas comment utiliser le système automatique de traitement des bordereaux de virements pour les Professionnels de Santé (médecins, cliniques, pharmacies).

---

## 1. Démarrer l'Application

Avant de lancer un traitement, assurez-vous que les services sont actifs sur votre poste ou votre serveur.

1. **Ouvrez votre navigateur internet** (Google Chrome, Microsoft Edge ou Firefox).
2. Saisissez l'adresse de votre espace de travail : `http://localhost:5678` (ou l'adresse fournie par votre équipe informatique).
3. Connectez-vous avec vos identifiants si nécessaire.

[SCREENSHOT: Écran de connexion et tableau de bord principal de n8n avec la liste des workflows]

---

## 2. Déposer le Fichier Bordereau

Le système a besoin de lire votre fichier texte contenant les ordres de virement.

1. Récupérez votre fichier bordereau (par exemple : `SEPA_ETAT.VIREMENT.txt` ou `sample_bordereau.txt`).
2. Déposez ce fichier dans le dossier partagé prévu à cet effet :
   * **Dossier d'entrée :** `data/`
3. Vérifiez simplement que le fichier porte bien une extension `.txt` ou `.OK` et qu'il n'est pas ouvert dans un autre logiciel (comme le Bloc-notes).

[SCREENSHOT: Explorateur de fichiers montrant le fichier bordereau déposé dans le répertoire data/]

---

## 3. Lancer le Traitement Automatique

1. Dans votre navigateur, ouvrez le workflow intitulé **`CETIP — Bordereau de Virements Workflow`**.
2. En bas de l'écran, cliquez sur le bouton orange **« Test Workflow »** (ou **« Execute Workflow »**).
3. Observez l'avancement : les étapes s'illuminent en vert au fur et à mesure de l'analyse.

[SCREENSHOT: Bouton d'exécution en bas de n8n et nœuds du workflow devenant verts lors de l'exécution]

> ⏱️ *Durée du traitement :* Pour un fichier standard d'une centaine de lignes, l'opération prend entre **5 et 15 secondes**.

---

## 4. Comprendre les Emails Envoyés et Reçus

À la fin de l'exécution, deux types d'emails peuvent être envoyés automatiquement selon le contenu de votre fichier :

### 🟢 A. Pour les Médecins / Professionnels de Santé (Dossiers Validés)
* **Destinataire :** L'adresse email du praticien (ex: `docteur.dupont@gmail.com`).
* **Objet :** *« CETIP - Votre bordereau de règlement de virements Tiers Payant »*.
* **Contenu :** Un message de confirmation avec le montant total viré et son récapitulatif officiel en pièce jointe au format **PDF**.

[SCREENSHOT: Exemple de l'email reçu par le médecin avec le document PDF officiel en pièce jointe]

### 🔴 B. Pour le Gestionnaire Émetteur (En cas de Rejets)
* **Destinataire :** L'adresse de l'émetteur indiquée en haut du bordereau.
* **Objet :** *« ALERTE CETIP : Rejets détectés lors du traitement du bordereau »*.
* **Contenu :** Un message d'alerte vous indiquant le nombre de lignes bloquées avec le fichier **`rejet.csv`** joint pour correction.

[SCREENSHOT: Exemple de l'email d'alerte reçu par l'équipe de gestion avec le fichier rejet.csv joint]

---

## 5. Comment Lire et Interpréter le Fichier `rejet.csv` ?

Si un praticien a des informations incorrectes, **toutes ses opérations sont mises de côté** pour éviter tout risque de paiement partiel ou erroné.

Ouvrez le fichier `rejet.csv` avec Microsoft Excel :

| Colonne | Signification | Ce qu'il faut vérifier |
| :--- | :--- | :--- |
| **NUM_PS** | Numéro du professionnel de santé | Vérifiez que le numéro de praticien existe. |
| **EMAIL** | Adresse email de contact | Vérifiez qu'il y a bien un `@` et un point (ex: `nom@domaine.fr`). |
| **BIC / IBAN** | Coordonnées bancaires | Contrôlez le compte bancaire du professionnel. |
| **MONTANT** | Montant de la prestation | Le montant doit comporter une virgule pour les centimes (ex: `256,00`). |
| **DATE_VIR** | Date du virement | Doit être au format 8 chiffres (AnnéeMoisJour : ex `20260805`). |
| **RAISON_REJET** | **Cause exacte du blocage** | **Lisez attentivement cette case pour comprendre l'anomalie.** |

[SCREENSHOT: Tableau Excel montrant le fichier rejet.csv ouvert avec les colonnes en surbrillance]

### Les 2 types de messages dans `RAISON_REJET` :
1. **L'erreur directe :** Par exemple *« Format Montant invalide »* ou *« Email invalide »*.
2. **Le rejet par protection (contagion) :** *« Rejet par contagion : une autre ligne du PS est en anomalie »*.  
   *(Explication : Si un médecin a 4 virements et que le 1er a une erreur, les 4 sont suspendus ensemble pour vérification).*

---

## 6. Que Faire si le Traitement Rencontre un Problème ?

Si un nœud apparaît en rouge ou si le traitement ne démarre pas :

1. **Vérifiez que le fichier est bien présent :** Assurez-vous que le fichier n'a pas été supprimé ou déplacé du dossier `data/`.
2. **Vérifiez votre connexion à la base de données :** Si le nœud *PostgreSQL* est rouge, vérifiez que le serveur de base de données est bien allumé.
3. **Consultez l'historique d'exécution :**
   * Cliquez sur **« Executions »** dans le menu de gauche de n8n.
   * Cliquez sur la ligne en rouge pour voir le message d'erreur précis.
4. **Contactez l'assistance :** Transmettez une capture d'écran du message d'erreur à votre administrateur technique ou à l'équipe Data.

[SCREENSHOT: Onglet Executions de n8n permettant de visualiser les détails d'un échec]
