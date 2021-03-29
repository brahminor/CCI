from . import membership

from datetime import date
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ResPartner(models.Model):

    _inherit = 'res.partner'

    is_member = fields.Boolean(
        string='Est Membre',
        help="Case cochée automatiquement lorsqu'une une adhésion est validée pour la période en cours.")
    individual_member = fields.Boolean(
        string='Membre individuel', compute="_compute_individual_member",
        help="Case cochée si une cotisation à titre individuelle est validée sur la période en cours")
    date_first_start = fields.Date(
        string='Date Première adhésion',
        help="Date de la première adhesion du membre")
    date_last_stop = fields.Date(
        string="Date fin adhésion",
        help="date de fin de la dernière adhésion valide")
    membership_type = fields.Char(
        string='Type Adhesion', size=64,
        help="Type d'adhesion, récupéré sur le service")
    total_membership = fields.Integer(
        string='Nombre adhesion', help='Nombre total des adhésion',
        compute="_total_membership")

    def _total_membership(self):
        """
        Count the number of invoice for this partner
        """
        subscription_mdl = self.env['sale.subscription']
        for partner in self:
            subscription_count = subscription_mdl.search_count([
                ('partner_id', '=', partner.id),
                ('is_membership', '=', True)])
            partner.total_membership = subscription_count

    def action_view_partner_membership(self):
        """
        Open list of current partner membership
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cci_france.sale_subscription_action_inherit")
        action['domain'] = [('partner_id', 'child_of', self.id)]

        return action

    def _compute_individual_member(self):
        """
        Check the individual member field on sale.subscription model
        an assing the value on current partner

        Note: Individuel_member is only for non company subscription
        """
        for partner in self:
            partner.individual_member = False
            # get the lastest subscription
            subscription = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id)], order="id desc", limit=1)
            if subscription and subscription.individual_member:
                partner.individual_member = True

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
                partner.write({
                    'membership_type': last_subscription.membership_type_id.name})

    def get_date_first_start(self):
        """
        Determine la date de la première adhesion valide
        """
        for partner in self:
            first_date = None

            subscriptions = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id),
                ('is_membership', '=', True),
                ('stage_id.category', '=', 'progress')])
            for subscription in subscriptions:
                if not first_date:
                    first_date = subscription.date_start
                elif subscription.date_start and subscription.date_start < first_date:
                    first_date = subscription.date_start
            return first_date

    def get_date_last_stop(self):
        """
        Determine la date de fin de la dernière adhesion valide
        """

        for partner in self:
            last_date = None

            subscriptions = self.env['sale.subscription'].search([
                ('partner_id', '=', partner.id),
                ('is_membership', '=', True),
                ('stage_id.category', '=', 'progress')])
            for subscription in subscriptions:
                if not last_date:
                    last_date = subscription.date
                elif subscription.date and subscription.date > last_date:
                    last_date = subscription.date
            return last_date

    @api.model
    def create(self, values):
        """
        When adding a new contact to a company, this contact should be
        mask as is_member if:
            - The parent company have a validate subscription
            - The company subscription is an all_members subscription

        Revert if we delete a contact to a company
        """

        res = super(ResPartner, self).create(values)

        if not values.get('parent_id'):
            return res
        else:
            parent = self.browse(values.get('parent_id'))
            # Case parent is not a member

            if parent and not parent.is_member:
                return res
            else:
                # Get the last subscription of parent
                last_subscription = self.env['sale.subscription'].search([
                    ('partner_id', '=', parent.id),
                    ('is_membership', '=', True),
                    ('stage_id.category', '=', 'progress')], order="id desc", limit=1)
                if not last_subscription:
                    return res
                elif last_subscription.all_members:
                    # Mark new company contact as member
                    res.write({'is_member': True})
                    # Update the lastest subscription
                    last_subscription.write({'contact_ids': [(4, res.id)]})
                else:
                    # Just add the partner as subscription contact
                    last_subscription.write({'contact_ids': [(4, res.id)]})
        return res

    def write(self, vals):
        """
        Override write method to update child_ids with
        subscription information
        """

        # Check last subscription
        last_subscription = self.env['sale.subscription'].search([
            ('partner_id', '=', self.id),
            ('is_membership', '=', True),
            ('stage_id.category', '=', 'progress')], order="id desc", limit=1)

        if not last_subscription:
            return super(ResPartner, self).write(vals)
        else:
            # Case add a new contact to a company, update is_member field
            if vals.get('child_ids') and last_subscription.all_members:
                for child in self.browse(vals.get('child_ids')[0]):
                    try:
                        super(ResPartner, child).write({'is_member': True})
                    except:
                        pass  # FIXME

            # Get other membership value
            membership_type = last_subscription.membership_type_id.name
            date_first_start = self.get_date_first_start()
            date_last_stop = self.get_date_last_stop()

            # Update values
            vals['membership_type'] = membership_type
            vals['date_first_start'] = date_first_start
            vals['date_last_stop'] = date_last_stop

            for contact in last_subscription.contact_ids:
                if contact.is_member:
                    contact_data = {
                        'date_first_start': date_first_start,
                        'date_last_stop': date_last_stop,
                        'membership_type': membership_type,
                    }
                    super(ResPartner, contact).write(contact_data)
        return super(ResPartner, self).write(vals)
