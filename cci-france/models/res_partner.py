from datetime import date
from odoo import fields, models

from . import membership


class ResPartner(models.Model):

    _inherit = 'res.partner'

    is_member = fields.Boolean(
        string='Est Membre',
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

    # Delete this fields
    membership_state = fields.Selection(
        selection_add=membership._STATE,
        store=False,
        compute="_compute_membership_state",
        string="Statut actuel de l'adhérent", help="")

    def _total_membership(self):
        """
        Count the number of invoice for this partner
        """
        membership_mdl = self.env['membership.membership_line']
        for partner in self:
            partner.total_membership = membership_mdl.search_count([('partner', '=', partner.id)])

    def action_view_partner_membership(self):
        """
        Open list of current partner membership
        """
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "cci-france.act_open_membership_membership_line_view")
        action['domain'] = [('partner', 'child_of', self.id)]

        return action

    def _compute_membership_state(self):
        """
        Compute the state of membership for this partner
        """
        today = fields.Date.today()

        if not self:
            return

        for partner in self:
            partner.membership_start = self.env['membership.membership_line'].search([
                ('partner', '=', partner.associate_member.id or partner.id),
                ('date_cancel',  '=', False)], limit=1, order='date_from').date_from
            partner.membership_stop = self.env['membership.membership_line'].search([
                ('partner', '=', partner.associate_member.id or partner.id),
                ('date_cancel', '=', False)], limit=1, order='date_to desc').date_to
            partner.membership_cancel = self.env['membership.membership_line'].search([
                ('partner', '=', partner.id)], limit=1, order='date_cancel').date_cancel

            if partner.membership_cancel and today > partner.membership_cancel:
                partner.membership_state = 'canceled'
                continue

            line_states = [mline.state for mline in partner.member_lines if \
                (mline.date_to or date.min) >= today and \
                (mline.date_from or date.min) <= today]

            state = "draft"
            if 'paid' in line_states:
                state = 'paid'
            elif 'invoiced' in line_states:
                state = 'invoiced'
            elif 'to_invoice' in line_states:
                state = 'to_invoice'
            elif 'canceled' in line_states:
                state = 'canceled'

            partner.membership_state = state

    def _membership_type(self):
        """
        Compute membership type field base on the last
        membership register for this partner
        """
        if not self:
            return

        for partner in self:
            last_membership = partner.member_lines[-1] if partner.member_lines else None

            if not last_membership:
                partner.membership_type = None
            else:
                membership_type = last_membership.membership_id.name

                # Insure that the last membership is the one to used
                for mship in partner.member_lines:
                    if mship.state not in ('draft', 'canceled') and mship.date_from:
                        if last_membership.date_from and mship.date_from > last_membership.date_from:
                            membership_type = mship.membership_id.name
                        else:
                            continue

                partner.membership_type = membership_type

    def compute_date_first_start(self):
        """
        Determine la date de la première adhesion payée
        """
        if not self:
            return

        for partner in self:
            first_date = None
            for mbship in partner.member_lines:
                if mbship.state not in ('draft', 'canceled') and mbship.date_from:
                    if not first_date or mbship.date_from < first_date:
                        first_date = mbship.date_from
                    else:
                        continue
            partner.date_first_start = first_date

    def compute_date_last_stop(self):
        """
        Determine la date de fin de la dernière adhesion
        """
        for partner in self:
            last_date = None
            for mbship in partner.member_lines:
                if mbship.state not in ('draft', 'canceled') and mbship.date_to:
                    if not last_date or mbship.date_to < last_date:
                        last_date = mbship.date_to
            partner.date_last_stop = last_date
