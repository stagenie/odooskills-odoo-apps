import werkzeug.utils
from werkzeug.exceptions import Forbidden, NotFound
from werkzeug.urls import url_encode

from odoo import _, http
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class OskiPortalUpload(CustomerPortal):

    @http.route("/oski/portal/document/<int:request_id>/upload", type="http",
                auth="public", methods=["POST"], website=True, csrf=True)
    def oski_portal_document_upload(self, request_id, access_token=None,
                                    ufile=None, **post):
        document_request = request.env["oski.portal.document.request"].sudo() \
            .browse(request_id).exists()
        if not document_request:
            raise NotFound()

        # L'autorisation est celle de la FICHE, pas celle de la demande : le
        # portail ne connaît que le jeton du document que le client consulte.
        try:
            record = self._document_check_access(
                document_request.res_model, document_request.res_id, access_token)
        except (AccessError, MissingError):
            raise Forbidden()

        if document_request.state != "pending":
            return self._oski_redirect(record, access_token, "closed")

        error = self._oski_check_file(document_request, ufile)
        if error:
            return self._oski_redirect(record, access_token, error)

        attachment = request.env["ir.attachment"].sudo().create({
            "name": ufile.filename,
            "raw": ufile.read(),
            "res_model": document_request.res_model,
            "res_id": document_request.res_id,
        })
        document_request._oski_receive(attachment)
        return self._oski_redirect(record, access_token, "ok")

    def _oski_redirect(self, record, access_token, status):
        """Ramène le client sur sa page, avec le sort de son dépôt."""
        url = record.access_url or "/my"
        params = {"oski_upload": status}
        if access_token:
            params["access_token"] = access_token
        separator = "&" if "?" in url else "?"
        return werkzeug.utils.redirect(url + separator + url_encode(params))

    def _oski_check_file(self, document_request, ufile):
        """Rend un code d'erreur, jamais une exception.

        Un client à qui l'on doit un document ne doit pas tomber sur une page
        d'erreur du serveur parce qu'il a choisi le mauvais fichier : il
        revient sur sa page, avec la raison.
        """
        if not ufile or not ufile.filename:
            return "empty"
        extension = ufile.filename.rpartition(".")[2].lower()
        allowed = document_request._oski_allowed_extensions()
        if allowed and extension not in allowed:
            return "extension"
        ufile.stream.seek(0, 2)
        size = ufile.stream.tell()
        ufile.stream.seek(0)
        if size == 0:
            return "empty"
        if size > document_request._oski_max_size():
            return "size"
        return False
