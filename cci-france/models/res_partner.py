from . import membership

from datetime import date
from odoo import fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):

    _inherit = 'res.partner'

    is_member = fields.Boolean(
        string='Est Membre',
        compute="_compute_is_member", search="_search_is_member",
        help="Case cochée automatiquement lorsqu'une une adhésion est validée pour la période en cours.")
    individual_member = fields.Boolean(
        string='Membre individuel',
        help="Case cochée si une cotisation à titre individuelle est validée sur la période en cours")
    date_first_start = fields.Date(
        string='Date Première adhésion',
        compute="compute_date_first_start",
        help="Date de la première adhesion du membre")
    date_last_stop = fields.Date(
        string="Date fin adhésion",
        compute="compute_date_last_stop",
        help="date de fin de la dernière adhésion valide")
    membership_type = fields.Char(
        string='Type Adhesion', size=64, compute="_membership_type",
        help="Type d'adhesion, récupéré sur le service")
    total_membership = fields.Integer(
        string='Nombre adhesion', help='Nombre total des adhésion',
        compute="_total_membership")

    # FIXME: Delete this fields ???
    # membership_state = fields.Selection(
    #    selection_add=membership._STATE,
    #    store=True,
    #    compute="_compute_membership_state",
    #    string="Statut actuel de l'adhérent", help="")

    def _total_membership(self):
        """
        Count the number of invoice for this partner
        """
        subscription_mdl = self.env['sale.subscription']
        for partner in self:
            partner.total_membership = subscription_mdl.search_count([
                ('partner_id', '=', partner.id), ('is_membership', '=', True)])

    def action_view_partner_membership(self):
        """
        Open list of current partner membership
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cci-france.sale_subscription_action_inherit")
        action['domain'] = [('partner_id', 'child_of', self.id)]

        return action

    def _compute_is_member(self):
        """
        Compute the is_member fiels base on sale.subscription health
        """
        for partner in self:
            partner.is_member = False
            # get the lastest subscription
            subscription = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id)], order="id desc", limit=1)
            if subscription and subscription.health != "bad":
                partner.is_member = True


    def _search_is_member(self, operator, value):
        """
        Implement search method to used on is_member computed field
        """
        recs = self.search([]).filtered(lambda partner : partner.is_member is True )

        if recs:
            return [('id', 'in', [x.id for x in recs])]


    def _compute_individual_member(self):
        """
        Check the individual member field on sale.subscription model
        an assing the value on current partner
        """
        # FIXME
        pass

    def _membership_type(self):
        """
        Compute the subscription type field base on the last
        subscription templace register for this partner
        """
        if not self:
            return

        for partner in self:
            last_subscription = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id)], order="id desc", limit=1)

            if not last_subscription:
                partner.membership_type = None
            else:
                partner.membership_type = last_subscription.template_id.name

    def compute_date_first_start(self):
        """
        Determine la date de la première adhesion payée
        """
        if not self:
            return

        for partner in self:
            first_date = None
            subscriptions = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id)])
            for subscription in subscriptions:
                if not first_date:
                    first_date = subscription.date_start
                elif subscription.date_start < first_date:
                    first_date = subscription.date_start
            partner.date_first_start = first_date

    def compute_date_last_stop(self):
        """
        Determine la date de fin de la dernière adhesion
        """
        for partner in self:
            last_date = None
            subscriptions = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id)])
            for subscription in subscriptions:
                if not last_date:
                    last_date = subscription.date
                elif subscription.date > last_date:
                    last_date = subscription.date
            partner.date_last_stop = last_date
