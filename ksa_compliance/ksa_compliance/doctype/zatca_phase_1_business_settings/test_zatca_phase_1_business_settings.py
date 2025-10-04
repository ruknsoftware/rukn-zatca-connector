# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import KSAComplianceTestBase


class TestZATCAPhase1BusinessSettings(FrappeTestCase):
    """Test class for ZATCA Phase 1 Business Settings DocType - standalone test infrastructure"""

    def setUp(self):
        """Set up each test - create minimal test data"""
        self._create_test_company()
        self._create_test_address()

    def _create_test_company(self):
        """Create test company for Phase 1 Business Settings"""
        self.test_company_name = "Test Company Phase 1"

        if not frappe.db.exists("Company", self.test_company_name):
            company = frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": self.test_company_name,
                    "abbr": "TCP1",
                    "default_currency": "SAR",
                    "country": "Saudi Arabia",
                }
            )
            company.insert(ignore_permissions=True)

    def _create_test_address(self):
        """Create test address for Phase 1 Business Settings"""
        self.test_address_name = "Test Address Phase 1"

        if not frappe.db.exists("Address", self.test_address_name):
            address = frappe.get_doc(
                {
                    "doctype": "Address",
                    "address_title": self.test_address_name,
                    "address_type": "Billing",
                    "address_line1": "123 Test Street",
                    "city": "Riyadh",
                    "state": "Riyadh",
                    "pincode": "12345",
                    "country": "Saudi Arabia",
                    "is_primary_address": 1,
                    "links": [{"link_doctype": "Company", "link_name": self.test_company_name}],
                }
            )
            address.insert(ignore_permissions=True)

    def _create_test_phase_1_settings(
        self,
        company=None,
        address=None,
        status="Active",
        type_of_transaction="Both",
        vat_registration_number="123456789012345",
    ):
        """Create test ZATCA Phase 1 Business Settings"""
        company = company or self.test_company_name
        address = address or self.test_address_name

        settings = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings.company = company
        settings.address = address
        settings.status = status
        settings.type_of_transaction = type_of_transaction
        settings.vat_registration_number = vat_registration_number
        settings.insert(ignore_permissions=True)
        return settings

    # ===== PHASE 1: CORE CRUD OPERATIONS =====

    def test_basic_setup(self):
        """Test basic test framework setup"""
        frappe.logger().info("🧪 Running test_basic_setup...")

        # Verify test data was created successfully
        self.assertTrue(frappe.db.exists("Company", self.test_company_name))
        self.assertTrue(frappe.db.exists("Address", self.test_address_name))

        frappe.logger().info("✅ test_basic_setup completed successfully")

    def test_create_phase_1_business_settings(self):
        """Test creating ZATCA Phase 1 Business Settings with valid data"""
        frappe.logger().info("🧪 Running test_create_phase_1_business_settings...")

        # Create Phase 1 Business Settings
        settings = self._create_test_phase_1_settings()

        # Verify the document was created
        self.assertIsNotNone(settings.name)
        self.assertEqual(settings.company, self.test_company_name)
        self.assertEqual(settings.address, self.test_address_name)
        self.assertEqual(settings.status, "Active")
        self.assertEqual(settings.type_of_transaction, "Both")
        self.assertEqual(settings.vat_registration_number, "123456789012345")

        # Verify document exists in database
        self.assertTrue(frappe.db.exists("ZATCA Phase 1 Business Settings", settings.name))

        frappe.logger().info("✅ test_create_phase_1_business_settings completed successfully")

    def test_required_fields_validation(self):
        """Test that required fields (company, address) are enforced"""
        frappe.logger().info("🧪 Running test_required_fields_validation...")

        # Test missing company
        settings = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings.address = self.test_address_name
        settings.status = "Active"
        settings.type_of_transaction = "Both"

        with self.assertRaises(frappe.ValidationError) as context:
            settings.insert(ignore_permissions=True)

        self.assertIn("company", str(context.exception))

        # Test missing address
        settings = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings.company = self.test_company_name
        settings.status = "Active"
        settings.type_of_transaction = "Both"

        with self.assertRaises(frappe.ValidationError) as context:
            settings.insert(ignore_permissions=True)

        self.assertIn("address", str(context.exception))

        frappe.logger().info("✅ test_required_fields_validation completed successfully")

    def test_unique_company_constraint(self):
        """Test that only one Phase 1 settings per company is allowed"""
        frappe.logger().info("🧪 Running test_unique_company_constraint...")

        # Create first Phase 1 settings
        settings1 = self._create_test_phase_1_settings()

        # Try to create second Phase 1 settings for same company
        settings2 = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings2.company = self.test_company_name
        settings2.address = self.test_address_name
        settings2.status = "Disabled"
        settings2.type_of_transaction = "Simplified Tax Invoice"

        with self.assertRaises(Exception) as context:
            settings2.insert(ignore_permissions=True)

        # Should get duplicate entry error
        self.assertIn("Duplicate entry", str(context.exception))

        frappe.logger().info("✅ test_unique_company_constraint completed successfully")

    def test_company_link_validation(self):
        """Test that company field links to valid Company document"""
        frappe.logger().info("🧪 Running test_company_link_validation...")

        settings = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings.company = "Non-Existent Company"
        settings.address = self.test_address_name
        settings.status = "Active"
        settings.type_of_transaction = "Both"

        with self.assertRaises(frappe.LinkValidationError) as context:
            settings.insert(ignore_permissions=True)

        self.assertIn("Could not find", str(context.exception))
        self.assertIn("Company", str(context.exception))

        frappe.logger().info("✅ test_company_link_validation completed successfully")

    def test_address_link_validation(self):
        """Test that address field links to valid Address document"""
        frappe.logger().info("🧪 Running test_address_link_validation...")

        settings = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings.company = self.test_company_name
        settings.address = "Non-Existent Address"
        settings.status = "Active"
        settings.type_of_transaction = "Both"

        with self.assertRaises(frappe.LinkValidationError) as context:
            settings.insert(ignore_permissions=True)

        self.assertIn("Could not find", str(context.exception))
        self.assertIn("Address", str(context.exception))

        frappe.logger().info("✅ test_address_link_validation completed successfully")

    def test_type_of_transaction_options(self):
        """Test valid options for type_of_transaction field"""
        frappe.logger().info("🧪 Running test_type_of_transaction_options...")

        valid_options = ["Simplified Tax Invoice", "Standard Tax Invoice", "Both"]

        for option in valid_options:
            # Create settings with each valid option
            settings = self._create_test_phase_1_settings(
                type_of_transaction=option, company=f"Test Company {option.replace(' ', '_')}"
            )
            self.assertEqual(settings.type_of_transaction, option)

        frappe.logger().info("✅ test_type_of_transaction_options completed successfully")

    def test_status_options(self):
        """Test valid options for status field"""
        frappe.logger().info("🧪 Running test_status_options...")

        valid_options = ["Active", "Disabled"]

        for option in valid_options:
            # Create settings with each valid option
            settings = self._create_test_phase_1_settings(
                status=option, company=f"Test Company {option}"
            )
            self.assertEqual(settings.status, option)

        frappe.logger().info("✅ test_status_options completed successfully")

    def test_autoname_behavior(self):
        """Test that document name is set to company name (autoname: field:company)"""
        frappe.logger().info("🧪 Running test_autoname_behavior...")

        settings = self._create_test_phase_1_settings()

        # Document name should be the same as company name
        self.assertEqual(settings.name, self.test_company_name)

        frappe.logger().info("✅ test_autoname_behavior completed successfully")
