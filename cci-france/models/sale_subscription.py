from odoo import fields, models


class SaleSubscription(models.Model):
    """
    Override sale_subscription model
    """

    _inherit = 'sale.subscription'

    is_membership = fields.Boolean(
        string='Adhesion', default=False,
        help='Cocher cette case si cet abonnement est de type adhesion')
    individual_member = fields.Boolean(
        string='Membre individuel', default=False,
        help="Case cochée si une cotisation à titre individuelle est validée sur la période en cours")
    contact_ids = fields.Many2many(
        'res.partner', string="Contacts",
        help="""Certaines chambres facturent une adhésion à la société membre, puis facturent une adhésion additionnelle par contact considérés comme membre au sein de l’entreprise. Il faut donc pouvoir identifier quels sont les contacts de l’entreprise qui doivent obtenir le statut membre via l’adhésion enregistrée""")
    all_members = fields.Boolean(
        string='Tous les contacts',
        help='Cochez cette case si tous les contacts sont membre')
