# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestLeadInactivity(TransactionCase):
    """Vérifie le calcul de l'inactivité des pistes/opportunités."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Lead = cls.env["crm.lead"]
        cls.Param = cls.env["ir.config_parameter"].sudo()
        cls.PARAM_KEY = "oski_crm_lead_inactivity.idle_days"

    def _set_reference_date(self, lead, dt):
        """Force la date de référence d'inactivité.

        ``date_last_stage_update`` est un champ calculé/stocké recalculé à
        chaque changement d'étape ; on l'écrit en SQL direct pour simuler
        une opportunité immobile depuis longtemps.

        On invalide le cache via ``env.cache.invalidate`` (relecture DB pure)
        et non ``invalidate_recordset`` : ce dernier marque le champ
        calculé/stocké « à recalculer », ce qui réécraserait notre valeur SQL
        par ``now()`` au prochain accès.

        En v15, ``date_last_stage_update`` (compute store=True) est encore en
        file de recalcul juste après la création du lead : on vide donc cette
        file via ``flush()`` AVANT l'écriture SQL, sinon le prochain accès
        relancerait le calcul et remettrait ``now()`` par-dessus notre valeur.
        """
        lead.flush()
        self.env.cr.execute(
            "UPDATE crm_lead SET date_last_stage_update = %s WHERE id = %s",
            (fields.Datetime.to_string(dt), lead.id),
        )
        self.env.cache.invalidate(
            [(lead._fields["date_last_stage_update"], lead.ids)]
        )
        # Les champs calculés dérivés doivent aussi être relus.
        self.env.cache.invalidate(
            [
                (lead._fields["oski_idle_days"], lead.ids),
                (lead._fields["oski_is_idle"], lead.ids),
            ]
        )

    def test_idle_lead_above_threshold(self):
        """Lead immobile depuis 30 jours, seuil 14 -> dormant."""
        self.Param.set_param(self.PARAM_KEY, "14")
        lead = self.Lead.create({"name": "Vieille opportunité", "type": "opportunity"})
        self._set_reference_date(lead, fields.Datetime.now() - timedelta(days=30))
        self.assertGreaterEqual(lead.oski_idle_days, 29)
        self.assertLessEqual(lead.oski_idle_days, 31)
        self.assertTrue(lead.oski_is_idle)

    def test_fresh_lead_not_idle(self):
        """Lead créé aujourd'hui -> non dormant."""
        self.Param.set_param(self.PARAM_KEY, "14")
        lead = self.Lead.create({"name": "Opportunité fraîche", "type": "opportunity"})
        self.assertLess(lead.oski_idle_days, 14)
        self.assertFalse(lead.oski_is_idle)

    def test_threshold_change_makes_lead_active(self):
        """Seuil monté à 60 -> le lead à 30 jours n'est plus dormant."""
        self.Param.set_param(self.PARAM_KEY, "14")
        lead = self.Lead.create({"name": "Opportunité 30j", "type": "opportunity"})
        self._set_reference_date(lead, fields.Datetime.now() - timedelta(days=30))
        self.assertTrue(lead.oski_is_idle)

        self.Param.set_param(self.PARAM_KEY, "60")
        self.env.cache.invalidate(
            [(lead._fields["oski_is_idle"], lead.ids)]
        )
        self.assertFalse(lead.oski_is_idle)

    def test_search_idle_returns_subset(self):
        """La recherche [('oski_is_idle','=',True)] retourne le bon sous-ensemble."""
        self.Param.set_param(self.PARAM_KEY, "14")
        idle = self.Lead.create({"name": "Dormante", "type": "opportunity"})
        fresh = self.Lead.create({"name": "Active", "type": "opportunity"})
        self._set_reference_date(idle, fields.Datetime.now() - timedelta(days=30))

        found = self.Lead.search([("oski_is_idle", "=", True)])
        self.assertIn(idle, found)
        self.assertNotIn(fresh, found)

        # Recherche inverse cohérente.
        not_idle = self.Lead.search([("oski_is_idle", "=", False)])
        self.assertIn(fresh, not_idle)
        self.assertNotIn(idle, not_idle)
