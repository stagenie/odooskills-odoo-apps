# OdooSkills — Alerte de stock bas

## Description

Ce module ajoute une alerte de stock bas **par produit**, simple et sans code.
Vous définissez un seuil sur la fiche produit ; lorsque la quantité disponible
passe en dessous de ce seuil, le produit est signalé partout dans Odoo et le
responsable de stock reçoit une activité quotidienne.

## Fonctionnalités

- Champ **Seuil d'alerte stock** sur la fiche produit (onglet *Inventaire*).
  Un seuil à `0` désactive l'alerte.
- Champ calculé **Stock bas** (non stocké, toujours à jour) : vrai quand un
  seuil est défini et que la quantité disponible lui est inférieure.
- Liste des produits : les lignes en stock bas s'affichent en **rouge**, avec
  une colonne *Stock bas* masquable.
- Filtre de recherche **« Stock bas »** pour isoler les produits concernés.
- **Cron quotidien** : une activité « À faire » intitulée *Stock bas* est créée
  pour le responsable de stock sur chaque produit en alerte, sans doublon.

## Grandes opérations

1. **Définir un seuil** sur la fiche produit (onglet *Inventaire*, champ
   *Seuil d'alerte stock*).
2. **Repérer les alertes** : dans la liste des produits, les lignes en stock bas
   passent en rouge ; le filtre *Stock bas* permet de ne garder que celles-ci.
3. **Suivre les actions** : chaque jour, une activité est automatiquement créée
   pour le responsable de stock sur les produits en alerte (sans recréer de
   doublon tant que l'activité précédente n'est pas terminée).

## Configuration

Aucune configuration technique. Il suffit de renseigner un seuil sur les
produits à surveiller. Le destinataire des activités est le premier utilisateur
du groupe *Responsable Inventaire* (à défaut, l'administrateur).

## Compatibilité

Odoo 15.0 → 19.0 (Community et Enterprise).

## Licence

LGPL-3.
