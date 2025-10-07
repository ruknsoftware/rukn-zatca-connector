"""
ZATCA Test Preparation Script

This script configures the system with the required settings before running ZATCA tests:
1. Disable rounded total
2. Configure SAR currency smallest fraction to 0.01
3. Set float precision to 2
4. Set currency precision to 2
5. Change rounding method to Banker's Rounding
6. Verify round tax amount row-wise is activated
"""
import logging

import frappe
from frappe import _


def prepare_system_for_zatca_tests():
    """
    Configure system settings required for ZATCA compliance testing
    """
    logging.info("Starting ZATCA test preparation...")

    # 1. Disable rounded total in Global Defaults
    disable_rounded_total()

    # 2. Configure SAR currency smallest fraction
    configure_sar_currency()

    # 3. Set float precision to 2
    set_float_precision()

    # 4. Set currency precision to 2
    set_currency_precision()

    # 5. Change rounding method to Banker's Rounding
    set_bankers_rounding()

    # 6. Verify round tax amount row-wise
    verify_round_tax_row_wise()

    logging.info("ZATCA test preparation completed successfully!")

    # Display current settings
    display_current_settings()


def disable_rounded_total():
    """Disable rounded total in Global Defaults"""
    try:
        global_defaults = frappe.get_doc("Global Defaults")
        global_defaults.disable_rounded_total = 1
        global_defaults.save()
        logging.info("✅ Disabled rounded total in Global Defaults")
    except Exception as e:
        logging.error(f"❌ Error disabling rounded total: {str(e)}")


def configure_sar_currency():
    """Configure SAR currency smallest fraction to 0.01"""
    try:
        # Check if SAR currency exists
        if frappe.db.exists("Currency", "SAR"):
            sar_currency = frappe.get_doc("Currency", "SAR")
            sar_currency.smallest_currency_fraction_value = 0.01
            sar_currency.fraction_units = 100
            sar_currency.fraction = "Halala"
            sar_currency.save()
            logging.info("✅ Configured SAR currency smallest fraction to 0.01")
        else:
            # Create SAR currency if it doesn't exist
            sar_currency = frappe.new_doc("Currency")
            sar_currency.currency_name = "SAR"
            sar_currency.enabled = 1
            sar_currency.smallest_currency_fraction_value = 0.01
            sar_currency.fraction_units = 100
            sar_currency.fraction = "Halala"
            sar_currency.symbol = "ر.س"
            sar_currency.number_format = "#,###.##"
            sar_currency.insert()
            logging.info("✅ Created and configured SAR currency with smallest fraction 0.01")
    except Exception as e:
        logging.error(f"❌ Error configuring SAR currency: {str(e)}")


def set_float_precision():
    """Set float precision to 2 in System Settings"""
    try:
        system_settings = frappe.get_doc("System Settings")
        system_settings.float_precision = "2"
        system_settings.save()
        logging.info("✅ Set float precision to 2")
    except Exception as e:
        logging.error(f"❌ Error setting float precision: {str(e)}")


def set_currency_precision():
    """Set currency precision to 2 in System Settings"""
    try:
        system_settings = frappe.get_doc("System Settings")
        system_settings.currency_precision = "2"
        system_settings.save()
        logging.info("✅ Set currency precision to 2")
    except Exception as e:
        logging.error(f"❌ Error setting currency precision: {str(e)}")


def set_bankers_rounding():
    """Change rounding method to Banker's Rounding"""
    try:
        system_settings = frappe.get_doc("System Settings")
        system_settings.rounding_method = "Banker's Rounding"
        system_settings.save()
        logging.info("✅ Set rounding method to Banker's Rounding")
    except Exception as e:
        logging.error(f"❌ Error setting rounding method: {str(e)}")


def verify_round_tax_row_wise():
    """Verify and activate round tax amount row-wise based on Frappe version"""
    try:
        # Get Frappe version
        frappe_version = frappe.get_version()
        major_version = int(frappe_version.split(".")[0])

        if major_version >= 15:
            # In v15+, this is a built-in feature in Account Settings
            activate_round_tax_row_wise_v15()
        else:
            # In v14, check if round_tax_amount_row_wise app is installed
            installed_apps = frappe.get_installed_apps()
            if "round_tax_amount_row_wise" in installed_apps:
                logging.info("✅ Round tax amount row-wise app is installed")

                # Check if the app is enabled
                app_info = frappe.get_doc(
                    "Installed Application", {"app_name": "round_tax_amount_row_wise"}
                )
                if app_info:
                    logging.info("✅ Round tax amount row-wise app is enabled")
                else:
                    logging.warning("⚠️  Round tax amount row-wise app is installed but may not be enabled")
            else:
                logging.warning("⚠️  Round tax amount row-wise app is not installed")
                logging.warning("   This feature requires the app in Frappe v14")
    except Exception as e:
        logging.error(f"❌ Error verifying round tax row-wise: {str(e)}")


def activate_round_tax_row_wise_v15():
    """Activate round tax amount row-wise in Frappe v15+ Account Settings"""
    try:
        # Check if Account Settings doctype exists
        if frappe.db.exists("DocType", "Account Settings"):
            # Get or create Account Settings
            if frappe.db.exists("Account Settings", "Account Settings"):
                account_settings = frappe.get_doc("Account Settings", "Account Settings")
            else:
                account_settings = frappe.new_doc("Account Settings")
                account_settings.name = "Account Settings"

            # Check if the field exists and activate it
            if hasattr(account_settings, "round_tax_amount_row_wise"):
                account_settings.round_tax_amount_row_wise = 1
                account_settings.save()
                logging.info("✅ Activated round tax amount row-wise in Account Settings (v15+)")
            else:
                logging.warning("⚠️  Round tax amount row-wise field not found in Account Settings")
                logging.warning("   This may indicate a different field name or missing feature")
        else:
            logging.warning("⚠️  Account Settings doctype not found")
            logging.warning("   This may indicate an older version or missing ERPNext module")
    except Exception as e:
        logging.error(f"❌ Error activating round tax row-wise in v15: {str(e)}")


def display_current_settings():
    """Display current system settings for verification"""
    logging.info("\n" + "=" * 50)
    logging.info("CURRENT SYSTEM SETTINGS:")
    logging.info("=" * 50)

    try:
        # Global Defaults
        global_defaults = frappe.get_doc("Global Defaults")
        logging.info(f"Disable Rounded Total: {global_defaults.disable_rounded_total}")

        # System Settings
        system_settings = frappe.get_doc("System Settings")
        logging.info(f"Float Precision: {system_settings.float_precision}")
        logging.info(f"Currency Precision: {system_settings.currency_precision}")
        logging.info(f"Rounding Method: {system_settings.rounding_method}")

        # SAR Currency
        if frappe.db.exists("Currency", "SAR"):
            sar_currency = frappe.get_doc("Currency", "SAR")
            logging.info(f"SAR Smallest Fraction: {sar_currency.smallest_currency_fraction_value}")
            logging.info(f"SAR Fraction Units: {sar_currency.fraction_units}")

        # Round tax row-wise status
        frappe_version = frappe.get_version()
        major_version = int(frappe_version.split(".")[0])

        if major_version >= 15:
            # Check Account Settings in v15+
            if frappe.db.exists("DocType", "Account Settings"):
                if frappe.db.exists("Account Settings", "Account Settings"):
                    account_settings = frappe.get_doc("Account Settings", "Account Settings")
                    if hasattr(account_settings, "round_tax_amount_row_wise"):
                        logging.info(
                            f"Round Tax Row-wise (v15+): {account_settings.round_tax_amount_row_wise}"
                        )
                    else:
                        logging.warning("Round Tax Row-wise (v15+): Field not found")
                else:
                    logging.warning("Round Tax Row-wise (v15+): Account Settings not configured")
            else:
                logging.warning("Round Tax Row-wise (v15+): Account Settings doctype not found")
        # Check app installation in v14
        installed_apps = frappe.get_installed_apps()
        logging.info(
            f"Round Tax Row-wise App Installed (v14): {'round_tax_amount_row_wise' in installed_apps}"
        )

    except Exception as e:
        logging.error(f"Error displaying settings: {str(e)}")

    logging.info("=" * 50)
