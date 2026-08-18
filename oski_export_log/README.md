# OdooSkills — Journal des exports

Odoo ne propose qu'un interrupteur : le groupe **Autoriser l'export** est donné, ou il ne l'est
pas. Une fois donné, plus rien n'est su.

Ce module inscrit chaque export réellement exécuté — auteur, modèle, champs demandés, nombre de
lignes produites, date — quel que soit le format (Excel ou CSV : les deux passent par la même
méthode `export_data`).

Il n'empêche rien et ne ralentit rien. Un export refusé faute de droits ne produit aucune ligne :
le journal ne recense que ce qui a réellement quitté la base.

- **Dépendances** : `base`
- **Licence** : LGPL-3
- **Auteur** : OdooSkills — https://apps.odooskills.com
