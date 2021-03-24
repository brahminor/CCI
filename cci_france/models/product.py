from odoo import fields, models


class Product(models.Model):
    """
    Override product model
    """
    _inherit = "product.template"

    membership_type_id = fields.Many2one('membership.type', string='Type Adhesion')
