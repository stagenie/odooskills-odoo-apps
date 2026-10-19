# OdooSkills — Garde-fou de suppression

Ferme la suppression modèle par modèle et journalise ce qui est réellement effacé.

- **Interdire, sauf aux groupes autorisés** : personne ne supprime, sauf les groupes que vous
  désignez. Message de refus personnalisable.
- **Autoriser, mais journaliser** : la suppression reste ouverte, la trace est prise.
- **Journal** : modèle, identifiant, nom affiché, auteur, date.

Les opérations menées en superutilisateur — installation, mise à jour, désinstallation, tâches
planifiées — traversent le garde-fou sans être arrêtées : il protège l'interface, pas la
maintenance.

- **Dépendances** : `base`
- **Licence** : LGPL-3
- **Auteur** : OdooSkills — https://apps.odooskills.com
