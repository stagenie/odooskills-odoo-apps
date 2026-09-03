# Dépôt de documents au portail

Dans Odoo 19, un client ne peut envoyer un fichier depuis le portail qu'en
écrivant un message dans le fil de discussion, et seulement sur les pages qui
affichent ce fil. Rien ne dit ce qu'on attend de lui, rien ne dit si c'est
arrivé.

Ce module renverse la démarche : c'est vous qui demandez, il dépose.

## Ce qui mérite d'être su

Le bloc **Documents attendus** se greffe sur le fil de discussion du portail,
commun au devis, à la facture, au bon de commande et à la tâche. Une seule
inclusion couvre toutes les pages qui l'affichent, et le module ne dépend
d'aucun module métier.

La demande porte sa propre cible — modèle et identifiant — et ne propose que
les modèles qui ont une **page portail**. Proposer les autres promettrait une
page inexistante.

Le dépôt s'autorise sur la **fiche**, jamais sur la demande : le contrôle passe
par le mécanisme du portail lui-même, droits de lecture ou jeton d'accès. Un
lien de demande volé ne suffit à rien.

Le rapprochement client se fait sur la **société du contact** : dans une
entreprise, ce n'est pas toujours la personne nommée dans la demande qui dépose
le fichier.

Un fichier refusé — mauvaise extension, trop lourd, demande déjà honorée —
ramène le client sur sa page avec la raison. Jamais sur une page d'erreur du
serveur : il n'y peut rien, et il ne saurait pas quoi en faire.

Le dépôt est raconté dans le fil de discussion de la fiche, là où l'équipe
regarde, et non sur la demande que personne n'ouvre.

Réglages par paramètres système : `oski_portal_upload.allowed_extensions` et
`oski_portal_upload.max_size_mb`.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
