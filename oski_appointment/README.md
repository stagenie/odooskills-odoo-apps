# Rendez-vous — Oski

Moteur de prise de rendez-vous pour Odoo 19 **Community** (équivalent backend de
l'app Appointment Enterprise).

## Fonctionnalités

- Types de RDV : durée, lieu, personnel, préavis, horizon, rappels.
- Disponibilités basées sur `resource.calendar` (heures + congés natifs).
- Génération de créneaux libres et prise de RDV interne.
- Le rendez-vous est un événement d'agenda Odoo natif (rappels et invitations
  standard).

## Dépendances

`calendar`, `resource`, `mail` (Odoo CE). Aucun module externe.

## Portée

Backend uniquement. La page de réservation publique (website) fait l'objet d'un
add-on séparé.
