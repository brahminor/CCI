from odoo import api, fields, models


class MembershipType(models.Model):
    """
    Type d'adhésion
    """
    _name = "membership.type"
    _description = "Type d'adhesion"

    name = fields.Char(string='Nom', size=64, required=True, help="Nom du type d'adhésion")
    description = fields.Text(string='Description', )
    company_ids = fields.Many2many(
        'res.company', string='Sociétés',
        help="Liste des sociétés pouvant utiliser ce type d'adhesion")


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
        'res.partner', string='Contacts',
        help="""Certaines chambres facturent une adhésion à la société membre, puis facturent une adhésion additionnelle par contact considérés comme membre au sein de l’entreprise. Il faut donc pouvoir identifier quels sont les contacts de l’entreprise qui doivent obtenir le statut membre via l’adhésion enregistrée""")
    all_members = fields.Boolean(
        string='Tous les contacts',
        help='Cochez cette case si tous les contacts sont membre')

    # Override partner field to delete domain
    partner_id = fields.Many2one(
        'res.partner', string='Contact/Société', required=True, auto_join= True)
    partner_invoice_id = fields.Many2one('res.partner', string='Invoice Address')
    partner_shipping_id = fields.Many2one('res.partner', string='Service Address')
    company_type = fields.Selection(
        string="Type partenaire", related="partner_id.company_type")
    membership_type_id = fields.Many2one('membership.type', string='Type adhesion')
    active = fields.Boolean(
        string='Actif', help='Allow to archive a membership', default=True)

    @api.onchange('all_members')
    def onchange_all_members(self):
        """
        update sub_partner is_member field while checking the box
        """
        if self.all_members:
            for contact in self.contact_ids:
                contact.is_member = True
        else:
            for contact in self.contact_ids:
                contact.is_member = False

    @api.onchange('partner_id')
    def onchange_partner(self):
        """
        Update contact_ids base on partner.
        If a partner is a company, contact list should only list company member
        """
        if not self.partner_id.company_type == 'company':
            self.contact_ids = None
            # also reset individual_member field
            self.individual_member = False
        self.contact_ids = self.partner_id.child_ids

    def check_valid_membership(self):
        """
        A Membership subscription is valid if:
            - It's a membership subscription
            - Their status catagogy is 'progress'
        """
        self.ensure_one()
        result = False
        if self.is_membership and self.stage_id.category == 'progress':
            result = True
        return result

    def update_membership_contacts_info(self):
        """
        Update partner and contacts other membership informations
        """
        for subscription in self:
            membership_type = subscription.membership_type_id.name
            date_first_start = subscription.partner_id.get_date_first_start()
            date_last_stop = subscription.partner_id.get_date_last_stop()

            for contact in subscription.contact_ids:
                if contact.is_member:
                    contact.write({
                        'date_first_start': date_first_start,
                        'date_last_stop': date_last_stop,
                        'membership_type': membership_type,
                    })
            return subscription

    def update_subscription_member(self):
        """
        The purpose of this fuction is to update all the subscription member
        including sub partner mask as is_member.
        """
        if not self:
            return

        partner_is_members = []
        partner_not_members = []

        for subscription in self:
            if subscription.check_valid_membership():
                partner_is_members.append(subscription.partner_id)

                if not subscription.contact_ids:
                    continue
                elif subscription.all_members:
                    for contact in subscription.contact_ids:
                        partner_is_members.append(contact)
                else:
                    for contact in subscription.contact_ids:
                        if contact.is_member:
                            partner_is_members.append(contact)
            else:
                # Mark all member as is_member False
                partner_not_members.append(subscription.partner_id)

                if not subscription.contact_ids:
                    continue
                elif subscription.all_members:
                    for contact in subscription.contact_ids:
                        partner_not_members.append(contact)
                else:
                    for contact in subscription.contact_ids:
                        if contact.is_member:
                            partner_not_members.append(contact)

        # Update related partner
        for partner in partner_is_members:
            partner.write({'is_member': True})
        for partner in partner_not_members:
            partner.write({'is_member': False})

        return self

    @api.model
    def create(self, values):
        """
        Override default create method
        """
        res = super(SaleSubscription, self).create(values)
        # If the subscription isn't in the valid stage, we mark all members as non_member
        if res.stage_id.category != 'progress':
            res.partner_id.write({'is_member': False})
            for contact in res.contact_ids:
                contact.write({'is_member': False})

        return res

    def write(self, vals):
        """
        Override default write method
        """
        res = super(SaleSubscription, self).write(vals)
        # Update is_member field on partner base on subscription status type
        self.update_subscription_member()
        self.update_membership_contacts_info()
        return res
