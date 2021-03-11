import datetime
import time

from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from . import common
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestMembership(common.TestMembershipCommon):

    def test_check_valid_membership(self):
        """
        We create, paid a membership and check their status
        """
        self.assertEqual(
            self.partner_1.membership_state, 'draft',
            'membership: default membership status of partners should be draft')

        # subscribes to a membership
        invoice = self.partner_1.create_membership_invoice(
            self.membership_1, self.membership_1.list_price)

        self.assertEqual(invoice.amount_total, self.membership_1.list_price)

        def patched_today(*args, **kwargs):
            return fields.Date.to_date('2021-01-01')

        with patch.object(fields.Date, 'today', patched_today):
            self.membership_1.check_valid_membership()

        self.assertIsTrue(self.membership_1.is_valid_membership)

    def test_compute_state(self):
        """
        Test _compute_state method
        """
        self.assertEqual(
            self.partner_1.membership_state, 'draft',
            'membership: default membership status of partners should be draft')

        # subscribes to a membership
        self.partner_1.create_membership_invoice(self.membership_1, 75.0)

        # checks for invoices
        invoice = self.env['account.move'].search([('partner_id', '=', self.partner_1.id)],   limit=1)

    def test_button_cancel(self):
        pass

    def test_action_post(self):
        pass

    def test_multi_invoice_membership(self):
        """
        Case we have multi invoice on a membership
        """
        pass
