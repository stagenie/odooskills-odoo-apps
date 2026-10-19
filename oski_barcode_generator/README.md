# Codes-barres EAN13 en masse

Odoo 19 sait vérifier un code-barres (`check_barcode_encoding`) et en calculer
la clé (`get_barcode_check_digit`) ; il ne sait pas en produire. Un catalogue
de mille références sans code se remplit à la main.

## Ce qui mérite d'être su

🚨 **`get_barcode_check_digit` attend le code ENTIER**, pas les douze premiers
chiffres : il retire lui-même le dernier caractère avant de calculer
(`numeric_barcode[-2::-1]`). Lui passer le corps seul décale tout le calcul et
produit des codes qui ressemblent à des EAN13 sans en être.

Le préfixe par défaut commence par **2** : la plage 20-29 est celle que la
norme réserve à l'usage interne d'une entreprise. Y déroger produirait des
codes ressemblant à ceux d'un autre fabricant.

Les articles qui portent déjà un code ne sont **jamais** touchés — écraser un
code casserait les étiquettes imprimées et les scanners qui les lisent. Les
numéros déjà pris sont sautés, y compris ceux venus d'un import : tous les
codes de la base sont chargés avant de commencer, pas seulement ceux de la
sélection.

Une plage épuisée est **dite**, pas bouclée : un préfixe de sept chiffres ne
laisse que cinq chiffres de numérotation.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
