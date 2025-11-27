from trytond.pool import PoolMeta
from trytond.model import fields, ModelSQL
from trytond.pyson import Eval
from trytond.i18n import gettext
from trytond.model.exceptions import ValidationError


class LandedCost(metaclass=PoolMeta):
    __name__ = 'account.landed_cost'

    shipments_internal = fields.Many2Many(
        'account.landed_cost-stock.shipment.internal', 'landed_cost', 'shipment',
        'Internal Shipments',
        domain=[
            ('company', '=', Eval('company', -1)),
            ('state', 'in', ['done']),
        ],
        states={
            'readonly': Eval('state') != 'draft',
        })

    @classmethod
    def validate(cls, landed_costs):
        super().validate(landed_costs)
        for landed_cost in landed_costs:
            landed_cost.check_shipments_internal()

    def check_shipments_internal(self):
        for shipment in self.shipments_internal:
            if not shipment.transit_location:
                raise ValidationError(gettext('account_stock_landed_cost_internal.msg_no_transit_location',
                    shipment=shipment.rec_name))


    def stock_moves(self):
        moves = super().stock_moves()
        for shipment in self.shipments_internal:
            for move in shipment.moves:
                if move.state != 'cancelled' and self._stock_move_filter(move):
                    moves.append(move)
        return moves

class LandedCostShipmentInternal(ModelSQL):
    'Landed Cost Shipment Internal'
    __name__ = 'account.landed_cost-stock.shipment.internal'

    landed_cost = fields.Many2One(
        'account.landed_cost', 'Landed Cost',
        required=True, ondelete='CASCADE')
    shipment = fields.Many2One(
        'stock.shipment.internal', 'Internal Shipment',
        required=True, ondelete='CASCADE')
