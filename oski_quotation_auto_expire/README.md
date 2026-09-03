# Devis périmés

Odoo calcule une date de validité sur chaque devis, sait dire qu'il est expiré
(`is_expired`)… et n'en fait rien : aucune tâche planifiée ne s'en occupe. Les
devis morts s'empilent dans le tunnel, faussent les prévisions, et personne ne
les rouvre jamais.

## Ce qui mérite d'être su

**La relance passe avant la péremption**, dans la même nuit et dans cet ordre.
Un devis relancé le matin puis annulé le soir ferait passer le vendeur pour un
menteur auprès de son client.

**La relance est une activité, jamais un courriel.** Le vendeur vit dans Odoo ;
une activité se retrouve dans sa liste du jour, là où un courriel de plus se
perd. Le contexte `mail_activity_quick_update=True` coupe la notification que
le cœur enverrait à l'assigné.

Les deux réglages sont **indépendants** : on peut vouloir être prévenu sans
laisser Odoo annuler quoi que ce soit. Ils vivent sur la société — une filiale
qui vend à la semaine et une maison mère qui vend au trimestre n'ont pas le
même rythme.

Un devis **verrouillé** n'est jamais touché, un devis **confirmé** non plus :
seuls les états brouillon et envoyé sont concernés. L'annulation laisse au
dossier une note qui dit quand et pourquoi — sans elle, une annulation nocturne
passe pour une manipulation.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
