# Location — Gestion de location générique (oski_rental)

Module Odoo 19 CE. Louez tout type de ressource unitaire : véhicules, salles,
engins, matériel.

## Fonctionnalités
- Ressources louables avec grille tarifaire heure/jour/semaine/mois et caution
- Flux complet : Devis → Réservée → En cours → Retournée → Facturée
- Wizards départ/retour avec état des lieux et suivi de caution
- Détection de conflits (réservations + indisponibilités maintenance)
- Facturation directe (account.move), retards facturables
- Alerte automatique des locations en retard (cron quotidien)
- Calendrier, pivot/graph CA, données de démonstration

## Extensions (store apps.odooskills.com)
- `oski_rental_website` — catalogue + réservation en ligne + portail
- `oski_rental_payment` — paiement en ligne (acompte ou total)
- `oski_rental_gantt` — planning visuel du parc

## Licence
LGPL-3 — © OdooSkills
