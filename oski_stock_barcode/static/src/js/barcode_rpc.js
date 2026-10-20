/** @odoo-module **/

import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";

/**
 * Appel d'une route JSON du code-barres avec le contexte utilisateur.
 *
 * `rpc()` n'envoie aucun contexte et les routes JSON ne lisent pas le cookie
 * `cids` : sans ce relais, le serveur agit dans la société par défaut de
 * l'utilisateur au lieu des sociétés cochées dans le sélecteur. Le serveur
 * (models/ir_http.py) ne retient que `allowed_company_ids`, filtré par les
 * sociétés de l'utilisateur. Réutilisé par oski_stock_barcode_lot.
 */
export function barcodeRpc(route, params = {}, settings) {
    return rpc(route, { ...params, context: user.context }, settings);
}
