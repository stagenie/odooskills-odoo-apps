# Numérotation des lignes de devis/commande

## Description

Ce module ajoute une numérotation automatique des lignes produit des devis et
bons de commande Odoo. Une colonne « N° » indique l'ordre de chaque ligne
(1, 2, 3, …), aussi bien dans le formulaire de la commande que sur le rapport
PDF imprimé. Les lignes de section, de sous-section et de note ne sont pas
numérotées.

## Fonctionnalités

- Champ `oski_line_number` calculé et stocké sur `sale.order.line`.
- Numérotation 1..n des seules lignes produit, dans l'ordre d'affichage
  (`sequence`, puis `id`).
- Exclusion automatique des lignes techniques (sections, sous-sections, notes),
  qui reçoivent le numéro 0.
- Renumérotation automatique lorsqu'on réordonne les lignes.
- Colonne « N° » en première position du tableau des lignes (lecture seule).
- Colonne « N° » en tête du tableau du rapport PDF de devis/commande, avec une
  cellule vide pour les lignes de section et de note.

## Grandes opérations

1. **Créer un devis** : ouvrez Ventes → Devis → Nouveau, ajoutez plusieurs
   lignes produit. La colonne « N° » affiche automatiquement 1, 2, 3, …
2. **Réordonner les lignes** : glissez-déposez les lignes (poignée de gauche)
   pour changer leur ordre. La numérotation se recalcule immédiatement selon le
   nouvel ordre.
3. **Imprimer le PDF** : cliquez sur Imprimer → Devis / Bon de commande. Le
   rapport PDF présente la colonne « N° » en tête du tableau des lignes ; les
   sections et notes apparaissent sans numéro.

## Configuration

Aucune configuration n'est nécessaire. Le module est opérationnel dès son
installation.

## Compatibilité

Compatible Odoo 15.0 → 19.0 (Community et Enterprise).

## Licence

LGPL-3.
