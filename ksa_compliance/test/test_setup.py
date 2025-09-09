import frappe
from frappe.utils import now_datetime
from frappe import _
from ksa_compliance.zatca_cli import setup as zatca_cli_setup
from ksa_compliance.compliance_checks import _perform_compliance_checks


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

    return {
        "simplified_customer": simplified_customer,
        "standard_customer": standard_customer_name,
        "item": item,
        "tax_category": tax_category_name,
    }

def _update_customer_address(customer_name, address):
    customer = frappe.get_doc("Customer", customer_name)
    customer.customer_primary_address = address.name
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

    address = frappe.get_doc({
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

    return address

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

def run_test_case_without_addresses(business_settings_id, simplified_customer, standard_customer, item, tax_category, success_status):
    print(_("\n🔍 Test Case 1: Without Customer Addresses"))

    simplified_result, standard_result = _perform_compliance_checks(
        business_settings_id=business_settings_id,
        simplified_customer_id=simplified_customer,
        standard_customer_id=standard_customer,
        item_id=item,
        tax_category_id=tax_category,
    )

    if standard_result and standard_result.invoice_result:
        assert standard_result.invoice_result != success_status, "Test Case 1: Standard invoice should fail without address"

    print(_("\n ✅✅✅ Test Case 1 completed: Validation failed as expected (no addresses) ✅✅✅\n"))


def run_test_case_with_addresses(business_settings_id, simplified_customer, standard_customer, item, tax_category, success_status):
    print(_("\n🔍 Test Case 2: With Customer Addresses"))

    standard_address = _create_customer_address(standard_customer)
    simplified_address = _create_customer_address(simplified_customer)
    _update_customer_address(standard_customer, standard_address)
    _update_customer_address(simplified_customer, simplified_address)
    frappe.db.commit()

    simplified_result, standard_result = _perform_compliance_checks(
        business_settings_id=business_settings_id,
        simplified_customer_id=simplified_customer,
        standard_customer_id=standard_customer,
        item_id=item,
        tax_category_id=tax_category,
    )

    if simplified_result:
        print(_("\n📝 Simplified Invoice Results:"))
        print(_(f"Invoice Status: {simplified_result.invoice_result}"))
        print(_(f"Credit Note Status: {simplified_result.credit_note_result}"))
        print(_(f"Debit Note Status: {simplified_result.debit_note_result}"))

        assert simplified_result.invoice_result == success_status, "Simplified invoice validation failed"
        assert simplified_result.credit_note_result == success_status, "Simplified credit note validation failed"
        assert simplified_result.debit_note_result == success_status, "Simplified debit note validation failed"

    if standard_result:
        print(_("\n📝 Standard Invoice Results:"))
        print(_(f"Invoice Status: {standard_result.invoice_result}"))
        print(_(f"Credit Note Status: {standard_result.credit_note_result}"))
        print(_(f"Debit Note Status: {standard_result.debit_note_result}"))

        assert standard_result.invoice_result == success_status, "Standard invoice validation failed"
        assert standard_result.credit_note_result == success_status, "Standard credit note validation failed"
        assert standard_result.debit_note_result == success_status, "Standard debit note validation failed"

    print(_("\n✅✅✅ Test Case 2 completed: All validations passed with addresses ✅✅✅"))


def test_compliance_check_messages(business_settings_id, simplified_customer, standard_customer, item, tax_category):
    frappe.flags.in_test = True
    success_status = "Invoice sent to ZATCA. Integration status: Accepted"

    print(_("\n=== ZATCA Compliance Test Suite ==="))

    run_test_case_without_addresses(
        business_settings_id, simplified_customer, standard_customer, item, tax_category, success_status
    )

    run_test_case_with_addresses(
        business_settings_id, simplified_customer, standard_customer, item, tax_category, success_status
    )

    print(_("\n=== ZATCA Compliance Test Suite Completed Successfully ==="))
