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
            'contact_ids': [(6, 0, [
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

        self.assertEqual(len(subscription.contact_ids), 3)

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
        self.assertEqual(partner.is_member, True)

        # Check contact membership informations
        for contact in subscription.contact_ids:
            self.assertEqual(contact.is_member, True)
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

    def test_03_update_subscription(self):
        """
        when updating a subscription, partner and contacts should be update
        depending of subscription state category.
        Case where subscription with multi contacts, but not all contact are member
        """
        Partner = self.env['res.partner']
        partner_eric = Partner.create({'name': 'Eric', 'is_member': False})
        partner_mathias = Partner.create({'name': 'Mathias', 'is_member': True})
        partner_audrey = Partner.create({'name': 'Audrey', 'is_member': True})

        subscription = self.env['sale.subscription'].create({
            'name': 'Test Subscription partial member',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_annual.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, [
                partner_audrey.id, partner_mathias.id, partner_eric.id
            ])],
            'all_members': False,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_nouveau.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(years=+1)),
        })

        self.assertIsNotNone(subscription)
        self.assertEqual(len(subscription.contact_ids), 3)

        # After creation, all contacts should be set a non_member (is_member: False)
        # until subscription becore valide
        self.assertEqual(self.partner_anybox.is_member, False)
        for contact in subscription.contact_ids:
            self.assertEqual(contact.is_member, False)

        # Validate the subscription
        self.assertEqual(subscription.stage_id.category, 'draft')
        subscription.write({'stage_id': self.stage_paye.id})
        self.assertEqual(subscription.stage_id.category, 'progress')

        # Ensure that partner is_member (but not contacts)
        self.assertEqual(self.partner_anybox.is_member, True)
        for contact in subscription.contact_ids:
            self.assertEqual(contact.is_member, False)

        # Set subscription to all members
        subscription.write({'all_members': True})

        # Ensure that partner and contacts are members
        self.assertEqual(self.partner_anybox.is_member, True)
        for contact in subscription.contact_ids:
            self.assertEqual(contact.is_member, True)

    def test_04_add_contact_to_company_with_valid_subscription_case1(self):
        """
        When we add a cntact to partner with a valid subscription:
            - The subscription should be udpade to add the new contact as member
            - The membership infos of partner should be copy on contact

            Case 1: All_members subscription
        """

        Partner = self.env['res.partner']
        partner_eric = Partner.create({'name': 'Eric', 'is_member': False})
        partner_mathias = Partner.create({'name': 'Mathias', 'is_member': False})

        # Add child_ids on main partner
        self.partner_anybox.write({'child_ids': [(4, partner_eric.id)]})
        self.partner_anybox.write({'child_ids': [(4, partner_mathias.id)]})

        subscription = self.env['sale.subscription'].create({
            'name': 'Test Subscription partial member',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_annual.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_nouveau.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(years=+1)),
        })

        self.assertIsNotNone(subscription)
        self.assertEqual(len(subscription.contact_ids), 2)
        self.assertEqual(len(self.partner_anybox.child_ids), 2)

        self.assertEqual(self.partner_anybox.is_member, False)

        # Validate the subscription
        self.assertEqual(subscription.stage_id.category, 'draft')
        subscription.write({'stage_id': self.stage_paye.id})
        self.assertEqual(subscription.stage_id.category, 'progress')

        self.assertEqual(partner_eric.is_member, True)
        self.assertEqual(partner_mathias.is_member, True)
        self.assertEqual(self.partner_anybox.is_member, True)

        # Add a new contact to this partner
        partner_audrey = Partner.create({
            'name': 'Audrey', 'is_member': False, 'parent_id': self.partner_anybox.id})
        self.assertEqual(len(self.partner_anybox.child_ids), 3)

        # Check subscription contacts
        self.assertEqual(len(subscription.contact_ids), 3)

        # Ensure that new contact is a member
        self.assertEqual(partner_audrey.is_member, True)

    def test_05_add_contact_to_company_with_valid_subscription_case2(self):
        """
        When we add a cntact to partner with a valid subscription:
            - The subscription should be udpade to add the new contact as member
            - The membership infos of partner should be copy on contact

            Case 2: NON All_members subscription
        """

        Partner = self.env['res.partner']
        partner_eric = Partner.create({'name': 'Eric', 'is_member': False})
        partner_mathias = Partner.create({'name': 'Mathias', 'is_member': False})

        # Add child_ids on main partner
        self.partner_anybox.write({'child_ids': [(4, partner_eric.id)]})
        self.partner_anybox.write({'child_ids': [(4, partner_mathias.id)]})

        subscription = self.env['sale.subscription'].create({
            'name': 'Test Subscription partial member',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_annual.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': False,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_nouveau.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(years=+1)),
        })

        self.assertIsNotNone(subscription)
        self.assertEqual(len(subscription.contact_ids), 2)
        self.assertEqual(len(self.partner_anybox.child_ids), 2)

        self.assertEqual(self.partner_anybox.is_member, False)

        # Update company contact and set them to is_member True
        partner_eric.write({'is_member': True})
        partner_mathias.write({'is_member': True})

        # Validate the subscription
        self.assertEqual(subscription.stage_id.category, 'draft')
        subscription.write({'stage_id': self.stage_paye.id})
        self.assertEqual(subscription.stage_id.category, 'progress')

        self.assertEqual(self.partner_anybox.is_member, True)

        # Add a new contact to this partner
        partner_audrey = Partner.create({
            'name': 'Audrey', 'is_member': False, 'parent_id': self.partner_anybox.id})
        self.assertEqual(len(self.partner_anybox.child_ids), 3)

        # Check subscription contacts
        self.assertEqual(len(subscription.contact_ids), 3)

        # Ensure that new contact is NOT a member
        self.assertEqual(
            partner_audrey.is_member, False,
            "This partner is a contact on subscription, but not a member")

    def test_06_get_date_first_start(self):
        """
        Test get_date_first_start function
        """
        # Create and validate 3 monthly membership
        Partner = self.env['res.partner']
        partner_eric = Partner.create({'name': 'Eric', 'is_member': False})
        partner_mathias = Partner.create({'name': 'Mathias', 'is_member': False})

        # Add child_ids on main partner
        self.partner_anybox.write({'child_ids': [(4, partner_eric.id)]})
        self.partner_anybox.write({'child_ids': [(4, partner_mathias.id)]})

        subscription1 = self.env['sale.subscription'].create({
            'name': 'Test Subscription 1',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_paye.id,
            'date_start': fields.Date.to_string(datetime.date.today() - relativedelta(months=+3)),
            'date': fields.Date.to_string(datetime.date.today() - relativedelta(months=+2)),
        })

        subscription2 = self.env['sale.subscription'].create({
            'name': 'Test Subscription 2',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_paye.id,
            'date_start': fields.Date.to_string(datetime.date.today() - relativedelta(months=+2)),
            'date': fields.Date.to_string(datetime.date.today() - relativedelta(months=+1)),
        })

        subscription3 = self.env['sale.subscription'].create({
            'name': 'Test Subscription 3',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_paye.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(months=+1)),
        })

        # Call this function and check the result
        today = fields.Date.context_today(self.env.user)

        date_first_start = self.partner_anybox.get_date_first_start()
        self.assertEqual(date_first_start, today - relativedelta(months=+3))

    def test_07_get_date_last_stop(self):
        """
        Test get_date_last_stop function
        """

        # Create and validate 3 monthly membership
        Partner = self.env['res.partner']
        partner_eric = Partner.create({'name': 'Eric', 'is_member': False})
        partner_mathias = Partner.create({'name': 'Mathias', 'is_member': False})

        # Add child_ids on main partner
        self.partner_anybox.write({'child_ids': [(4, partner_eric.id)]})
        self.partner_anybox.write({'child_ids': [(4, partner_mathias.id)]})

        subscription1 = self.env['sale.subscription'].create({
            'name': 'Test Subscription 1',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_paye.id,
            'date_start': fields.Date.to_string(datetime.date.today() - relativedelta(months=+3)),
            'date': fields.Date.to_string(datetime.date.today() - relativedelta(months=+2)),
        })

        subscription2 = self.env['sale.subscription'].create({
            'name': 'Test Subscription 2',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_paye.id,
            'date_start': fields.Date.to_string(datetime.date.today() - relativedelta(months=+2)),
            'date': fields.Date.to_string(datetime.date.today() - relativedelta(months=+1)),
        })

        subscription3 = self.env['sale.subscription'].create({
            'name': 'Test Subscription 3',
            'partner_id': self.partner_anybox.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'template_id': self.subscription_tmpl_monthly.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(6, 0, self.partner_anybox.child_ids.ids)],
            'all_members': True,
            'membership_type_id': self.membership_type_complex.id,
            'stage_id': self.stage_paye.id,
            'date_start': fields.Date.to_string(datetime.date.today()),
            'date': fields.Date.to_string(datetime.date.today() + relativedelta(months=+1)),
        })

        today = fields.Date.context_today(self.env.user)

        # Call this function and check the result
        date_last_stop = self.partner_anybox.get_date_last_stop()
        self.assertEqual(date_last_stop, today + relativedelta(months=+1))

    def test_08_compute_individual_member(self):
        """
        test _compute_individual_member function
        """
        pass
