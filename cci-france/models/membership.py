from datetime import datetime
from dateutil import relativedelta

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_STATE = [
    ('draft', 'Nouveau'),
    ('to_invoice', 'A facturer'),
    ('invoiced', 'En attente de paiement'),
    ('paid', 'Payée'),
    ('canceled', 'Annulée/Suspendue'),
]

class SaleOrder(models.Model):
    _inherit = "sale.order"

    membership_line_id = fields.Many2one(
        'membership.membership_line', string='Adhesion',
        help="Ligne adhesion liée à ce bon de commande")


class AccountMove(models.Model):
    """
    Lien entre les factures et l'adhesion
    """
    _inherit = "account.move"

    membership_line_id = fields.Many2one(
        'membership.membership_line', string='Adhesion',
        help="Ligne adhesion liée à cette facture")


class MembershipType(models.Model):
    """
    Type d'adhésion
    """
    _name = "membership.type"
    _description = "Type d'adhesion"

    name = fields.Char(string='Nom', size=64, required=True, help="Nom du type d'adhésion")
    description = fields.Text(string='Description', )


class MembershipLine(models.Model):
    _inherit = "membership.membership_line"
    _description = "Ligne d'adhesion"

    name = fields.Char(string='Nom', tracking=True, size=64, help='Designation adhesion')
    partner = fields.Many2one(
        'res.partner', string='Contact/Societe', ondelete='cascade',
        index=True, required=True)
    user = fields.Many2one(
        'res.users', string='Responsable',
        help='Utilisateur Odoo responsable de cette adhésion')
    state = fields.Selection(
        selection_add=_STATE, compute='_compute_state',
        string='Statut Adherent', store=True,
        default="draft", help="Indique le statut de l'adherent")
    individual_member = fields.Boolean(
        string='Membre individuel', related="partner.individual_member",
        readonly=True, store=True,
        help="Case cochée si une cotisation à titre individuelle est validée sur la période   en cours")
    company_id = fields.Many2one('res.company', string="Societé", readonly=False)
    date_from = fields.Date(
        string='From', readonly=False, required=True,
        default=datetime.now().strftime('%Y-01-01'))
    date_to = fields.Date(
        string='To', readonly=False, required=True,
        default=datetime.now().strftime('%Y-12-31'))
        # default=str(datetime.now() + relativedelta.relativedelta(
        #    months=+1, day=1, days=-1))[:10])
    member_price = fields.Float(
        string="Frais adhésion", digits='Product Price', required=False,
        store=True, related="membership_id.lst_price")
    sale_order_ids = fields.Many2many('sale.order', string="Bon de commande", )
    account_move_ids = fields.One2many(
        'account.move', 'membership_line_id', string="Factures",
        compute="_get_membership_invoice")
    contact_ids = fields.Many2many('res.partner', string="Contacts", help="Certaines chambres facturent une adhésion à la société membre, puis facturent une adhésion additionnelle par contact considérés comme membre au sein de l’entreprise. Il faut donc pouvoir identifier quels sont les contacts de l’entreprise qui doivent obtenir le statut membre via l’adhésion enregistrée")
    all_members = fields.Boolean(
        string='Tous les contacts',
        help='Cochez cette case si tous les contacts sont membre')

    is_valid_membership = fields.Boolean(
        string="Adhesion valide", compute="check_valid_membership",
        help="Check if a membership is valid")

    # -----------------------------------------------
    # COMPUTE METHODS
    # -----------------------------------------------

    def _get_membership_invoice(self):
        """
        Get all invoices link to this membership
        """
        if not self:
            # Case create
            return

        for membership in self:
            invoices = self.env['account.move'].search([
                ('membership_line_id', '=', membership.id)])
            membership.account_move_ids = invoices

    def check_valid_membership(self):
        """
        Pour qu’une adhésion soit valide et donne le statut membre,
        il faut qu’elle respecte les conditions suivantes :
            - Statut = « En attente de paiement » OU « Payée »
            - Date de début <= date du jour
            - Date de fin >= date du jour
        """
        if not self:
            return

        today = fields.Date.today()
        for mship in self:
            if mship.state in ('invoiced', 'paid'):
                condition = bool(
                    (mship.date_from and mship.date_from <= today) and
                    (mship.date_to and mship.date_to >= today))
                if condition:
                    mship.is_valid_membership = True
                else:
                    mship.is_valid_membership = False

    def _compute_state(self):
        """
        Compute the membership state
        A membership is set to invoiced when all draft invoices are confirm
        """
        if not self:
            return

        for membership in self:
            if not membership.state:
                membership.state = "draft"  # Default state
            for move in membership.account_move_ids:
                if move.state == 'cancel':
                    # We can have membership without invoice
                    continue
                elif move.state == 'posted':
                    if move.payment_state in ("paid", "in_payment"):
                        membership.state = 'paid'
                    else:
                        membership.state = 'invoiced'
                elif move.state == 'draft':
                    membership.state = 'to_invoice'
                else:
                    pass

    def button_cancel(self):
        """
        Mark a membership as canceled
        """
        today = fields.Date.today()
        self.write({'state': 'canceled', 'date_cancel': today})

    def action_create_invoice(self):
        """
        Create an invoice linked to the current membership
        """
        invoice_vals_list = []
        for membership in self:
            partner = membership.partner
            product = membership.membership_id
            addr = partner.address_get(['invoice'])

            if not addr.get('invoice', False):
                raise UserError(_("Partner doesn't have an address to make the invoice."))

            invoice_vals_list.append({
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'membership_line_id': membership.id,
                'invoice_line_ids': [(0, None, {
                    'product_id': product.id, 'quantity': 1,
                    'price_unit': membership.member_price,
                    'tax_ids': [(6, 0, product.taxes_id.ids)]})]
            })

        return self.env['account.move'].create(invoice_vals_list)


    def action_post(self):
        """
        Change membership state
        """
        for membership in self:
            if membership.state == 'draft':
                membership.write({'state': 'to_invoice'})
            elif membership.state == 'canceled':
                membership.write({'state': 'draft'})
            else:
                pass
