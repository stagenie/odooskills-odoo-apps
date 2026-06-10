# Pistes dormantes CRM

Détection des pistes et opportunités dormantes dans le pipeline Odoo : celles
qui n'ont connu aucun mouvement depuis un nombre de jours configurable.

## Description

Dans un pipeline chargé, certaines affaires s'endorment sans qu'on s'en rende
compte. Ce module calcule, pour chaque piste ou opportunité, le nombre de jours
écoulés depuis son dernier mouvement (dernier changement d'étape, ou date de
création à défaut) et signale visuellement celles qui dépassent un seuil
d'inactivité.

La mesure s'appuie volontairement sur la date du dernier changement d'étape
plutôt que sur la date de dernière modification technique, afin de refléter
l'immobilité réelle de l'affaire et non les écritures internes du système.

## Fonctionnalités

- Champ **Jours d'inactivité** calculé (non stocké) sur chaque piste/opportunité.
- Indicateur **Dormante** (booléen) recherchable, vrai uniquement pour les
  affaires encore en jeu (actives, ni gagnées ni perdues) immobiles depuis au
  moins le seuil configuré.
- **Seuil d'inactivité paramétrable** depuis les Réglages du CRM (14 jours par
  défaut).
- **Colonne** « Jours d'inactivité » et **surlignage** des lignes dormantes dans
  la liste du pipeline.
- **Filtre « Dormantes »** dans la recherche des opportunités.
- Badge discret « Dormante depuis N j » sur le formulaire de la piste.

## Grandes opérations

1. **Régler le seuil** : ouvrez *Réglages → CRM* et ajustez le champ
   « Seuil d'inactivité (jours) » selon votre cycle de vente.
2. **Repérer les affaires immobiles** : dans le pipeline en vue liste, la
   colonne « Jours d'inactivité » et les lignes surlignées en orange mettent
   en évidence les pistes dormantes.
3. **Relancer** : appliquez le filtre « Dormantes » dans la recherche pour
   isoler les affaires à relancer et planifier vos actions.

## Configuration

Aucune configuration obligatoire. Le seuil par défaut est de 14 jours et se
modifie dans *Réglages → CRM → Seuil d'inactivité (jours)*. La valeur est
stockée dans `ir.config_parameter` sous la clé
`oski_crm_lead_inactivity.idle_days`.

## Compatibilité

Compatible Odoo 15.0 → 19.0 (Community et Enterprise).

## Licence

LGPL-3.
