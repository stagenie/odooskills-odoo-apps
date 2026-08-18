# Moniteur de la file de courriels

Un serveur sortant mal configuré ne fait aucun bruit. Les courriels s'empilent
en `mail.mail`, la file grossit, et personne ne l'apprend avant qu'un client
demande pourquoi il n'a rien reçu. Odoo sait renvoyer un courriel en échec,
mais ne surveille rien.

Une tâche planifiée quotidienne ausculte la file et inscrit son verdict :

- **Saine** — rien en échec, rien qui traîne ;
- **Ralentie** — le plus vieux courriel en attente dépasse le seuil ;
- **En échec** — au moins un courriel est mort.

Chaque relevé garde le nombre d'envois en attente, le nombre d'échecs, l'âge du
plus vieux courriel en attente et la répartition des causes.

## L'alerte ne passe pas par un courriel

Prévenir d'une file de courriels morte **en envoyant un courriel** reviendrait
à confier le diagnostic au malade. L'alerte prend la forme d'une **activité**
posée aux administrateurs : elle se lit dans l'interface, quel que soit l'état
du serveur sortant. La notification que Odoo enverrait normalement à l'assigné
est explicitement coupée, et un test le vérifie.

Une seule alerte reste ouverte à la fois : une panne qui dure des semaines ne
doit pas produire une activité par jour, sinon plus personne ne les lit.

## Réglage

Le paramètre système `oski_mail_queue_monitor.max_pending_hours` fixe le seuil
de la file à l'arrêt (6 heures par défaut).

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
