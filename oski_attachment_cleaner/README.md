# Nettoyage des pièces jointes

Le magasin de fichiers d'une base vieillit mal. Ce module en fait l'inventaire,
en mesure le poids, et purge sur demande — jamais avant un relevé lu.

Deux critères :

- **orphelines** — la pièce désigne un enregistrement qui n'existe plus ;
- **copies redondantes** — même empreinte, **même document**, plusieurs fois.

## D'où viennent réellement les orphelines

`unlink()` d'Odoo emporte au passage les pièces jointes du document supprimé :
une suppression ordinaire n'en laisse aucune. Les orphelines naissent ailleurs
— suppressions en cascade au niveau de la base, migrations, scripts SQL,
imports ratés — et personne ne les voit passer. C'est exactement ce que ce
module va chercher.

## Ce qui n'est jamais proposé

Le filet de sécurité est écrit une seule fois et toute recherche en part :

| Écarté | Pourquoi |
|---|---|
| `res_field` renseigné | La pièce **est** la valeur d'un champ binaire ; la supprimer viderait le champ. |
| `url` renseignée | Fichier servi : bundle d'assets, ressource publique. |
| Pièce publique | Servie sans authentification, souvent par le site web. |
| `ir.ui.view`, `ir.attachment`, `ir.module.module`, `ir.asset` | Cycle de vie tenu par Odoo. |
| Plus récente que l'âge minimum | Un envoi en cours n'a pas encore son enregistrement. |
| Modèle absent du registre | Module désinstallé : le réinstaller rendrait la pièce utile, et une purge est sans retour. |

La même empreinte sur **deux documents différents** n'est pas une redondance :
un contrat type ou un logo attaché à deux clients doit rester attaché aux deux.
Seules les copies du même document sont proposées, la plus ancienne conservée.

## La purge

La purge **rejoue le relevé** au lieu de faire confiance à la sélection
enregistrée : entre les deux, la base a continué de vivre. Chaque purge laisse
une trace nominative — qui, quand, combien, sur quels critères, et la liste des
pièces.

Menu : **Paramètres → Technique → Nettoyage des pièces jointes**.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
