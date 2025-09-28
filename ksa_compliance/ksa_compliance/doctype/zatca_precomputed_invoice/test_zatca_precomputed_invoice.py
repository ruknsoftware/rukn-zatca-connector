# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

from unittest.mock import patch

import frappe

from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
    ZATCAPrecomputedInvoice,
)
from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import KSAComplianceTestBase
from ksa_compliance.test.test_constants import (
    TEST_SIMPLIFIED_CUSTOMER_NAME,
    TEST_STANDARD_CUSTOMER_NAME,
)


class TestZATCAPrecomputedInvoice(KSAComplianceTestBase):
    """Test class for ZATCA Precomputed Invoice DocType - inherits from shared test infrastructure"""

    def setUp(self):
        """Set up each test - call parent setup to reuse existing infrastructure"""
        super().setUp()  # Call parent's setUp method to create test data

        # Create test invoices for our tests (without submitting to avoid ZATCA processing)
        self.test_sales_invoice = self._create_test_sales_invoice(submit=False)
        self.test_pos_invoice = self._create_test_pos_invoice(submit=False)

    def _create_precomputed_invoice_for_sales_invoice(
        self, sales_invoice_name, device_id="TEST-DEVICE-001"
    ):
        """Create a precomputed invoice following the real production flow"""
        from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
            SalesInvoiceAdditionalFields,
        )
        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.zatca_business_settings import (
            ZATCABusinessSettings,
        )

        # Get business settings
        settings = ZATCABusinessSettings.for_invoice(sales_invoice_name, "Sales Invoice")
        if not settings:
            frappe.throw(
                f"Missing ZATCA business settings for sales invoice: {sales_invoice_name}"
            )

        # Create Sales Invoice Additional Fields to generate real ZATCA data
        si_additional_fields = SalesInvoiceAdditionalFields.create_for_invoice(
            sales_invoice_name, "Sales Invoice"
        )

        # Ensure it runs the full ZATCA pipeline (not precomputed)
        si_additional_fields.precomputed = False

        # Insert to trigger the ZATCA processing pipeline
        si_additional_fields.insert()

        # Create precomputed invoice with the real generated data
        precomputed_invoice = frappe.new_doc("ZATCA Precomputed Invoice")
        precomputed_invoice.sales_invoice = sales_invoice_name
        precomputed_invoice.device_id = device_id
        precomputed_invoice.invoice_counter = str(si_additional_fields.invoice_counter)
        precomputed_invoice.invoice_uuid = si_additional_fields.uuid
        precomputed_invoice.previous_invoice_hash = si_additional_fields.previous_invoice_hash
        precomputed_invoice.invoice_hash = si_additional_fields.invoice_hash
        precomputed_invoice.invoice_qr = si_additional_fields.qr_code
        precomputed_invoice.invoice_xml = si_additional_fields.invoice_xml

        precomputed_invoice.insert(ignore_permissions=True)

        # Clean up the temporary Sales Invoice Additional Fields
        si_additional_fields.delete()

        return precomputed_invoice

    def test_basic_setup(self):
        """Test basic test framework setup"""
        frappe.logger().info("🧪 Running test_basic_setup...")

        # Verify test data was created successfully
        self.assertIsNotNone(self.test_sales_invoice)
        self.assertIsNotNone(self.test_pos_invoice)
        self.assertEqual(self.test_sales_invoice.customer, TEST_STANDARD_CUSTOMER_NAME)
        self.assertEqual(self.test_pos_invoice.customer, TEST_SIMPLIFIED_CUSTOMER_NAME)

        frappe.logger().info("✅ test_basic_setup completed successfully")

    def test_create_precomputed_invoice(self):
        """Test creating a precomputed invoice following the real production flow"""
        frappe.logger().info("🧪 Running test_create_precomputed_invoice...")

        # Create precomputed invoice using real ZATCA processing
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name, device_id="TEST-DEVICE-001"
        )

        # Verify the document was created with real ZATCA data
        self.assertIsNotNone(precomputed_invoice.name)
        self.assertEqual(precomputed_invoice.sales_invoice, self.test_sales_invoice.name)
        self.assertEqual(precomputed_invoice.device_id, "TEST-DEVICE-001")

        # Verify real ZATCA data was generated
        self.assertIsNotNone(precomputed_invoice.invoice_uuid)
        self.assertIsNotNone(precomputed_invoice.invoice_hash)
        self.assertIsNotNone(precomputed_invoice.invoice_qr)
        self.assertIsNotNone(precomputed_invoice.invoice_xml)

        # Verify UUID format (should be a proper UUID4)
        import uuid

        try:
            uuid.UUID(precomputed_invoice.invoice_uuid)
        except ValueError:
            self.fail("invoice_uuid is not a valid UUID")

        frappe.logger().info("✅ test_create_precomputed_invoice completed successfully")

    def test_cannot_delete_precomputed_invoice(self):
        """Test that precomputed invoices cannot be deleted"""
        frappe.logger().info("🧪 Running test_cannot_delete_precomputed_invoice...")

        # Create precomputed invoice using real ZATCA processing
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name
        )

        # Try to delete the document
        with self.assertRaises(frappe.ValidationError) as context:
            precomputed_invoice.delete()

        # Verify the error message
        self.assertIn(
            "You cannot Delete a configured ZATCA Precomputed Invoice", str(context.exception)
        )

        frappe.logger().info("✅ test_cannot_delete_precomputed_invoice completed successfully")

    def test_unique_invoice_uuid_constraint(self):
        """Test that invoice_uuid must be unique"""
        frappe.logger().info("🧪 Running test_unique_invoice_uuid_constraint...")

        # Create first precomputed invoice using real ZATCA processing
        precomputed_invoice1 = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name
        )

        # Create another sales invoice for the second precomputed invoice
        sales_invoice2 = self._create_test_sales_invoice(submit=False)

        # Try to create second precomputed invoice with same UUID
        precomputed_invoice2 = frappe.new_doc("ZATCA Precomputed Invoice")
        precomputed_invoice2.sales_invoice = sales_invoice2.name
        precomputed_invoice2.device_id = "TEST-DEVICE-002"
        precomputed_invoice2.invoice_counter = "2"
        precomputed_invoice2.invoice_uuid = precomputed_invoice1.invoice_uuid  # Same UUID
        precomputed_invoice2.previous_invoice_hash = "previous-hash-789"
        precomputed_invoice2.invoice_hash = "current-hash-012"
        precomputed_invoice2.invoice_qr = "QR_CODE_DATA_HERE_2"
        precomputed_invoice2.invoice_xml = "<xml>test</xml>"

        # This should raise an integrity error due to unique constraint
        with self.assertRaises(Exception) as context:
            precomputed_invoice2.insert(ignore_permissions=True)

        # Verify it's an integrity error (duplicate key)
        self.assertIn("Duplicate entry", str(context.exception))

        frappe.logger().info("✅ test_unique_invoice_uuid_constraint completed successfully")

    def test_integration_with_sales_invoice_additional_fields(self):
        """Test integration with Sales Invoice Additional Fields following real production flow"""
        frappe.logger().info("🧪 Running test_integration_with_sales_invoice_additional_fields...")

        # Create precomputed invoice using real ZATCA processing
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name
        )

        # Now submit the sales invoice - this should use the precomputed data
        self.test_sales_invoice.submit()

        # Verify that Sales Invoice Additional Fields was created and uses precomputed data
        additional_fields = frappe.get_all(
            "Sales Invoice Additional Fields",
            filters={"sales_invoice": self.test_sales_invoice.name},
            limit=1,
        )

        self.assertTrue(
            len(additional_fields) > 0,
            "Sales Invoice Additional Fields should be created automatically",
        )

        # Get the additional fields document
        additional_fields_doc = frappe.get_doc(
            "Sales Invoice Additional Fields", additional_fields[0].name
        )

        # Verify the relationship and that it uses precomputed data
        self.assertEqual(additional_fields_doc.sales_invoice, self.test_sales_invoice.name)
        self.assertTrue(additional_fields_doc.precomputed, "Should be marked as precomputed")
        self.assertEqual(additional_fields_doc.precomputed_invoice, precomputed_invoice.name)

        # Verify the data was copied correctly
        self.assertEqual(
            additional_fields_doc.invoice_counter, int(precomputed_invoice.invoice_counter)
        )
        self.assertEqual(additional_fields_doc.uuid, precomputed_invoice.invoice_uuid)
        self.assertEqual(additional_fields_doc.invoice_hash, precomputed_invoice.invoice_hash)
        self.assertEqual(additional_fields_doc.qr_code, precomputed_invoice.invoice_qr)

        frappe.logger().info(
            "✅ test_integration_with_sales_invoice_additional_fields completed successfully"
        )

    def test_for_invoice_returns_none_when_not_found(self):
        """Test that for_invoice returns None when no precomputed invoice exists"""
        frappe.logger().info("🧪 Running test_for_invoice_returns_none_when_not_found...")

        # Test with a non-existent invoice
        result = ZATCAPrecomputedInvoice.for_invoice("NON-EXISTENT-INVOICE")

        # Verify the result is None
        self.assertIsNone(result)

        frappe.logger().info(
            "✅ test_for_invoice_returns_none_when_not_found completed successfully"
        )

    def test_device_id_can_be_modified(self):
        """Test that device_id can be modified (it's not read-only)"""
        frappe.logger().info("🧪 Running test_device_id_can_be_modified...")

        # Create precomputed invoice using real ZATCA processing
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name
        )

        # Modify device_id
        new_device_id = "MODIFIED-DEVICE-001"
        precomputed_invoice.device_id = new_device_id
        precomputed_invoice.save()

        # Reload from database
        precomputed_invoice.reload()

        # Verify the change was saved
        self.assertEqual(precomputed_invoice.device_id, new_device_id)

        frappe.logger().info("✅ test_device_id_can_be_modified completed successfully")

    @patch("frappe.response")
    def test_download_xml_endpoint(self, mock_response):
        """Test the download_xml API endpoint"""
        frappe.logger().info("🧪 Running test_download_xml_endpoint...")

        # Create precomputed invoice using real ZATCA processing
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name
        )

        # Mock the response object
        mock_response.type = None
        mock_response.display_content_as = None
        mock_response.filename = None
        mock_response.filecontent = None

        # Import and call the download_xml function
        from ksa_compliance.ksa_compliance.doctype.zatca_precomputed_invoice.zatca_precomputed_invoice import (
            download_xml,
        )

        download_xml(precomputed_invoice.name)

        # Verify the response was set correctly
        self.assertEqual(mock_response.type, "download")
        self.assertEqual(mock_response.display_content_as, "attachment")
        self.assertEqual(mock_response.filename, f"{precomputed_invoice.name}.xml")
        self.assertEqual(mock_response.filecontent, precomputed_invoice.invoice_xml)

        frappe.logger().info("✅ test_download_xml_endpoint completed successfully")

    def test_create_precomputed_invoice_with_real_zatca_data(self):
        """Test creating a precomputed invoice using real ZATCA processing pipeline"""
        frappe.logger().info("🧪 Running test_create_precomputed_invoice_with_real_zatca_data...")

        # Create precomputed invoice with real ZATCA data
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name, device_id="REAL-DEVICE-001"
        )

        # Verify the document was created with real data
        self.assertIsNotNone(precomputed_invoice.name)
        self.assertEqual(precomputed_invoice.sales_invoice, self.test_sales_invoice.name)
        self.assertEqual(precomputed_invoice.device_id, "REAL-DEVICE-001")

        # Verify real ZATCA data was generated
        self.assertIsNotNone(precomputed_invoice.invoice_uuid)
        self.assertIsNotNone(precomputed_invoice.invoice_hash)
        self.assertIsNotNone(precomputed_invoice.invoice_qr)
        self.assertIsNotNone(precomputed_invoice.invoice_xml)

        # Verify UUID format (should be a proper UUID4)
        import uuid

        try:
            uuid.UUID(precomputed_invoice.invoice_uuid)
        except ValueError:
            self.fail("invoice_uuid is not a valid UUID")

        # Verify hash format (should be base64 encoded)
        import base64

        try:
            base64.b64decode(precomputed_invoice.invoice_hash)
        except Exception:
            self.fail("invoice_hash is not valid base64")

        # Verify XML contains expected elements
        self.assertIn("Invoice", precomputed_invoice.invoice_xml)
        self.assertIn("xml", precomputed_invoice.invoice_xml.lower())

        frappe.logger().info(
            "✅ test_create_precomputed_invoice_with_real_zatca_data completed successfully"
        )

    def test_precomputed_invoice_data_mapping(self):
        """Test that precomputed invoice data maps correctly to Sales Invoice Additional Fields"""
        frappe.logger().info("🧪 Running test_precomputed_invoice_data_mapping...")

        # Create precomputed invoice with real data
        precomputed_invoice = self._create_precomputed_invoice_for_sales_invoice(
            self.test_sales_invoice.name
        )

        # Create Sales Invoice Additional Fields and use the precomputed data
        from ksa_compliance.ksa_compliance.doctype.sales_invoice_additional_fields.sales_invoice_additional_fields import (
            SalesInvoiceAdditionalFields,
        )

        si_additional_fields = SalesInvoiceAdditionalFields.create_for_invoice(
            self.test_sales_invoice.name, "Sales Invoice"
        )

        # Use the precomputed invoice data
        si_additional_fields.use_precomputed_invoice(precomputed_invoice)

        # Verify the data mapping is correct
        self.assertTrue(si_additional_fields.precomputed)
        self.assertEqual(si_additional_fields.precomputed_invoice, precomputed_invoice.name)
        self.assertEqual(
            si_additional_fields.invoice_counter, int(precomputed_invoice.invoice_counter)
        )
        self.assertEqual(si_additional_fields.uuid, precomputed_invoice.invoice_uuid)
        self.assertEqual(
            si_additional_fields.previous_invoice_hash, precomputed_invoice.previous_invoice_hash
        )
        self.assertEqual(si_additional_fields.invoice_hash, precomputed_invoice.invoice_hash)
        self.assertEqual(
            si_additional_fields.qr_code, precomputed_invoice.invoice_qr
        )  # Field name mapping
        self.assertEqual(si_additional_fields.invoice_xml, precomputed_invoice.invoice_xml)

        frappe.logger().info("✅ test_precomputed_invoice_data_mapping completed successfully")

