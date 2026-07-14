/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ShopFloorApp extends Component {
    static template = "oski_shop_floor.App";
    static props = ["*"];
}

registry.category("actions").add("oski_shop_floor.app", ShopFloorApp);
