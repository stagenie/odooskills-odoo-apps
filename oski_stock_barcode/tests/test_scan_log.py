import json

from odoo.tests.common import HttpCase, TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestScanLog(TransactionCase):

    def test_log_visibility_per_user(self):
        Log = self.env['oski.barcode.scan.log']
        op1 = self.env['res.users'].create({
            'name': 'Op1', 'login': 'op1',
            'group_ids': [(4, self.env.ref('stock.group_stock_user').id)]})
        op2 = self.env['res.users'].create({
            'name': 'Op2', 'login': 'op2',
            'group_ids': [(4, self.env.ref('stock.group_stock_user').id)]})
        Log.with_user(op1).create({'action': 'receipt'})
        Log.with_user(op2).create({'action': 'delivery'})
        seen_by_1 = Log.with_user(op1).search([])
        self.assertTrue(all(l.user_id == op1 for l in seen_by_1))
        self.assertEqual(len(seen_by_1), 1)

    def test_manager_sees_all(self):
        Log = self.env['oski.barcode.scan.log']
        op1 = self.env['res.users'].create({
            'name': 'Op3', 'login': 'op3',
            'group_ids': [(4, self.env.ref('stock.group_stock_user').id)]})
        mgr = self.env['res.users'].create({
            'name': 'Mgr', 'login': 'mgr',
            'group_ids': [(4, self.env.ref('stock.group_stock_manager').id),
                          (4, self.env.ref('stock.group_stock_user').id)]})
        Log.with_user(op1).create({'action': 'receipt'})
        self.assertTrue(Log.with_user(mgr).search([
            ('user_id', '=', op1.id)]))


@tagged('post_install', '-at_install')
class TestSessionLogEndpoint(HttpCase):

    def test_get_session_log(self):
        Log = self.env['oski.barcode.scan.log']
        admin = self.env.ref('base.user_admin')
        # self.env defaults to SUPERUSER_ID, distinct from the 'admin' login
        # used below — pin user_id explicitly so the endpoint's
        # user_id = env.user filter matches the authenticated session.
        Log.create({'action': 'receipt', 'quantity': 3, 'user_id': admin.id})
        self.authenticate('admin', 'admin')
        r = self.url_open('/oski_stock_barcode/get_session_log',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                             'params': {}}).encode(),
            headers={'Content-Type': 'application/json'})
        res = json.loads(r.content)['result']
        self.assertIn('receipt', res['summary'])
        self.assertGreaterEqual(res['summary']['receipt']['count'], 1)

    def test_get_session_log_tz_day_boundary(self):
        """A scan just after local midnight in Africa/Algiers (UTC+1) must be
        attributed to the correct local day, even though its create_date
        (stored UTC) falls on the previous UTC calendar day. Regression test
        for the naive-UTC day-bounds bug in get_session_log."""
        import pytz
        from datetime import datetime, time as dtime

        admin = self.env.ref('base.user_admin')
        admin.tz = 'Africa/Algiers'
        Log = self.env['oski.barcode.scan.log']
        log = Log.create({'action': 'delivery', 'quantity': 2, 'user_id': admin.id})

        tz = pytz.timezone('Africa/Algiers')
        target_local_day = datetime.now(tz).date()
        local_early = tz.localize(datetime.combine(target_local_day, dtime(0, 30)))
        utc_naive = local_early.astimezone(pytz.utc).replace(tzinfo=None)
        self.env.cr.execute(
            "UPDATE oski_barcode_scan_log SET create_date = %s WHERE id = %s",
            (utc_naive, log.id))
        self.env.invalidate_all()

        self.authenticate('admin', 'admin')
        r = self.url_open('/oski_stock_barcode/get_session_log',
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call',
                             'params': {'day': target_local_day.isoformat()}}).encode(),
            headers={'Content-Type': 'application/json'})
        res = json.loads(r.content)['result']
        self.assertIn('delivery', res['summary'])
        self.assertGreaterEqual(res['summary']['delivery']['count'], 1)
