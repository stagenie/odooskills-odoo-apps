# Filigrane sur les rapports

Un devis non confirmé, une facture annulée et une réimpression sortent de
l'imprimante avec exactement la même allure que le document valide. Odoo 19
ne propose aucun filigrane : le seul du dépôt sert à marquer les documents de
démonstration, en interne, et n'est ouvert à personne.

Ce module en pose un, décidé par une règle : un rapport, une condition, un mot.

## Ce qui mérite d'être su

Le filigrane est dessiné **dans le corps du rapport**, avant impression, et non
appliqué au fichier produit. C'est ce qui lui permet de se répéter sur **toutes
les pages** d'un document long : un élément en position fixe est reporté par le
moteur d'impression sur chacune d'elles.

La contrepartie est une règle que le module tient explicitement : quand une
impression groupe plusieurs documents qui appellent des filigranes différents,
**aucun n'est posé**. Poser celui du premier marquerait les pages des autres.
Le journal du serveur le note ; l'écran de la règle le dit.

La condition est un **domaine**, vérifié à l'enregistrement contre le modèle du
rapport. Une condition illisible ou étrangère au modèle est refusée là, devant
son auteur, et non plus tard au moment d'imprimer.

Les règles se lisent en `sudo` : personne n'a besoin des droits de paramétrage
pour imprimer un document marqué. La société retenue est celle du **document**,
pas celle de la session — un utilisateur multi-société imprime aussi ce qui
n'est pas le sien.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
