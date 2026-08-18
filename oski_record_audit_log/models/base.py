from odoo import api, models

# Le journal et sa configuration ne se journalisent pas : purger le registre
# le remplirait, et écrire une règle produirait une ligne à chaque réglage.
UNAUDITED = ("oski.audit.log", "oski.audit.rule")

# Types de champs dont la valeur n'a pas de représentation lisible tenant sur
# une ligne : on note qu'ils ont changé, pas ce qu'ils contiennent.
OPAQUE_TYPES = ("binary", "image", "one2many", "many2many")

VALUE_MAX = 120


class Base(models.AbstractModel):
    """Greffe la journalisation sur create, write et unlink de tous les modèles."""

    _inherit = "base"

    # ------------------------------------------------------------------
    # Règle applicable
    # ------------------------------------------------------------------

    def _oski_audit_rule(self):
        if self._transient or self._abstract or self._name in UNAUDITED:
            return None
        # Les gestes du superutilisateur — installation, mise à jour, tâches
        # planifiées — ne sont pas des gestes humains : les journaliser
        # noierait le registre sous le bruit de la maintenance.
        if self.env.su:
            return None
        return self.env["oski.audit.rule"]._rule_for_model(self._name)

    # ------------------------------------------------------------------
    # Mise en forme
    # ------------------------------------------------------------------

    def _oski_audit_format(self, field, value):
        if value is False or value is None:
            return "(vide)"
        if field.type == "many2one":
            return self.env[field.comodel_name].browse(value).display_name if isinstance(value, int) else (value.display_name if value else "(vide)")
        text = str(value)
        return text if len(text) <= VALUE_MAX else text[:VALUE_MAX] + "…"

    def _oski_audit_watched_names(self, rule_fields, candidate_names):
        """Champs réellement suivis parmi ceux touchés par l'écriture."""
        names = []
        for name in candidate_names:
            field = self._fields.get(name)
            if field is None or not field.store or field.type in OPAQUE_TYPES:
                continue
            if rule_fields and name not in rule_fields:
                continue
            names.append(name)
        return names

    def _oski_audit_create_logs(self, operation, entries):
        self.env["oski.audit.log"].sudo().create([
            {
                "model_name": self._name,
                "model_label": self.env["ir.model"]._get(self._name).name,
                "res_id": res_id,
                "res_name": res_name,
                "operation": operation,
                "changes": changes,
                "user_id": self.env.uid,
            }
            for res_id, res_name, changes in entries
        ])

    # ------------------------------------------------------------------
    # Greffes
    # ------------------------------------------------------------------

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        rule = records._oski_audit_rule() if records else None
        if not rule or not rule[0]:
            return records
        rule_fields = rule[3]
        entries = []
        for record, vals in zip(records, vals_list):
            names = record._oski_audit_watched_names(rule_fields, vals.keys())
            detail = "\n".join(
                "%s : %s" % (
                    record._fields[name].string,
                    record._oski_audit_format(record._fields[name], record[name]),
                )
                for name in names
            )
            entries.append((record.id, record.display_name, detail or False))
        if entries:
            records._oski_audit_create_logs("create", entries)
        return records

    def write(self, vals):
        rule = self._oski_audit_rule() if self else None
        tracked = bool(rule and rule[1])
        if tracked:
            names = self._oski_audit_watched_names(rule[3], vals.keys())
            # Les anciennes valeurs doivent être lues avant le super() :
            # après lui, elles n'existent plus nulle part.
            before = {
                record.id: {name: record[name] for name in names} for record in self
            } if names else {}
        res = super().write(vals)
        if tracked and before:
            entries = []
            for record in self:
                lines = []
                for name in names:
                    field = record._fields[name]
                    old, new = before[record.id][name], record[name]
                    if old == new:
                        continue
                    lines.append("%s : %s → %s" % (
                        field.string,
                        record._oski_audit_format(field, old),
                        record._oski_audit_format(field, new),
                    ))
                if lines:
                    entries.append((record.id, record.display_name, "\n".join(lines)))
            if entries:
                self._oski_audit_create_logs("write", entries)
        return res

    def unlink(self):
        rule = self._oski_audit_rule() if self else None
        if rule and rule[2]:
            self._oski_audit_create_logs(
                "unlink",
                [(record.id, record.display_name, False) for record in self],
            )
        return super().unlink()
