from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _slug(cls, value):
        # A module page keeps the same URL in every language: the slug comes
        # from the technical name, so the canonical redirect of the frontend
        # (`_pre_dispatch`) and `website_url` agree.
        if isinstance(value, models.BaseModel) and value._name == "oski.module":
            value = (value.id, value.technical_name)
        return super()._slug(value)
