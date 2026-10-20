/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { ScreenWorkcenter } from "./screen_workcenter";
import { ScreenOrders } from "./screen_orders";
import { ScreenDetail } from "./screen_detail";

export class ShopFloorApp extends Component {
    static template = "oski_shop_floor.App";
    static components = { ScreenWorkcenter, ScreenOrders, ScreenDetail };
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
        this.state = useState({
            screen: "workcenter",
            workcenterId: false,
            orderId: false,
            workcenters: [],
            orders: [],
            detail: null,
        });
        onWillStart(() => this.loadWorkcenters());
    }

    async loadWorkcenters() {
        this.state.workcenters = await this.orm.call(
            "mrp.workcenter", "sf_get_workcenters", []
        );
    }

    async openWorkcenter(id) {
        this.state.workcenterId = id;
        this.state.orders = await this.orm.call(
            "mrp.workorder", "sf_get_orders", [id]
        );
        this.state.screen = "orders";
    }

    async openOrder(id) {
        this.state.orderId = id;
        this.state.detail = await this.orm.call(
            "mrp.workorder", "sf_get_detail", [[id]]
        );
        this.state.screen = "detail";
    }

    async goHome() {
        this.state.screen = "workcenter";
        this.state.orderId = false;
        await this.loadWorkcenters();
    }

    async goOrders() {
        this.state.orderId = false;
        this.state.orders = await this.orm.call(
            "mrp.workorder", "sf_get_orders", [this.state.workcenterId]
        );
        this.state.screen = "orders";
    }
}

registry.category("actions").add("oski_shop_floor.app", ShopFloorApp);
