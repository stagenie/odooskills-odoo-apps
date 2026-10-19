# OdooSkills — Édition en masse

Modifiez un champ sur toute une sélection depuis la vue liste, sans ouvrir chaque fiche.

Un administrateur déclare les modèles concernés (menu **Paramètres › Technique › Édition
en masse**) ; l'entrée apparaît alors dans le menu **Actions** de leur vue liste.

Types pris en charge : texte, texte long, HTML, sélection, entier, décimal, monétaire,
booléen, date, date-heure, relation simple (`many2one`). Tout autre type est refusé par un
message explicite plutôt que converti approximativement.

L'écriture passe par les droits et les règles d'enregistrement de l'utilisateur courant :
le module n'emploie jamais `sudo()`.

- **Dépendances** : `base`
- **Licence** : LGPL-3
- **Auteur** : OdooSkills — https://apps.odooskills.com
