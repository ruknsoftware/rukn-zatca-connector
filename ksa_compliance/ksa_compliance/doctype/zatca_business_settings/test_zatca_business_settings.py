# Copyright (c) 2024, Lavaloon and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestZATCABusinessSettings(FrappeTestCase):
    def test_basic_setup(self):
        """Test basic ZATCA Business Settings setup"""
        # This is a simple test to verify the test framework is working
        self.assertTrue(True, "Basic test framework is working")
        
    def test_company_exists(self):
        """Test that the test company exists"""
        company_name = "RUKN"
        self.assertTrue(
            frappe.db.exists("Company", company_name),
            f"Test company {company_name} should exist"
        )
        
    def test_zatca_business_settings_exists(self):
        """Test that ZATCA Business Settings exists"""
        settings_name = "RUKN-Saudi Arabia-SAR"
        self.assertTrue(
            frappe.db.exists("ZATCA Business Settings", settings_name),
            f"ZATCA Business Settings {settings_name} should exist"
        )
        
    def test_zatca_business_settings_creation(self):
        """Test creating a new ZATCA Business Settings"""
        # Test creating a new settings document
        settings = frappe.get_doc({
            "doctype": "ZATCA Business Settings",
            "company": "RUKN",
            "currency": "SAR",
            "country": "Saudi Arabia",
            "seller_name": "Test Company",
            "vat_registration_number": "123456789012345",
            "enable_zatca_integration": 0,  # Disabled for testing
            "fatoora_server": "Sandbox",
        })
        
        # Test validation
        settings.validate()
        
        # Test that required fields are set
        self.assertEqual(settings.company, "RUKN")
        self.assertEqual(settings.currency, "SAR")
        self.assertEqual(settings.country, "Saudi Arabia")
