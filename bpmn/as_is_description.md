# Modélisation BPMN : Processus AS-IS (Manuel)

Ce document fournit la description textuelle détaillée pour la création du diagramme BPMN du processus de traitement des bordereaux tel qu'il existe actuellement (Avant automatisation).

## Paramètres du Modèle
- **Format** : Pool unique (CETIP) avec 3 Swimlanes, plus des pools externes (Émetteur, PS).
- **Temps de traitement estimé** : ~45 minutes par bordereau.

## Swimlanes (Couloirs d'activités)
1. **Émetteur (Mutuelle / Assureur)**
2. **Gestionnaire CETIP (Back-Office)**
3. **Professionnel de Santé (PS)**

## Séquence des Étapes

### Phase d'entrée
1. **Émetteur** : Envoie le fichier de bordereau `bordereau.txt` par email.
2. **Gestionnaire CETIP** : [Événement de début] Réception de l'email contenant le fichier.
3. **Gestionnaire CETIP** : Télécharge le fichier manuellement sur son poste.
   - *Pain Point ⚠️ : Perte de temps (2 min)*

### Phase de vérification
4. **Gestionnaire CETIP** : Ouvre le fichier `.txt` avec Excel (conversion texte en colonnes).
   - *Pain Point ⚠️ : Risque d'erreur de formatage des données, notamment sur les montants et les numéros de PS commençant par des zéros (5 min).*
5. **Gestionnaire CETIP** : Vérifie visuellement la présence des colonnes obligatoires (N° PS, IBAN, Montant).
   - *Passerelle (XOR) : Fichier valide ?*
   - *Non* : Rédaction d'un email d'erreur manuel à l'Émetteur (10 min). [Fin du processus pour ce fichier].
   - *Oui* : Poursuite du processus.

### Phase d'agrégation et calculs
6. **Gestionnaire CETIP** : Filtre Excel par N° PS et calcule la somme des montants (Tableau croisé dynamique).
   - *Pain Point ⚠️ : Calcul manuel, fort risque d'erreur humaine (10 min).*

### Phase de communication
7. **Gestionnaire CETIP** : Ouvre Word, copie-colle les montants et numéros de virement dans un template de lettre pour le PS.
   - *Pain Point ⚠️ : Travail très répétitif et non valorisant (15 min).*
8. **Gestionnaire CETIP** : Sauvegarde la lettre en PDF.
9. **Gestionnaire CETIP** : Cherche l'adresse email du PS, rédige le mail, joint le PDF et l'envoie.
   - *Pain Point ⚠️ : Risque d'envoyer le PDF d'un PS à un autre (fuite de données médicales/bancaires).*

### Phase d'historisation
10. **Gestionnaire CETIP** : Saisit manuellement les statistiques du jour dans un fichier Excel de suivi. (3 min)
11. **Gestionnaire CETIP** : [Événement de fin] Processus terminé.

---

## Bilan des Pain Points (AS-IS)
- **Coût temporel** : 45 minutes de travail ininterrompu par bordereau.
- **Taux d'erreur** : Estimé à 8% (erreur de copier-coller, oubli d'une ligne lors du calcul de la somme).
- **Risque Compliance** : Non-conformité avec les normes d'audit des prestataires de services de paiement (pas de log inaltérable, manipulation manuelle des données sensibles).
