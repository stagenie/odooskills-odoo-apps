from odoo.tests import HttpCase, tagged


@tagged("post_install", "-at_install", "test_oski_helpdesk")
class TestHelpdeskTour(HttpCase):

    def test_smoke_tour(self):
        """L'appli s'ouvre, le kanban et la liste s'affichent, un ticket créé
        à l'écran reçoit son numéro."""
        self.env.ref("base.user_admin").write({
            "group_ids": [(4, self.env.ref("oski_helpdesk.group_helpdesk_manager").id)]})
        team = self.env["helpdesk.team"].create({"name": "Équipe parcours"})
        self.env["helpdesk.ticket"].create({"name": "Ticket du parcours", "team_id": team.id})
        self.start_tour("/odoo", "oski_helpdesk_smoke", login="admin")
        ticket = self.env["helpdesk.ticket"].search([("name", "=", "Imprimante en panne")])
        self.assertEqual(ticket.team_id, team)
        self.assertTrue(ticket.number.startswith("HT/"))
