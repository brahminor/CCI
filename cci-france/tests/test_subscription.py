import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


class TestCCISaleSubscription(TestSubscriptionCommon):
    """
    Test sale subscription with CCI-France rules
    """

    @classmethod
    def setUpClass(cls):
        context_no_mail = {
            'no_reset_password': True,
            'mail_create_nosubscribe': True,
            'mail_create_nolog': True}
        Subscription = cls.env['sale.subscription'].with_context(context_no_mail)
        SubscriptionStage = cls.env['sale.subscription.stage']
        MembershipType = cls.env['membership.type']
        Partner = cls.env['res.partner']

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
            'template_id': cls.subscription_tmpl.id,
            'is_membership': True,
            'individual_member': True,
            'contact_ids': [],
            'all_members': False,
            'membership_type_id': cls.membership_type_simple.id,
            'stage_id': cls.stage_nouveau.id,
        })
        cls.subscription_multi = Subscription.create({
            'name': 'TestSubscription',
            'partner_id': cls.partner_anybox.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
            'template_id': cls.subscription_tmpl.id,
            'is_membership': True,
            'individual_member': False,
            'contact_ids': [(4, 0, [
                cls.partner_clovis, cls.partner_audrey, cls.partner_amiguel])],
            'all_members': True,
            'membership_type_id': cls.membership_type_complex.id,
            'stage_id': cls.stage_nouveau.id,
        })

    # sale_subscription unittest

    # res_partner unittest

    def test_01_update_subscription_partner(self):
        """
        When update a partner with a valid subscription, membership information
        of all contacts link to this subscription and mark as is_member
        should be update
        """
        subscription = self.subscription_multi

        # Subscription isn't valid, so update main partner
        # should not update membership field
        self.partner_anybox.write({'name': 'Anybox SAS'})

        self.assertEquals(self.partner_anybox.name, 'Anybox SAS')
        self.assertFalse(self.partner.date_first_start, "Date first start should be empty")
        self.assertFalse(self.partner.date_last_stop, "Date last start should be empty")
        self.assertFalse(self.partner.membership_type, "Membership type field must be empty")



