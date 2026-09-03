# Taux de change automatiques

Odoo Community sait tenir un tableau de taux de change ; il ne sait pas le
remplir. Chaque matin quelqu'un recopie donc des taux à la main, ou personne ne
le fait et les conversions dérivent en silence.

Une tâche planifiée quotidienne va chercher les taux de référence publiés par
la **Banque centrale européenne** et les inscrit pour chaque société qui l'a
demandé. Pas de clé d'interface, pas de compte à ouvrir : la BCE publie ses
taux librement.

## Ce qui mérite d'être su

- **La tâche dort tant que personne ne l'a demandée.** Cocher la case sur une
  société l'active ; la décocher partout l'éteint. Un module installé n'appelle
  pas la BCE toutes les nuits sans consentement.
- **La devise de la société est le pivot**, quelle qu'elle soit. La BCE publie
  en euro ; le module fait la division. Une société en dollar obtient bien des
  taux vus depuis le dollar.
- **Un seul taux par devise et par jour** : une seconde exécution corrige celui
  du jour au lieu d'en ajouter un.
- Les devises **inactives** sont laissées de côté, et celles absentes du flux
  passent leur tour sans faire échouer le reste.
- **Une société en panne n'arrête pas les autres** : l'erreur est inscrite sur
  la société — un message dans le journal du serveur ne se lit pas depuis
  l'interface.

Onglet **Taux de change** sur la fiche de la société, avec un bouton pour une
mise à jour immédiate.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
