import unittest
import datetime as dt
from decimal import Decimal

from proteus import Model
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules
from trytond.modules.account.tests.tools import create_chart, create_fiscalyear, get_accounts
from trytond.modules.account_invoice.tests.tools import set_fiscalyear_invoice_sequences
from trytond.modules.company.tests.tools import create_company, get_company


class TestInternalLandedCost(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        activate_modules(['account_stock_landed_cost_internal'])

        # Setup
        create_company()
        company = get_company()
        self.company = company
        today = dt.date.today()
        tomorrow = today + dt.timedelta(days=1)
        yesterday = today - dt.timedelta(days=1)

        # Fiscal year and chart
        fiscalyear = set_fiscalyear_invoice_sequences(create_fiscalyear(company))
        fiscalyear.click('create_period')
        _ = create_chart(company)
        accounts = get_accounts(company)
        expense = accounts['expense']
        revenue = accounts['revenue']

        # Party
        Party = Model.get('party.party')
        party = Party(name='Party')
        party.save()

        # Product category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.save()
        category = ProductCategory(name="Category")
        category.save()

        # Product
        ProductUom = Model.get('product.uom')
        ProductTemplate = Model.get('product.template')
        unit, = ProductUom.find([('name', '=', 'Unit')])

        template = ProductTemplate()
        template.name = 'Product'
        template.type = 'goods'
        template.default_uom = unit
        template.list_price = Decimal('100')
        template.cost_price_method = 'average'
        template.account_category = account_category
        template.categories.append(ProductCategory(category.id))
        template.save()
        product, = template.products
        product.cost_price = Decimal('80')
        product.save()

        # Product with landed cost
        template2 = ProductTemplate()
        template2.name = 'Landed Cost'
        template2.type = 'service'
        template2.default_uom = unit
        template2.list_price = Decimal('1000')
        template2.landed_cost = True
        template2.account_category = account_category
        template2.save()
        product_landed_cost, = template2.products
        product_landed_cost.cost_price = Decimal('1000')
        product_landed_cost.save()

        # Locations
        Location = Model.get('stock.location')
        warehouse1, = Location.find([('type', '=', 'warehouse')])
        warehouse2, = warehouse1.duplicate()
        warehouse1.save()
        warehouse2.save()

        # Set transit bool in Transit location
        transit_location, = Location.find([('name', '=', 'Transit')])
        transit_location.transit = True
        transit_location.save()

        # Lead time for transit
        LeadTime = Model.get('stock.location.lead_time')
        lead_time = LeadTime()
        lead_time.warehouse_from = warehouse1
        lead_time.warehouse_to = warehouse2
        lead_time.lead_time = dt.timedelta(days=1)
        lead_time.save()

        # Internal Shipment
        Shipment = Model.get('stock.shipment.internal')
        shipment = Shipment()
        shipment.company = company
        shipment.from_location = warehouse1.storage_location
        shipment.to_location = warehouse2.storage_location
        shipment.planned_date = tomorrow
        shipment.save()

        move = shipment.moves.new()
        move.product = product
        move.quantity = 10
        move.unit = unit
        move.from_location = shipment.from_location
        move.to_location = shipment.to_location
        shipment.save()
        shipment.click('wait')

        outgoing_move, = shipment.outgoing_moves
        incoming_move, = shipment.incoming_moves

        self.assertEqual(outgoing_move.from_location, shipment.from_location)
        self.assertEqual(outgoing_move.to_location, shipment.transit_location)
        self.assertEqual(incoming_move.from_location, shipment.transit_location)
        self.assertEqual(incoming_move.to_location, shipment.to_location)

        shipment.click('assign_force')
        shipment.effective_start_date = yesterday
        shipment.click('pack')
        self.assertEqual(shipment.outgoing_moves[0].state, 'assigned')
        shipment.click('ship')
        self.assertEqual(shipment.outgoing_moves[0].state, 'done')
        self.assertEqual(shipment.outgoing_moves[0].effective_date, yesterday)

        shipment.click('do')
        self.assertEqual(shipment.incoming_moves[0].state, 'done')
        self.assertEqual(shipment.outgoing_moves[0].currency, company.currency)
        self.assertEqual(shipment.incoming_moves[0].currency, company.currency)

        # Payment term
        PaymentTerm = Model.get('account.invoice.payment_term')
        payment_term = PaymentTerm(name='Term')
        payment_term.lines.new(type='remainder')
        payment_term.save()

        # Invoice
        Invoice = Model.get('account.invoice')
        invoice = Invoice()
        invoice.party = party
        invoice.type = 'in'
        invoice.payment_term = payment_term
        invoice.invoice_date = today
        line = invoice.lines.new()
        line.product = product_landed_cost
        line.quantity = 1
        line.unit_price = Decimal('1000')
        invoice.click('post')

        # Landed Cost
        LandedCost = Model.get('account.landed_cost')
        landed_cost = LandedCost()
        shipment, = landed_cost.shipments_internal.find([])
        landed_cost.shipments_internal.append(shipment)
        InvoiceLine = Model.get('account.invoice.line')
        invoice_line, = InvoiceLine.find([('invoice', '=', invoice.id),
                                          ('product.landed_cost', '=', True),])
        landed_cost.invoice_lines.append(invoice_line)
        landed_cost.allocation_method = 'value'
        landed_cost.categories.append(account_category)
        landed_cost.save()

        # Post landed cost
        wizard = landed_cost.click('post_wizard')
        wizard.execute('post')

        # Las checkings
        shipment.reload()

        self.assertEqual(landed_cost.state, 'posted')

        incoming_move, = shipment.incoming_moves
        outgoing_move, = shipment.outgoing_moves

        self.assertEqual((incoming_move.unit_landed_cost + outgoing_move.unit_landed_cost), Decimal('100'))
        self.assertEqual(incoming_move.cost_price, Decimal('80'))
        self.assertEqual(outgoing_move.cost_price, Decimal('80'))
        self.assertEqual(incoming_move.currency, company.currency)
        self.assertEqual(outgoing_move.currency, company.currency)
