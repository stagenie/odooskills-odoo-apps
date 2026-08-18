from werkzeug.exceptions import Forbidden, NotFound

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import content_disposition, request


class OskiAttachmentZip(http.Controller):
    """Le seul rôle du contrôleur est de servir l'archive : le tri des
    pièces, les droits et les limites sont décidés par le modèle, où les
    tests peuvent les atteindre sans passer par HTTP."""

    @http.route("/oski/attachment/zip", type="http", auth="user", readonly=True)
    def oski_attachment_zip(self, model=None, ids="", **kwargs):
        if not model or model not in request.env:
            raise NotFound()
        try:
            record_ids = [int(value) for value in (ids or "").split(",") if value]
        except ValueError:
            raise NotFound()
        if not record_ids:
            raise NotFound()

        records = request.env[model].browse(record_ids).exists()
        if not records:
            raise NotFound()
        try:
            name, content = request.env["ir.attachment"]._oski_zip_bytes(records)
        except AccessError:
            raise Forbidden()
        except UserError:
            raise NotFound()

        return request.make_response(content, headers=[
            ("Content-Type", "application/zip"),
            ("X-Content-Type-Options", "nosniff"),
            ("Content-Length", len(content)),
            ("Content-Disposition", content_disposition(name)),
        ])
