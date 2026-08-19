# Rappel de saisie des temps

Odoo 19 Community affiche deux cases dans les paramètres des feuilles de temps
— *Employee Reminder* et *Approver Reminder* — qui **ne déclenchent rien** :
aucune tâche planifiée, aucun modèle de courriel, aucun consommateur dans tout
le dépôt. N'étant reliées ni à un champ de société ni à un paramètre système,
elles ne se souviennent même pas d'avoir été cochées. L'envoi vit dans
l'édition Enterprise.

Un test de ce module le vérifie explicitement : si Odoo branche un jour ces
cases, il tombera, et il faudra revoir le positionnement.

## Ce qui mérite d'être su

**Le retard est une donnée, pas un courriel.** Il se relit, se totalise et se
compare d'une semaine à l'autre, en liste comme en tableau croisé. Le rappel
n'en est qu'une conséquence — et c'est une activité, jamais un courriel.

**L'horaire de travail de l'employé fait foi**, la société n'est qu'un recours.
Un mi-temps relevé sur 35 heures serait en retard toutes les semaines, et le
tableau ne dirait plus rien à personne.

**La tâche planifiée relève la semaine écoulée**, du lundi au dimanche :
relever la semaine en cours accuserait tout le monde d'un retard qui n'existe
pas encore.

Le rappel se pose **une seule fois** par semaine relevée ; repasser la tâche
planifiée met la ligne à jour sans empiler les activités.

## Licence

LGPL-3 — OdooSkills, https://apps.odooskills.com
