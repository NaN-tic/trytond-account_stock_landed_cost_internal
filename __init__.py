# This file is part account_stock_landed_cost_internal module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import account, stock

def register():
    Pool.register(
        account.LandedCost,
        account.LandedCostShipmentInternal,
        stock.Move,
        stock.Location,
        module='account_stock_landed_cost_internal', type_='model')
    Pool.register(
        module='account_stock_landed_cost_internal', type_='wizard')
    Pool.register(
        module='account_stock_landed_cost_internal', type_='report')
