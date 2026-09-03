from odoo import models

FIELDS_MAX = 2000


class Base(models.AbstractModel):
    _inherit = "base"

    def export_data(self, fields_to_export):
        """Inscrit l'export au journal, une fois qu'il a réussi.

        Le ``super()`` passe en premier volontairement : il porte le contrôle
        de droits d'Odoo, et un export refusé ne doit pas laisser croire que
        des données sont sorties.
        """
        result = super().export_data(fields_to_export)
        # Le journal lui-même s'exporte comme n'importe quel modèle, mais
        # l'inscrire produirait une ligne à chaque consultation exportée.
        if self._name != "oski.export.log":
            names = ", ".join(str(f) for f in fields_to_export)
            self.env["oski.export.log"].sudo().create({
                "model_name": self._name,
                "model_label": self.env["ir.model"]._get(self._name).name,
                "record_count": len(result.get("datas") or []),
                "field_count": len(fields_to_export),
                "field_names": names[:FIELDS_MAX],
                "user_id": self.env.uid,
            })
        return result
