# Moniteur des tâches planifiées

Odoo enregistre la date du dernier passage d'une tâche planifiée dans
`lastcall`, et le nombre d'échecs consécutifs dans `failure_count`. Aucun des
deux n'apparaît dans une vue. Une tâche qui échoue toutes les nuits ne se voit
donc que dans le journal du serveur.

Ce module inscrit chaque exécution — début, durée, réussite ou échec, message
d'erreur complet — et les rend consultables :

- onglet **Exécutions** sur la tâche planifiée elle-même ;
- menu **Paramètres → Technique → Automatisation → Exécutions planifiées**,
  filtrable sur les seuls échecs et groupable par tâche.

## Ce qui mérite d'être su

Le journal s'écrit **sur une transaction distincte**. `ir.cron._callback`
annule la transaction de la tâche quand celle-ci lève : une trace posée dedans
disparaîtrait avec elle, or l'échec est précisément ce qu'il faut garder.

L'écriture ne peut jamais faire échouer une tâche qui a réussi : une panne du
registre part dans le journal du serveur et la tâche aboutit.

Les exécutions sont purgées au-delà de 30 jours par le nettoyage automatique
d'Odoo. Le paramètre système `oski_cron_monitor.retention_days` change ce
délai ; `0` conserve tout.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
