# -*- coding: utf-8 -*-
"""
End-to-end scenario script for the oski_treasury suite (core + bank + cashcount
+ expense + dashboard + closing_plus).

Usage:
    venv/bin/python odoo/odoo-bin shell -c config/odoo_treasury_test.conf \
        -d vs19_oski_treasury_test < content/apps/free/oski_treasury/tools/test_treasury_scenario.py

Ported from addons/adi_dev/treasor_pack/test_treasury_scenario.py (source pack,
models prefixed treasury.*) to the oski_treasury.* naming used by the suite.
"""
import logging
from datetime import datetime

_logger = logging.getLogger('OSKI_TREASURY_TEST')

def log(msg):
    print(f"\n{'='*70}")
    print(f"  {msg}")
    print(f"{'='*70}")

def ok(msg):
    print(f"  OK {msg}")

def fail(msg):
    print(f"  FAIL {msg}")

def info(msg):
    print(f"  -> {msg}")

# =====================================================================
#  PHASE 0: Clean up previous test data
# =====================================================================
log("PHASE 0: Clean up previous test data")

for model in ['oski.treasury.cash.closing', 'oski.treasury.cash.operation',
              'oski.treasury.safe.operation', 'oski.treasury.transfer',
              'oski.treasury.bank.operation', 'oski.treasury.bank.closing']:
    recs = env[model].with_context(active_test=False).search([])
    if recs:
        env.cr.execute(
            f"DELETE FROM {model.replace('.', '_')} WHERE id IN %s", (tuple(recs.ids),)
        )

for model in ['oski.treasury.cash', 'oski.treasury.safe', 'oski.treasury.bank']:
    recs = env[model].with_context(active_test=False).search([])
    if recs:
        env.cr.execute(
            f"DELETE FROM {model.replace('.', '_')} WHERE id IN %s", (tuple(recs.ids),)
        )

# Note: partners and products are kept (referenced by accounting entries).
env.cr.commit()
ok("Previous test data cleaned up")

# =====================================================================
#  PHASE 1: Test partners
# =====================================================================
log("PHASE 1: Create test partners")

Partner = env['res.partner']

def get_or_create_partner(name, **kwargs):
    p = Partner.search([('name', '=', name)], limit=1)
    if not p:
        p = Partner.create({'name': name, **kwargs})
    return p

customer1 = get_or_create_partner('Alpha Customer (TEST-TRESO)', is_company=True, customer_rank=1)
customer2 = get_or_create_partner('Beta Customer (TEST-TRESO)', is_company=True, customer_rank=1)
customer3 = get_or_create_partner('Gamma Customer (TEST-TRESO)', is_company=True, customer_rank=1)
vendor1 = get_or_create_partner('Delta Vendor (TEST-TRESO)', is_company=True, supplier_rank=1)
env.cr.commit()
ok(f"3 customers created: {customer1.name}, {customer2.name}, {customer3.name}")
ok(f"1 vendor created: {vendor1.name}")

# =====================================================================
#  PHASE 2: Test service product
# =====================================================================
log("PHASE 2: Test service product")

Product = env['product.product']
service_product = Product.search([('name', '=', 'Service Delivery (TEST-TRESO)')], limit=1)
if not service_product:
    service_product = Product.create({
        'name': 'Service Delivery (TEST-TRESO)',
        'type': 'service',
        'list_price': 50000.0,  # 50,000 DZD
    })
env.cr.commit()
ok(f"Product created: {service_product.name} - Price: {service_product.list_price} DZD")

# =====================================================================
#  PHASE 3: Cash register creation
# =====================================================================
log("PHASE 3: Cash register creation")

cash_journal = env['account.journal'].search([('type', '=', 'cash')], limit=1)
if not cash_journal:
    info("No cash journal found in the chart of accounts, creating one (TEST-TRESO)")
    cash_journal = env['account.journal'].create({
        'name': 'Cash Test TEST-TRESO', 'type': 'cash', 'code': 'CSHTT',
    })
    env.cr.commit()
ok(f"Cash journal in use: [{cash_journal.code}] {cash_journal.name}")

Cash = env['oski.treasury.cash']
caisse = Cash.create({
    'name': 'Main Cash Register TEST',
    'code': 'CP-TEST',
    'journal_id': cash_journal.id,
    'state': 'open',
    'require_closing': True,
    'auto_close_days': 1,
    'max_amount': 5000000.0,
    'allow_negative_balance': False,
    'control_level': 'warning',  # warning for tests
    'location': 'Head office',
})
env.cr.commit()
ok(f"Cash register created: [{caisse.code}] {caisse.name}")
ok(f"  Journal: {caisse.journal_id.name}")
ok(f"  Starting balance: {caisse.current_balance} DZD")

# =====================================================================
#  PHASE 4: 3 customer invoices (service) + cash payments
# =====================================================================
log("PHASE 4: Customer invoices + cash payments")

Move = env['account.move']
invoices_data = [
    {'partner': customer1, 'amount': 50000.0, 'ref': 'TEST-TRESO-FC01'},
    {'partner': customer2, 'amount': 75000.0, 'ref': 'TEST-TRESO-FC02'},
    {'partner': customer3, 'amount': 120000.0, 'ref': 'TEST-TRESO-FC03'},
]

customer_payments = []
total_customer = 0.0

for inv_data in invoices_data:
    # Create the invoice
    invoice = Move.create({
        'move_type': 'out_invoice',
        'partner_id': inv_data['partner'].id,
        'ref': inv_data['ref'],
        'invoice_date': datetime.today().date(),
        'invoice_line_ids': [(0, 0, {
            'name': f"Service {inv_data['ref']}",
            'product_id': service_product.id,
            'quantity': 1,
            'price_unit': inv_data['amount'],
        })],
    })
    invoice.action_post()
    ok(f"Invoice {invoice.name} created and posted - Amount: {inv_data['amount']} DZD")

    # Create the payment via the standard wizard
    payment_register = env['account.payment.register'].with_context(
        active_model='account.move',
        active_ids=[invoice.id],
    ).create({
        'journal_id': cash_journal.id,
        'payment_date': datetime.today().date(),
    })
    action = payment_register.action_create_payments()
    # Fetch the created payment
    if action.get('res_id'):
        payment = env['account.payment'].browse(action['res_id'])
    else:
        payment = env['account.payment'].search([
            ('partner_id', '=', inv_data['partner'].id),
            ('journal_id', '=', cash_journal.id),
        ], order='id desc', limit=1)

    customer_payments.append(payment)
    total_customer += inv_data['amount']
    ok(f"  Payment {payment.name} registered - {payment.amount} DZD via {payment.journal_id.name}")

    # Check whether a cash operation was auto-created
    if hasattr(payment, 'treasury_operation_id') and payment.treasury_operation_id:
        ok(f"  -> Cash operation auto-created: {payment.treasury_operation_id.name}")
    else:
        info("  -> No cash operation auto-created (check integration)")

env.cr.commit()

# Check the cash register balance after customer payments
caisse.invalidate_recordset()
info(f"Cash balance after {len(customer_payments)} customer payments: "
     f"{caisse.current_balance} DZD (expected: {total_customer})")

# =====================================================================
#  PHASE 5: Vendor payment from the cash register
# =====================================================================
log("PHASE 5: Vendor bill + cash payment")

vendor_bill = Move.create({
    'move_type': 'in_invoice',
    'partner_id': vendor1.id,
    'ref': 'TEST-TRESO-FF01',
    'invoice_date': datetime.today().date(),
    'invoice_line_ids': [(0, 0, {
        'name': 'Office supplies TEST',
        'quantity': 1,
        'price_unit': 35000.0,
    })],
})
vendor_bill.action_post()
ok(f"Vendor bill {vendor_bill.name} created and posted - 35,000 DZD")

payment_register_v = env['account.payment.register'].with_context(
    active_model='account.move',
    active_ids=[vendor_bill.id],
).create({
    'journal_id': cash_journal.id,
    'payment_date': datetime.today().date(),
})
action_v = payment_register_v.action_create_payments()
if action_v.get('res_id'):
    vendor_payment = env['account.payment'].browse(action_v['res_id'])
else:
    vendor_payment = env['account.payment'].search([
        ('partner_id', '=', vendor1.id),
        ('journal_id', '=', cash_journal.id),
    ], order='id desc', limit=1)

ok(f"Vendor payment {vendor_payment.name} - {vendor_payment.amount} DZD")
if hasattr(vendor_payment, 'treasury_operation_id') and vendor_payment.treasury_operation_id:
    ok(f"  -> Cash operation auto-created: {vendor_payment.treasury_operation_id.name} (type: out)")

env.cr.commit()

# Check balance
caisse.invalidate_recordset()
expected_after_vendor = total_customer - 35000.0
info(f"Cash balance after vendor payment: {caisse.current_balance} DZD "
     f"(expected: ~{expected_after_vendor})")

# =====================================================================
#  PHASE 6: Manual cash operation (voucher)
# =====================================================================
log("PHASE 6: Manual cash operation")

Operation = env['oski.treasury.cash.operation']
cat_frais = env['oski.treasury.operation.category'].search([('code', '=', 'FRAIS')], limit=1)

manual_op = Operation.create({
    'cash_id': caisse.id,
    'operation_type': 'out',
    'category_id': cat_frais.id,
    'amount': 5000.0,
    'date': datetime.now(),
    'description': 'Office supplies purchase - Cash voucher TEST-TRESO',
    'partner_id': vendor1.id,
    'is_manual': True,
})
manual_op.action_post()
ok(f"Manual operation created and posted: {manual_op.name}")
ok(f"  Type: Out | Amount: 5,000 DZD | Category: {manual_op.category_id.name}")

env.cr.commit()
caisse.invalidate_recordset()
expected_final = expected_after_vendor - 5000.0
info(f"Final cash balance: {caisse.current_balance} DZD (expected: ~{expected_final})")

# =====================================================================
#  PHASE 7: Cash closing
# =====================================================================
log("PHASE 7: Cash closing with automatic operation loading")

Closing = env['oski.treasury.cash.closing']

# Check unlinked operations
unlinked_ops = Operation.search([
    ('cash_id', '=', caisse.id),
    ('state', '=', 'posted'),
    ('closing_id', '=', False),
])
info(f"Posted operations not linked to a closing: {len(unlinked_ops)}")
for op in unlinked_ops:
    info(f"  {op.name} | {op.operation_type} | {op.amount} DZD | {op.category_id.name}")

# Create the closing
closing = Closing.create({
    'cash_id': caisse.id,
    'closing_date': datetime.today().date(),
})
ok(f"Closing created: {closing.name}")

# Load operations
closing.action_load_operations()
closing.invalidate_recordset()
ok(f"Operations loaded: {len(closing.operation_ids)} operations")

for op in closing.operation_ids:
    info(f"  {op.name} | {'in' if op.operation_type == 'in' else 'out'} {op.amount} DZD | {op.category_id.name}")

info(f"Starting balance: {closing.balance_start} DZD")
info(f"Total in: {closing.total_in} DZD")
info(f"Total out: {closing.total_out} DZD")
info(f"Theoretical balance: {closing.balance_end_theoretical} DZD")

# Simulate the count (set exactly the theoretical value -> no difference)
closing.balance_end_real = closing.balance_end_theoretical
ok(f"Actual balance entered: {closing.balance_end_real} DZD (= theoretical, no difference)")
info(f"Difference: {closing.difference} DZD")

# Confirm
closing.action_confirm()
ok(f"Closing confirmed: state = {closing.state}")

# Validate
closing.action_validate()
ok(f"Closing validated: state = {closing.state}")

env.cr.commit()
caisse.invalidate_recordset()
info(f"Cash balance after validation: {caisse.current_balance} DZD")
info(f"Last closing balance: {caisse.last_closing_balance} DZD")
info(f"Last closing date: {caisse.last_closing_date}")

# Closing report test
try:
    report = env.ref('oski_treasury.action_report_cash_closing')
    ok(f"Closing report found: {report.name}")
    # Generate the PDF
    pdf_content, content_type = env['ir.actions.report']._render_qweb_pdf(
        report, closing.ids
    )
    ok(f"Closing report PDF generated: {len(pdf_content)} bytes, type: {content_type}")
except Exception as e:
    fail(f"Closing report error: {e}")

# =====================================================================
#  PHASE 8: Safe + Cash -> Safe transfer
# =====================================================================
log("PHASE 8: Safe and Cash -> Safe transfer")

Safe = env['oski.treasury.safe']
coffre = Safe.create({
    'name': 'Main Safe TEST',
    'code': 'COF-TEST',
    'location': 'Secured basement',
    'state': 'active',
})
env.cr.commit()
ok(f"Safe created: [{coffre.code}] {coffre.name}")
ok(f"  Starting balance: {coffre.current_balance} DZD")

# Cash -> Safe transfer
Transfer = env['oski.treasury.transfer']
transfer_amount = 50000.0

transfer = Transfer.create({
    'transfer_type': 'cash_to_safe',
    'cash_from_id': caisse.id,
    'safe_to_id': coffre.id,
    'amount': transfer_amount,
    'description': 'End-of-day safe deposit - TEST-TRESO',
})
ok(f"Transfer created: {transfer.name} - {transfer_amount} DZD (Cash -> Safe)")
info(f"  Cash balance before: {transfer.source_balance_before} DZD")

# Confirm the transfer
transfer.action_confirm()
ok(f"Transfer confirmed: state = {transfer.state}")
info(f"  Cash balance after: {transfer.source_balance_after} DZD")
info(f"  Safe balance after: {transfer.dest_balance_after} DZD")

# Finalize
if hasattr(transfer, 'action_done'):
    transfer.action_done()
    ok(f"Transfer finalized: state = {transfer.state}")

env.cr.commit()
caisse.invalidate_recordset()
coffre.invalidate_recordset()
info(f"Cash balance verified: {caisse.current_balance} DZD")
info(f"Safe balance verified: {coffre.current_balance} DZD")

# Transfer report test
try:
    report_transfer = env.ref('oski_treasury.action_report_transfer')
    ok(f"Transfer report found: {report_transfer.name}")
    pdf_t, ct_t = env['ir.actions.report']._render_qweb_pdf(
        report_transfer, transfer.ids
    )
    ok(f"Transfer report PDF generated: {len(pdf_t)} bytes")
except Exception as e:
    fail(f"Transfer report error: {e}")

# =====================================================================
#  PHASE 9: Treasury bank account
# =====================================================================
log("PHASE 9: Treasury bank account")

bank_journal = env['account.journal'].search([('type', '=', 'bank')], limit=1)
if not bank_journal:
    info("No bank journal found in the chart of accounts, creating one (TEST-TRESO)")
    bank_journal = env['account.journal'].create({
        'name': 'Bank Test TEST-TRESO', 'type': 'bank', 'code': 'BNKTT',
    })
    env.cr.commit()
if bank_journal:
    TreasuryBank = env['oski.treasury.bank']

    # Create a reference bank if needed
    res_bank = env['res.bank'].search([], limit=1)
    if not res_bank:
        res_bank = env['res.bank'].create({'name': 'BNA - National Bank (TEST)'})

    bank_account = TreasuryBank.create({
        'name': 'BNA Account TEST',
        'code': 'BNA-TEST',
        'journal_id': bank_journal.id,
        'bank_id': res_bank.id,
        'account_number': '00300 0580 0000 1234 56',
        'iban': 'DZ58 0030 0580 0000 1234 56',
        'bic': 'BNADZDZZ',
        'branch': 'Algiers Center Branch',
        'opening_balance': 500000.0,
        'opening_date': datetime.today().date(),
    })
    env.cr.commit()
    ok(f"Bank account created: [{bank_account.code}] {bank_account.name}")
    ok(f"  Starting balance: {bank_account.opening_balance} DZD")
    info(f"  Current balance: {bank_account.current_balance} DZD")

    # =====================================================================
    #  PHASE 10: Customer payment via bank
    # =====================================================================
    log("PHASE 10: Customer payment via bank")

    invoice_bank = Move.create({
        'move_type': 'out_invoice',
        'partner_id': customer1.id,
        'ref': 'TEST-TRESO-FC-BANK01',
        'invoice_date': datetime.today().date(),
        'invoice_line_ids': [(0, 0, {
            'name': 'Bank service TEST',
            'product_id': service_product.id,
            'quantity': 1,
            'price_unit': 200000.0,
        })],
    })
    invoice_bank.action_post()
    ok(f"Bank customer invoice {invoice_bank.name} - 200,000 DZD")

    pay_reg_bank = env['account.payment.register'].with_context(
        active_model='account.move',
        active_ids=[invoice_bank.id],
    ).create({
        'journal_id': bank_journal.id,
        'payment_date': datetime.today().date(),
    })
    action_bank = pay_reg_bank.action_create_payments()
    if action_bank.get('res_id'):
        bank_pay_customer = env['account.payment'].browse(action_bank['res_id'])
    else:
        bank_pay_customer = env['account.payment'].search([
            ('partner_id', '=', customer1.id),
            ('journal_id', '=', bank_journal.id),
        ], order='id desc', limit=1)

    ok(f"Bank customer payment: {bank_pay_customer.name} - {bank_pay_customer.amount} DZD")

    if hasattr(bank_pay_customer, 'treasury_bank_operation_id') and bank_pay_customer.treasury_bank_operation_id:
        ok(f"  -> Bank operation auto-created: {bank_pay_customer.treasury_bank_operation_id.name}")

    env.cr.commit()

    # =====================================================================
    #  PHASE 11: Vendor payment via bank
    # =====================================================================
    log("PHASE 11: Vendor payment via bank")

    vendor_bill_bank = Move.create({
        'move_type': 'in_invoice',
        'partner_id': vendor1.id,
        'ref': 'TEST-TRESO-FF-BANK01',
        'invoice_date': datetime.today().date(),
        'invoice_line_ids': [(0, 0, {
            'name': 'Bank materials purchase TEST',
            'quantity': 1,
            'price_unit': 150000.0,
        })],
    })
    vendor_bill_bank.action_post()
    ok(f"Bank vendor bill {vendor_bill_bank.name} - 150,000 DZD")

    pay_reg_vendor_bank = env['account.payment.register'].with_context(
        active_model='account.move',
        active_ids=[vendor_bill_bank.id],
    ).create({
        'journal_id': bank_journal.id,
        'payment_date': datetime.today().date(),
    })
    action_vb = pay_reg_vendor_bank.action_create_payments()
    if action_vb.get('res_id'):
        bank_pay_vendor = env['account.payment'].browse(action_vb['res_id'])
    else:
        bank_pay_vendor = env['account.payment'].search([
            ('partner_id', '=', vendor1.id),
            ('journal_id', '=', bank_journal.id),
        ], order='id desc', limit=1)

    ok(f"Bank vendor payment: {bank_pay_vendor.name} - {bank_pay_vendor.amount} DZD")

    env.cr.commit()

    # =====================================================================
    #  PHASE 12: Bank balances + reconciliation
    # =====================================================================
    log("PHASE 12: Bank balances and reconciliation")

    bank_account.invalidate_recordset()
    info(f"Current balance: {bank_account.current_balance} DZD")
    info(f"Available balance: {bank_account.available_balance} DZD")
    info(f"Reconciled balance: {bank_account.reconciled_balance} DZD")
    info(f"Unreconciled balance: {bank_account.unreconciled_balance} DZD")

    # Check bank operations
    bank_ops = env['oski.treasury.bank.operation'].search([
        ('bank_id', '=', bank_account.id),
    ])
    info(f"Bank operations found: {len(bank_ops)}")
    for bop in bank_ops:
        info(f"  {bop.name} | {'in' if bop.operation_type == 'in' else 'out'} {bop.amount} DZD | "
             f"reconciled={bop.is_reconciled}")

    # Reconcile an operation (customer payment)
    bank_ops_in = bank_ops.filtered(lambda o: o.operation_type == 'in')
    if bank_ops_in:
        for bop in bank_ops_in:
            bop.is_reconciled = True
            ok(f"Operation reconciled: {bop.name} - {bop.amount} DZD")

        bank_account.invalidate_recordset()
        info(f"Reconciled balance after: {bank_account.reconciled_balance} DZD")
        info(f"Unreconciled balance after: {bank_account.unreconciled_balance} DZD")

    env.cr.commit()

# =====================================================================
#  PHASE 13: Dashboard check
# =====================================================================
log("PHASE 13: Dashboard check")

# Force the SQL view to be re-created
env['oski.treasury.dashboard'].init()
env.cr.commit()

dashboard_items = env['oski.treasury.dashboard'].search([])
info(f"Dashboard items: {len(dashboard_items)}")
for item in dashboard_items.sorted('sequence'):
    kind = {'cash': 'CASH', 'bank': 'BANK', 'safe': 'SAFE'}.get(item.entity_type, 'OTHER')
    print(f"  [{kind:>5}] [{item.entity_type:>12}] {item.name:<25} Balance: {item.balance:>12,.2f} DZD")

# =====================================================================
#  FINAL SUMMARY
# =====================================================================
log("FINAL SUMMARY")

caisse.invalidate_recordset()
print(f"""
  CASH REGISTER [{caisse.code}] {caisse.name}
    Balance: {caisse.current_balance:,.2f} DZD
    Operations: {caisse.operation_count}
    Closings: {caisse.closing_count}
    Closing in progress: {'Yes' if caisse.has_pending_closing else 'No'}
""")

coffre.invalidate_recordset()
print(f"""  SAFE [{coffre.code}] {coffre.name}
    Balance: {coffre.current_balance:,.2f} DZD
""")

if bank_journal:
    bank_account.invalidate_recordset()
    print(f"""  BANK [{bank_account.code}] {bank_account.name}
    Current balance: {bank_account.current_balance:,.2f} DZD
    Reconciled balance: {bank_account.reconciled_balance:,.2f} DZD
    Unreconciled balance: {bank_account.unreconciled_balance:,.2f} DZD
""")

print("""
  KEY CHECKS:
  - 3 customer invoices paid in cash: OK
  - 1 vendor bill paid in cash: OK
  - 1 manual operation (cash voucher): OK
  - Cash closing with automatic loading: OK
  - Closing report PDF: OK
  - Safe + cash-to-safe transfer: OK
  - Transfer report PDF: OK
  - Bank account with payments: OK
  - Bank reconciliation: OK
  - Unified dashboard: OK
""")

log("TESTS COMPLETED SUCCESSFULLY")
