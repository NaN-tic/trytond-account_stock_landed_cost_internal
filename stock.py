from decimal import Decimal
from trytond.pool import PoolMeta, Pool
from trytond.model import fields
from trytond.pyson import Eval


class Move(metaclass=PoolMeta):
    __name__ = 'stock.move'

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
                        if new_values.get('unit_price') is None and move.unit_price is None:
                            new_values['unit_price'] = Decimal(0)
                        if new_values.get('currency') is None and move.currency is None:
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

    def get_cost_price(self, product_cost_price=None):
        if self.from_location.transit or self.to_location.transit:
            if product_cost_price is None:
                product_cost_price = self.product.get_multivalue(
                    'cost_price', **self._cost_price_pattern)
            return product_cost_price + (self.unit_landed_cost or Decimal(0))
        return super().get_cost_price(product_cost_price)

    def _do(self):
        "Return cost_price and a list of moves to save"
        cost_price_method = self.product.get_multivalue(
            'cost_price_method', **self._cost_price_pattern)
        if cost_price_method == 'average' and (self.from_location.transit
                or self.to_location.transit):
            return self._compute_product_cost_price('in'), []
        return super()._do()


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    transit = fields.Boolean('Transit',
        states={
            'invisible': Eval('type') != 'storage',
        })

