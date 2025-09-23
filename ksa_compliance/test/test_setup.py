import frappe
from frappe.utils import now_datetime
from frappe import _
from ksa_compliance.compliance_checks import _perform_compliance_checks
from ksa_compliance.ksa_compliance.doctype.zatca_business_settings.test_zatca_business_settings import setup_zatca_business_settings
from ksa_compliance.test.test_constants import TEST_COMPANY_NAME, SAUDI_COUNTRY, SAUDI_CURRENCY, TEST_TAX_CATEGORY_NAME, TEST_STANDARD_CUSTOMER_NAME, TEST_SIMPLIFIED_CUSTOMER_NAME

def custom_erpnext_setup():
    frappe.clear_cache()
    from erpnext.setup.setup_wizard.setup_wizard import setup_complete


    if not frappe.db.exists("Company", TEST_COMPANY_NAME):
        current_year = now_datetime().year
        setup_complete(
            frappe._dict({
                "currency": SAUDI_CURRENCY,
                "company_name": TEST_COMPANY_NAME,
                "country": SAUDI_COUNTRY,
                "full_name": "Test User",
                "timezone": "Asia/Riyadh",
                "company_abbr": "RUKN",
                "industry": "Manufacturing",
                "fy_start_date": f"{current_year}-01-01",
                "fy_end_date": f"{current_year}-12-31",
                "language": "english",
                "company_tagline": "ZATCA Testing",
                "email": "test@example.com",
                "password": "test",
                "chart_of_accounts": "Standard",
            })
        )

    if frappe.db.exists("Country", SAUDI_COUNTRY):
        frappe.db.set_value("Country", SAUDI_COUNTRY, "code", "SA")

    # Add Arabic name and Tax ID to company for Saudi Arabia compliance
    if frappe.db.exists("Company", TEST_COMPANY_NAME):
        frappe.db.set_value("Company", TEST_COMPANY_NAME, "company_name_in_arabic", "شركة ركن للاختبار")
        frappe.db.set_value("Company", TEST_COMPANY_NAME, "tax_id", "399999999900003")

    frappe.db.sql("delete from `tabItem Price`")
    
    # Create Gender records for test data
    _create_gender_records()
    
    # Create currency exchange rate for USD-SAR to avoid E-Commerce validation errors
    if not frappe.db.exists("Currency Exchange", {"from_currency": "USD", "to_currency": "SAR"}):
        frappe.get_doc({
            "doctype": "Currency Exchange",
            "from_currency": "USD",
            "to_currency": "SAR",
            "exchange_rate": 3.75,  # Approximate SAR to USD rate
            "date": now_datetime().date()
        }).insert(ignore_permissions=True)


    setup_zatca_business_settings(TEST_COMPANY_NAME, SAUDI_COUNTRY, SAUDI_CURRENCY)

    frappe.db.commit()

def data_setup():
    setup_zatca_business_settings(TEST_COMPANY_NAME, SAUDI_COUNTRY, SAUDI_CURRENCY)
    setup_compliance_check_data(TEST_COMPANY_NAME)
    frappe.db.commit()

def setup_compliance_check_data(company_name):
    tax_category_name = _create_tax_category()
    standard_customer_name = _create_standard_customer(tax_category_name)
    simplified_customer = _create_simplified_customer()
    item = _create_test_item()
    _create_tax_template(company_name, tax_category_name)

    return {
        "simplified_customer": simplified_customer,
        "standard_customer": standard_customer_name,
        "item": item,
        "tax_category": tax_category_name,
    }


def _create_tax_category():
    if not frappe.db.exists("Tax Category", TEST_TAX_CATEGORY_NAME):
        frappe.get_doc({
            "doctype": "Tax Category",
            "title": TEST_TAX_CATEGORY_NAME
        }).insert(ignore_permissions=True)

    return TEST_TAX_CATEGORY_NAME

def _create_standard_customer(tax_category_name):

    if not frappe.db.exists("Customer", TEST_STANDARD_CUSTOMER_NAME):
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": TEST_STANDARD_CUSTOMER_NAME,
            "customer_type": "Company",
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
            "tax_id": "311609596400003",
            "custom_vat_registration_number": "311609596400003",
            "tax_category": tax_category_name,
        }).insert(ignore_permissions=True)

    return TEST_STANDARD_CUSTOMER_NAME

def _create_simplified_customer():

    if not frappe.db.exists("Customer", TEST_SIMPLIFIED_CUSTOMER_NAME):
        frappe.get_doc({
            "doctype": "Customer",
            "customer_name": TEST_SIMPLIFIED_CUSTOMER_NAME,
            "customer_type": "Individual",
            "customer_group": "All Customer Groups",
            "territory": "All Territories",
        }).insert(ignore_permissions=True)

    return TEST_SIMPLIFIED_CUSTOMER_NAME


def _create_test_item():
    item_name = "ZATCA Test Item"

    if not frappe.db.exists("Item", item_name):
        frappe.get_doc({
            "doctype": "Item",
            "item_code": item_name,
            "item_group": "Products",
            "is_stock_item": 1
        }).insert(ignore_permissions=True)

    return item_name

def _create_tax_template(company_name, tax_category_name):

    tax_template_name = "VAT 15 %"
    company_abbr = frappe.get_cached_value('Company', company_name, 'abbr')
    full_template_name = f"{tax_template_name} - {company_abbr}"

    if not frappe.db.exists("Sales Taxes and Charges Template", full_template_name):
        tax_template = frappe.get_doc({
            "doctype": "Sales Taxes and Charges Template",
            "title": tax_template_name,
            "is_default": 1,
            "company": company_name,
            "tax_category": tax_category_name,
            "taxes": [{
                "charge_type": "On Net Total",
                "account_head": f"Miscellaneous Expenses - {company_abbr}",
                "rate": 15,
                "description": "Miscellaneous Expenses",
            }],
        })
        tax_template.insert(ignore_permissions=True)

    return tax_template_name

def _create_gender_records():
    """Create Gender records for test data"""
    default_genders = [
        "Male",
        "Female",
    ]
    
    for gender in default_genders:
        if not frappe.db.exists("Gender", gender):
            frappe.get_doc({
                "doctype": "Gender",
                "gender": gender
            }).insert(ignore_permissions=True, ignore_if_duplicate=True)