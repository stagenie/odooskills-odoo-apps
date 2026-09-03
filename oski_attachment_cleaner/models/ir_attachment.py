from datetime import timedelta

from odoo import api, fields, models

# Modèles dont les pièces jointes ne sont jamais candidates : leur cycle de vie
# est tenu par Odoo lui-même, et une pièce qui « semble » orpheline y est
# souvent un rouage vivant (bundles d'assets, images de vues).
PROTECTED_MODELS = ("ir.ui.view", "ir.attachment", "ir.module.module", "ir.asset")


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.model
    def _oski_protected_domain(self, min_age_days):
        """Le filet de sécurité, écrit une seule fois.

        Toute recherche de candidates part de ce domaine : une pièce qui
        n'entre pas ici ne peut être proposée à la purge par aucun chemin.

        - ``res_field`` renseigné : la pièce **est** la valeur d'un champ
          binaire ; la supprimer viderait le champ.
        - ``url`` renseignée : fichier servi (bundle d'assets, pièce publique).
        - ``public`` : servie sans authentification, potentiellement par le
          site web.
        - trop récente : un envoi en cours n'a pas encore son enregistrement.
        """
        limit_date = fields.Datetime.now() - timedelta(days=min_age_days)
        return [
            ("res_field", "=", False),
            ("url", "=", False),
            ("public", "=", False),
            ("create_date", "<", limit_date),
            ("res_model", "not in", list(PROTECTED_MODELS)),
        ]

    @api.model
    def _oski_find_orphans(self, min_age_days):
        """Les pièces dont l'enregistrement porteur a disparu.

        La recherche passe en superutilisateur, et ce n'est pas un raccourci :
        ``ir.attachment`` fait dépendre l'accès à une pièce de l'accès à son
        document. Une orpheline n'a plus de document — donc plus personne n'y
        a accès, et un administrateur ordinaire ne la verrait jamais. Le
        contrôle se joue à l'entrée : seul le groupe Paramètres peut ouvrir
        l'outil.

        Un modèle absent du registre — module désinstallé — n'est pas déclaré
        orphelin : réinstaller le module rendrait la pièce de nouveau utile, et
        une purge est sans retour.
        """
        candidates = self.sudo().search(self._oski_protected_domain(min_age_days) + [
            ("res_model", "!=", False)])
        orphans = self.sudo().browse()
        for model_name, attachments in candidates.grouped("res_model").items():
            if model_name not in self.env:
                continue
            model = self.env[model_name].sudo().with_context(active_test=False)
            attached_ids = {res_id for res_id in attachments.mapped("res_id") if res_id}
            alive = set(model.browse(attached_ids).exists().ids)
            orphans |= attachments.filtered(
                lambda att: not att.res_id or att.res_id not in alive)
        return orphans

    @api.model
    def _oski_find_duplicates(self, min_age_days):
        """Les copies redondantes : même empreinte, **même document**.

        La restriction au même document n'est pas un détail. Deux
        enregistrements différents peuvent légitimement porter le même fichier
        — un contrat type, un logo — et supprimer l'une des deux copies
        priverait un document de sa pièce.

        La plus ancienne de chaque groupe est conservée.
        """
        candidates = self.sudo().search(
            self._oski_protected_domain(min_age_days) + [("checksum", "!=", False)],
            order="id asc")
        seen = set()
        duplicates = self.sudo().browse()
        for attachment in candidates:
            key = (attachment.res_model, attachment.res_id, attachment.checksum)
            if key in seen:
                duplicates |= attachment
            else:
                seen.add(key)
        return duplicates
