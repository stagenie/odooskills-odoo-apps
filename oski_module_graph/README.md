# Graphe des dépendances des modules

La liste des applications dit ce qui est installé. Elle ne dit pas ce qui tient
quoi : quel module s'effondrerait si on désinstallait celui-ci, ni combien de
couches séparent une personnalisation du cœur.

Ce module dessine le graphe des dépendances en SVG : un étage par profondeur,
une flèche par dépendance. Depuis la fiche d'un module, un bouton montre son
propre arbre.

- Le dessin est produit **par le serveur** : aucune bibliothèque tierce, aucun
  appel réseau, rien à charger.
- Un module se place à l'étage de sa **plus longue chaîne** de dépendances,
  pour qu'aucune flèche ne remonte.
- Une dépendance hors du périmètre est écartée : le dessin ne porte jamais une
  flèche vers un nœud absent.
- Au-delà de 60 modules le graphe cesse d'être lisible : le module le dit et
  demande de restreindre, plutôt que de rendre une image illisible.
- Le calcul se protège des cycles — impossibles entre modules Odoo, mais un
  graphe tronqué n'a pas à figer le serveur.

Menu : **Paramètres → Technique → Graphe des dépendances**.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
