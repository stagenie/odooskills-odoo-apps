# Historique des prix

Odoo 19 n'a plus de modèle d'historique de prix — `product.price.history` a
disparu. Le prix affiché est celui d'aujourd'hui ; celui d'avant la dernière
hausse n'existe plus nulle part.

## Ce qui mérite d'être su

**Le relevé se prend avant l'écriture.** Après, l'ancienne valeur n'existe plus
nulle part : c'est tout l'objet de l'historique.

**Le coût s'écoute sur la variante, pas sur l'article.** `standard_price` est
un champ dépendant de la société, porté par `product.product` ; celui de
`product.template` est un calcul qui écrit dans ses variantes. Écouter le
mauvais niveau laisserait échapper la moitié des mouvements, et perdrait la
société concernée.

**Aucune purge automatique**, contrairement aux journaux techniques de la
gamme. Un historique de prix qui s'efface au bout de trente jours ne répond
plus à la seule question qu'on lui pose.

Le module ne dépend que de `product`, qui ne déclare aucun menu — les menus
d'articles viennent de Ventes, d'Achats ou d'Inventaire. D'où sa racine propre,
seul point d'entrée qui ne suppose aucun de ces modules installé.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
