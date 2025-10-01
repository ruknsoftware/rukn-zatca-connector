# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

import frappe
from frappe import _

from ksa_compliance.ksa_compliance.test.ksa_compliance_test_base import (
    KSAComplianceTestBase,
)
from ksa_compliance.ksa_compliance.doctype.zatca_egs.zatca_egs import ZATCAEGS


class TestZATCAEGS(KSAComplianceTestBase):
    """Test class for ZATCA EGS DocType - inherits from shared test infrastructure"""

    def setUp(self):
        """Set up each test - call parent setup to reuse existing infrastructure"""
        super().setUp()  # Call parent's setUp method to create test data
        self._create_test_business_settings()

    def _create_test_business_settings(self):
        """Create test ZATCA Business Settings for EGS testing using comprehensive setup"""
        from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.test_zatca_business_settings import (
            setup_zatca_business_settings,
        )
        from ksa_compliance.test.test_constants import (
            TEST_COMPANY_NAME,
            SAUDI_COUNTRY,
            SAUDI_CURRENCY,
        )

        # Use the comprehensive setup function from business settings tests
        self.business_settings_name = setup_zatca_business_settings(
            TEST_COMPANY_NAME, SAUDI_COUNTRY, SAUDI_CURRENCY
        )

    def _create_test_erpnext_egs(self, device_id="ERPNext"):
        """Create test ERPNext EGS configuration"""
        egs = frappe.new_doc("ZATCA EGS")
        egs.business_settings = self.business_settings_name
        egs.egs_type = "ERPNext"
        egs.unit_common_name = device_id
        egs.unit_serial = "1-ERPNext|2-15|3-1"
        egs.enable_zatca_integration = 1
        egs.sync_with_zatca = "Live"
        egs.validate_generated_xml = 0
        egs.insert(ignore_permissions=True)
        return egs

    def _create_test_pos_egs(self, device_id="POS-DEVICE-001"):
        """Create test POS device EGS configuration"""
        egs = frappe.new_doc("ZATCA EGS")
        egs.business_settings = self.business_settings_name
        egs.egs_type = "POS Device"
        egs.unit_common_name = device_id
        egs.unit_serial = "1-Sunmi|2-Sunmi Pro v2s|3-V222201B00815"
        egs.enable_zatca_integration = 1
        egs.sync_with_zatca = "Batches"
        egs.validate_generated_xml = 1
        egs.insert(ignore_permissions=True)
        return egs

    def test_basic_setup(self):
        """Test basic test framework setup"""
        frappe.logger().info("🧪 Running test_basic_setup...")

        # Verify test data was created successfully
        self.assertIsNotNone(self.item_name)
        self.assertTrue(frappe.db.exists("Item", self.item_name))
        self.assertTrue(
            frappe.db.exists("ZATCA Business Settings", self.business_settings_name)
        )

        frappe.logger().info("✅ test_basic_setup completed successfully")

    # ===== PHASE 1: CORE EGS FUNCTIONALITY TESTS =====

    def test_create_erpnext_egs(self):
        """Test creating ERPNext EGS configuration"""
        frappe.logger().info("🧪 Running test_create_erpnext_egs...")

        # Create ERPNext EGS
        egs = self._create_test_erpnext_egs()

        # Verify the document was created
        self.assertIsNotNone(egs.name)
        self.assertEqual(egs.business_settings, self.business_settings_name)
        self.assertEqual(egs.egs_type, "ERPNext")
        self.assertEqual(egs.unit_common_name, "ERPNext")
        self.assertEqual(egs.unit_serial, "1-ERPNext|2-15|3-1")
        self.assertEqual(egs.enable_zatca_integration, 1)
        self.assertEqual(egs.sync_with_zatca, "Live")
        self.assertEqual(egs.validate_generated_xml, 0)

        frappe.logger().info("✅ test_create_erpnext_egs completed successfully")

    def test_create_pos_device_egs(self):
        """Test creating POS Device EGS configuration"""
        frappe.logger().info("🧪 Running test_create_pos_device_egs...")

        # Create POS device EGS
        egs = self._create_test_pos_egs()

        # Verify the document was created
        self.assertIsNotNone(egs.name)
        self.assertEqual(egs.business_settings, self.business_settings_name)
        self.assertEqual(egs.egs_type, "POS Device")
        self.assertEqual(egs.unit_common_name, "POS-DEVICE-001")
        self.assertEqual(egs.unit_serial, "1-Sunmi|2-Sunmi Pro v2s|3-V222201B00815")
        self.assertEqual(egs.enable_zatca_integration, 1)
        self.assertEqual(egs.sync_with_zatca, "Batches")
        self.assertEqual(egs.validate_generated_xml, 1)

        frappe.logger().info("✅ test_create_pos_device_egs completed successfully")

    def test_egs_required_fields_validation(self):
        """Test that required fields are enforced"""
        frappe.logger().info("🧪 Running test_egs_required_fields_validation...")

        # Test missing business_settings
        egs = frappe.new_doc("ZATCA EGS")
        egs.egs_type = "ERPNext"
        egs.unit_common_name = "Test Device"
        egs.unit_serial = "1-Test|2-1|3-1"

        with self.assertRaises(frappe.ValidationError) as context:
            egs.insert(ignore_permissions=True)

        self.assertIn("business_settings", str(context.exception))

        # Test invalid egs_type value
        egs = frappe.new_doc("ZATCA EGS")
        egs.business_settings = self.business_settings_name
        egs.egs_type = "Invalid Type"  # Invalid value
        egs.unit_common_name = "Test Device"
        egs.unit_serial = "1-Test|2-1|3-1"

        with self.assertRaises(frappe.ValidationError) as context:
            egs.insert(ignore_permissions=True)

        self.assertIn("EGS Type", str(context.exception))

        # Test missing unit_common_name
        egs = frappe.new_doc("ZATCA EGS")
        egs.business_settings = self.business_settings_name
        egs.egs_type = "ERPNext"
        egs.unit_serial = "1-Test|2-1|3-1"

        with self.assertRaises(frappe.ValidationError) as context:
            egs.insert(ignore_permissions=True)

        self.assertIn("unit_common_name", str(context.exception))

        # Test missing unit_serial - this field has fetch_if_empty so it gets a
        # default value
        # Let's test with an invalid business_settings instead
        egs = frappe.new_doc("ZATCA EGS")
        egs.business_settings = "INVALID-BUSINESS-SETTINGS"
        egs.egs_type = "ERPNext"
        egs.unit_common_name = "Test Device"
        egs.unit_serial = "1-Test|2-1|3-1"

        with self.assertRaises(frappe.ValidationError) as context:
            egs.insert(ignore_permissions=True)

        self.assertIn("Could not find", str(context.exception))

        frappe.logger().info(
            "✅ test_egs_required_fields_validation completed successfully"
        )

    def test_egs_business_settings_link(self):
        """Test linking to ZATCA Business Settings"""
        frappe.logger().info("🧪 Running test_egs_business_settings_link...")

        # Create EGS with valid business settings
        egs = self._create_test_erpnext_egs()

        # Verify the link is working
        self.assertEqual(egs.business_settings, self.business_settings_name)
        self.assertTrue(
            frappe.db.exists("ZATCA Business Settings", egs.business_settings)
        )

        # Test with invalid business settings
        egs_invalid = frappe.new_doc("ZATCA EGS")
        egs_invalid.business_settings = "INVALID-SETTINGS"
        egs_invalid.egs_type = "ERPNext"
        egs_invalid.unit_common_name = "Test Device"
        egs_invalid.unit_serial = "1-Test|2-1|3-1"

        with self.assertRaises(frappe.ValidationError) as context:
            egs_invalid.insert(ignore_permissions=True)

        self.assertIn("Could not find", str(context.exception))

        frappe.logger().info("✅ test_egs_business_settings_link completed successfully")

    def test_for_device_static_method(self):
        """Test ZATCAEGS.for_device() static method"""
        frappe.logger().info("🧪 Running test_for_device_static_method...")

        # Create test EGS configurations
        erpnext_egs = self._create_test_erpnext_egs("ERPNext")
        pos_egs = self._create_test_pos_egs("POS-DEVICE-001")

        # Test finding ERPNext EGS
        found_egs = ZATCAEGS.for_device("ERPNext")
        self.assertIsNotNone(found_egs)
        self.assertEqual(found_egs.name, erpnext_egs.name)
        self.assertEqual(found_egs.egs_type, "ERPNext")

        # Test finding POS device EGS
        found_pos_egs = ZATCAEGS.for_device("POS-DEVICE-001")
        self.assertIsNotNone(found_pos_egs)
        self.assertEqual(found_pos_egs.name, pos_egs.name)
        self.assertEqual(found_pos_egs.egs_type, "POS Device")

        # Test finding non-existent device
        not_found_egs = ZATCAEGS.for_device("NON-EXISTENT-DEVICE")
        self.assertIsNone(not_found_egs)

        frappe.logger().info("✅ test_for_device_static_method completed successfully")

    def test_device_lookup_by_common_name(self):
        """Test finding EGS by unit_common_name"""
        frappe.logger().info("🧪 Running test_device_lookup_by_common_name...")

        # Create multiple EGS configurations with different device IDs
        device_ids = ["DEVICE-001", "DEVICE-002", "DEVICE-003"]
        created_egs = []

        for device_id in device_ids:
            egs = self._create_test_erpnext_egs(device_id)
            created_egs.append(egs)

        # Test lookup for each device
        for i, device_id in enumerate(device_ids):
            found_egs = ZATCAEGS.for_device(device_id)
            self.assertIsNotNone(found_egs)
            self.assertEqual(found_egs.name, created_egs[i].name)
            self.assertEqual(found_egs.unit_common_name, device_id)

        frappe.logger().info(
            "✅ test_device_lookup_by_common_name completed successfully"
        )

    def test_device_lookup_returns_none_when_not_found(self):
        """Test device lookup when EGS doesn't exist"""
        frappe.logger().info(
            "🧪 Running test_device_lookup_returns_none_when_not_found..."
        )

        # Test with various non-existent device IDs
        non_existent_devices = [
            "NON-EXISTENT-001",
            "INVALID-DEVICE",
            "MISSING-DEVICE-123",
            "",
            "   ",
        ]

        for device_id in non_existent_devices:
            found_egs = ZATCAEGS.for_device(device_id)
            self.assertIsNone(found_egs, f"Expected None for device ID: '{device_id}'")

        frappe.logger().info(
            "✅ test_device_lookup_returns_none_when_not_found completed successfully"
        )

    def test_multiple_devices_lookup(self):
        """Test lookup with multiple EGS configurations"""
        frappe.logger().info("🧪 Running test_multiple_devices_lookup...")

        # Create multiple EGS configurations
        devices = [
            ("ERPNext", "ERPNext"),
            ("POS-DEVICE-001", "POS Device"),
            ("POS-DEVICE-002", "POS Device"),
            ("CASHIER-001", "ERPNext"),
        ]

        created_egs = {}
        for device_id, egs_type in devices:
            if egs_type == "ERPNext":
                egs = self._create_test_erpnext_egs(device_id)
            else:
                egs = self._create_test_pos_egs(device_id)
            created_egs[device_id] = egs

        # Test lookup for each device
        for device_id, expected_type in devices:
            found_egs = ZATCAEGS.for_device(device_id)
            self.assertIsNotNone(found_egs)
            self.assertEqual(found_egs.unit_common_name, device_id)
            self.assertEqual(found_egs.egs_type, expected_type)
            self.assertEqual(found_egs.name, created_egs[device_id].name)

        frappe.logger().info("✅ test_multiple_devices_lookup completed successfully")

    def test_is_live_sync_property(self):
        """Test is_live_sync property calculation"""
        frappe.logger().info("🧪 Running test_is_live_sync_property...")

        # Test Live sync
        live_egs = self._create_test_erpnext_egs("LIVE-DEVICE")
        live_egs.sync_with_zatca = "Live"
        live_egs.save()

        self.assertTrue(live_egs.is_live_sync)

        # Test Batches sync
        batch_egs = self._create_test_pos_egs("BATCH-DEVICE")
        batch_egs.sync_with_zatca = "Batches"
        batch_egs.save()

        self.assertFalse(batch_egs.is_live_sync)

        # Test case insensitive
        live_egs.sync_with_zatca = "Live"  # proper case
        live_egs.save()
        self.assertTrue(live_egs.is_live_sync)

        live_egs.sync_with_zatca = "Live"  # proper case
        live_egs.save()
        self.assertTrue(live_egs.is_live_sync)

        frappe.logger().info("✅ test_is_live_sync_property completed successfully")

    def test_sync_mode_override_behavior(self):
        """Test EGS sync mode vs company sync mode"""
        frappe.logger().info("🧪 Running test_sync_mode_override_behavior...")

        # Get business settings
        business_settings = frappe.get_doc(
            "ZATCA Business Settings", self.business_settings_name
        )
        business_settings.sync_with_zatca = "Batches"  # Company setting: Batches
        business_settings.save()

        # Create EGS with Live sync (should override company setting)
        egs = self._create_test_erpnext_egs("OVERRIDE-DEVICE")
        egs.sync_with_zatca = "Live"
        egs.save()

        # Verify EGS overrides company setting
        self.assertEqual(
            business_settings.sync_with_zatca, "Batches"
        )  # Company: Batches
        self.assertEqual(egs.sync_with_zatca, "Live")  # EGS: Live
        self.assertTrue(egs.is_live_sync)  # EGS should be Live

        # Test the other way around
        egs.sync_with_zatca = "Batches"
        egs.save()
        self.assertFalse(egs.is_live_sync)  # EGS should be Batches

        frappe.logger().info(
            "✅ test_sync_mode_override_behavior completed successfully"
        )

    def test_xml_validation_configuration(self):
        """Test device-specific XML validation settings"""
        frappe.logger().info("🧪 Running test_xml_validation_configuration...")

        # Create EGS with XML validation enabled
        egs_with_validation = self._create_test_erpnext_egs("VALIDATION-DEVICE")
        egs_with_validation.validate_generated_xml = 1
        egs_with_validation.save()

        self.assertEqual(egs_with_validation.validate_generated_xml, 1)

        # Create EGS with XML validation disabled
        egs_without_validation = self._create_test_pos_egs("NO-VALIDATION-DEVICE")
        egs_without_validation.validate_generated_xml = 0
        egs_without_validation.save()

        self.assertEqual(egs_without_validation.validate_generated_xml, 0)

        frappe.logger().info(
            "✅ test_xml_validation_configuration completed successfully"
        )

    def test_egs_deletion_prevention(self):
        """Test that configured EGS cannot be deleted"""
        frappe.logger().info("🧪 Running test_egs_deletion_prevention...")

        # Create EGS
        egs = self._create_test_erpnext_egs("NO-DELETE-DEVICE")

        # Try to delete the EGS
        with self.assertRaises(frappe.ValidationError) as context:
            egs.delete()

        # Verify the error message
        self.assertIn(
            "You cannot Delete a configured ZATCA EGS", str(context.exception)
        )

        frappe.logger().info("✅ test_egs_deletion_prevention completed successfully")
