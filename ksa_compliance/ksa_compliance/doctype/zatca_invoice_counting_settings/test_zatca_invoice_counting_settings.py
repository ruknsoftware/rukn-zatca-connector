# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

import frappe

from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import KSAComplianceTestBase


class TestZATCAInvoiceCountingSettings(KSAComplianceTestBase):
    """Test class for ZATCA Invoice Counting Settings DocType"""

    def setUp(self):
        """Set up each test - call parent setup to reuse existing infrastructure"""
        super().setUp()

    def test_regular_sales_invoice_updates_counting_settings(self):
        """Test that regular Sales Invoice submission updates counting settings"""
        frappe.logger().info("🧪 Running test_regular_sales_invoice_updates_counting_settings...")

        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
            ZATCABusinessSettings,
        )

        # Create a test sales invoice first to get proper settings
        sales_invoice = self._create_test_sales_invoice(submit=False)

        # Get initial counting settings using the actual invoice
        settings = ZATCABusinessSettings.for_invoice(sales_invoice.name, "Sales Invoice")
        self.assertIsNotNone(settings, "ZATCA Business Settings should exist for test invoice")
        counting_settings = frappe.get_doc(
            "ZATCA Invoice Counting Settings", {"business_settings_reference": settings.name}
        )
        initial_counter = counting_settings.invoice_counter
        initial_hash = counting_settings.previous_invoice_hash

        # Submit the sales invoice
        sales_invoice.submit()

        # Reload counting settings
        counting_settings.reload()

        # Verify counting settings were updated
        self.assertGreater(
            counting_settings.invoice_counter,
            initial_counter,
            "Counting settings should be updated when regular Sales Invoice is submitted",
        )
        self.assertNotEqual(
            counting_settings.previous_invoice_hash,
            initial_hash,
            "Previous hash should be updated when regular Sales Invoice is submitted",
        )

        frappe.logger().info("✅ test_regular_sales_invoice_updates_counting_settings completed successfully")

    def test_regular_pos_invoice_updates_counting_settings(self):
        """Test that regular POS Invoice submission updates counting settings"""
        frappe.logger().info("🧪 Running test_regular_pos_invoice_updates_counting_settings...")

        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
            ZATCABusinessSettings,
        )

        # Create a test POS invoice first to get proper settings
        pos_invoice = self._create_test_pos_invoice(submit=False)

        # Get initial counting settings using the actual invoice
        settings = ZATCABusinessSettings.for_invoice(pos_invoice.name, "POS Invoice")
        self.assertIsNotNone(settings, "ZATCA Business Settings should exist for test POS invoice")
        counting_settings = frappe.get_doc(
            "ZATCA Invoice Counting Settings", {"business_settings_reference": settings.name}
        )
        initial_counter = counting_settings.invoice_counter
        initial_hash = counting_settings.previous_invoice_hash

        # Submit the POS invoice
        pos_invoice.submit()

        # Reload counting settings
        counting_settings.reload()

        # Verify counting settings were updated
        self.assertGreater(
            counting_settings.invoice_counter,
            initial_counter,
            "Counting settings should be updated when regular POS Invoice is submitted",
        )
        self.assertNotEqual(
            counting_settings.previous_invoice_hash,
            initial_hash,
            "Previous hash should be updated when regular POS Invoice is submitted",
        )

        frappe.logger().info("✅ test_regular_pos_invoice_updates_counting_settings completed successfully")

    def test_precomputed_invoice_creation_updates_counting_settings(self):
        """Test that creating a precomputed invoice updates counting settings (generates real ZATCA data)"""
        frappe.logger().info("🧪 Running test_precomputed_invoice_creation_updates_counting_settings...")

        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
            ZATCABusinessSettings,
        )
        from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.test_zatca_precomputed_invoice import (
            TestZATCAPrecomputedInvoice,
        )

        # Create a test sales invoice
        test_sales_invoice = self._create_test_sales_invoice(submit=False)

        # Get initial counting settings
        settings = ZATCABusinessSettings.for_invoice(test_sales_invoice.name, "Sales Invoice")
        counting_settings = frappe.get_doc(
            "ZATCA Invoice Counting Settings", {"business_settings_reference": settings.name}
        )
        initial_counter = counting_settings.invoice_counter
        initial_hash = counting_settings.previous_invoice_hash

        # Create precomputed invoice (this generates real ZATCA data, so should update counting settings)
        precomputed_test = TestZATCAPrecomputedInvoice()
        precomputed_test.setUp()
        precomputed_test._create_precomputed_invoice_for_sales_invoice(test_sales_invoice.name)

        # Reload counting settings
        counting_settings.reload()

        # Verify counting settings were updated (because precomputed invoice creation generates real data)
        self.assertGreater(
            counting_settings.invoice_counter,
            initial_counter,
            "Counting settings should be updated when precomputed invoice is created (generates real ZATCA data)",
        )
        self.assertNotEqual(
            counting_settings.previous_invoice_hash,
            initial_hash,
            "Previous hash should be updated when precomputed invoice is created (generates real ZATCA data)",
        )

        frappe.logger().info("✅ test_precomputed_invoice_creation_updates_counting_settings completed successfully")

    def test_sales_invoice_with_precomputed_data_skips_counting_settings_update(self):
        """Test that Sales Invoice submission with precomputed data does NOT update counting settings"""
        frappe.logger().info("🧪 Running test_sales_invoice_with_precomputed_data_skips_counting_settings_update...")

        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
            ZATCABusinessSettings,
        )
        from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.test_zatca_precomputed_invoice import (
            TestZATCAPrecomputedInvoice,
        )

        # Create a test sales invoice
        test_sales_invoice = self._create_test_sales_invoice(submit=False)

        # Get initial counting settings
        settings = ZATCABusinessSettings.for_invoice(test_sales_invoice.name, "Sales Invoice")
        counting_settings = frappe.get_doc(
            "ZATCA Invoice Counting Settings", {"business_settings_reference": settings.name}
        )

        # Create precomputed invoice first (this will update counting settings)
        precomputed_test = TestZATCAPrecomputedInvoice()
        precomputed_test.setUp()
        precomputed_test._create_precomputed_invoice_for_sales_invoice(test_sales_invoice.name)

        # Reload counting settings to get the updated values after precomputed invoice creation
        counting_settings.reload()
        counter_after_precomputed = counting_settings.invoice_counter
        hash_after_precomputed = counting_settings.previous_invoice_hash

        # Now submit the sales invoice with precomputed data
        test_sales_invoice.submit()

        # Reload counting settings
        counting_settings.reload()

        # Verify counting settings were NOT updated (because it uses precomputed data)
        self.assertEqual(
            counting_settings.invoice_counter,
            counter_after_precomputed,
            "Counting settings should NOT be updated when Sales Invoice uses precomputed data",
        )
        self.assertEqual(
            counting_settings.previous_invoice_hash,
            hash_after_precomputed,
            "Previous hash should NOT be updated when Sales Invoice uses precomputed data",
        )

        frappe.logger().info("✅ test_sales_invoice_with_precomputed_data_skips_counting_settings_update completed successfully")


    def test_counting_settings_sequential_behavior(self):
        """Test that counting settings maintain proper sequential behavior across multiple invoices"""
        frappe.logger().info("🧪 Running test_counting_settings_sequential_behavior...")

        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
            ZATCABusinessSettings,
        )

        # Create a test invoice first to get proper settings
        first_invoice = self._create_test_sales_invoice(submit=False)

        # Get initial counting settings using the actual invoice
        settings = ZATCABusinessSettings.for_invoice(first_invoice.name, "Sales Invoice")
        self.assertIsNotNone(settings, "ZATCA Business Settings should exist for test invoice")
        counting_settings = frappe.get_doc(
            "ZATCA Invoice Counting Settings", {"business_settings_reference": settings.name}
        )
        initial_counter = counting_settings.invoice_counter

        # Create and submit multiple invoices
        invoice_counters = []
        for i in range(3):
            invoice = self._create_test_sales_invoice(submit=False)
            invoice.submit()

            # Reload counting settings
            counting_settings.reload()
            invoice_counters.append(counting_settings.invoice_counter)

        # Verify sequential behavior
        self.assertEqual(
            invoice_counters[0], initial_counter + 1, "First invoice should increment counter by 1"
        )
        self.assertEqual(
            invoice_counters[1], initial_counter + 2, "Second invoice should increment counter by 2"
        )
        self.assertEqual(
            invoice_counters[2], initial_counter + 3, "Third invoice should increment counter by 3"
        )

        # Verify all counters are sequential
        for i in range(1, len(invoice_counters)):
            self.assertEqual(
                invoice_counters[i], invoice_counters[i-1] + 1,
                f"Invoice {i+1} counter should be sequential"
            )

        frappe.logger().info("✅ test_counting_settings_sequential_behavior completed successfully")
