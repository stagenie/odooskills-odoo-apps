/** @odoo-module **/

import { Component } from "@odoo/owl";

export class ScreenOrders extends Component {
    static template = "oski_shop_floor.ScreenOrders";
    static props = { orders: Array, onBack: Function, onOpen: Function };
}
