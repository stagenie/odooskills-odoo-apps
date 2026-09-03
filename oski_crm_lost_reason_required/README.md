# Motif de perte obligatoire

Dans Odoo 19, `crm.lead.lost.lost_reason_id` n'est pas requis : l'assistant
affiche le champ, personne n'est obligé de le remplir. Six mois plus tard, la
moitié du pipeline perdu est sans explication.

## Ce qui mérite d'être su

**L'exigence se pose sur le modèle**, dans `action_set_lost`, et pas seulement
sur l'assistant : un import, une action serveur ou un appel direct passent par
là aussi. L'assistant, lui, annonce la règle à l'écran — la découvrir après
avoir rempli le formulaire serait une brimade.

Le refus **nomme chaque opportunité fautive**. Perdre en masse et se voir
refuser sans savoir laquelle bloque obligerait à essayer une par une.

Perdre une opportunité l'**archive** : tout décompte qui l'ignorerait
afficherait zéro. Les agrégats du module lisent donc avec `active_test=False`.

Le motif porte enfin ce qu'il coûte : Odoo compte les opportunités par motif,
il ne dit pas ce que chacun emporte. « Prix trop élevé » sur deux affaires de
mille euros et sur une de deux cent mille n'appelle pas la même réaction.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
