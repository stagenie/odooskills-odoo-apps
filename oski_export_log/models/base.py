from odoo import models
from odoo.tools.constants import IN_MAX

FIELDS_MAX = 2000


class Base(models.AbstractModel):
    _inherit = "base"

    def export_data(self, fields_to_export):
        """Inscrit l'export au journal, une fois qu'il a réussi.

        Le ``super()`` passe en premier volontairement : il porte le contrôle
        de droits d'Odoo, et un export refusé ne doit pas laisser croire que
        des données sont sorties.

        Depuis Odoo 20, le contrôleur d'export appelle ``export_data`` par
        lots de ``IN_MAX`` enregistrements (``web/controllers/export.py``) :
        un lot qui prolonge le précédent complète la même ligne de journal
        au lieu d'en ouvrir une nouvelle.
        """
        result = super().export_data(fields_to_export)
        # Le journal lui-même s'exporte comme n'importe quel modèle, mais
        # l'inscrire produirait une ligne à chaque consultation exportée.
        if self._name == "oski.export.log":
            return result
        row_count = len(result.get("datas") or [])
        key = ("oski_export_log", self.env.uid, self._name, tuple(map(str, fields_to_export)))
        previous = self.env.cr.cache.get(key)
        Log = self.env["oski.export.log"].sudo()
        if (
            previous
            and previous["last_size"] == IN_MAX
            and previous["seen"].isdisjoint(self.ids)
        ):
            # Suite d'un export découpé en lots : même auteur, même modèle,
            # mêmes champs, lot précédent plein, enregistrements nouveaux.
            log = Log.browse(previous["log_id"])
            log.record_count += row_count
        else:
            names = ", ".join(str(f) for f in fields_to_export)
            log = Log.create({
                "model_name": self._name,
                "model_label": self.env["ir.model"].sudo()._get(self._name).name,
                "record_count": row_count,
                "field_count": len(fields_to_export),
                "field_names": names[:FIELDS_MAX],
                "user_id": self.env.uid,
            })
            previous = {"log_id": log.id, "seen": set()}
        previous["seen"].update(self.ids)
        previous["last_size"] = len(self)
        self.env.cr.cache[key] = previous
        return result
