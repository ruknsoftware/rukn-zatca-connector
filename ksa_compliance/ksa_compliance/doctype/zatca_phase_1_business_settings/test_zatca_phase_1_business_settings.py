# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase

from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import KSAComplianceTestBase
from ksa_compliance.test.test_constants import SAUDI_COUNTRY, SAUDI_CURRENCY


class TestZATCAPhase1BusinessSettings(FrappeTestCase):
    """Test class for ZATCA Phase 1 Business Settings DocType - standalone test infrastructure"""

    def setUp(self):
        """Set up each test - create minimal test data"""
        # Use unique identifiers to avoid conflicts
        self.test_id = str(uuid.uuid4())[:8]
        self._ensure_country_exists()
        self._create_test_company()
        self._create_test_address()

    def tearDown(self):
        """Clean up test data after each test"""
        # Clean up test data
        if hasattr(self, "test_company_name") and frappe.db.exists(
            "Company", self.test_company_name
        ):
            frappe.delete_doc(
                "Company", self.test_company_name, ignore_permissions=True, force=True
            )

        if hasattr(self, "test_address_name") and frappe.db.exists(
            "Address", self.test_address_name
        ):
            frappe.delete_doc(
                "Address", self.test_address_name, ignore_permissions=True, force=True
            )

        # Clean up any ZATCA Phase 1 Business Settings created during tests
        frappe.db.sql(
            "DELETE FROM `tabZATCA Phase 1 Business Settings` WHERE company LIKE 'Test Company%'"
        )
        frappe.db.commit()  # nosemgrep

    def _ensure_country_exists(self):
        """Ensure Saudi Arabia country exists in the database"""
        if not frappe.db.exists("Country", SAUDI_COUNTRY):
            country = frappe.get_doc(
                {"doctype": "Country", "country_name": SAUDI_COUNTRY, "code": "SA"}
            )
            country.insert(ignore_permissions=True)
            frappe.db.commit()  # nosemgrep

    def _create_test_company(self):
        """Create test company for Phase 1 Business Settings"""
        self.test_company_name = f"Test Company Phase 1 {self.test_id}"
        self.test_company_abbr = f"TCP1{self.test_id[:4]}"

        if not frappe.db.exists("Company", self.test_company_name):
            try:
                company = frappe.get_doc(
                    {
                        "doctype": "Company",
                        "company_name": self.test_company_name,
                        "abbr": self.test_company_abbr,
                        "default_currency": SAUDI_CURRENCY,
                        "country": SAUDI_COUNTRY,
                    }
                )
                company.insert(ignore_permissions=True)
                frappe.db.commit()  # nosemgrep

                # Verify the company was created
                if not frappe.db.exists("Company", self.test_company_name):
                    frappe.logger().error(f"Failed to create company: {self.test_company_name}")
                    raise Exception(f"Company creation failed: {self.test_company_name}")

            except Exception as e:
                frappe.logger().error(f"Error creating company {self.test_company_name}: {str(e)}")
                raise

    def _create_test_address(self):
        """Create test address for Phase 1 Business Settings"""
        self.test_address_title = f"Test Address Phase 1 {self.test_id}"
        # Address autoname creates name as: address_title + "-" + address_type
        self.test_address_name = f"{self.test_address_title}-Billing"

        if not frappe.db.exists("Address", self.test_address_name):
            try:
                frappe.logger().info(f"Creating address: {self.test_address_name}")
                frappe.logger().info(f"Company name: {self.test_company_name}")
                frappe.logger().info(f"Country: {SAUDI_COUNTRY}")

                address = frappe.get_doc(
                    {
                        "doctype": "Address",
                        "address_title": self.test_address_title,
                        "address_type": "Billing",
                        "address_line1": "123 Test Street",
                        "city": "Riyadh",
                        "state": "Riyadh",
                        "pincode": "12345",
                        "country": SAUDI_COUNTRY,
                        "is_primary_address": 1,
                        "links": [
                            {"link_doctype": "Company", "link_name": self.test_company_name}
                        ],
                    }
                )
                frappe.logger().info("Address doc created, inserting...")
                address.insert(ignore_permissions=True)
                frappe.logger().info("Address inserted, committing...")
                frappe.db.commit()  # nosemgrep
                frappe.logger().info("Address committed, verifying...")

                # Verify the address was created
                if not frappe.db.exists("Address", self.test_address_name):
                    frappe.logger().error(f"Failed to create address: {self.test_address_name}")
                    raise Exception(f"Address creation failed: {self.test_address_name}")
                else:
                    frappe.logger().info(f"Address created successfully: {self.test_address_name}")

            except Exception as e:
                frappe.logger().error(f"Error creating address {self.test_address_name}: {str(e)}")
                frappe.logger().error(f"Exception type: {type(e)}")
                import traceback

                frappe.logger().error(f"Traceback: {traceback.format_exc()}")
                raise

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

        # Create company if it doesn't exist
        if company != self.test_company_name and not frappe.db.exists("Company", company):
            # Generate unique abbreviation using hash of company name and test_id
            import hashlib

            company_hash = hashlib.md5(f"{company}{self.test_id}".encode()).hexdigest()[:8]
            company_abbr = f"TC{company_hash}"
            frappe.get_doc(
                {
                    "doctype": "Company",
                    "company_name": company,
                    "abbr": company_abbr,
                    "default_currency": SAUDI_CURRENCY,
                    "country": SAUDI_COUNTRY,
                }
            ).insert(ignore_permissions=True)
            frappe.db.commit()  # nosemgrep

        # Create address if it doesn't exist
        if address != self.test_address_name and not frappe.db.exists("Address", address):
            # Address autoname creates name as: address_title + "-" + address_type
            address_title = (
                address.replace("-Billing", "") if address.endswith("-Billing") else address
            )
            frappe.get_doc(
                {
                    "doctype": "Address",
                    "address_title": address_title,
                    "address_type": "Billing",
                    "address_line1": "123 Test Street",
                    "city": "Riyadh",
                    "state": "Riyadh",
                    "pincode": "12345",
                    "country": SAUDI_COUNTRY,
                    "is_primary_address": 1,
                    "links": [{"link_doctype": "Company", "link_name": company}],
                }
            ).insert(ignore_permissions=True)
            frappe.db.commit()  # nosemgrep

        settings = frappe.new_doc("ZATCA Phase 1 Business Settings")
        settings.company = company
        settings.address = address
        settings.status = status
        settings.type_of_transaction = type_of_transaction
        settings.vat_registration_number = vat_registration_number
        settings.insert(ignore_permissions=True)
        frappe.db.commit()  # nosemgrep
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
        self.assertIsNotNone(settings1.name)

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
        """Test valid options for type_of_transaction field - OPTIMIZED"""
        frappe.logger().info("🧪 Running test_type_of_transaction_options...")

        valid_options = ["Simplified Tax Invoice", "Standard Tax Invoice", "Both"]

        # Create ONE settings document to reuse
        settings = self._create_test_phase_1_settings()

        try:
            for option in valid_options:
                # Update the same document with different field value
                settings.type_of_transaction = option
                settings.save(ignore_permissions=True)
                frappe.db.commit()  # nosemgrep

                # Reload to verify the change
                settings.reload()
                self.assertEqual(settings.type_of_transaction, option)

        finally:
            # Clean up the single settings document
            if frappe.db.exists("ZATCA Phase 1 Business Settings", settings.name):
                frappe.delete_doc("ZATCA Phase 1 Business Settings", settings.name, ignore_permissions=True, force=True)
                frappe.db.commit()  # nosemgrep

        frappe.logger().info("✅ test_type_of_transaction_options completed successfully")

    def test_status_options(self):
        """Test valid options for status field - OPTIMIZED"""
        frappe.logger().info("🧪 Running test_status_options...")

        valid_options = ["Active", "Disabled"]

        # Create ONE settings document to reuse
        settings = self._create_test_phase_1_settings()

        try:
            for option in valid_options:
                # Update the same document with different field value
                settings.status = option
                settings.save(ignore_permissions=True)
                frappe.db.commit()  # nosemgrep
                
                # Reload to verify the change
                settings.reload()
                self.assertEqual(settings.status, option)

        finally:
            # Clean up the single settings document
            if frappe.db.exists("ZATCA Phase 1 Business Settings", settings.name):
                frappe.delete_doc("ZATCA Phase 1 Business Settings", settings.name, ignore_permissions=True, force=True)
                frappe.db.commit()  # nosemgrep

        frappe.logger().info("✅ test_status_options completed successfully")

    def test_autoname_behavior(self):
        """Test that document name is set to company name (autoname: field:company)"""
        frappe.logger().info("🧪 Running test_autoname_behavior...")

        settings = self._create_test_phase_1_settings()

        # Document name should be the same as company name
        self.assertEqual(settings.name, self.test_company_name)

        frappe.logger().info("✅ test_autoname_behavior completed successfully")
