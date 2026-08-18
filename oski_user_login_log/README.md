# OdooSkills — Journal des connexions

Odoo retient la date de dernière connexion et rien d'autre. Les tentatives échouées partent dans
le fichier de journal du serveur, que personne n'ouvre.

Ce module tient un registre consultable depuis l'interface : identifiant saisi, utilisateur
reconnu s'il y en a un, réussite ou échec, adresse IP, date. Une rafale d'échecs sur un même
identifiant se voit alors d'un coup d'œil.

**Détail qui compte** : les tentatives sont écrites sur une transaction propre. Un échec
d'authentification annule la transaction de la requête ; une trace posée dedans disparaîtrait
avec elle. Et si le registre lui-même tombe en panne, il n'empêche personne d'entrer : l'incident
part dans le journal du serveur et l'authentification suit son cours.

Le registre est réservé aux administrateurs : il contient des identifiants saisis.

- **Dépendances** : `base`
- **Licence** : LGPL-3
- **Auteur** : OdooSkills — https://apps.odooskills.com
