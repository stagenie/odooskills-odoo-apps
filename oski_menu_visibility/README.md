# OdooSkills — Menus masqués par utilisateur

Retirez des menus de l'écran d'un utilisateur précis, sans créer de groupe ni toucher aux droits.
Le réglage vit sur la fiche utilisateur, onglet **Menus masqués**. Masquer un menu masque aussi
tout ce qu'il contient.

**Ce module range l'écran, il ne verrouille pas la donnée** : un menu masqué reste atteignable
par son adresse directe. Pour interdire réellement l'accès, il faut des droits.

Détail d'implémentation qui compte : le filtrage se greffe sur `_filter_visible_menus`, non sur
`_visible_menu_ids` — cette dernière est mise en cache sur les **groupes** de l'utilisateur, si
bien qu'un masquage individuel y serait servi à tous ceux qui partagent ses groupes.

- **Dépendances** : `base`
- **Licence** : LGPL-3
- **Auteur** : OdooSkills — https://apps.odooskills.com
