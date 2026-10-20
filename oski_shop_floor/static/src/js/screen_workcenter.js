/** @odoo-module **/

import { Component, t, useProps } from "@odoo/owl";

export class ScreenWorkcenter extends Component {
    static template = "oski_shop_floor.ScreenWorkcenter";
    props = useProps({ workcenters: t.array(), onOpen: t.function() });
}
