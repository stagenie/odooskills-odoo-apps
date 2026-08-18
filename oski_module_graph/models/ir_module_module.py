from odoo import _, models


class IrModuleModule(models.Model):
    _inherit = "ir.module.module"

    def action_oski_module_graph(self):
        """Ouvre le graphe centré sur ce module et ce dont il dépend."""
        self.ensure_one()
        wizard = self.env["oski.module.graph"].create({
            "module_ids": [(6, 0, self.ids)],
            "with_dependencies": True,
        })
        wizard.action_draw()
        return {
            "type": "ir.actions.act_window",
            "name": _("Dépendances de %s", self.shortdesc or self.name),
            "res_model": "oski.module.graph",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
