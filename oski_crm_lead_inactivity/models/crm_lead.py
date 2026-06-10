# -*- coding: utf-8 -*-
from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = "crm.lead"

    oski_idle_days = fields.Integer(
        string="Jours d'inactivité",
        compute="_compute_oski_idle",
        help="Nombre de jours écoulés depuis le dernier mouvement de la piste "
        "(dernier changement d'étape, ou création à défaut).",
    )
    oski_is_idle = fields.Boolean(
        string="Dormante",
        compute="_compute_oski_idle",
        search="_search_oski_is_idle",
        help="Piste active, non gagnée et non perdue, immobile depuis au moins "
        "le seuil d'inactivité configuré dans les Réglages CRM.",
    )

    @api.depends("date_last_stage_update", "create_date", "probability", "active")
    def _compute_oski_idle(self):
        """Calcule l'ancienneté du dernier mouvement et l'état dormant.

        On s'appuie sur ``date_last_stage_update or create_date`` plutôt que sur
        ``write_date`` : ce dernier bougerait à chaque écriture (y compris nos
        propres recalculs), faussant la mesure d'immobilité réelle.
        """
        threshold = self._oski_idle_threshold()
        now = fields.Datetime.now()
        for lead in self:
            reference = lead.date_last_stage_update or lead.create_date
            if reference:
                lead.oski_idle_days = (now - reference).days
            else:
                lead.oski_idle_days = 0

            # Dormante uniquement si encore en jeu : active, ni gagnée ni perdue.
            in_play = lead.active and lead.probability < 100
            lead.oski_is_idle = bool(in_play and lead.oski_idle_days >= threshold)

    def _oski_idle_threshold(self):
        """Retourne le seuil d'inactivité (en jours) issu de la configuration."""
        param = self.env["ir.config_parameter"].sudo().get_param(
            "oski_crm_lead_inactivity.idle_days", default="14"
        )
        try:
            return int(param)
        except (TypeError, ValueError):
            return 14

    def _search_oski_is_idle(self, operator, value):
        """Recherche les pistes dormantes via un filtre Python robuste.

        On charge les pistes encore en jeu, on calcule leur état dormant en
        mémoire, puis on retourne un domaine ``[('id', 'in', ids)]``. C'est
        plus simple et plus sûr qu'un domaine SQL dépendant du fuseau et de la
        date de référence dérivée.

        En v19, l'optimiseur de domaine convertit ``('field', '=', True)`` en
        ``('field', 'in', [True])`` ; on accepte donc les opérateurs ``=``,
        ``!=``, ``in`` et ``not in`` et on normalise la cible booléenne.
        """
        if operator in ("=", "!="):
            want_idle = bool(value)
            negate = operator == "!="
        elif operator in ("in", "not in"):
            truthy = any(bool(v) for v in value)
            want_idle = truthy
            negate = operator == "not in"
        else:
            raise ValueError("Opérateur non supporté : %s" % operator)

        if negate:
            want_idle = not want_idle

        candidates = self.search([("active", "=", True), ("probability", "<", 100)])
        idle_ids = candidates.filtered("oski_is_idle").ids

        if want_idle:
            return [("id", "in", idle_ids)]
        return [("id", "not in", idle_ids)]
