from odoo import fields, models


class MembershipInvoice(models.TransientModel):
    """
    Override membership invoice model
    """
    _inherit = "membership.invoice"

    partner_id = fields.Many2one('res.partner', string='Adherent', required=True)

    def membership_invoice(self):
        mship_id = self._context.get('active_ids', False)
        invoice_list = self.env['res.partner'].browse(
            self._context.get('active_ids')).create_membership_invoice(
                self.partner_id,
                self.product_id,
                self.member_price,
                mship_id[0] if mship_id else False)

        # Update membership status
        if invoice_list and mship_id:
            membership = self.env['membership.membership_line'].browse(mship_id)
            membership.write({'state': 'invoiced'})

        search_view_ref = self.env.ref('account.view_account_invoice_filter', False)
        form_view_ref = self.env.ref('account.view_move_form', False)
        tree_view_ref = self.env.ref('account.view_move_tree', False)

        return  {
            'domain': [('id', 'in', invoice_list.ids)],
            'name': "Facture d'adhésion",
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
            'search_view_id': search_view_ref and search_view_ref.id,
        }
