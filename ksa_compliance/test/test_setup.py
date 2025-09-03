import frappe
from frappe.utils import now_datetime
from frappe import _
from ksa_compliance.zatca_cli import setup as zatca_cli_setup
from ksa_compliance.compliance_checks import _perform_compliance_checks

import re
import html

company_name =   "RUKN"
country = "Saudi Arabia"
currency = "SAR"

def custom_erpnext_setup():
    frappe.clear_cache()
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete


    if not frappe.db.exists("Company", company_name):
        current_year = now_datetime().year
        setup_complete(
            {
                "currency": currency,
                "company_name": company_name,
                "country": country,
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
            }
        )

    if frappe.db.exists("Country", "Saudi Arabia"):
        frappe.db.set_value("Country", "Saudi Arabia", "code", "SA")

    frappe.db.sql("delete from `tabItem Price`")


    setup_zatca_business_settings(company_name, country, currency)

    frappe.db.commit()

def runing_test():
    business_settings_id = setup_zatca_business_settings(company_name, country, currency)
    data = setup_compliance_check_data(company_name)
    frappe.db.commit()
    test_compliance_check_messages(business_settings_id=business_settings_id,**data)

def setup_compliance_check_data(company_name):
    tax_category_name = _create_tax_category()
    standard_customer_name = _create_standard_customer(tax_category_name)
    simplified_customer = _create_simplified_customer()
    item = _create_test_item()
    _create_tax_template(company_name, tax_category_name)
    _create_customer_address(standard_customer_name)
    _create_customer_address(simplified_customer)
    _update_customer_address(standard_customer_name)
    _update_customer_address(simplified_customer)

    return {
        "simplified_customer": simplified_customer,
        "standard_customer": standard_customer_name,
        "item": item,
        "tax_category": tax_category_name,
    }

def _update_customer_address(customer_name):
    customer = frappe.get_doc("Customer", customer_name)
    address_title = f"{customer_name} Address"
    address_name = f"{address_title}-Billing"

    address = frappe.get_doc("Address", address_name)
    customer.customer_primary_address = address
    customer.save(ignore_permissions=True)

def _create_tax_category():
    tax_category_name = "ZATCA Test Tax Category"

    frappe.get_doc({
        "doctype": "Tax Category",
        "title": tax_category_name
    }).insert(ignore_permissions=True)

    return tax_category_name

def _create_standard_customer(tax_category_name):

    standard_customer_name = "standard ZATCA Customer"

    frappe.get_doc({
        "doctype": "Customer",
        "customer_name": standard_customer_name,
        "customer_type": "Company",
        "tax_id": "311609596400003",
        "custom_vat_registration_number": "311609596400003",
        "tax_category": tax_category_name,
    }).insert(ignore_permissions=True)

    return standard_customer_name

def _create_simplified_customer():

    simplified_customer_name = "simplified ZATCA Customer"

    frappe.get_doc({
        "doctype": "Customer",
        "customer_name": simplified_customer_name,
        "customer_type": "Individual",
    }).insert(ignore_permissions=True)

    return simplified_customer_name

def _create_customer_address(customer_name):
    address_title = f"{customer_name} Address"

    frappe.get_doc({
        "doctype": "Address",
        "address_title": address_title,
        "address_type": "Billing",
        "address_line1": "الرياض",
        "address_line2": "طريق الملك فهد",
        "city": "الرياض",
        "pincode": "12344",
        "country": country,
        "custom_building_number": "1125",
        "custom_area": "العليا",
        "phone": "95233255",
        "is_primary_address": 1,
        "is_shipping_address": 1,
        "links": [
            {"link_doctype": "Customer", "link_name": customer_name}
        ],
    }).insert(ignore_permissions=True)


def _create_test_item():
    item_name = "ZATCA Test Item"

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

def setup_zatca_business_settings(company_name, country, currency):
    doc_name = f"{company_name}-{country}-{currency}"

    if not frappe.db.exists("ZATCA Business Settings", doc_name):
        address_title = "السلمانية الأمير عبد العزيز بن مساعد بن جلوي"
        address_name = f"{address_title}-Billing"

        if not frappe.db.exists("Address", address_name):
            address = frappe.get_doc(
                {
                    "doctype": "Address",
                    "address_title": address_title,
                    "address_type": "Billing",
                    "address_line1": "الرياض",
                    "address_line2": "طريق الملك فهد",
                    "city": "الرياض",
                    "pincode": "12344",
                    "country": country,
                    "custom_building_number": "1125",
                    "custom_area": "العليا",
                    "phone": "95233255",
                    "is_primary_address": 1,
                    "is_shipping_address": 1,
                    "links": [{"link_doctype": "Company", "link_name": company_name}],
                }
            )
            address.insert(ignore_permissions=True)

        item_code = "Advance Payment"
        if not frappe.db.exists("Item", item_code):
            frappe.get_doc(
                {
                    "doctype": "Item",
                    "item_code": item_code,
                    "item_name": item_code,
                    "item_group": "Services",
                    "is_stock_item": 0,
                }
            ).insert(ignore_permissions=True)

        settings = frappe.get_doc(
            {
                "doctype": "ZATCA Business Settings",
                "company": company_name,
                "company_address": address_name,
                "currency": currency,
                "country": country,
                "company_unit": "السلمانية الأمير عبد العزيز بن مساعد بن جلوي",
                "seller_name": "شركة الاعمال المبدعه المحدودة",
                "vat_registration_number": "399999999900003",
                "company_unit_serial": "1-ERPNext|2-15|3-2",
                "company_category": "اااااfdf",
                "enable_zatca_integration": 1,
                "sync_with_zatca": "Live",
                "type_of_business_transactions": "Let the system decide (both)",
                "advance_payment_item": item_code,
                "cli_setup": "Automatic",
                "validate_generated_xml": 1,
                "block_invoice_on_invalid_xml": 1,
                "fatoora_server": "Sandbox",
                "other_ids": [
                    {"type_name": "Commercial Registration Number", "type_code": "CRN" , "value": "7034967856"},
                    {"type_name": "MOMRAH License", "type_code": "MOM"},
                    {"type_name": "MHRSD License", "type_code": "MLS", "value": "2714887-1"},
                    {"type_name": "700 Number", "type_code": "700"},
                    {"type_name": "MISA License", "type_code": "SAG", "value": "102084407189825"},
                    {"type_name": "Other ID", "type_code": "OTH"},
                ],
            }
        )
        settings.insert(ignore_permissions=True)

    b_settings = frappe.get_doc("ZATCA Business Settings", doc_name)

    if b_settings.cli_setup == "Automatic":
        zatca_cli_response = zatca_cli_setup('','')
        if zatca_cli_response:
            b_settings.zatca_cli_path = zatca_cli_response.get("cli_path")
            b_settings.java_home = zatca_cli_response.get("jre_path")
            b_settings.save(ignore_permissions=True)

    otp = "123456"

    if not b_settings.compliance_request_id:
        b_settings.onboard(otp=otp)

    b_settings.reload()

    if b_settings.compliance_request_id and not b_settings.production_request_id:
        b_settings.get_production_csid(otp=otp)

    return doc_name

def test_compliance_check_messages(business_settings_id,simplified_customer,standard_customer,item,tax_category):
    business_settings_id = business_settings_id
    simplified_customer = simplified_customer
    standard_customer = standard_customer
    item = item
    tax_category = tax_category

    frappe.clear_messages()

    _perform_compliance_checks(
        business_settings_id=business_settings_id,
        simplified_customer_id=simplified_customer,
        standard_customer_id=standard_customer,
        item_id=item,
        tax_category_id=tax_category,
    )

    messages = frappe.get_message_log()

    print(_("\n--- Compliance Check Results (from test case) ---"))
    if messages:
        for msg in messages:
            title = msg.get("title")
            message_content = msg.get("message")
            if title:
                print(_(f"\nTitle: {title}\n"))
            if message_content:
                formatted = format_message(message_content)
                print(_(formatted))
            print(_("-" * 30))
    else:
        print(_("No messages were generated."))
    print(_("--- End of test printout ---\n"))



def format_message(msg_html):
    text = html.unescape(msg_html)

    text = re.sub(r'<li>(.*?)</li>', r'  - \1', text, flags=re.DOTALL)

    text = re.sub(r'<p>(.*?)</p>', r'\n\1\n', text, flags=re.DOTALL)

    text = re.sub(r'<strong>(.*?)</strong>', r'\n\1\n', text, flags=re.DOTALL)

    text = re.sub(r'<.*?>', '', text)

    return text.strip()
