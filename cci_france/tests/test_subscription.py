import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon
from odoo import fields


class TestCCISaleSubscription(TestSubscriptionCommon):
    """
    Test sale subscription with CCI France rules
    """

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        context_no_mail = {
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True}
        Subscription = cls.env['sale.subscription'].with_context(context_no_mail)
        SubscriptionStage = cls.env['sale.subscription.stage']
        SubTemplate = cls.env['sale.subscription.template'].with_context(context_no_mail)
        MembershipType = cls.env['membership.type']
        Partner = cls.env['res.partner']

        # Subscription template
        cls.subscription_tmpl_monthly = SubTemplate.create({
            'name': 'Monthly subscription',
            'description': 'Test Subscription by month',
            'journal_id': cls.journal.id,
            'user_closable': True,
            'recurring_interval': 1,
            'recurring_rule_type': "monthly",
            'recurring_rule_count': 6,
            'recurring_rule_boundary': "limited",
            'payment_mode': "manual",
            'code': "MON",
        })
        cls.subscription_tmpl_annual = SubTemplate.create({
            'name': 'Annual subscription',
            'description': 'Test Subscription by year',
            'journal_id': cls.journal.id,
            'user_closable': True,
            'recurring_interval': 1,
            'recurring_rule_type': "yearly",
            'recurring_rule_count': 5,
            'recurring_rule_boundary': "limited",
            'payment_mode': "manual",
            'code': "YEA",
        })

        # Subscription stage
        cls.stage_nouveau = SubscriptionStage.create({'name': 'Nouveau', 'category': 'draft'})
        cls.stage_paye = SubscriptionStage.create({'name': 'Nouveau', 'category': 'progress'})
        cls.stage_ferme = SubscriptionStage.create({'name': 'Nouveau', 'category': 'closed'})

        # Partner
        cls.partner_clovis = Partner.create({'name': 'Clovis'})
        cls.partner_audrey = Partner.create({'name': 'Audrey'})
        cls.partner_amiguel = Partner.create({'name': 'Amiguel'})
        cls.partner_anybox = Partner.create({'name': 'Anybox', 'child_ids': [(4, 0, [
            cls.partner_clovis, cls.partner_audrey, cls.partner_amiguel])]})

        # Membership type
        cls.membership_type_simple = MembershipType.create({'name': 'Simple'})
        cls.membership_type_complex = MembershipType.create({'name': 'Complex'})

        cls.subscription_single = Subscription.create({
            'name': 'TestSubscription',
            'partner_id': cls.user_portal.partner_id.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'template_id': cls.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': True,
            'contact_ids': [],
            'all_members': False,
            'membership_type_id': cls.membership_type_simple.id,
            'stage_id': cls.stage_nouveau.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(months=+1)),
        })
        cls.subscription_multi = Subscription.create({
            'name': 'TestSubscription',
            'partner_id': cls.partner_anybox.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'template_id': cls.subscription_tmpl_annual.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(5, 0, [
                cls.partner_clovis.id,
                cls.partner_audrey.id,
                cls.partner_amiguel.id])],
            'all_members': True,
            'membership_type_id': cls.membership_type_complex.id,
            'stage_id': cls.stage_nouveau.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(years=+1)),
        })

    # sale_subscription unittest

    # res_partner unittest

    def test_01_validated_subscription_should_update_partner_and_contacts(self):
        """
        When update a partner with a valid subscription, membership information
        of all contacts link to this subscription and mark as is_member
        should be update
        """
        subscription = self.subscription_multi
        partner = self.partner_anybox
        today = fields.Date.context_today(self.env.user)

        # Subscription isn't valid, so update main partner
        # should not update membership field
        partner.write({'name': 'Anybox SAS'})

        self.assertEqual(partner.name, 'Anybox SAS')
        self.assertFalse(partner.date_first_start, "Date first start should be empty")
        self.assertFalse(partner.date_last_stop, "Date last start should be empty")
        self.assertFalse(partner.membership_type, "Membership type field must be empty")

        # Validate the subscription
        self.assertEqual(subscription.stage_id.category, 'draft')
        subscription.write({'stage_id': self.stage_paye.id})
        self.assertEqual(subscription.stage_id.category, 'progress')

        # Check main partner membership info
        self.assertEqual(
            partner.date_first_start,
            today,
            "Frist date should be today date")
        self.assertEqual(
            partner.date_last_stop,
            today + relativedelta(years=+1),
            "Date last stop should set to: today + 1 year",
        )
        self.assertEqual(partner.membership_type, self.membership_type_complex.name)

        # Check contact membership informations
        for contact in subscription.contact_ids:
            self.assertEqual(contact.date_first_start, partner.date_first_start)
            self.assertEqual(contact.date_last_stop, partner.date_last_stop)
            self.assertEqual(contact.membership_type, partner.membership_type,)

    def test_02_check_valid_membership(self):
        """
        Test check_valid_membership function
        """

        subscription = self.subscription_multi
        self.assertFalse(subscription.check_valid_membership())

        # Validate the subscription
        self.assertEqual(subscription.stage_id.category, 'draft')
        subscription.write({'stage_id': self.stage_paye.id})

        self.assertTrue(subscription.check_valid_membership)

