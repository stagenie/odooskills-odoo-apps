/** @odoo-module **/

import { Component, t, useProps } from "@odoo/owl";

export class ScreenOrders extends Component {
    static template = "oski_shop_floor.ScreenOrders";
    props = useProps({ orders: t.array(), onBack: t.function(), onOpen: t.function() });
}
