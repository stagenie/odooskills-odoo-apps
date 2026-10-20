from odoo import models
from odoo.http import request

# Toutes les routes JSON de l'écran code-barres (socle ET module lots).
OSKI_BARCODE_ROUTE_PREFIX = '/oski_stock_barcode/'


def oski_barcode_allowed_company_ids(env, context):
    """Sociétés cochées envoyées par le client, réduites à celles de l'utilisateur.

    Le client web envoie ``user.context`` (``allowed_company_ids`` = sociétés
    cochées dans le sélecteur, la première étant la société active). Une
    société hors ``env.user.company_ids`` (id forgé, droit retiré entre-temps)
    est écartée : jamais transmise à l'ORM. Liste vide = rien d'exploitable,
    l'appelant garde le comportement par défaut de l'utilisateur."""
    if not isinstance(context, dict):
        return []
    requested = context.get('allowed_company_ids')
    if not isinstance(requested, (list, tuple)):
        return []
    user_company_ids = set(env.user.company_ids.ids)
    allowed = []
    for cid in requested:
        if (isinstance(cid, int) and not isinstance(cid, bool)
                and cid in user_company_ids and cid not in allowed):
            allowed.append(cid)
    return allowed


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    @classmethod
    def _dispatch(cls, endpoint):
        """Applique les sociétés cochées aux routes du code-barres.

        Les routes JSON ne lisent pas le cookie ``cids`` : sans contexte,
        ``env.company`` reste la société par défaut de l'utilisateur et
        ``env.companies`` toutes ses sociétés. Le JS envoie donc ``context``
        (voir ``barcode_rpc.js``) ; seul ``allowed_company_ids`` filtré en est
        retenu (aucune autre clé de contexte venue du client)."""
        params = request.params
        if (isinstance(params, dict) and 'context' in params
                and request.httprequest.path.startswith(OSKI_BARCODE_ROUTE_PREFIX)):
            company_ids = oski_barcode_allowed_company_ids(
                request.env, params.pop('context'))
            if company_ids:
                request.update_context(allowed_company_ids=company_ids)
        return super()._dispatch(endpoint)
