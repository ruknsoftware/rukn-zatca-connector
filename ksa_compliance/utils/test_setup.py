import frappe
from frappe.utils import now_datetime
from ksa_compliance.compliance_checks import perform_compliance_checks
from ksa_compliance.zatca_cli import setup as zatca_cli_setup

def setup_compliance_check_data(company_name, business_settings_id):

    tax_category_name = "ZATCA Test Tax Category"
    standard_customer_name = "standard ZATCA Customer"
    simplified_customer_name = "simplified ZATCA Customer"
    item_name = "ZATCA Test Item"
    tax_template_name = "VAT 15 %"

    for doctype, name in [
        ("Customer", standard_customer_name),
        ("Customer", simplified_customer_name),
        ("Item", item_name),
        ("Sales Taxes and Charges Template", tax_template_name),
        ("Tax Category", tax_category_name),
    ]:
        if frappe.db.exists(doctype, name):
            frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)


    frappe.get_doc({"doctype": "Tax Category", "title": tax_category_name}).insert(
        ignore_permissions=True
    )

    frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": standard_customer_name,
            "customer_type": "Company",
            "tax_id": "311609596400003",
            "custom_vat_registration_number": "311609596400003",
            "tax_category": tax_category_name,
        }
    ).insert(ignore_permissions=True)

    frappe.get_doc(
        {
            "doctype": "Customer",
            "customer_name": simplified_customer_name,
            "customer_type": "Individual",
        }
    ).insert(ignore_permissions=True)

    frappe.get_doc(
        {"doctype": "Item", "item_code": item_name, "item_group": "Products", "is_stock_item": 1}
    ).insert(ignore_permissions=True)

    tax_template = frappe.get_doc(
        {
            "doctype": "Sales Taxes and Charges Template",
            "title": tax_template_name,
            "is_default": 1,
            "company": company_name,
            "tax_category": tax_category_name,
            "taxes": [
                {
                    "charge_type": "On Net Total",
                    "account_head": f"Miscellaneous Expenses - {frappe.get_cached_value('Company', company_name, 'abbr')}",
                    "rate": 15,
                    "description": "Miscellaneous Expenses",
                }
            ],
        }
    )
    tax_template.insert(ignore_permissions=True)

    perform_compliance_checks(
        business_settings_id=business_settings_id,
        simplified_customer_id=simplified_customer_name,
        standard_customer_id=standard_customer_name,
        item_id=item_name,
        tax_category_id=tax_category_name,
    )


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
            }
        )
        settings.insert(ignore_permissions=True)

    db_settings = frappe.get_doc("ZATCA Business Settings", doc_name)
    id_values_to_set = {
        "CRN": "7034967856",
        "MLS": "2714887-1",
        "SAG": "102084407189825",
    }
    db_settings.update_additional_ids(id_values_to_set)

    if db_settings.cli_setup == "Automatic":
        zatca_cli_response = zatca_cli_setup('','')
        if zatca_cli_response:
            db_settings.zatca_cli_path = zatca_cli_response.get("cli_path")
            db_settings.java_home = zatca_cli_response.get("jre_path")
            db_settings.save(ignore_permissions=True)

    otp = "123456"

    if not db_settings.compliance_request_id:
        db_settings.onboard(otp=otp)

    db_settings.reload()

    if db_settings.compliance_request_id and not db_settings.production_request_id:
        db_settings.get_production_csid(otp=otp)

    return doc_name


def custom_erpnext_setup():
    frappe.clear_cache()
    from frappe.desk.page.setup_wizard.setup_wizard import setup_complete

    company_name = "RUKN"
    country = "Saudi Arabia"
    currency = "SAR"

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

    business_settings_id = setup_zatca_business_settings(company_name, country, currency)
    setup_compliance_check_data(company_name, business_settings_id)

    frappe.db.commit()
