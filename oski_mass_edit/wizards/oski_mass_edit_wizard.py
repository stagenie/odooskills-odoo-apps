from odoo import _, api, fields, models
from odoo.exceptions import UserError

# Types de champs que l'assistant sait écrire. Tout le reste est refusé
# explicitement plutôt que traduit approximativement : mieux vaut un message
# clair qu'une valeur fausse posée sur mille enregistrements.
TEXT_TYPES = ("char", "text", "html", "selection")
NUMBER_TYPES = ("integer", "float", "monetary")
SUPPORTED_TYPES = TEXT_TYPES + NUMBER_TYPES + ("boolean", "date", "datetime", "many2one")


class OskiMassEditWizard(models.TransientModel):
    _name = "oski.mass.edit.wizard"
    _description = "Mass Edit"

    model_name = fields.Char(string="Model", readonly=True, required=True)
    record_count = fields.Integer(string="Selected Records", readonly=True)
    field_id = fields.Many2one(
        "ir.model.fields", string="Field to Change", required=True,
        domain="[('model', '=', model_name), ('store', '=', True), ('readonly', '=', False)]",
        ondelete="cascade",
    )
    field_ttype = fields.Selection(related="field_id.ttype", string="Type")
    operation = fields.Selection(
        [("set", "Set a value"), ("clear", "Clear the field")],
        string="Operation", default="set", required=True,
    )
    value_char = fields.Char(string="Value")
    value_number = fields.Float(string="Numeric Value")
    value_bool = fields.Boolean(string="Checked")
    value_date = fields.Date(string="Date")
    value_datetime = fields.Datetime(string="Date and Time")
    value_reference = fields.Reference(
        selection="_selection_reference_models", string="Linked Record",
    )
    selection_hint = fields.Char(compute="_compute_selection_hint", string="Accepted Values")

    @api.model
    def _selection_reference_models(self):
        models_ = self.env["ir.model"].sudo().search([("transient", "=", False)])
        return [(m.model, m.name) for m in models_]

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids") or []
        if active_model:
            vals.setdefault("model_name", active_model)
        vals.setdefault("record_count", len(active_ids))
        return vals

    @api.depends("field_id")
    def _compute_selection_hint(self):
        for wizard in self:
            hint = False
            field = wizard._resolve_field(raise_if_missing=False)
            if field is not None and field.type == "selection":
                keys = [key for key, _label in field._description_selection(self.env)]
                hint = ", ".join(keys)
            wizard.selection_hint = hint

    def _resolve_field(self, raise_if_missing=True):
        """Retourne le champ ORM visé, ou ``None``.

        On passe par ``_fields`` et non par ``ir.model.fields`` : seule la
        définition Python porte ``compute``, ``inverse`` et ``store``, dont
        dépend la question « ce champ est-il réellement inscriptible ? ».
        """
        self.ensure_one()
        model = self.env.get(self.model_name)
        if model is None:
            if raise_if_missing:
                raise UserError(_("Model “%s” does not exist.", self.model_name))
            return None
        # ir.model.fields n'est lisible que par les administrateurs : on ne lit
        # ici que le nom du champ, en sudo ; l'écriture reste sous les droits.
        field_name = self.field_id.sudo().name
        field = model._fields.get(field_name)
        if field is None and raise_if_missing:
            raise UserError(
                _("Field “%s” does not exist on “%s”.", field_name, self.model_name)
            )
        return field

    def _check_writable(self, field):
        if field.type not in SUPPORTED_TYPES:
            raise UserError(
                _("Unsupported field type: “%s”. The wizard writes text, numbers, "
                  "booleans, dates and simple relations.", field.type)
            )
        if not field.store:
            raise UserError(
                _("“%s” is not stored in the database: it is recomputed and cannot "
                  "be written.", field._description_string(self.env))
            )
        if field.readonly:
            raise UserError(_("“%s” is read-only.", field._description_string(self.env)))
        if field.compute and not field.inverse:
            raise UserError(
                _("“%s” is computed and has no inverse: it cannot be written.",
                  field._description_string(self.env))
            )

    def _coerce_value(self, field):
        """Traduit la saisie de l'assistant vers la valeur attendue par le champ."""
        self.ensure_one()
        if self.operation == "clear":
            if field.type in NUMBER_TYPES:
                return 0
            return False
        if field.type in TEXT_TYPES:
            value = self.value_char or ""
            if field.type == "selection":
                keys = [key for key, _label in field._description_selection(self.env)]
                if value not in keys:
                    raise UserError(
                        _("“%(value)s” is not an accepted value. Possible values: %(keys)s",
                          value=value, keys=", ".join(keys))
                    )
            return value
        if field.type == "integer":
            return int(self.value_number)
        if field.type in ("float", "monetary"):
            return self.value_number
        if field.type == "boolean":
            return self.value_bool
        if field.type == "date":
            return self.value_date
        if field.type == "datetime":
            return self.value_datetime
        # many2one
        target = self.value_reference
        if not target:
            raise UserError(_("Choose the record to link, or switch to “Clear the field”."))
        if target._name != field.comodel_name:
            raise UserError(
                _("“%(field)s” expects a record of type “%(expected)s”, not "
                  "“%(given)s”.",
                  field=field._description_string(self.env), expected=field.comodel_name, given=target._name)
            )
        return target.id

    def _target_records(self):
        self.ensure_one()
        model = self.env.get(self.model_name)
        if model is None:
            raise UserError(_("Model “%s” does not exist.", self.model_name))
        return model.browse(self.env.context.get("active_ids") or []).exists()

    def action_apply(self):
        self.ensure_one()
        records = self._target_records()
        if not records:
            raise UserError(_("No record selected."))
        field_def = self.field_id.sudo()
        if field_def.model != self.model_name:
            raise UserError(
                _("Field “%(field)s” does not belong to model “%(model)s”.",
                  field=field_def.name, model=self.model_name)
            )
        field = self._resolve_field()
        self._check_writable(field)
        value = self._coerce_value(field)
        if field.required and value in (False, None, ""):
            raise UserError(
                _("“%s” is required: it cannot be cleared.", field._description_string(self.env))
            )
        # Aucun sudo : l'écriture passe par les droits et les règles de
        # l'utilisateur courant, exactement comme une saisie fiche par fiche.
        records.write({field_def.name: value})
        return {"type": "ir.actions.act_window_close"}
