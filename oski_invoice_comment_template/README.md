# OdooSkills — Modèles de remarque sur factures

## Description

Ce module ajoute la possibilité de créer des **modèles de remarques
réutilisables** pour les factures clients et fournisseurs. La remarque
sélectionnée est recopiée dans la **note de la facture** (champ `narration`),
qui est imprimée nativement dans le PDF de la facture — **aucun héritage de
rapport n'est nécessaire**.

## Fonctionnalités

- Nouveau modèle « Modèle de remarque » (nom, contenu HTML, séquence, actif).
- Filtrage optionnel par type de facture : clients, fournisseurs ou toutes.
- Sélecteur de modèle directement sur le formulaire de facture.
- Recopie automatique du contenu du modèle dans la note de la facture.
- Retirer le modèle ne vide pas la note déjà saisie.
- Sécurité : la facturation peut gérer les modèles, tous les utilisateurs
  peuvent les lire.

## Grandes opérations

1. **Créer des modèles de remarques** dans la configuration de la
   Comptabilité : *Comptabilité → Configuration → Modèles de remarque*.
2. **Sélectionner un modèle sur la facture** : le champ « Modèle de remarque »
   apparaît dans l'en-tête (factures clients et fournisseurs) ; le choix d'un
   modèle remplit automatiquement la note de la facture.
3. **La remarque apparaît dans le PDF** : la note étant imprimée nativement,
   le texte du modèle figure tel quel sur la facture imprimée.

## Configuration

Aucune configuration technique n'est requise. Après installation, créez vos
modèles depuis *Comptabilité → Configuration → Modèles de remarque*.

## Compatibilité

Compatible Odoo 15.0 → 19.0 (Community et Enterprise).

## Licence

LGPL-3
