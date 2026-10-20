/** @odoo-module **/

import { Component } from "@odoo/owl";

export class ScreenWorkcenter extends Component {
    static template = "oski_shop_floor.ScreenWorkcenter";
    static props = { workcenters: Array, onOpen: Function };
}
