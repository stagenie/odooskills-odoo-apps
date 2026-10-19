# Analytique obligatoire par journal

Odoo 19 sait **déjà** rendre l'analytique obligatoire : l'applicabilité des
plans analytiques (`account.analytic.applicability`) l'exige par domaine
d'activité, par préfixe de compte et par catégorie d'article, et la vérifie à
la comptabilisation via `_validate_distribution`.

Ce module ne refait pas ce travail. Il ajoute les deux choses qui manquent :

- le **journal** comme critère — c'est ainsi que raisonnent la plupart des
  cabinets, et le cœur ne le propose pas ;
- le **moment** : un écran qui liste, parmi les brouillons, les lignes qui
  bloqueront, au lieu de découvrir le refus une fois la saisie finie.

## Ce qui mérite d'être su

🚨 **La règle ne se réécrit pas en domaine, elle se rejoue.**
`analytic_distribution` est un champ JSON doté de sa propre méthode de
recherche, qui ne comprend que « contient tel compte » : lui demander « est
vide » rend un résultat silencieusement faux. Le tri final se fait donc en
Python, sur une population déjà réduite par les critères que la base sait
filtrer.

🚨 **Odoo 19 normalise `('champ', '=', True)` en `operator='in'`,
`value=OrderedSet([True])`** avant d'appeler la méthode `search` d'un champ.
Lire l'opérateur brut rend le **complément exact** du résultat attendu — une
liste plausible et fausse.

🪤 **`UNIQUE(journal_id, account_prefix)` ne protège rien tant que le préfixe
peut être nul** : PostgreSQL ne compare jamais deux `NULL` comme égaux. Le
champ est donc normalisé à la chaîne vide en création comme en écriture.

Les contreparties — comptes clients et fournisseurs — et les lignes de taxe
sont exclues d'office : elles soldent l'écriture, elles ne consomment rien. Une
écriture déjà comptabilisée ne bloque plus rien, et sort donc du contrôle.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
