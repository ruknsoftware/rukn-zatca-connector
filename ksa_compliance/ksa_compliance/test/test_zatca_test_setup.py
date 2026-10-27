# Copyright (c) 2024, LavaLoon and Contributors
# See license.txt

import frappe

from ksa_compliance.test.compat import IntegrationTestCase


class TestZATCATestSetup(IntegrationTestCase):
    """Test class for ZATCA test setup functionality"""

    def test_required_settings_are_configured(self):
        """Test that all required ZATCA settings are properly configured"""
        # Verify Global Defaults
        global_defaults = frappe.get_doc("Global Defaults")
        self.assertEqual(
            global_defaults.disable_rounded_total, 1, "Rounded total should be disabled"
        )

        # Verify System Settings
        system_settings = frappe.get_doc("System Settings")
        self.assertEqual(system_settings.float_precision, "2", "Float precision should be 2")
        self.assertEqual(system_settings.currency_precision, "2", "Currency precision should be 2")
        self.assertEqual(
            system_settings.rounding_method,
            "Banker's Rounding",
            "Rounding method should be Banker's Rounding",
        )

        # Verify SAR Currency
        if frappe.db.exists("Currency", "SAR"):
            sar_currency = frappe.get_doc("Currency", "SAR")
            self.assertEqual(
                sar_currency.smallest_currency_fraction_value,
                0.01,
                "SAR smallest fraction should be 0.01",
            )
            self.assertEqual(sar_currency.fraction_units, 100, "SAR fraction units should be 100")
            self.assertEqual(sar_currency.fraction, "Halala", "SAR fraction should be Halala")

        # Verify round tax row-wise based on version
        frappe_version = frappe.__version__
        major_version = int(frappe_version.split(".")[0])

        if major_version >= 15:
            # Check Accounts Settings in v15+
            round_row_wise_tax = frappe.db.get_single_value(
                "Accounts Settings", "round_row_wise_tax"
            )
            self.assertEqual(
                round_row_wise_tax, 1, "Round tax amount row-wise should be enabled in v15+"
            )
