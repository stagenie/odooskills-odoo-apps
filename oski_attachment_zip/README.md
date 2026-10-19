# Pièces jointes en archive

Odoo 19 sait zipper les fichiers **d'un message** du fil de discussion. Personne
ne range ses documents ainsi : une commande porte le bon signé dans un message,
le plan dans un autre, et le reste dans la boîte à pièces jointes. Les
récupérer demande autant de clics que de fichiers.

Ce module ajoute au menu d'actions l'entrée **Télécharger les pièces jointes
(ZIP)**, sur la fiche comme sur une sélection de fiches.

## Ce qui mérite d'être su

L'entrée s'active **modèle par modèle**, depuis *Paramètres → Technique →
Structure de la base de données → Téléchargement groupé (ZIP)*. Une action
contextuelle vise un modèle : Odoo ne permet pas de la greffer sur tous à la
fois, et choisir à la place de l'utilisateur une liste de modèles « utiles »
serait arbitraire.

Les fichiers se lisent **avec les droits de l'appelant**, sans `sudo` : une
pièce jointe hérite de l'accès à son document, et le document vient d'être
vérifié. Faire autrement livrerait des fichiers que l'utilisateur n'a pas le
droit de voir.

Sont écartées les valeurs de champs binaires — un logo, une photo ne sont pas
des pièces jointes — et les pièces servies par une URL, qui n'ont aucun contenu
à archiver.

Un nom de fichier ne devient jamais un chemin : une pièce nommée
`../../etc/passwd` écrirait hors de son dossier chez qui décompresse l'archive.
Les doublons de nom sont numérotés, et une sélection de plusieurs fiches est
rangée dans un dossier par fiche.

Deux garde-fous : 200 fiches par téléchargement, et un poids maximal réglé par
`oski_attachment_zip.max_size_mb` (200 Mo par défaut, `0` pour lever la limite).
Le refus se prononce devant l'utilisateur, dans une boîte de dialogue, et non
dans une page d'erreur du navigateur.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
