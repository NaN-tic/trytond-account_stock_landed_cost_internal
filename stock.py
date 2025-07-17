from trytond.pool import PoolMeta, Pool
from trytond.model import fields
from trytond.pyson import Eval
from trytond.transaction import Transaction


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

    """@classmethod
    def create(cls, vlist):
        pool = Pool()
        Location = pool.get('stock.location')
        Company = pool.get('company.company')
        Product = pool.get('product.product')
        company_id = Transaction().context.get('company')
        vlist = [x.copy() for x in vlist]
        for vals in vlist:
            from_location = Location(vals.get('from_location'))
            to_location = Location(vals.get('to_location'))
            company = Company(vals.get('company', company_id))
            product = Product(vals.get('product'))
            if vals.get('state', cls.default_state()) != 'done':
                continue
            if ((from_location and from_location.transit) or (to_location and to_location.transit)):
                move = cls(company=company)
                cost_price = product.get_multivalue(
                    'cost_price', **move._cost_price_pattern)

                if cost_price and 'unit_price' not in vals:
                    vals['unit_price'] = cost_price
                if 'currency' not in vals:
                    vals['currency'] = company.currency.id

        return super().create(vlist)"""

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Location = pool.get('stock.location')
        actions = iter(args)
        new_args = []
        for moves, values in zip(actions, actions):
            for move in moves:
                new_values = values.copy()
                if new_values.get('from_location'):
                    from_location = Location(new_values.get('from_location'))
                else:
                    from_location = move.from_location
                if new_values.get('to_location'):
                    to_location = Location(new_values.get('to_location'))
                else:
                    to_location = move.to_location
                if new_values.get('state'):
                    state = new_values.get('state')
                else:
                    state = move.state

                if state == 'done':
                    if from_location.transit or to_location.transit:
                        if 'unit_price' not in new_values and move.unit_price is None:
                            product = move.product
                            cost_price = product.get_multivalue(
                                'cost_price', **move._cost_price_pattern)
                            if cost_price and move.unit_price != cost_price:
                                new_values['unit_price'] = cost_price

                        if 'currency' not in new_values and move.currency is None:
                            currency = move.company.currency
                            if move.currency != currency:
                                new_values['currency'] = currency.id

                new_args.append([move])
                new_args.append(new_values)

        if new_args:
            super().write(*new_args)

    @fields.depends('from_location', 'to_location', 'state')
    def on_change_with_unit_price_required(self, name=None):
        if super().on_change_with_unit_price_required(name):
            return True
        if self.state != 'done':
            return False
        if self.from_location and self.from_location.transit:
            return True
        if self.to_location and self.to_location.transit:
            return True
        return False

    def on_change_with_cost_price_required(self, name=None):
        if super().on_change_with_cost_price_required(name):
            return True
        if self.from_location and self.from_location.transit:
            return True
        if self.to_location and self.to_location.transit:
            return True
        return False

    """@fields.depends('from_location', 'product', 'currency', 'unit_price')
    def on_change_from_location(self, name=None):
        if self.from_location and self.from_location.transit:
            product = self.product
            company = self.company
            if not self.unit_price and product:
                cost_price = product.get_multivalue(
                    'cost_price', **self._cost_price_pattern)
                if cost_price:
                    self.unit_price = cost_price
            if not self.currency:
                self.currency = company.currency.id


    @fields.depends('to_location', 'product', 'currency', 'unit_price')
    def on_change_to_location(self, name=None):
        if self.to_location and self.to_location.transit:
            product = self.product
            company = self.company
            if not self.unit_price and product:
                cost_price = product.get_multivalue(
                    'cost_price', **self._cost_price_pattern)
                if cost_price:
                    self.unit_price = cost_price
            if not self.currency:
                self.currency = company.currency.id


    @fields.depends('product', 'from_location', 'to_location', 'company', 'unit_price', 'currency')
    def on_change_product(self):
        super().on_change_product()
        if ((self.from_location and self.from_location.transit)
        or (self.to_location and self.to_location.transit)) and self.product:
            product = self.product
            company = self.company
            if not self.unit_price or self.unit_price != product.cost_price:
                cost_price = product.get_multivalue(
                    'cost_price', **self._cost_price_pattern)
                if cost_price:
                    self.unit_price = cost_price
            if not self.currency:
                self.currency = company.currency.id"""



class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    transit = fields.Boolean(
        "Transit",
        states={
            'invisible': Eval('type') != 'storage',
        })

