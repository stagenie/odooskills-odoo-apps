# Checklist d'étapes sur les tâches de projet

## Description

Ce module ajoute à chaque tâche de projet une **checklist d'étapes** assortie
d'une **barre de progression**. Il permet de décomposer une tâche en étapes
concrètes, de suivre leur réalisation et, le cas échéant, d'assigner chaque
étape à un membre de l'équipe.

## Fonctionnalités

- Nouvel onglet **« Checklist »** sur le formulaire de tâche.
- Liste **éditable en ligne** et **réordonnable** (poignée de glisser-déposer).
- Champ **« Étape »**, case **« Fait »** (interrupteur), et **« Assigné à »**
  avec avatar utilisateur.
- **Barre de progression** indiquant le pourcentage d'étapes terminées
  (0 % lorsqu'aucune étape n'est définie).
- **Colonne d'avancement** dans la liste des tâches (affichable/masquable).
- Compteur du nombre d'étapes.

## Grandes opérations

1. **Ouvrir une tâche** de projet, puis se rendre sur l'onglet **« Checklist »**.
2. **Cocher les étapes** au fur et à mesure de leur réalisation : la **barre de
   progression** se met à jour automatiquement.
3. Consulter la **colonne « Checklist » (%)** dans la liste des tâches pour
   suivre l'avancement d'un coup d'œil.

## Configuration

Aucune configuration n'est requise. Les droits sont gérés automatiquement :

- Les **utilisateurs de projet** (`project.group_project_user`) peuvent créer,
  modifier et supprimer des étapes.
- Les **utilisateurs internes** (`base.group_user`) peuvent les consulter.

## Compatibilité

Compatible Odoo **15.0 → 19.0** (Community et Enterprise).

## Licence

LGPL-3
