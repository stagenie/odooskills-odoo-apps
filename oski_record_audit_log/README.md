# OdooSkills — Journal des modifications

Qui a créé, modifié ou supprimé quoi, sur les modèles que vous désignez.

Le suivi natif d'Odoo ne couvre que les champs marqués « tracking » sur les modèles dotés d'un
chatter. Ce module comble le reste : choisissez un modèle, les opérations à suivre et, si vous le
souhaitez, la liste des champs qui comptent.

Chaque ligne porte l'auteur, la date, l'enregistrement et le détail
`ancienne valeur → nouvelle valeur`.

Deux limites assumées :

- les opérations menées en superutilisateur (installation, mise à jour, tâches planifiées) ne
  sont pas journalisées — le registre garde les gestes humains, pas la maintenance ;
- pièces jointes, images et listes liées sont ignorées : leur contenu ne tient pas sur une ligne.

- **Dépendances** : `base`
- **Licence** : LGPL-3
- **Auteur** : OdooSkills — https://apps.odooskills.com
